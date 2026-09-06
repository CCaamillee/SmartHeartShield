from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from components.cards import render_profile_strip, risk_badge
from components.header import render_header
from components.i18n import display_value, ui_text
from components.react_chat import (
    TOOL_LABELS,
    inject_react_chat_styles,
    partial_model_answer,
    partial_model_thinking,
    restored_timeline_steps,
    source_strip_html,
    timeline_html,
)
from components.patient_navigation import (
    consume_pending_encounter_key,
    normalize_encounter_key,
)
from components.records import render_record_cards
from agent.react_agent import ClinicalReActAgent
from services.chat_store import (
    append_chat_message,
    clear_chat_feed,
    clear_encounter_chat,
    load_chat_feed,
    load_encounter_chat,
)
from services.prediction_api import (
    get_prediction_for_encounter,
    normalize_live_prediction,
)
from services.react_data import get_encounter_dataframe, get_encounter_detail


SUGGESTIONS = {
    "Review Diagnoses & Key Records": "Review the diagnoses and key clinical records that can be confirmed for this encounter.",
    "Summarize Examinations & Labs": "Summarize the available examinations and laboratory tests, and identify any items that cannot be reliably matched.",
    "Show the Clinical Timeline": "List the structured clinical timeline for this encounter.",
    "Run Cardiac Rupture Prediction": "Run the cardiac rupture prediction model, assess rupture within the next 14 days and current acuity, and list the key evidence.",
}

AGENT_PANEL_HEIGHT = 720
AGENT_CHAT_FEED_HEIGHT = 480


def _clear_filters() -> None:
    for key in (
        "agent_query",
        "agent_age",
        "agent_gender",
        "agent_admission_dates",
        "agent_diagnosis",
        "agent_department",
        "agent_surgery",
    ):
        st.session_state.pop(key, None)


def _filter_frame(frame: pd.DataFrame, values: dict) -> pd.DataFrame:
    filtered = frame.copy()
    query = str(values.get("query") or "").strip().lower()
    if query:
        filtered = filtered.loc[
            filtered["regno"].str.lower().str.contains(query, regex=False)
            | filtered["admno"].str.lower().str.contains(query, regex=False)
        ]
    age_range = values["age"]
    filtered = filtered.loc[
        filtered["age"].isna()
        | filtered["age"].between(age_range[0], age_range[1], inclusive="both")
    ]
    if values["gender"]:
        filtered = filtered.loc[filtered["gender"].isin(values["gender"])]
    if values["department"]:
        filtered = filtered.loc[filtered["department"].isin(values["department"])]
    for field, column in (("diagnosis", "diagnosis"), ("surgery", "surgery")):
        text = str(values.get(field) or "").strip().lower()
        if text:
            translated = filtered[column].fillna("").astype(str).map(display_value).str.lower()
            filtered = filtered.loc[
                filtered[column].str.lower().str.contains(text, regex=False)
                | translated.str.contains(text, regex=False)
            ]
    selected_dates = values.get("admission_dates")
    if selected_dates:
        dates = list(selected_dates) if isinstance(selected_dates, (tuple, list)) else [selected_dates]
        start = pd.Timestamp(dates[0])
        end = pd.Timestamp(dates[-1]) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
        parsed = pd.to_datetime(filtered["admission_datetime"], errors="coerce")
        filtered = filtered.loc[parsed.between(start, end, inclusive="both")]
    return filtered.reset_index(drop=True)


def _render_filter_panel(frame: pd.DataFrame) -> pd.DataFrame:
    ages = frame["age"].dropna().astype(int)
    min_age = int(ages.min()) if not ages.empty else 0
    max_age = int(ages.max()) if not ages.empty else 120
    genders = sorted(
        (value for value in frame["gender"].unique() if value != "暂无记录"),
        key=display_value,
    )
    departments = sorted(
        (value for value in frame["department"].unique() if value != "暂无记录"),
        key=display_value,
    )

    with st.form("agent_filter_form", border=False):
        query = st.text_input(
            "Find a patient by ID",
            placeholder="Enter regno or admno",
            key="agent_query",
        )
        with st.expander(
            "More patient filters",
            icon=":material/tune:",
        ):
            age_range = st.slider(
                "Age range",
                min_age,
                max_age,
                (min_age, max_age),
                key="agent_age",
            )
            gender = st.multiselect(
                "Sex",
                genders,
                key="agent_gender",
                placeholder="All sexes",
                format_func=ui_text,
            )
            admission_dates: tuple[date, ...] | date | list[date] = st.date_input(
                "Admission / encounter date",
                value=(),
                key="agent_admission_dates",
            )
            diagnosis = st.text_input(
                "Diagnosis",
                placeholder="Enter a diagnosis keyword",
                key="agent_diagnosis",
            )
            department = st.multiselect(
                "Department",
                departments,
                key="agent_department",
                placeholder="All departments",
                format_func=display_value,
            )
            surgery = st.text_input(
                "Procedure or intervention",
                placeholder="Enter a procedure keyword",
                key="agent_surgery",
            )
        with st.container(horizontal=True, horizontal_alignment="right"):
            st.form_submit_button(
                "Clear",
                icon=":material/restart_alt:",
                on_click=_clear_filters,
            )
            st.form_submit_button(
                "Apply filters",
                type="primary",
                icon=":material/search:",
            )

    st.caption("Search directly by identifier, or combine age, sex, date, diagnosis, department, and procedure filters.")
    return _filter_frame(
        frame,
        {
            "query": query,
            "age": age_range,
            "gender": gender,
            "admission_dates": admission_dates,
            "diagnosis": diagnosis,
            "department": department,
            "surgery": surgery,
        },
    )


def _encounter_label(key: str, encounter_map: dict[str, dict]) -> str:
    item = encounter_map[key]
    diagnosis = display_value(item["diagnosis"])
    if len(diagnosis) > 34:
        diagnosis = diagnosis[:34] + "…"
    age = f"{int(item['age'])} years" if pd.notna(item.get("age")) else "Age unavailable"
    return f"{item['regno']} | {ui_text(item['cohort_group'])} | {age} | {diagnosis}"


def _ordered_encounter_keys(
    encounter_map: dict[str, dict],
) -> list[str]:
    """Keep real rupture-cohort database samples first for ReAct testing."""
    return sorted(
        encounter_map,
        key=lambda encounter_key: (
            -int(encounter_map[encounter_key].get("cohort_label") or 0),
            encounter_key,
        ),
    )


def _encounter_history(encounter_key: str) -> list[dict]:
    encounter_key = normalize_encounter_key(encounter_key)
    if not encounter_key:
        return []
    histories = st.session_state.setdefault("chat_history", {})
    if encounter_key not in histories:
        histories[encounter_key] = load_encounter_chat(encounter_key)
    return histories[encounter_key]


def _chat_transcript() -> list[dict]:
    if "agent_chat_transcript" not in st.session_state:
        st.session_state["agent_chat_transcript"] = load_chat_feed()
    return st.session_state["agent_chat_transcript"]


def _submit_question(encounter_key: str, question: str) -> None:
    encounter_key = normalize_encounter_key(encounter_key)
    question = str(question or "").strip()
    if not encounter_key or not question:
        return
    pending = st.session_state.setdefault("pending_agent_questions", {})
    if encounter_key in pending:
        return
    history = _encounter_history(encounter_key)
    prior = list(history)
    message = {"role": "user", "content": question}
    history.append(message)
    append_chat_message(encounter_key, message)
    _chat_transcript().append({**message, "encounter_key": encounter_key})
    pending[encounter_key] = {"question": question, "history": prior}


def _clear_history(encounter_key: str) -> None:
    encounter_key = normalize_encounter_key(encounter_key)
    if not encounter_key:
        return
    st.session_state.setdefault("chat_history", {})[encounter_key] = []
    st.session_state.setdefault("pending_agent_questions", {}).pop(encounter_key, None)
    clear_encounter_chat(encounter_key)
    transcript = _chat_transcript()
    transcript[:] = [
        message
        for message in transcript
        if normalize_encounter_key(message.get("encounter_key")) != encounter_key
    ]


def _clear_chat_transcript() -> None:
    """Clear the visible transcript only after the user clicks the clear action."""
    clear_chat_feed()
    st.session_state["chat_history"] = {}
    st.session_state["agent_chat_transcript"] = []
    st.session_state["pending_agent_questions"] = {}


def _run_pending_question(encounter_key: str) -> None:
    encounter_key = normalize_encounter_key(encounter_key)
    if not encounter_key:
        return
    pending_map = st.session_state.setdefault("pending_agent_questions", {})
    pending = pending_map.pop(encounter_key, None)
    if not pending:
        return

    history = _encounter_history(encounter_key)
    question = str(pending.get("question") or "").strip()
    prior_history = list(pending.get("history") or [])
    steps: list[dict] = []
    step_indexes: dict[tuple[object, ...], int] = {}
    risk_output = ""
    streamed_thinking = ""
    final_output = ""

    with st.chat_message("assistant", avatar=":material/clinical_notes:"):
        status_box = st.status("Analyzing the current question…", expanded=True)
        with status_box:
            process_slot = st.empty()
        final_slot = st.empty()

        def update_step(
            key: tuple[object, ...],
            title: str,
            *,
            detail: str | None = None,
            thinking: str | None = None,
            answer: str | None = None,
            fields: dict | None = None,
            status: str | None = None,
        ) -> None:
            if key not in step_indexes:
                step_indexes[key] = len(steps)
                steps.append({"title": title})
            step = steps[step_indexes[key]]
            step["title"] = title
            if detail is not None:
                step["detail"] = detail
            if thinking is not None:
                step["thinking"] = thinking
            if answer is not None:
                step["answer"] = answer
            if fields is not None:
                step["fields"] = fields
            if status is not None:
                step["status"] = status
            process_slot.markdown(timeline_html(steps), unsafe_allow_html=True)

        def tool_step_key(tool: str) -> tuple[object, ...]:
            return next(
                (key for key in reversed(step_indexes) if key[-1:] == (tool,)),
                ("tool", 0, tool),
            )

        def on_event(event: dict) -> None:
            nonlocal risk_output, streamed_thinking, final_output
            event_type = str(event.get("type") or "")
            if event_type == "phase":
                phase = str(event.get("phase") or "")
                iteration = event.get("iteration", 0)
                tool = str(event.get("tool") or "")
                if phase == "Reason":
                    update_step(
                        ("Reason", iteration),
                        str(event.get("title") or "Clarify the Question"),
                        detail=str(event.get("detail") or "Determining which records are needed."),
                    )
                elif phase == "Act":
                    update_step(
                        ("tool", iteration, tool),
                        TOOL_LABELS.get(tool, "Review Relevant Records"),
                        detail=str(event.get("detail") or "Reading and reviewing the relevant records."),
                    )
                elif phase == "Observation":
                    update_step(
                        ("tool", iteration, tool),
                        TOOL_LABELS.get(tool, "Review Relevant Records"),
                        detail=str(event.get("label") or "The required records have been retrieved."),
                        status=str(event.get("status") or "success"),
                    )
                elif phase == "Final":
                    update_step(
                        ("Final",),
                        str(event.get("title") or "Prepare the Answer"),
                        detail=str(event.get("detail") or "Organizing the available information."),
                    )
            elif event_type == "risk_retry":
                update_step(
                    tool_step_key("calculate_risk"),
                    TOOL_LABELS["calculate_risk"],
                    detail="The prediction service did not respond; trying a fallback endpoint.",
                )
            elif event_type == "risk_think_delta":
                streamed_thinking += str(event.get("delta") or "")
                update_step(
                    tool_step_key("calculate_risk"),
                    TOOL_LABELS["calculate_risk"],
                    thinking=streamed_thinking.strip(),
                )
            elif event_type == "risk_delta":
                risk_output += str(event.get("delta") or "")
                thinking = partial_model_thinking(risk_output)
                answer = partial_model_answer(risk_output)
                if (thinking and not streamed_thinking) or answer:
                    update_step(
                        tool_step_key("calculate_risk"),
                        TOOL_LABELS["calculate_risk"],
                        thinking=thinking if not streamed_thinking else None,
                        answer=answer or None,
                    )
            elif event_type == "risk_complete":
                thinking = str(event.get("thinking") or "").strip()
                answer = str(event.get("answer") or "").strip()
                fields = event.get("fields") if isinstance(event.get("fields"), dict) else {}
                if thinking or answer:
                    update_step(
                        tool_step_key("calculate_risk"),
                        TOOL_LABELS["calculate_risk"],
                        thinking=thinking or None,
                        answer=answer or None,
                        fields=fields,
                    )
            elif event_type == "final_delta":
                final_output += str(event.get("delta") or "")
                if final_output.strip():
                    final_slot.markdown(final_output + " ▌")

        try:
            response = ClinicalReActAgent().run(
                encounter_key,
                question,
                history=prior_history,
                event_callback=on_event,
            )
        except Exception as exc:
            response = {
                "content": f"The clinical assistant could not complete this request: {type(exc).__name__}",
                "sources": [],
                "trace": [],
                "mode": "react-unavailable",
                "reasoning": {"duration_seconds": 0, "trace": [], "risk_runs": []},
            }

        duration = float(response.get("reasoning", {}).get("duration_seconds") or 0)
        failed = response.get("mode") == "react-unavailable"
        status_box.update(
            label=(
                f"Analysis interrupted ({duration:.1f}s)"
                if failed
                else f"Analysis complete ({duration:.1f}s)"
            ),
            state="error" if failed else "complete",
            expanded=False,
        )
        final_slot.markdown(display_value(response.get("content") or "No answer is available to display."))

    risk_runs = response.get("reasoning", {}).get("risk_runs", [])
    if risk_runs:
        st.session_state.setdefault("latest_model_predictions", {})[
            encounter_key
        ] = risk_runs[-1]
    message = {"role": "assistant", **response}
    history.append(message)
    append_chat_message(encounter_key, message)
    _chat_transcript().append({**message, "encounter_key": encounter_key})


def _render_reasoning(message: dict) -> None:
    steps = restored_timeline_steps(message)
    if not steps:
        return
    duration = float((message.get("reasoning") or {}).get("duration_seconds") or 0)
    with st.expander(f"Analysis complete ({duration:.1f}s)", expanded=False):
        st.markdown(timeline_html(steps), unsafe_allow_html=True)


def _render_message(message: dict) -> None:
    role = str(message.get("role") or "assistant")
    avatar = ":material/clinical_notes:" if role == "assistant" else None
    with st.chat_message(role, avatar=avatar):
        message_encounter = normalize_encounter_key(message.get("encounter_key"))
        if message_encounter:
            st.caption(f"Patient and encounter: {message_encounter.replace('::', ' | ', 1)}")
        if role == "assistant":
            _render_reasoning(message)
        st.markdown(display_value(message.get("content") or "No answer available"))
        if role == "assistant":
            source_html = source_strip_html(message.get("sources") or [])
            if source_html:
                st.markdown(source_html, unsafe_allow_html=True)


def _scroll_to_latest_question() -> None:
    st.html(
        """
        <script>
        (() => {
          const positionLatestQuestion = () => {
            const root = document.querySelector('.st-key-agent_chat_feed');
            const anchor = root?.querySelector('[data-latest-question="true"]');
            if (!root || !anchor) return;
            const candidates = [root, ...root.querySelectorAll('*')];
            const scroller = candidates.find((element) => {
              const overflowY = getComputedStyle(element).overflowY;
              return (overflowY === 'auto' || overflowY === 'scroll') &&
                element.scrollHeight > element.clientHeight;
            }) || root;
            const offset = anchor.getBoundingClientRect().top -
              scroller.getBoundingClientRect().top + scroller.scrollTop;
            scroller.scrollTo({top: Math.max(0, offset - 8), behavior: 'instant'});
          };
          requestAnimationFrame(() => requestAnimationFrame(positionLatestQuestion));
        })();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def _render_chat(encounter_key: str, profile: dict) -> None:
    inject_react_chat_styles()
    transcript = _chat_transcript()
    with st.container(
        horizontal=True,
        horizontal_alignment="distribute",
        vertical_alignment="center",
    ):
        st.subheader(":material/clinical_notes: Clinical Assistant History")
        if transcript:
            st.button(
                "Clear conversation",
                icon=":material/delete_sweep:",
                key="clear_agent_chat_transcript",
                on_click=_clear_chat_transcript,
                help="Delete the full conversation history shown in the right panel. The history is retained until this action is used.",
            )
    st.caption(
        f"Current encounter: {display_value(profile['regno'])} | {display_value(profile['admno'])}."
    )
    _encounter_history(encounter_key)
    with st.container(
        height=AGENT_CHAT_FEED_HEIGHT,
        key="agent_chat_feed",
        gap="small",
    ):
        if not transcript:
            with st.container(key="agent_empty_prompt", height="stretch", gap="small"):
                st.html(
                    """
                    <div class="agent-empty-state">
                      <span class="agent-empty-icon" aria-hidden="true">AI</span>
                      <strong>What would you like to review?</strong>
                      <span>Choose a common question below or enter your own at the bottom.</span>
                    </div>
                    """
                )
                suggestion_columns = st.columns(2, gap="small")
                for index, (label, suggestion) in enumerate(SUGGESTIONS.items()):
                    if suggestion_columns[index % 2].button(
                        label,
                        icon=":material/arrow_outward:",
                        width="stretch",
                        key=f"agent_suggestion_{index}_{encounter_key}",
                    ):
                        _submit_question(encounter_key, suggestion)
                        st.rerun()
        else:
            latest_user_index = next(
                (
                    index
                    for index in range(len(transcript) - 1, -1, -1)
                    if transcript[index].get("role") == "user"
                ),
                None,
            )
            for index, message in enumerate(transcript):
                if latest_user_index is not None and index == latest_user_index:
                    st.html(
                        '<span class="agent-question-scroll-anchor" '
                        'data-latest-question="true"></span>'
                    )
                _render_message(message)

        if encounter_key in st.session_state.setdefault(
            "pending_agent_questions", {}
        ):
            _run_pending_question(encounter_key)
        if transcript:
            _scroll_to_latest_question()

    question = st.chat_input(
        "Enter a question for clinical review…",
        key=f"agent_chat_input_{encounter_key}",
        submit_mode="disable",
    )
    if question:
        _submit_question(encounter_key, question)
        st.rerun()


def render() -> None:
    with st.container(key="clinical_agent_page", gap="small"):
        render_header(
            "Clinical Assistant",
            "Select a patient and review one encounter with an agent that organizes diagnoses, examinations, tests, treatments, and the clinical timeline.",
            eyebrow=None,
        )

        try:
            with st.skeleton(height=120):
                frame = get_encounter_dataframe()
        except (FileNotFoundError, ImportError, ValueError) as error:
            st.error(
                f"The ReAct patient samples could not be loaded: {display_value(error)}",
                icon=":material/error:",
            )
            return
        if frame.empty:
            st.info("The patient database contains no valid samples to display.", icon=":material/inbox:")
            return

        pending = consume_pending_encounter_key()
        if pending in set(frame["encounter_key"]):
            st.session_state.selected_encounter_key = pending
            st.session_state.agent_encounter_selector = pending

        patient_col, chat_col = st.columns(
            [0.95, 2.05],
            gap="medium",
            vertical_alignment="top",
        )
        with patient_col:
            with st.container(
                border=True,
                height=AGENT_PANEL_HEIGHT,
                key="agent_patient_panel",
            ):
                st.subheader(":material/person_search: Patient & Encounter")
                st.caption("Find a record by ID or combine additional filters.")
                filtered = _render_filter_panel(frame)
                if filtered.empty:
                    st.warning(
                        "No encounters match the current filters. Adjust the search criteria.",
                        icon=":material/search_off:",
                    )
                    return

                encounter_map = {
                    row["encounter_key"]: row.to_dict()
                    for _, row in filtered.iterrows()
                }
                options = _ordered_encounter_keys(encounter_map)
                selected_state = normalize_encounter_key(
                    st.session_state.get("selected_encounter_key")
                )
                if selected_state not in encounter_map:
                    selected_state = options[0]
                if st.session_state.get("agent_encounter_selector") not in encounter_map:
                    st.session_state.agent_encounter_selector = selected_state
                selected = st.selectbox(
                    "Current patient and encounter",
                    options,
                    format_func=lambda value: _encounter_label(value, encounter_map),
                    key="agent_encounter_selector",
                    persist_state="session",
                )
                st.session_state.selected_encounter_key = selected
                st.caption(
                    f"{len(filtered)} database samples after filtering. "
                    "Both rupture and non-rupture cohorts come from patient_data.db."
                )

                detail = get_encounter_detail(selected)
                profile = detail["profile"]
                st.subheader(":material/id_card: Current Patient")
                render_profile_strip(profile)
                st.caption("This is a ReAct database sample. Expand the section below to view structured records.")

                with st.expander(
                    "View structured patient records",
                    icon=":material/folder_open:",
                ):
                    record_group = st.selectbox(
                        "Record group",
                        ["Overview", "Diagnoses", "Examinations & Labs", "Treatment & Course", "Risk Information"],
                        key=f"agent_record_group_{selected}",
                    )
                    if record_group == "Overview":
                        render_record_cards(detail["basic"])
                    elif record_group == "Diagnoses":
                        render_record_cards(
                            detail["groups"]["诊断信息"],
                            "No diagnosis records are available.",
                        )
                    elif record_group == "Examinations & Labs":
                        render_record_cards(
                            detail["groups"]["检查与检验"],
                            "No examination or laboratory records are available.",
                        )
                    elif record_group == "Treatment & Course":
                        treatment = [
                            *detail["groups"]["用药与医嘱"],
                            *detail["groups"]["手术信息"],
                            *detail["groups"]["病程记录"],
                        ]
                        render_record_cards(treatment, "No treatment or clinical course records are available.")
                    else:
                        live_result = st.session_state.get(
                            "latest_model_predictions", {}
                        ).get(selected) or get_prediction_for_encounter(selected)
                        normalized = normalize_live_prediction(live_result or {})
                        if normalized["available"]:
                            st.markdown(
                                f"<div class='risk-legend'><strong>Model Prediction</strong>"
                                f"{risk_badge(normalized['risk_level'])}"
                                f"<span>Rupture prediction: {ui_text(normalized['rupture_judgment'])} | "
                                f"Current acuity: {ui_text(normalized['current_urgency'] or '模型未提供')}</span></div>",
                                unsafe_allow_html=True,
                            )
                            if normalized["core_evidence"]:
                                st.caption(display_value(normalized["core_evidence"]))
                        else:
                            st.markdown(
                                f"<div class='risk-legend'><strong>Risk Status</strong>"
                                f"{risk_badge(profile['risk_level'])}"
                                "<span>No valid prediction result is available for this encounter.</span></div>",
                                unsafe_allow_html=True,
                            )
                        render_record_cards(detail["risk"])

        with chat_col:
            with st.container(
                border=True,
                height=AGENT_PANEL_HEIGHT,
                key="agent_chat_panel",
            ):
                _render_chat(selected, profile)
