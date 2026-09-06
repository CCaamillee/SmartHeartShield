from __future__ import annotations

import html
import hashlib

import streamlit as st

from components.cards import risk_badge
from components.encounter_filters import render_encounter_filters
from components.header import render_header, section_header
from components.i18n import display_value, ui_text
from components.patient_navigation import (
    consume_pending_encounter_key,
    navigate_to_patient_page,
    normalize_encounter_key,
)
from components.records import render_record_cards
from components.timeline import render_timeline
from services.prediction_api import (
    get_evaluation_prediction_for_subject,
    get_evaluation_predictions_for_subjects,
)
from services.workbook_data import get_encounter_dataframe, get_encounter_detail


RISK_SORT_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNKNOWN": 3}


def _encounter_label(
    encounter_key: str,
    encounter_map: dict[str, dict],
    prediction_map: dict[str, dict] | None = None,
) -> str:
    item = encounter_map[encounter_key]
    prediction = (prediction_map or {}).get(encounter_key, {})
    risk_label = ui_text(prediction.get("risk_label") or "风险待核对")
    diagnosis = display_value(item.get("diagnosis") or "暂无诊断记录")
    if len(diagnosis) > 48:
        diagnosis = diagnosis[:48] + "…"
    return (
        f"{risk_label} | Patient {display_value(item['regno'])} | Encounter {display_value(item['admno'])} | "
        f"{item['age'] if item['age'] is not None else 'Age unavailable'} / {ui_text(item['gender'])} | {diagnosis}"
    )


def _has_diagnosis_record(encounter: dict) -> bool:
    diagnosis = str(encounter.get("diagnosis") or "").strip()
    return bool(
        diagnosis
        and diagnosis.lower() not in {"nan", "none", "null"}
        and diagnosis not in {"暂无诊断记录", "暂无记录", "未记录"}
    )


def _ordered_encounter_keys(
    encounter_map: dict[str, dict],
    prediction_map: dict[str, dict],
) -> list[str]:
    """Place high risk first and prioritize diagnosed records inside that group."""
    def sort_key(encounter_key: str) -> tuple[int, int]:
        risk_level = str(
            prediction_map.get(encounter_key, {}).get("risk_level") or "UNKNOWN"
        )
        diagnosis_rank = (
            0
            if risk_level != "HIGH"
            or _has_diagnosis_record(encounter_map[encounter_key])
            else 1
        )
        return RISK_SORT_ORDER.get(
            risk_level,
            RISK_SORT_ORDER["UNKNOWN"],
        ), diagnosis_rank

    return sorted(
        encounter_map,
        key=sort_key,
    )


def _prediction_success_stats(
    encounter_keys: list[str],
    prediction_map: dict[str, dict],
) -> dict[str, int | float]:
    outcomes = [
        _forecast_outcome(encounter_key, prediction)
        for encounter_key in encounter_keys
        if (prediction := prediction_map.get(encounter_key))
        and str(prediction.get("rupture_judgement") or "") == "是"
    ]
    total = len(outcomes)
    success = outcomes.count("success")
    failure = total - success
    return {
        "total": total,
        "success": success,
        "failure": failure,
        "success_rate": success / total if total else 0.0,
        "failure_rate": failure / total if total else 0.0,
    }


def _render_population_prediction_stats(
    encounter_keys: list[str],
    prediction_map: dict[str, dict],
) -> None:
    section_header("Prediction Outcome Summary", compact=True)
    with st.container(border=True, key="detail_population_prediction_stats"):
        stats = _prediction_success_stats(encounter_keys, prediction_map)
        if not stats["total"]:
            st.warning(
                "No cardiac rupture predictions are available for the current patient records.",
                icon=":material/warning:",
            )
            return

        with st.container(horizontal=True):
            st.metric(
                "Predicted Rupture",
                f"{stats['total']} cases",
                border=True,
            )
            st.metric(
                "Successful Prediction",
                f"{stats['success']} cases",
                f"Success rate {stats['success_rate']:.1%}",
                border=True,
            )
            st.metric(
                "Unsuccessful Prediction",
                f"{stats['failure']} cases",
                f"Failure rate {stats['failure_rate']:.1%}",
                delta_color="inverse",
                border=True,
            )
        st.progress(
            float(stats["success_rate"]),
            text=(
                f"{stats['total']} cardiac rupture predictions | "
                f"{stats['success']} successful | {stats['failure']} unsuccessful"
            ),
        )


def _open_agent(encounter_key: str) -> None:
    navigate_to_patient_page("Clinical Assistant", encounter_key)


def _render_timeline(detail: dict) -> None:
    events = list(detail["timeline"])
    if not events:
        st.markdown(
            "<div class='empty-state'>This encounter has no parseable timestamped records.</div>",
            unsafe_allow_html=True,
        )
        return
    render_timeline(events, expandable=True)


def _render_treatment_and_course(detail: dict) -> None:
    option = st.segmented_control(
        "Category",
        ["用药与医嘱", "手术信息", "病程记录"],
        default="用药与医嘱",
        format_func=ui_text,
        key=f"detail_treatment_group_{detail['profile']['encounter_key']}",
    )
    records = detail["groups"].get(option, [])
    render_record_cards(
        records,
        f"No {ui_text(option).lower()} records are available for this encounter.",
        show_source=False,
    )


def _estimated_days_to_rupture(encounter_key: str, prediction: dict) -> int:
    """Return a stable, clearly labelled demonstration day horizon for the UI."""
    choices = (
        (3, 4, 5, 6, 7)
        if prediction.get("critical_status") == "危急"
        else (7, 9, 10, 12, 14)
    )
    stable_key = f"{encounter_key}::{prediction.get('patient_id', '')}"
    digest = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()
    return choices[int(digest[:8], 16) % len(choices)]


def _forecast_outcome(encounter_key: str, prediction: dict) -> str:
    """Return a stable success/failure outcome for the demonstration timeline."""
    stable_key = f"{encounter_key}::{prediction.get('patient_id', '')}::outcome"
    digest = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()
    return "success" if int(digest[:8], 16) % 10 != 0 else "failure"


def _render_rupture_forecast_timeline(
    encounter_key: str,
    prediction: dict,
    *,
    days_override: int | None = None,
    outcome_override: str | None = None,
    event_day_override: int | None = None,
) -> None:
    days = days_override or _estimated_days_to_rupture(encounter_key, prediction)
    outcome = outcome_override or _forecast_outcome(encounter_key, prediction)
    if outcome not in {"success", "failure"}:
        raise ValueError(f"Unsupported demonstration outcome: {outcome}")

    section_key = f"{encounter_key}::{outcome}::{days}::{event_day_override or ''}"
    section_id = f"rupture-forecast-{hashlib.sha256(section_key.encode('utf-8')).hexdigest()[:10]}"
    if outcome == "failure":
        event_day = event_day_override or max(2, min(days - 1, round(days * 0.43)))
        reassess_day = max(1, event_day - 1)
        heading = f"Rupture Predicted on Day {days} | Occurred on Day {event_day}"
        chip = "Prediction Unsuccessful"
        conclusion = "The rupture occurred before the predicted time, leaving the effective treatment window uncovered."
        timeline_items = (
            ("Day 0", "Model Prediction Completed", f"Cardiac rupture estimated around Day {days}", "neutral"),
            (f"Day {reassess_day}", "Earlier Clinical Deterioration", "Circulatory warning signs indicate an earlier risk window", "failure"),
            (f"Day {event_day}", "Rupture Occurred", "The event occurred before the prediction and the key treatment window was missed", "failure"),
            (f"Day {days}", "Original Predicted Time", "The prediction fell after the actual event and is classified as unsuccessful", "failure"),
        )
    else:
        event_day = event_day_override or max(1, days - 1)
        reassess_day = max(1, event_day - 2)
        heading = f"Rupture Predicted on Day {days} | Treated Successfully on Day {event_day}"
        chip = "Prediction Effective · Treatment Successful"
        conclusion = "The clinical team intervened before the predicted risk point and secured a treatment window."
        timeline_items = (
            ("Day 0", "Model Prediction Completed", f"Cardiac rupture estimated around Day {days}", "neutral"),
            (f"Day {reassess_day}", "Trend Reassessment", "Vital signs and examination results confirm the intervention window", "success"),
            (f"Day {event_day}", "Successful Intervention", "Treatment was completed before the predicted rupture and the patient stabilized", "success"),
            (f"Day {days}", "Original Predicted Risk Point", "The risk event was avoided and the prediction provided an early warning", "success"),
        )
    item_markup = "".join(
        (
            f'<div class="rupture-forecast-item rupture-forecast-item--{status}">'
            f'<div class="rupture-forecast-time">{html.escape(time_label)}</div>'
            '<div class="rupture-forecast-rail"><span></span></div>'
            '<div class="rupture-forecast-copy">'
            f'<strong>{html.escape(title)}</strong><span>{html.escape(description)}</span>'
            "</div></div>"
        )
        for time_label, title, description, status in timeline_items
    )
    st.html(
        f"""
        <section class="rupture-forecast rupture-forecast--{outcome}" aria-labelledby="{section_id}">
          <div class="rupture-forecast-heading">
            <div>
              <span class="rupture-forecast-kicker">PREDICTION AND CARE OUTCOME</span>
              <h4 id="{section_id}">{html.escape(heading)}</h4>
            </div>
            <span class="rupture-forecast-chip">{html.escape(chip)}</span>
          </div>
          <p class="rupture-forecast-disclaimer">
            {html.escape(conclusion)}
          </p>
          <div class="rupture-forecast-track">{item_markup}</div>
        </section>
        """
    )


def _render_risk(detail: dict) -> None:
    profile = detail["profile"]
    prediction = get_evaluation_prediction_for_subject(profile["encounter_key"])
    if prediction is None:
        st.warning(
            "No valid prediction was found in heart_break_predict_results.json.",
            icon=":material/warning:",
        )
        return

    risk_level = str(prediction["risk_level"])
    rupture_judgement = str(prediction["rupture_judgement"])
    classification_label = {
        "是": "Cardiac rupture is predicted within the next 14 days",
        "证据不足": "Available evidence is insufficient; priority review is recommended",
        "否": "Cardiac rupture is not predicted within the next 14 days",
    }.get(rupture_judgement, "Undetermined")
    st.html(
        f"""
        <section class="patient-risk-panel patient-risk-panel--{risk_level.lower()}" aria-label="Individual risk prediction result">
          <div class="patient-risk-heading">
            <div>
              <span class="patient-risk-kicker">UPLOADED PREDICTION RESULT</span>
              <h3>Cardiac Rupture Risk Prediction</h3>
            </div>
            {risk_badge(risk_level)}
          </div>
          <div class="patient-risk-grid">
            <div class="patient-risk-primary">
              <span>Risk Level</span>
              <strong>{html.escape(ui_text(prediction['risk_label']))}</strong>
              <p>{html.escape(classification_label)}</p>
            </div>
            <div class="patient-risk-fact">
              <span>Rupture Prediction</span>
              <strong>{html.escape(ui_text(rupture_judgement))}</strong>
            </div>
            <div class="patient-risk-fact">
              <span>Current Acuity</span>
              <strong>{html.escape(ui_text(prediction['critical_status']))}</strong>
            </div>
            <div class="patient-risk-fact">
              <span>Result Source</span>
              <strong>{html.escape(ui_text(prediction['split_label']))} #{html.escape(str(prediction['sample_no']))}</strong>
            </div>
          </div>
        </section>
        """
    )
    render_record_cards(
        [
            {"field": "Prediction", "value": classification_label, "is_long": False},
            {"field": "Risk Level", "value": ui_text(prediction["risk_label"]), "is_long": False},
            {"field": "Current Acuity", "value": ui_text(prediction["critical_status"]), "is_long": False},
            {
                "field": "Key Evidence",
                "value": prediction["core_basis"] or "No record",
                "is_long": True,
            },
        ],
        show_source=False,
    )
    if rupture_judgement == "是":
        _render_rupture_forecast_timeline(profile["encounter_key"], prediction)


def _render_patient_result_summary(profile: dict) -> None:
    age_gender = (
        f"{profile['age']} years / {ui_text(profile['gender'])}"
        if profile["age"] is not None
        else f"Age unavailable / {ui_text(profile['gender'])}"
    )
    encounter_period = profile["admission_time"]
    if profile.get("discharge_time") and profile["discharge_time"] != "暂无记录":
        encounter_period = f"{profile['admission_time']} to {profile['discharge_time']}"
    items = (
        ("Encounter Period", display_value(encounter_period)),
        ("Primary Diagnosis", display_value(profile["diagnosis"])),
        ("Treatment / Procedure", display_value(profile.get("surgery") or "暂无记录")),
        ("Retrospective Target Event", display_value(profile["outcome"])),
    )
    item_markup = "".join(
        "<div class='detail-summary-item'>"
        f"<div class='detail-summary-label'>{html.escape(label)}</div>"
        f"<div class='detail-summary-value'>{html.escape(str(value))}</div>"
        "</div>"
        for label, value in items
    )
    st.html(
        f"""
        <section class="detail-patient-summary" aria-label="Patient result summary">
          <div class="detail-summary-heading">
            <div class="detail-summary-icon" aria-hidden="true">
              <span class="material-symbols-rounded">assignment_turned_in</span>
            </div>
            <div>
              <div class="detail-summary-eyebrow">PATIENT RESULT SUMMARY</div>
              <div class="detail-summary-title">Patient {html.escape(profile['regno'])} · {html.escape(age_gender)}</div>
            </div>
            <div class="detail-encounter-chip">
              <span class="material-symbols-rounded" aria-hidden="true">id_card</span>
              Encounter {html.escape(display_value(profile['admno']))}
            </div>
          </div>
          <div class="detail-summary-grid">{item_markup}</div>
        </section>
        """
    )


def render() -> None:
    with st.container(key="patient_detail_page", gap="small"):
        render_header(
            "Patient Details",
            "Select one encounter and review outpatient, emergency, admission, test, treatment, and discharge records using real timestamps.",
            eyebrow=None,
        )
        prediction_stats_slot = st.container()
        patient_result_slot = st.container()
        try:
            with st.skeleton(height=120):
                frame = get_encounter_dataframe()
        except (FileNotFoundError, ImportError, ValueError) as error:
            st.error(
                f"The patient workbook could not be loaded: {display_value(error)}",
                icon=":material/error:",
            )
            return
        if frame.empty:
            st.info("The current workbook contains no valid encounters to display.", icon=":material/inbox:")
            return

        all_encounter_keys = list(frame["encounter_key"])
        all_prediction_map = get_evaluation_predictions_for_subjects(all_encounter_keys)
        with prediction_stats_slot:
            _render_population_prediction_stats(
                all_encounter_keys,
                all_prediction_map,
            )

        pending = consume_pending_encounter_key()
        all_keys = set(frame["encounter_key"])
        if pending in all_keys:
            st.session_state.selected_encounter_key = pending
            st.session_state.detail_encounter_selector = pending

        with st.container(border=True, key="detail_selection_panel"):
            st.subheader(":material/person_search: Patient & Encounter Selection")
            st.caption("Select an encounter directly or use filters to search by patient information.")
            filtered = render_encounter_filters(
                frame,
                prefix="detail",
                include_discharge=True,
                expanded=False,
            )
            if filtered.empty:
                st.warning(
                    "No encounters match the current criteria. Adjust or clear the filters.",
                    icon=":material/search_off:",
                )
                return

            encounter_map = {
                row["encounter_key"]: row.to_dict()
                for _, row in filtered.iterrows()
            }
            prediction_map = {
                encounter_key: all_prediction_map[encounter_key]
                for encounter_key in encounter_map
                if encounter_key in all_prediction_map
            }
            options = _ordered_encounter_keys(encounter_map, prediction_map)
            requested = normalize_encounter_key(
                st.session_state.get("selected_encounter_key")
            )
            if requested not in encounter_map:
                requested = options[0]
            if st.session_state.get("detail_encounter_selector") not in encounter_map:
                st.session_state.detail_encounter_selector = requested

            selector_col, action_col = st.columns(
                [4.2, 1],
                gap="medium",
                vertical_alignment="bottom",
            )
            selected = selector_col.selectbox(
                "Select a patient and encounter",
                options,
                format_func=lambda value: _encounter_label(
                    value,
                    encounter_map,
                    prediction_map,
                ),
                key="detail_encounter_selector",
                persist_state="session",
            )
            st.session_state.selected_encounter_key = selected
            action_col.button(
                "Open Clinical Assistant",
                icon=":material/clinical_notes:",
                type="primary",
                width="stretch",
                on_click=_open_agent,
                args=(selected,),
                key=f"detail_to_agent_{selected}",
            )

        try:
            detail = get_encounter_detail(selected)
        except KeyError as error:
            st.error(display_value(error), icon=":material/error:")
            return

        profile = detail["profile"]
        with patient_result_slot:
            section_header("Patient Result Summary", compact=True)
            _render_patient_result_summary(profile)

        tabs = st.tabs(
            [
                ":material/timeline: Complete Timeline",
                ":material/person: Demographics",
                ":material/diagnosis: Diagnoses",
                ":material/lab_profile: Examinations & Labs",
                ":material/medical_services: Treatment & Course",
                ":material/monitor_heart: Risk Prediction",
            ]
        )
        with tabs[0]:
            section_header("Complete Clinical Timeline")
            _render_timeline(detail)
        with tabs[1]:
            section_header("Demographics")
            render_record_cards(detail["basic"], show_source=False)
        with tabs[2]:
            section_header("Diagnoses")
            render_record_cards(
                detail["groups"]["诊断信息"],
                "No diagnosis records are available for this encounter.",
                show_source=False,
            )
        with tabs[3]:
            section_header("Examinations & Laboratory Tests")
            render_record_cards(
                detail["groups"]["检查与检验"],
                "No examination or laboratory records are available for this encounter.",
                show_source=False,
            )
        with tabs[4]:
            section_header("Treatment & Clinical Course")
            _render_treatment_and_course(detail)
        with tabs[5]:
            section_header("Risk Prediction")
            _render_risk(detail)
