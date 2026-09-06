from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

import pandas as pd

from agent.config import (
    context_compression_enabled,
    get_agent_settings,
    get_context_model,
    get_context_timeout_seconds,
)
from services.data_api import (
    _clean_text,
    _format_number,
    _single_number,
    get_patient_detail,
    get_patients,
)
from services.database import (
    connect_readonly,
    database_signature,
    get_database_path,
    quote_identifier,
    resolve_display_id,
)


REACT_SAMPLE_LIMIT = 1000
SOURCE_NAME = "patient_data.db (ReAct read-only sample)"


def _compress_untimed_evidence(
    evidence: list[dict[str, str]],
    client: Any | None = None,
) -> tuple[str | None, str]:
    """Compress grounded ReAct facts with the configured Bailian context model."""
    if not evidence:
        return None, "not_required"
    settings = get_agent_settings()
    if not context_compression_enabled() or not settings.is_configured:
        return None, "deterministic_fallback"
    if client is None:
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=get_context_timeout_seconds(),
            max_retries=0,
        )
    payload = {
        "facts": evidence,
        "required_output": {
            "text": "压缩去重后的临床事实",
            "evidence_ids": ["使用的事实ID"],
        },
    }
    try:
        response = client.chat.completions.create(
            model=get_context_model(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是临床记录压缩器，只能压缩、合并和去重输入事实。"
                        "不得增加诊断、症状、数值、时间、因果、风险或未来结局。"
                        "输入事实缺少可靠事件时间，输出不得补充或推断时间窗。"
                        "只输出JSON对象，字段只能是text和evidence_ids。"
                    ),
                },
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0,
            max_tokens=1800,
            extra_body={"enable_thinking": False},
        )
        raw = str(response.choices[0].message.content or "").strip()
        start, end = raw.find("{"), raw.rfind("}")
        parsed = json.loads(raw[start : end + 1]) if 0 <= start < end else None
    except Exception:
        return None, "compression_failed"
    if not isinstance(parsed, dict):
        return None, "validation_failed"
    text = str(parsed.get("text") or "").strip()
    evidence_ids = parsed.get("evidence_ids") or []
    source_by_id = {item["evidence_id"]: item["text"] for item in evidence}
    if (
        not text
        or not isinstance(evidence_ids, list)
        or not evidence_ids
        or any(str(item) not in source_by_id for item in evidence_ids)
    ):
        return None, "validation_failed"
    cited = " ".join(source_by_id[str(item)] for item in evidence_ids)
    source_numbers = set(re.findall(r"\d+(?:\.\d+)?", cited))
    output_numbers = set(re.findall(r"\d+(?:\.\d+)?", text))
    forbidden = (
        "将发生心脏破裂",
        "即将发生",
        "高风险",
        "考虑心脏破裂",
        "提示心脏破裂",
    )
    if not output_numbers.issubset(source_numbers) or any(term in text for term in forbidden):
        return None, "validation_failed"
    return text, "compressed"


@lru_cache(maxsize=2)
def _react_patient_records(
    signature: tuple[int, int, int, int],
    limit: int,
) -> tuple[dict[str, Any], ...]:
    del signature
    return tuple(get_patients(limit=limit))


def get_encounter_dataframe(limit: int = REACT_SAMPLE_LIMIT) -> pd.DataFrame:
    """Return a balanced, de-identified database sample for the ReAct page only."""
    bounded_limit = max(2, min(int(limit), REACT_SAMPLE_LIMIT))
    records = _react_patient_records(database_signature(), bounded_limit)
    rows = [
        {
            "encounter_key": str(item["patient_id"]),
            "regno": str(item["patient_id"]),
            "admno": "Database Sample",
            "age": pd.to_numeric(item.get("age"), errors="coerce"),
            "gender": str(item.get("gender") or "No record"),
            "admission_datetime": "",
            "diagnosis": str(item.get("diagnosis") or "No diagnosis recorded"),
            "department": str(item.get("ward") or "No record"),
            "surgery": "",
            "cohort_label": int(item.get("cohort_label") or 0),
            "cohort_group": str(item.get("cohort_group") or "Unassigned Cohort"),
        }
        for item in records
    ]
    return pd.DataFrame(rows)


def _record(
    field: object,
    value: object,
    source: object,
    *,
    is_long: bool = False,
) -> dict[str, Any]:
    return {
        "field": str(field or "Unnamed field"),
        "value": str(value or "No record"),
        "source": str(source or SOURCE_NAME),
        "is_long": is_long,
    }


def get_encounter_detail(encounter_key: str) -> dict[str, Any]:
    """Adapt the existing database detail to the ReAct page's display contract."""
    detail = get_patient_detail(encounter_key)
    source_profile = detail["profile"]
    review = detail["review"]
    profile = {
        "regno": str(source_profile["patient_id"]),
        "admno": "Database Sample",
        "age": (
            int(source_profile["age"])
            if isinstance(source_profile.get("age"), (int, float))
            else None
        ),
        "gender": str(source_profile.get("gender") or "No record"),
        "admission_time": str(source_profile.get("admission_time") or "No record"),
        "diagnosis": str(source_profile.get("diagnosis") or "No diagnosis recorded"),
        "department": str(source_profile.get("ward") or "No record"),
        "risk_level": "UNKNOWN",
        "label": int(review.get("cohort_label") or 0),
        "cohort_group": str(review.get("cohort_group") or "Unassigned Cohort"),
    }
    basic = [
        _record("患者编号", profile["regno"], "数据库脱敏展示编号"),
        _record("样本分组", profile["cohort_group"], "patient_data.db 数据表"),
        _record("年龄", f"{profile['age']} 岁" if profile["age"] is not None else "暂无记录", "基础信息"),
        _record("性别", profile["gender"], "基础信息"),
        _record("入院/就诊时间", profile["admission_time"], "结构化时间字段"),
    ]
    diagnostic = [
        _record("主要诊断", profile["diagnosis"], "院内结构化数据", is_long=True)
    ]
    examinations = [
        _record(
            item.get("name"),
            " ".join(
                part
                for part in (
                    str(item.get("value") or ""),
                    str(item.get("unit") or ""),
                    str(item.get("status") or ""),
                )
                if part
            ),
            item.get("source") or "院内结构化数据",
        )
        for item in detail.get("important_features", [])
        if str(item.get("name") or "") not in {"年龄", "性别"}
    ]
    course = [
        _record(
            item.get("title"),
            item.get("summary") or "暂无摘要",
            item.get("source") or "院内结构化数据",
            is_long=True,
        )
        for item in detail.get("timeline", [])
    ]
    risk = [
        _record(
            "回顾性样本分组",
            profile["cohort_group"],
            "patient_data.db；仅用于选择测试样本，不发送给预测模型",
        ),
        _record(
            "实时模型结果",
            "尚未调用心脏破裂预测模型",
            "ReAct calculate_risk",
        ),
    ]
    return {
        "profile": profile,
        "basic": basic,
        "groups": {
            "诊断信息": diagnostic,
            "检查与检验": examinations,
            "用药与医嘱": [],
            "手术信息": [],
            "病程记录": course,
        },
        "risk": risk,
        "timeline": list(detail.get("timeline", [])),
        "source_file": SOURCE_NAME,
    }


def get_source_record(patient_id: str) -> dict[str, Any]:
    """Read one de-identified display ID from the database for ReAct tools."""
    location = resolve_display_id(patient_id)
    if not location:
        raise KeyError(f"未找到ReAct样本：{patient_id}")
    table, rowid = location
    with connect_readonly() as connection:
        row = connection.execute(
            f"SELECT rowid AS _rowid, * FROM {quote_identifier(table)} WHERE rowid = ?",
            (rowid,),
        ).fetchone()
    if row is None:
        raise KeyError(f"ReAct样本已不存在：{patient_id}")
    return dict(row)


def get_source_signature() -> tuple[int, int, int, int]:
    return database_signature()


def get_source_name() -> str:
    return get_database_path().name


def get_prediction_context(
    patient_id: str,
    *,
    use_llm_compression: bool = True,
    compressor_client: Any | None = None,
) -> dict[str, Any]:
    """Build a label-free ReAct model input from one database row.

    Database rows can contain valid narrative facts without an event-level
    timestamp. Such facts remain explicitly time-unaligned instead of being
    silently discarded from the prediction input.
    """
    row = get_source_record(patient_id)
    detail = get_patient_detail(patient_id)
    profile = detail["profile"]
    sections: list[tuple[str, list[str]]] = []
    grounded_evidence: list[dict[str, str]] = []

    sections.append(
        (
            "基本资料",
            [
                f"年龄：{profile.get('age', '未知')}",
                f"性别：{profile.get('gender', '未知')}",
                f"来源科室：{profile.get('ward', '未知')}",
                f"主要诊断：{profile.get('diagnosis', '未知')}",
            ],
        )
    )

    narrative_groups = (
        (
            "症状与病史（具体记录时间未可靠对齐）",
            (
                "门诊-主诉",
                "门诊-现病史",
                "主诉",
                "现病史",
                "急诊-主要就诊原因",
                "门诊-体格检查",
                "体格检查(生命体征、一般情况)",
                "专科检查",
                "诊断依据",
            ),
        ),
        (
            "诊断与处置（具体记录时间未可靠对齐）",
            (
                "门诊-诊断",
                "首页门急诊诊断",
                "急诊-主诊断名称",
                "入院诊断",
                "初步诊断",
                "门诊-病情变化及处置",
                "诊疗计划",
            ),
        ),
    )
    seen_values: set[str] = set()
    for title, columns in narrative_groups:
        section_rows: list[str] = []
        for column in columns:
            value = _clean_text(row.get(column), limit=700)
            if not value or value in seen_values:
                continue
            seen_values.add(value)
            rendered = f"{column}：{value}"
            section_rows.append(rendered)
            grounded_evidence.append(
                {
                    "evidence_id": f"U{len(grounded_evidence) + 1:04d}",
                    "text": rendered,
                    "source_column": column,
                    "time_alignment": "unavailable",
                }
            )
        if section_rows:
            sections.append((title, section_rows[:10]))

    timeline_rows = [
        f"{item.get('time', '预测截点前')}｜"
        f"{item.get('title', '临床记录')}：{item.get('summary', '—')}"
        for item in detail.get("timeline", [])
        if item.get("summary")
    ]
    if timeline_rows:
        sections.append(("相对病程时间轴", timeline_rows[:12]))

    observations: list[str] = []
    for category in ("vitals", "laboratory"):
        for item in detail.get("observations", {}).get(category, []):
            if item.get("pairing_status") != "paired":
                continue
            name = item.get("display_name") or item.get("item") or "检查项目"
            value = str(item.get("value") or "").strip()
            unit = str(item.get("unit") or "").strip()
            flag = str(item.get("flag") or "").strip()
            time_label = str(item.get("time") or "预测截点前").strip()
            if value:
                suffix = f"，标记：{flag}" if flag else ""
                observations.append(
                    f"{time_label}｜{name}：{value} {unit}".strip() + suffix
                )
    if observations:
        sections.append(("生命体征与检验", observations[:20]))

    echo_rows: list[str] = []
    for column in ("超声-超声描述", "超声-超声提示"):
        value = _clean_text(row.get(column), limit=700)
        if value:
            echo_rows.append(f"{column}：{value}")
    lvef = _single_number(row.get("超声-射血分数"))
    if lvef is not None:
        echo_rows.insert(0, f"LVEF：{_format_number(lvef)}%")
    if echo_rows:
        sections.append(("心脏超声", echo_rows[:6]))

    gaps = [
        str(item.get("title") or "").strip()
        for item in detail.get("evidence", {}).get("missing", [])
        if str(item.get("title") or "").strip()
    ]
    if gaps:
        sections.append(("资料缺口（未知，不能视为阴性）", gaps[:8]))

    compressed_text: str | None = None
    compression_status = "disabled"
    if use_llm_compression:
        compressed_text, compression_status = _compress_untimed_evidence(
            grounded_evidence,
            client=compressor_client,
        )
    rendered_sections = sections
    if compressed_text:
        narrative_titles = {title for title, _ in narrative_groups}
        rendered_sections = [
            sections[0],
            ("病历事实（具体记录时间未可靠对齐）", [compressed_text]),
            *[
                item
                for item in sections[1:]
                if item[0] not in narrative_titles
            ],
        ]

    text_lines = [
        "以下资料均来自预测截点前的脱敏结构化记录。",
        "具体时间无法可靠对齐的病历事实单独列出，不归入任一过去观察窗。",
        "数据库回顾性标签、病例分组和预测截点后的结局未提供给模型。",
    ]
    for title, section_rows in rendered_sections:
        text_lines.append(f"\n【{title}】")
        text_lines.extend(f"- {item}" for item in section_rows)
    clinical_input = "\n".join(text_lines).strip()[:6000]

    quality_flags = []
    if grounded_evidence:
        quality_flags.append(
            {
                "code": "event_time_unavailable",
                "message": (
                    f"{len(grounded_evidence)}条病历事实缺少可可靠对齐的事件时间；"
                    "已保留为截点前未分窗资料。"
                ),
                "count": len(grounded_evidence),
                "source_columns": [
                    item["source_column"] for item in grounded_evidence
                ],
            }
        )

    return {
        "patient_id": patient_id,
        "as_of": "当前就诊 cutoff_time",
        "observation_window": "预测截点前资料",
        "window_definitions": {
            "recent_0_1d": "截点前0～48小时",
            "day_2": "截点前48～72小时",
            "day_3_14": "截点前72～360小时",
        },
        "event_count": len(timeline_rows),
        "grounded_fact_count": len(grounded_evidence) + len(timeline_rows),
        "window_event_counts": {
            "recent_0_1d": 0,
            "day_2": 0,
            "day_3_14": 0,
        },
        "basic_profile": {
            "age": str(profile.get("age") or "未知"),
            "gender": str(profile.get("gender") or "未知"),
            "department": str(profile.get("ward") or "未知"),
        },
        "clinical_input": clinical_input,
        "clinical_text": clinical_input,
        "observation_windows": {},
        "untimed_evidence": grounded_evidence,
        "objective_trends": [],
        "quality_flags": quality_flags,
        "provenance": [],
        "compression": {
            "status": compression_status,
            "model": get_context_model() if compression_status == "compressed" else None,
        },
        "section_count": len(sections),
        "included_sections": [title for title, _ in sections],
        "excluded_fields": [
            "label",
            "cohort_label",
            "cohort_group",
            "回顾性病例分组",
            "预测截点后结局",
            "原始患者标识",
            "绝对日期",
        ],
        "privacy_notice": "仅向本机垂直模型发送脱敏的预测截点前资料。",
        "sources": [get_source_name(), "预测截点前结构化字段"],
    }
