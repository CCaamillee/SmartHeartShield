from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Callable

from agent.config import (
    AgentSettings,
    get_agent_settings,
    get_knowledge_timeout_seconds,
)
from agent.tools import COHORT_SCOPE_ID, execute_tool


KNOWLEDGE_MODEL = (
    os.getenv("BAILIAN_KNOWLEDGE_MODEL", "").strip() or "deepseek-v4-flash"
)


SYSTEM_PROMPT = """
You are the SmartHeartShield clinical ReAct assistant. Always respond to the user in clear, concise English and follow this loop:

Reason: understand the question internally and identify missing information; never expose hidden reasoning.
Act: call one or more of the four provided tools.
Observation: review tool results and determine whether the evidence is sufficient.
Repeat or Final: continue the loop when evidence is insufficient; otherwise provide the final answer.

Tool boundaries:
1. get_patient_timeline reads the real, timestamped timeline for the current encounter.
2. extract_clinical_features reads structured features, supporting evidence, counterevidence, and data gaps.
3. calculate_risk calls the local cardiac-rupture model and independently returns rupture prediction within 14 days, current acuity, and key evidence using de-identified facts before the prediction cutoff.
4. knowledge_search is used only when a specific medical term or mechanism cannot otherwise be explained; submit a clear, standalone medical-knowledge query.

Requirements:
1. Call the relevant tools before answering patient-specific questions; do not rely only on the user's description or general knowledge.
2. Patient facts may come only from get_patient_timeline or extract_clinical_features. calculate_risk returns a prediction, not an observed fact.
3. knowledge_search returns model-generated general knowledge, not patient facts or literature-search results.
4. For cardiac-rupture prediction, current acuity, or other specialty predictions, call extract_clinical_features first and calculate_risk second. Never substitute your own prediction.
5. Preserve missing, unknown, unmatched, conflicting, or erroneous information as uncertainty.
6. Do not expose hidden reasoning or invent patient facts. Patient and encounter identifiers are not sent to the model.
7. Do not prescribe drug doses or make surgical decisions. Identify specific information that needs attention or supplementation.
8. Within one turn for one encounter, call each patient-record tool and calculate_risk at most once; reuse valid observations.
9. Treat calculate_risk <answer> as the final prediction output. Preserve its two judgments and key evidence, translating labels into natural English. Keep <think> only in the collapsible analysis trace.
10. Write the final answer for clinicians: concise conclusion, key evidence, and specific concerns. Do not include development notes, generic disclaimers, internal plans, or meta-commentary.
11. Ordinary missing data, uncertainty, counterevidence, alternative causes, differential diagnoses, and evidence conflicts do not justify knowledge_search. Call it at most once per turn.
12. Decide tool use from the question and observations, not fixed keywords. Use native API function calls and never print Reason, Act, <function_calls>, <invoke>, or tool-call code in content.
""".strip()


KNOWLEDGE_SYSTEM_PROMPT = """
You explain medical knowledge in concise English. Provide only general medical information and do not infer a specific patient's diagnosis, risk, or treatment. State uncertainty when evidence is disputed, guideline-dependent, or insufficient. Do not invent citations, guideline names, study data, probabilities, or thresholds. If no external literature search was performed, say that this is a model-generated knowledge summary rather than a literature-search result. Identify what a clinician should verify.
""".strip()


def _patient_parameter() -> dict[str, Any]:
    return {
        "type": "string",
        "description": "The encounter selected in the interface; the system always enforces the actual scope.",
    }


REACT_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_patient_timeline",
            "description": "Read the real timestamped clinical timeline and structured events for the current encounter.",
            "parameters": {
                "type": "object",
                "properties": {"patient_id": _patient_parameter()},
                "required": ["patient_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_clinical_features",
            "description": "Read structured fields, field sources, and data gaps for the current encounter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": _patient_parameter(),
                    "focus": {
                        "type": "string",
                        "description": "The clinical issue to extract or review.",
                    },
                },
                "required": ["patient_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_risk",
            "description": (
                "Call the cardiac-rupture model to independently assess rupture within the next 14 days "
                "and whether the patient was critical or currently stable at the prediction cutoff. "
                "Use this for questions about cardiac-rupture prediction or current acuity."
            ),
            "parameters": {
                "type": "object",
                "properties": {"patient_id": _patient_parameter()},
                "required": ["patient_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "knowledge_search",
            "description": (
                "Use only when a specific medical term, mechanism, or concept cannot be explained. "
                "Missing data, prediction uncertainty, counterevidence, and differential diagnosis do not qualify. "
                "Generate a standalone query without patient identifiers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A clear, standalone medical question without patient identifiers.",
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
]


def _tool_call_payload(call: Any) -> dict[str, Any]:
    if hasattr(call, "model_dump"):
        return call.model_dump(exclude_none=True)
    return {
        "id": call.id,
        "type": "function",
        "function": {
            "name": call.function.name,
            "arguments": call.function.arguments,
        },
    }


def _parse_arguments(raw_arguments: Any) -> dict[str, Any]:
    if isinstance(raw_arguments, dict):
        return dict(raw_arguments)
    try:
        parsed = json.loads(str(raw_arguments or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _sanitize_tool_result_for_model(value: Any) -> Any:
    """Remove stable patient/encounter identifiers before a tool result reaches a model."""
    blocked = {
        "patient_id",
        "regno",
        "admno",
        "encounter_key",
        "endpoint",
        "failed_endpoints",
        "model",
    }
    if isinstance(value, dict):
        return {
            key: _sanitize_tool_result_for_model(item)
            for key, item in value.items()
            if str(key).lower() not in blocked
        }
    if isinstance(value, list):
        return [_sanitize_tool_result_for_model(item) for item in value]
    return value


AgentEventCallback = Callable[[dict[str, Any]], None]


def _emit(callback: AgentEventCallback | None, event: dict[str, Any]) -> None:
    if callback is None:
        return
    try:
        callback(event)
    except Exception:
        # Rendering failures must not interrupt clinical tool execution.
        return


def _requires_timeline(question: str) -> bool:
    normalized = str(question or "")
    return any(term in normalized for term in ("时间轴", "时间线", "病程变化", "如何变化"))


def _requires_risk_prediction(question: str) -> bool:
    """Backward-compatible intent hint kept for callers and focused tests.

    The Agent no longer uses this keyword check to force a tool call; the model
    decides whether risk calculation is needed from the full conversation.
    """
    normalized = str(question or "").lower()
    return any(
        term in normalized
        for term in (
            "风险",
            "破裂",
            "预测",
            "危急",
            "risk",
            "rupture",
        )
    )


def _question_analysis_summary(
    question: str,
    observations: list[dict[str, Any]],
) -> tuple[str, str]:
    completed_tools = {
        item.get("tool")
        for item in observations
        if not item.get("result", {}).get("error")
    }
    if "calculate_risk" in completed_tools:
        return (
            "Review Prediction Result",
            "The specialty prediction is available; reviewing the conclusion, key evidence, and relevant data gaps.",
        )
    if "extract_clinical_features" in completed_tools:
        return (
            "Determine the Next Step",
            "Clinical records are organized; determining whether the timeline, specialty prediction, or medical knowledge is still needed.",
        )
    if "get_patient_timeline" in completed_tools:
        return (
            "Determine the Next Step",
            "The clinical timeline has been reviewed; determining whether the available records are sufficient.",
        )
    if _requires_timeline(question):
        return (
            "Clarify the Question",
            "This request requires the clinical course and examination changes, so the reliable timeline will be reviewed first.",
        )
    normalized = str(question or "")
    if any(term in normalized for term in ("资料", "缺口", "质量", "对齐")):
        return (
            "Clarify the Question",
            "This request requires review of record completeness, field sources, and temporal alignment.",
        )
    return (
        "Clarify the Question",
        "Identifying whether the question concerns patient facts, clinical changes, specialty prediction, or medical knowledge.",
    )


def _final_step_title(question: str, has_risk_prediction: bool) -> str:
    if has_risk_prediction:
        return "Prepare the Prediction Result"
    normalized = str(question or "")
    if any(term in normalized for term in ("资料", "缺口", "质量", "对齐")):
        return "Summarize Record Availability"
    if _requires_timeline(question) or any(
        term in normalized for term in ("症状", "生命体征", "循环", "检验", "影像")
    ):
        return "Summarize Clinical Changes"
    return "Prepare the Answer"


def _final_step_summary(
    question: str,
    has_risk_prediction: bool,
    observations: list[dict[str, Any]],
) -> str:
    if has_risk_prediction:
        risk_result = next(
            (
                item.get("result", {})
                for item in observations
                if item.get("tool") == "calculate_risk"
                and not item.get("result", {}).get("error")
            ),
            {},
        )
        prediction = risk_result.get("prediction") or {}
        fields = prediction.get("fields") or {}
        rupture = str(fields.get("rupture_judgment") or "").strip()
        urgency = str(fields.get("current_urgency") or "").strip()
        if rupture and urgency:
            return f"The model returned rupture={rupture} and current acuity={urgency}; organizing the key evidence."
        label = str(fields.get("rupture_label") or "").strip()
        conclusion = {"1": "cardiac rupture predicted", "0": "cardiac rupture not predicted"}.get(
            label,
            "specialty model result available",
        )
        return f"The result is: {conclusion}; organizing the key evidence."
    if _requires_timeline(question):
        return "The encounter timeline has been reviewed; organizing the clinical course and examination changes."
    if any(term in str(question or "") for term in ("资料", "缺口", "质量", "对齐")):
        return "The encounter records have been reviewed; organizing field sources and data gaps."
    return "The required records have been reviewed; preparing the answer."


def _contains_textual_tool_call(content: str) -> bool:
    """Reject tool protocol text that should have arrived as a native tool call."""
    normalized = str(content or "").lower()
    return any(
        marker in normalized
        for marker in (
            "<function_calls",
            "</function_calls",
            "<invoke ",
            "</invoke>",
        )
    )


def _observation_summary(tool_name: str, result: dict[str, Any]) -> str:
    if result.get("error"):
        return f"Tool call failed: {result['error']}"
    if tool_name == "get_patient_timeline":
        return f"Reviewed {result.get('event_count', 0)} timestamped timeline events."
    if tool_name == "extract_clinical_features":
        if result.get("scope") == COHORT_SCOPE_ID:
            cohort = result.get("cohort_features", {})
            return f"Reviewed {cohort.get('patient_count', 0)} structured cohort records."
        evidence = result.get("features", {})
        return (
            f"Reviewed {len(evidence.get('supporting', []))} supporting items, "
            f"{len(evidence.get('counter', []))} counterevidence items, and "
            f"{len(evidence.get('missing', []))} data gaps."
        )
    if tool_name == "calculate_risk":
        prediction = result.get("prediction", {})
        answer = " ".join(str(prediction.get("answer") or "").split())
        if len(answer) > 110:
            answer = answer[:110] + "…"
        return "The cardiac rupture model completed this prediction" + (f": {answer}" if answer else ".")
    if tool_name == "knowledge_search":
        return (
            f"{result.get('model', KNOWLEDGE_MODEL)} returned a general medical knowledge summary. "
            "This is not a patient fact or literature-search result."
        )
    return "The tool returned an observation."


def _error_response(message: str, trace: list[dict[str, str]] | None = None) -> dict[str, Any]:
    return {
        "content": f"The ReAct analysis could not be completed: {message}",
        "sources": [],
        "simulated": False,
        "mode": "react-unavailable",
        "model": "unavailable",
        "trace": trace or [],
        "react_steps": [],
        "reasoning": {"duration_seconds": 0, "trace": trace or [], "risk_runs": []},
        "task_drafts": [],
        "validation": {"status": "not-completed", "problems": [message]},
    }


class ClinicalReActAgent:
    """A single Reason → Act → Observation loop backed by structured tool calls."""

    def __init__(
        self,
        settings: AgentSettings | None = None,
        client: Any | None = None,
        knowledge_model: str | None = None,
        risk_predictor: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        self.settings = settings or get_agent_settings()
        self.knowledge_model = (knowledge_model or KNOWLEDGE_MODEL).strip()
        self._client = client
        self._knowledge_client: Any | None = None
        self._risk_predictor = risk_predictor

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        from openai import OpenAI

        self._client = OpenAI(
            api_key=self.settings.api_key,
            base_url=self.settings.base_url,
            timeout=self.settings.timeout_seconds,
            max_retries=1,
        )
        return self._client

    def _query_medical_knowledge(self, query: str) -> dict[str, Any]:
        normalized_query = str(query or "").strip()
        normalized_query = re.sub(
            r"\b(?:regno|admno)\s*[:：=]?\s*[^\s，。；]+",
            "current encounter",
            normalized_query,
            flags=re.I,
        )[:1000]
        if not normalized_query:
            return {"error": "knowledge_search requires a valid query", "sources": []}

        try:
            if self._client is not None:
                knowledge_client = self._client
            else:
                if self._knowledge_client is None:
                    from openai import OpenAI

                    self._knowledge_client = OpenAI(
                        api_key=self.settings.api_key,
                        base_url=self.settings.base_url,
                        timeout=get_knowledge_timeout_seconds(),
                        max_retries=0,
                    )
                knowledge_client = self._knowledge_client
            completion = knowledge_client.chat.completions.create(
                model=self.knowledge_model,
                messages=[
                    {"role": "system", "content": KNOWLEDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": normalized_query},
                ],
                temperature=0.1,
                extra_body={"enable_thinking": False},
            )
            answer = (completion.choices[0].message.content or "").strip()
        except Exception as exc:
            return {
                "error": f"The medical knowledge model call failed: {type(exc).__name__}",
                "query": normalized_query,
                "sources": [],
            }

        if not answer:
            return {
                "error": "The medical knowledge model returned no valid content",
                "query": normalized_query,
                "sources": [],
            }
        source = f"Alibaba Bailian model / {self.knowledge_model}"
        return {
            "query": normalized_query,
            "answer": answer,
            "model": self.knowledge_model,
            "knowledge_type": "model_generated_general_medical_knowledge",
            "patient_fact": False,
            "literature_search_performed": False,
            "notice": "This is a model-generated general medical knowledge summary, not a literature-search result or patient fact.",
            "sources": [source],
        }

    def _act(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        scope_id: str,
        event_callback: AgentEventCallback | None = None,
    ) -> dict[str, Any]:
        if tool_name == "knowledge_search":
            return self._query_medical_knowledge(str(arguments.get("query", "")))
        if tool_name == "calculate_risk":
            if self._risk_predictor is None:
                from agent.risk_model import predict_patient_risk

                predictor = predict_patient_risk
            else:
                predictor = self._risk_predictor
            return predictor(scope_id, callback=event_callback)
        if tool_name in {"get_patient_timeline", "extract_clinical_features"}:
            clean_arguments = dict(arguments)
            clean_arguments["patient_id"] = scope_id
            return execute_tool(tool_name, clean_arguments, scope_id)
        return {"error": f"Unknown or disabled tool: {tool_name}", "sources": []}

    def _stream_final_answer(
        self,
        client: Any,
        messages: list[dict[str, Any]],
        callback: AgentEventCallback | None,
        has_risk_prediction: bool,
    ) -> str:
        if has_risk_prediction:
            final_instruction = (
                "Tool review is complete. Answer the clinician directly in English using only the observations above. "
                "Do not output internal plans, <think>, Reason, Act, Observation, tool names, or meta-commentary.\n"
                "Rupture prediction: translate 是 as Yes, 否 as No, and 证据不足 as Insufficient Evidence.\n"
                "Current acuity: translate 危急 as Critical and 暂时稳定 as Currently Stable; never infer this from the rupture prediction.\n"
                "Key evidence: faithfully summarize the tool's key evidence in one to three sentences.\n"
                "Attention: only when information is missing or the conclusion has a material limitation, identify the specific information to review in one sentence.\n"
                "Preserve calculate_risk's two independent judgments. Do not reverse them or invent probabilities, confidence levels, or time windows. "
                "Do not expose program fields such as rupture_label or add generic disclaimers."
            )
        else:
            final_instruction = (
                "Tool review is complete. Answer the clinician directly in concise English using only the observations above. "
                "Do not output internal plans, <think>, Reason, Act, Observation, tool names, data-processing details, meta-commentary, "
                "generic disclaimers, or an invitation to ask another question. If records are insufficient, identify only the specific missing information."
            )
        response = client.chat.completions.create(
            model=self.settings.model,
            messages=[
                *messages,
                {
                    "role": "user",
                    "content": final_instruction,
                },
            ],
            temperature=0.1,
            stream=True,
            extra_body={"enable_thinking": False},
        )

        # Test doubles and a few compatible gateways may ignore stream=True.
        if hasattr(response, "choices"):
            content = str(response.choices[0].message.content or "").strip()
            if content:
                _emit(callback, {"type": "final_delta", "delta": content})
            return content

        chunks: list[str] = []
        for chunk in response:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            content = getattr(delta, "content", "") if delta is not None else ""
            if not content:
                continue
            text = str(content)
            chunks.append(text)
            _emit(callback, {"type": "final_delta", "delta": text})
        return "".join(chunks).strip()

    def run(
        self,
        scope_id: str,
        question: str,
        history: list[dict[str, Any]] | None = None,
        event_callback: AgentEventCallback | None = None,
    ) -> dict[str, Any]:
        normalized_question = str(question or "").strip()
        if not normalized_question:
            return _error_response("The question is empty")
        if not self.settings.is_configured:
            return _error_response("The Bailian API key is not configured, so the reasoning step cannot run")

        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for item in (history or [])[-8:]:
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content[:6000]})

        scope_description = (
            "all valid encounters in the uploaded workbook"
            if scope_id == COHORT_SCOPE_ID
            else "the encounter currently selected in the interface (patient and encounter identifiers are not sent to the model)"
        )
        messages.append(
            {
                "role": "user",
                "content": f"Current scope: {scope_description}\nUser question: {normalized_question}\nRespond in English.",
            }
        )

        trace: list[dict[str, str]] = []
        react_steps: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        sources: set[str] = set()
        started_at = time.monotonic()

        try:
            client = self._get_client()

            def finalize(
                iteration: int,
            ) -> dict[str, Any]:
                has_risk_prediction = any(
                    item["tool"] == "calculate_risk"
                    and item.get("result", {}).get("prediction")
                    for item in observations
                )
                final_title = _final_step_title(
                    normalized_question,
                    has_risk_prediction,
                )
                final_summary = _final_step_summary(
                    normalized_question,
                    has_risk_prediction,
                    observations,
                )
                react_steps.append(
                    {
                        "phase": "Final",
                        "iteration": iteration,
                        "title": final_title,
                        "summary": final_summary,
                    }
                )
                _emit(
                    event_callback,
                    {
                        "type": "phase",
                        "phase": "Final",
                        "iteration": iteration,
                        "title": final_title,
                        "detail": final_summary,
                    },
                )

                # The no-tool response is only the planner's decision to stop.
                # Always synthesize a separate physician-facing answer so that
                # planning notes never leak into the chat output.
                final_answer = self._stream_final_answer(
                    client,
                    messages,
                    event_callback,
                    has_risk_prediction,
                )
                if not final_answer:
                    return _error_response("The model returned no final answer", trace)

                duration_seconds = round(time.monotonic() - started_at, 2)
                risk_runs = [
                    item["result"]
                    for item in observations
                    if item["tool"] == "calculate_risk"
                    and item.get("result", {}).get("prediction")
                ]
                result_payload = {
                    "content": final_answer,
                    "sources": sorted(source for source in sources if source),
                    "simulated": False,
                    "mode": "bailian-react",
                    "model": self.settings.model,
                    "knowledge_model": self.knowledge_model,
                    "trace": trace,
                    "react_steps": react_steps,
                    "reasoning": {
                        "duration_seconds": duration_seconds,
                        "trace": trace,
                        "risk_runs": risk_runs,
                    },
                    "task_drafts": [],
                    "validation": {
                        "status": "completed-after-observation",
                        "observation_count": len(observations),
                        "problems": [],
                    },
                }
                _emit(
                    event_callback,
                    {
                        "type": "complete",
                        "duration_seconds": duration_seconds,
                        "trace": trace,
                    },
                )
                return result_payload

            for iteration in range(1, self.settings.max_iterations + 1):
                reason_title, reason_detail = _question_analysis_summary(
                    normalized_question,
                    observations,
                )
                _emit(
                    event_callback,
                    {
                        "type": "phase",
                        "phase": "Reason",
                        "iteration": iteration,
                        "title": reason_title,
                        "detail": reason_detail,
                    },
                )
                react_steps.append(
                    {
                        "phase": "Reason",
                        "iteration": iteration,
                        "title": reason_title,
                        "summary": reason_detail,
                    }
                )
                completion = client.chat.completions.create(
                    model=self.settings.model,
                    messages=messages,
                    tools=REACT_TOOL_SCHEMAS,
                    tool_choice="auto",
                    temperature=0.1,
                    extra_body={"enable_thinking": False},
                )
                assistant = completion.choices[0].message
                tool_calls = assistant.tool_calls or []

                if not tool_calls:
                    assistant_content = str(assistant.content or "").strip()
                    if _contains_textual_tool_call(assistant_content):
                        messages.append(
                            {"role": "assistant", "content": assistant_content}
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    "You wrote the tool protocol in the response body. Reassess the next step: "
                                    "use native API function calls when a tool is needed; otherwise provide the final answer directly in English "
                                    "without Reason, Act, or XML."
                                ),
                            }
                        )
                        continue
                    if not assistant_content:
                        messages.append(
                            {"role": "assistant", "content": ""}
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    "Use the question and existing observations to decide whether to call another required tool "
                                    "or provide the final answer directly in English."
                                ),
                            }
                        )
                        continue
                    return finalize(iteration)

                messages.append(
                    {
                        "role": "assistant",
                        "content": assistant.content or "",
                        "tool_calls": [_tool_call_payload(call) for call in tool_calls],
                    }
                )

                ordered_calls = sorted(
                    tool_calls,
                    key=lambda call: {
                        "extract_clinical_features": 0,
                        "get_patient_timeline": 1,
                        "calculate_risk": 2,
                        "knowledge_search": 3,
                    }.get(str(call.function.name), 4),
                )
                for call in ordered_calls:
                    tool_name = str(call.function.name)
                    arguments = _parse_arguments(call.function.arguments)
                    cached_result = next(
                        (
                            item["result"]
                            for item in observations
                            if item["tool"] == tool_name
                            and (
                                tool_name == "knowledge_search"
                                or not item.get("result", {}).get("error")
                            )
                        ),
                        None,
                    )
                    if cached_result is not None:
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": call.id,
                                "content": json.dumps(
                                    _sanitize_tool_result_for_model(cached_result),
                                    ensure_ascii=False,
                                    default=str,
                                ),
                            }
                        )
                        continue
                    react_steps.append(
                        {
                            "phase": "Act",
                            "iteration": iteration,
                            "tool": tool_name,
                        }
                    )
                    _emit(
                        event_callback,
                        {
                            "type": "phase",
                            "phase": "Act",
                            "iteration": iteration,
                            "tool": tool_name,
                            "title": "Review Required Records",
                            "detail": {
                                "extract_clinical_features": "Organizing structured clinical records, field sources, and data gaps for this encounter.",
                                "get_patient_timeline": "Reviewing the clinical timeline and structured events for this encounter.",
                                "calculate_risk": "Calling the cardiac rupture prediction model and reviewing its result.",
                                "knowledge_search": "Reviewing a medical concept that could not be explained directly.",
                            }.get(tool_name, "Reviewing relevant records."),
                        },
                    )
                    result = self._act(
                        tool_name,
                        arguments,
                        scope_id,
                        event_callback=event_callback,
                    )
                    observations.append({"tool": tool_name, "result": result})
                    sources.update(result.get("sources", []))
                    summary = _observation_summary(tool_name, result)
                    status = "error" if result.get("error") else "success"
                    trace.append(
                        {
                            "tool": tool_name,
                            "status": status,
                            "observation": summary,
                        }
                    )
                    _emit(
                        event_callback,
                        {
                            "type": "phase",
                            "phase": "Observation",
                            "iteration": iteration,
                            "tool": tool_name,
                            "status": status,
                            "label": summary,
                        },
                    )
                    react_steps.append(
                        {
                            "phase": "Observation",
                            "iteration": iteration,
                            "tool": tool_name,
                            "status": status,
                            "summary": summary,
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": json.dumps(
                                _sanitize_tool_result_for_model(result),
                                ensure_ascii=False,
                                default=str,
                            ),
                        }
                    )

            return _error_response(
                f"The maximum of {self.settings.max_iterations} ReAct iterations was reached without a final answer",
                trace,
            )
        except Exception as exc:
            return _error_response(f"ReAct call failed: {type(exc).__name__}", trace)
