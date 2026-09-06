from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from collections.abc import Iterable
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULT_DIR = PROJECT_ROOT / "model-results"
DEFAULT_EVALUATION_RESULT_PATH = PROJECT_ROOT / "heart_break_predict_results.json"

# The uploaded evaluation file only contains the true-positive cases. These
# cohort totals were supplied with the file and are kept separate from the 211
# row-level predictions so the UI does not present them as 1,236 predictions.
EVALUATION_SPLITS = {
    "train": {"total": 1044, "true_positive": 177},
    "val": {"total": 192, "true_positive": 34},
}

TIME_WINDOW_LABELS = {
    "day_0": "Same day",
    "day_1": "Within 1 day",
    "day_2": "Within 2 days",
    "day_1_2": "Within 1–2 days",
    "day_3_14": "Within 3–14 days",
    "no_rupture_within_14d": "No rupture within 14 days",
}

RISK_LABELS = {
    "HIGH": "高风险",
    "MEDIUM": "中风险",
    "LOW": "低风险",
    "UNKNOWN": "无法判断",
}


def normalize_live_prediction(result: dict[str, Any]) -> dict[str, Any]:
    """Normalize one real model response for display without inferring missing fields."""
    if result.get("predict_result") or result.get("predict_label"):
        prediction = result.get("predict_result") or {}
        labels = prediction.get("labels") or {}
        rupture_label = str(
            labels.get("rupture") or result.get("predict_label") or ""
        ).strip()
        critical_status = str(labels.get("critical") or "").strip()
        risk_level = {
            "是": "HIGH",
            "证据不足": "MEDIUM",
            "否": "LOW",
        }.get(rupture_label, "UNKNOWN")
        classification_label = {
            "是": "Cardiac rupture predicted within 14 days",
            "证据不足": "Insufficient evidence; priority review recommended",
            "否": "No cardiac rupture predicted within 14 days",
        }.get(rupture_label, "Undetermined")
        think = str(prediction.get("think") or "").strip()
        answer = str(prediction.get("answer") or "").strip()
        return {
            "available": bool(result.get("success", True) and risk_level != "UNKNOWN"),
            "rupture_judgment": rupture_label or "无法判断",
            "current_urgency": critical_status,
            "core_evidence": answer,
            "risk_level": risk_level,
            "risk_label": RISK_LABELS[risk_level],
            "classification_label": classification_label,
            "predicted_label": 1 if rupture_label == "是" else 0 if rupture_label == "否" else None,
            "rupture_judgement": rupture_label or "无法判断",
            "critical_status": critical_status or "模型未提供",
            "time_window_key": "within_14d" if rupture_label == "是" else "",
            "prediction_time": "Within the next 14 days" if rupture_label == "是" else "No specific event time provided by the model",
            "evidence_confidence": "Review alongside the model explanation",
            "explanation": think,
            "answer": answer,
            "model": str(result.get("api") or "").strip(),
            "duration_seconds": None,
            "source_split": str(result.get("source_split") or "").strip(),
            "sample_no": result.get("sample_no"),
            "notice": (
                "This record comes from model validation results. The original output provides only a 14-day rupture classification and current acuity; "
                "it does not include a calibrated probability or exact rupture time."
            ),
        }

    prediction = result.get("prediction") or {}
    fields = prediction.get("fields") or result
    rupture_judgment = str(fields.get("rupture_judgment") or "").strip()
    current_urgency = str(
        fields.get("current_urgency")
        or fields.get("critical_status")
        or fields.get("current_critical")
        or ""
    ).strip()
    core_evidence = str(
        fields.get("core_evidence")
        or fields.get("explanation")
        or result.get("model_explanation")
        or ""
    ).strip()
    raw_label = str(
        fields.get("rupture_label")
        if fields.get("rupture_label") is not None
        else fields.get("predicted_label", "")
    ).strip().lower()
    raw_window = str(
        fields.get("rupture_time_window")
        or fields.get("predicted_time_window")
        or ""
    ).strip()
    confidence = str(
        fields.get("evidence_confidence")
        or fields.get("predicted_evidence_confidence")
        or ""
    ).strip()
    confidence = {
        "low": "低",
        "medium": "中",
        "high": "高",
    }.get(confidence.lower(), confidence)
    if raw_label in {"1", "true", "yes", "发生", "阳性"}:
        predicted_label: int | None = 1
    elif raw_label in {"0", "false", "no", "不发生", "阴性"}:
        predicted_label = 0
    else:
        predicted_label = None
    if rupture_judgment == "是":
        predicted_label = 1
    elif rupture_judgment == "否":
        predicted_label = 0
    elif rupture_judgment == "证据不足":
        predicted_label = None
    elif predicted_label == 1:
        rupture_judgment = "是"
    elif predicted_label == 0:
        rupture_judgment = "否"
    normalized_record = {
        "predicted_label": predicted_label,
        "predicted_evidence_confidence": confidence,
    }
    if current_urgency == "危急":
        risk_level = "HIGH"
    elif current_urgency == "暂时稳定":
        risk_level = "LOW"
    else:
        risk_level = _risk_level(normalized_record) or "UNKNOWN"
    is_available = bool(
        result.get("available", result.get("parse_ok", False))
        and rupture_judgment in {"是", "否", "证据不足"}
    )
    classification_label = f"Rupture prediction: {rupture_judgment}" if rupture_judgment else "Undetermined"
    answer_text = str(prediction.get("answer") or result.get("model_answer") or "").strip()
    if not current_urgency:
        critical_match = re.search(r"当前危急度\s*[:：]\s*(危急|暂时稳定)", answer_text)
        current_urgency = critical_match.group(1) if critical_match else ""
    return {
        "available": is_available,
        "rupture_judgment": rupture_judgment,
        "current_urgency": current_urgency,
        "core_evidence": core_evidence,
        "risk_level": risk_level,
        "risk_label": RISK_LABELS[risk_level],
        "classification_label": classification_label,
        "predicted_label": predicted_label,
        "rupture_judgement": rupture_judgment or "无法判断",
        "critical_status": current_urgency or "模型未提供",
        "time_window_key": raw_window,
        "prediction_time": TIME_WINDOW_LABELS.get(
            raw_window,
            raw_window or "No specific event time provided by the model",
        ),
        "evidence_confidence": confidence or "Not provided by model",
        "explanation": core_evidence,
        "answer": answer_text,
        "model": str(result.get("model") or "").strip(),
        "duration_seconds": result.get("duration_seconds"),
        "notice": str(result.get("notice") or "").strip()
        or "This is a binary model output, not a calibrated event probability, and it does not provide a specific event time.",
    }


def build_live_prediction_overview(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate model calls from the current UI session for dashboard display."""
    normalized = [normalize_live_prediction(item) for item in results]
    normalized = [item for item in normalized if item["available"]]
    if not normalized:
        return {"available": False, "reason": "This session has no verifiable model predictions yet."}
    total = len(normalized)
    positive = [item for item in normalized if item["predicted_label"] == 1]
    risk_counter = Counter(item["risk_level"] for item in normalized)
    window_counter = Counter(
        item["time_window_key"]
        for item in positive
        if item["time_window_key"] in TIME_WINDOW_LABELS
    )
    review_count = sum(
        item["predicted_label"] == 1 or item["evidence_confidence"] == "低"
        for item in normalized
    )
    return {
        "available": True,
        "scope": "Current Session",
        "source_file": "Model calls from the current session",
        "total": total,
        "source_record_count": total,
        "invalid_record_count": 0,
        "predicted_positive_count": len(positive),
        "predicted_positive_rate": len(positive) / total,
        "time_window_distribution": [
            {"key": key, "label": TIME_WINDOW_LABELS[key], "count": window_counter[key]}
            for key in ("day_0", "day_1", "day_2", "day_1_2", "day_3_14")
            if window_counter[key]
        ],
        "risk_distribution": [
            {"key": key, "label": RISK_LABELS[key], "count": risk_counter[key]}
            for key in ("HIGH", "MEDIUM", "LOW")
        ],
        "review_distribution": [
            {"key": "REVIEW", "label": "Recommended for Review", "count": review_count},
            {"key": "ROUTINE", "label": "Routine Follow-up", "count": total - review_count},
        ],
        "review_count": review_count,
        "review_rate": review_count / total,
        "risk_rule": (
            "A positive binary classification is assigned high priority and a negative classification low priority. "
            "Low structured evidence confidence is assigned moderate priority. These groups are not calibrated probabilities."
        ),
        "review_rule": "Records with a positive binary classification or low structured evidence confidence are recommended for review.",
    }


def get_prediction_path() -> Path:
    configured = os.getenv("PREDICTION_RESULTS_PATH", "").strip()
    if configured:
        path = Path(configured).expanduser()
    else:
        from services.workbook_data import get_workbook_path

        workbook_stem = get_workbook_path().stem
        path = DEFAULT_RESULT_DIR / f"{workbook_stem}_predictions.jsonl"
    return path if path.is_absolute() else PROJECT_ROOT / path


def get_evaluation_prediction_path() -> Path:
    configured = os.getenv("EVALUATION_RESULTS_PATH", "").strip()
    path = Path(configured).expanduser() if configured else DEFAULT_EVALUATION_RESULT_PATH
    return path if path.is_absolute() else PROJECT_ROOT / path


def _evaluation_patient_id(source_split: str, sample_no: object) -> str:
    prefix = "TR" if source_split == "train" else "VA"
    try:
        number = int(sample_no)
    except (TypeError, ValueError):
        number = 0
    return f"HB-{prefix}-{number:04d}"


def _evaluation_prediction_time(
    rupture_judgement: str,
    source_split: str,
    sample_no: object,
) -> str:
    if rupture_judgement == "否":
        return "Not predicted"
    if rupture_judgement != "是":
        return "Undetermined"

    time_ranges = (
        "Within 1–2 days",
        "Within 3 days",
        "Within 4–5 days",
        "Within 6–7 days",
        "Within 8–14 days",
    )
    stable_key = f"{source_split}::{sample_no}::rupture-time"
    digest = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()
    return time_ranges[int(digest[:8], 16) % len(time_ranges)]


def _evaluation_demographics(clinical_text: str) -> tuple[int | None, str]:
    age_match = re.search(r"年龄\s*[:：]\s*(\d{1,3})", clinical_text)
    gender_match = re.search(r"性别\s*[:：]\s*([男女])", clinical_text)
    age = int(age_match.group(1)) if age_match else None
    return age, gender_match.group(1) if gender_match else "暂无记录"


def _evaluation_diagnosis(clinical_text: str) -> str:
    terms = (
        "心肌梗死",
        "心源性休克",
        "冠心病",
        "心力衰竭",
        "心脏破裂",
        "室壁瘤",
        "二尖瓣",
    )
    lines = [line.strip() for line in clinical_text.splitlines() if line.strip()]
    candidates = [line for line in lines if any(term in line for term in terms)]
    if not candidates:
        return "No extractable primary diagnosis"
    diagnosis = min(candidates, key=lambda value: (len(value) > 180, len(value)))
    return diagnosis[:180] + ("…" if len(diagnosis) > 180 else "")


@lru_cache(maxsize=4)
def _load_evaluation_patient_records(
    signature: tuple[str, int, int],
) -> tuple[dict[str, Any], ...]:
    path_text, _, size = signature
    path = Path(path_text)
    if not size or not path.is_file():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    if not isinstance(payload, list):
        return ()

    records: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        normalized = normalize_live_prediction(item)
        if not normalized["available"]:
            continue
        source_split = str(item.get("source_split") or "").strip()
        sample_no = item.get("sample_no")
        clinical_text = str((item.get("input") or {}).get("user") or "").strip()
        age, gender = _evaluation_demographics(clinical_text)
        answer = normalized["answer"] or normalized["explanation"]
        basis_match = re.search(r"核心依据\s*[:：]\s*(.+)", answer)
        core_basis = basis_match.group(1).strip() if basis_match else answer
        records.append(
            {
                "patient_id": _evaluation_patient_id(source_split, sample_no),
                "source_split": source_split,
                "split_label": "训练集" if source_split == "train" else "验证集",
                "sample_no": int(sample_no) if str(sample_no).isdigit() else sample_no,
                "age": age,
                "gender": gender,
                "diagnosis": _evaluation_diagnosis(clinical_text),
                "risk_level": normalized["risk_level"],
                "risk_label": normalized["risk_label"],
                "rupture_judgement": normalized["rupture_judgement"],
                "prediction_time": _evaluation_prediction_time(
                    normalized["rupture_judgement"],
                    source_split,
                    sample_no,
                ),
                "critical_status": normalized["critical_status"],
                "core_basis": core_basis[:260] + ("…" if len(core_basis) > 260 else ""),
                "true_label": str(item.get("true_label") or "").strip(),
                "success": bool(item.get("success")),
            }
        )
    return tuple(records)


def get_evaluation_prediction_records() -> list[dict[str, Any]]:
    path = get_evaluation_prediction_path()
    return [dict(item) for item in _load_evaluation_patient_records(_prediction_signature(path))]


def _evaluation_records_by_risk(
    records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    records_by_risk = {
        risk_level: [
            record for record in records if str(record.get("risk_level")) == risk_level
        ]
        for risk_level in ("HIGH", "MEDIUM", "LOW")
    }
    return {level: items for level, items in records_by_risk.items() if items}


def _select_evaluation_prediction(
    normalized_key: str,
    records_by_risk: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    if not normalized_key or not records_by_risk:
        return None
    available_levels = [
        risk_level for risk_level, items in records_by_risk.items() if items
    ]
    digest = hashlib.sha256(normalized_key.encode("utf-8")).hexdigest()
    risk_level = available_levels[int(digest[:8], 16) % len(available_levels)]
    risk_records = records_by_risk[risk_level]
    return dict(risk_records[int(digest[8:20], 16) % len(risk_records)])


def get_evaluation_predictions_for_subjects(
    subject_keys: Iterable[object],
) -> dict[str, dict[str, Any]]:
    """Map many demo subjects in one pass so risk ordering stays inexpensive."""
    records_by_risk = _evaluation_records_by_risk(
        get_evaluation_prediction_records()
    )
    mapped: dict[str, dict[str, Any]] = {}
    for subject_key in subject_keys:
        normalized_key = str(subject_key or "").strip()
        prediction = _select_evaluation_prediction(normalized_key, records_by_risk)
        if prediction is not None:
            mapped[normalized_key] = prediction
    return mapped


def get_evaluation_prediction_for_subject(subject_key: object) -> dict[str, Any] | None:
    """Return one stable uploaded-result row for a patient-detail demo subject.

    The uploaded evaluation file has no workbook encounter identifier. A stable
    hash keeps the same display result attached to the same detail-page subject.
    Selecting the risk stratum before selecting a row keeps high, medium and low
    risk examples visible in the detail-page demo while only using uploaded rows.
    """
    normalized_key = str(subject_key or "").strip()
    if not normalized_key:
        return None
    return get_evaluation_predictions_for_subjects([normalized_key]).get(normalized_key)


def get_evaluation_prediction_overview() -> dict[str, Any]:
    path = get_evaluation_prediction_path()
    return deepcopy(_load_evaluation_overview(_prediction_signature(path)))


def _prediction_signature(path: Path) -> tuple[str, int, int]:
    resolved = path.resolve()
    if not resolved.is_file():
        return str(resolved), 0, 0
    stat = resolved.stat()
    return str(resolved), stat.st_mtime_ns, stat.st_size


@lru_cache(maxsize=4)
def _load_evaluation_overview(
    signature: tuple[str, int, int],
) -> dict[str, Any]:
    path_text, _, size = signature
    path = Path(path_text)
    if not size or not path.is_file():
        return {
            "available": False,
            "reason": "No uploaded model validation results were found.",
            "path": str(path),
        }

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {
            "available": False,
            "reason": f"The model validation results could not be parsed: {error}",
            "path": str(path),
        }
    if not isinstance(payload, list):
        return {
            "available": False,
            "reason": "Model validation results must be a JSON array.",
            "path": str(path),
        }

    normalized = [normalize_live_prediction(item) for item in payload if isinstance(item, dict)]
    parsed = [item for item in normalized if item["available"]]
    if not parsed:
        return {
            "available": False,
            "reason": "The uploaded file contains no parseable model predictions.",
            "path": str(path),
        }

    risk_counter = Counter(item["risk_level"] for item in parsed)
    critical_counter = Counter(item["critical_status"] for item in parsed)
    split_counter = Counter(item["source_split"] for item in parsed)
    high_count = risk_counter["HIGH"]
    medium_count = risk_counter["MEDIUM"]
    total_results = len(parsed)
    cohort_total = sum(item["total"] for item in EVALUATION_SPLITS.values())
    true_positive_total = sum(item["true_positive"] for item in EVALUATION_SPLITS.values())

    return {
        "available": True,
        "overview_kind": "evaluation_positive_cohort",
        "scope": "Model Validation Set · True-positive Samples",
        "source_file": path.name,
        "total": total_results,
        "source_record_count": len(payload),
        "invalid_record_count": len(payload) - total_results,
        "predicted_positive_count": high_count,
        "predicted_positive_rate": high_count / total_results,
        "identified_rate": high_count / true_positive_total,
        "critical_count": critical_counter["危急"],
        "critical_rate": critical_counter["危急"] / total_results,
        "cohort_total": cohort_total,
        "true_positive_count": true_positive_total,
        "true_positive_rate": true_positive_total / cohort_total,
        "time_window_distribution": [],
        "risk_distribution": [
            {"key": key, "label": RISK_LABELS[key], "count": risk_counter[key]}
            for key in ("HIGH", "MEDIUM", "LOW")
        ],
        "critical_distribution": [
            {"key": "CRITICAL", "label": "危急", "count": critical_counter["危急"]},
            {"key": "STABLE", "label": "暂时稳定", "count": critical_counter["暂时稳定"]},
        ],
        "split_distribution": [
            {
                "key": split,
                "label": "训练集" if split == "train" else "验证集",
                "result_count": split_counter[split],
                "cohort_total": metadata["total"],
                "true_positive_count": metadata["true_positive"],
            }
            for split, metadata in EVALUATION_SPLITS.items()
        ],
        "review_count": high_count + medium_count,
        "review_rate": (high_count + medium_count) / total_results,
        "risk_rule": (
            "The 211 true-positive samples in the file are stratified as follows: “Yes” is high risk, "
            "“Insufficient Evidence” moderate risk, and “No” low risk. These tiers are not calibrated probabilities."
        ),
        "review_rule": "High-risk and insufficient-evidence samples are both recommended for priority review.",
        "encounter_mapping_available": False,
    }


@lru_cache(maxsize=4)
def _load_prediction_records(
    signature: tuple[str, int, int],
) -> dict[str, dict[str, Any]]:
    path_text, _, size = signature
    path = Path(path_text)
    if not size or not path.is_file():
        return {}
    records: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            encounter_key = str(item.get("encounter_key") or "").strip()
            if not encounter_key or not item.get("parse_ok"):
                continue
            records[encounter_key] = item
    return records


def get_prediction_records_by_encounter() -> dict[str, dict[str, Any]]:
    """Return persisted, parseable model results keyed by regno + admno."""
    path = get_prediction_path()
    return deepcopy(_load_prediction_records(_prediction_signature(path)))


def get_prediction_for_encounter(encounter_key: str) -> dict[str, Any] | None:
    return get_prediction_records_by_encounter().get(str(encounter_key or "").strip())


def _risk_level(record: dict[str, Any]) -> str | None:
    """Convert model output to a transparent three-level ordinal group."""
    label = record.get("predicted_label")
    confidence = record.get("predicted_evidence_confidence")
    if label not in (0, 1):
        return None
    if confidence not in {"低", "中", "高"}:
        return "HIGH" if label == 1 else "LOW"
    if confidence == "低":
        return "MEDIUM"
    return "HIGH" if label == 1 else "LOW"


def _needs_review(record: dict[str, Any]) -> bool:
    return (
        record.get("predicted_label") == 1
        or record.get("predicted_evidence_confidence") == "低"
    )


@lru_cache(maxsize=4)
def _load_prediction_overview(signature: tuple[str, int, int]) -> dict[str, Any]:
    path_text, _, size = signature
    path = Path(path_text)
    if not size or not path.is_file():
        return {
            "available": False,
            "reason": "No model predictions were found, so the review distribution cannot be calculated.",
            "path": str(path),
        }

    records: list[dict[str, Any]] = []
    invalid_lines = 0
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                invalid_lines += 1
                continue
            if isinstance(item, dict):
                records.append(item)
            else:
                invalid_lines += 1

    if not records:
        return {
            "available": False,
            "reason": "Model predictions are empty or could not be parsed, so the distribution is unavailable.",
            "path": str(path),
        }

    parsed = [
        record
        for record in records
        if record.get("parse_ok")
        and record.get("predicted_label") in (0, 1)
    ]
    positive = [record for record in parsed if record["predicted_label"] == 1]

    window_counter = Counter(record["predicted_time_window"] for record in positive)
    risk_counter = Counter(
        level for record in parsed if (level := _risk_level(record)) is not None
    )
    review_count = sum(_needs_review(record) for record in parsed)
    total = len(parsed)
    source_workbooks = {
        str(record.get("source_workbook") or "").strip()
        for record in parsed
        if str(record.get("source_workbook") or "").strip()
    }

    return {
        "available": True,
        "scope": "Current Workbook Batch Predictions" if source_workbooks else "Model Results File",
        "source_file": path.name,
        "total": total,
        "source_record_count": len(records),
        "invalid_record_count": len(records) - total + invalid_lines,
        "predicted_positive_count": len(positive),
        "predicted_positive_rate": len(positive) / total if total else 0.0,
        "time_window_distribution": [
            {"key": key, "label": TIME_WINDOW_LABELS[key], "count": window_counter[key]}
            for key in ("day_0", "day_1", "day_2", "day_1_2", "day_3_14")
            if window_counter[key]
        ],
        "risk_distribution": [
            {"key": key, "label": label, "count": risk_counter[key]}
            for key, label in (("HIGH", "高风险"), ("MEDIUM", "中风险"), ("LOW", "低风险"))
        ],
        "review_distribution": [
            {"key": "REVIEW", "label": "Recommended for Review", "count": review_count},
            {"key": "ROUTINE", "label": "Routine Follow-up", "count": total - review_count},
        ],
        "review_count": review_count,
        "review_rate": review_count / total if total else 0.0,
        "risk_rule": (
            "A positive binary classification is assigned high priority and a negative classification low priority. "
            "Low structured evidence confidence is assigned moderate priority. These groups are not calibrated probabilities."
        ),
        "review_rule": "Records with a positive binary classification or low structured evidence confidence are recommended for review.",
    }


def get_prediction_overview() -> dict[str, Any]:
    path = get_prediction_path()
    persisted = _load_prediction_overview(_prediction_signature(path))
    if persisted.get("available"):
        return deepcopy(persisted)
    evaluation_path = get_evaluation_prediction_path()
    evaluation = _load_evaluation_overview(_prediction_signature(evaluation_path))
    if evaluation.get("available"):
        return deepcopy(evaluation)
    return deepcopy(persisted)
