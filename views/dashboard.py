from __future__ import annotations

import html
import math

import altair as alt
import pandas as pd
import streamlit as st

from components.header import render_header, section_header
from components.i18n import display_value, ui_text
from services.prediction_api import (
    get_evaluation_prediction_overview,
    get_evaluation_prediction_records,
)


ROWS_PER_PAGE = 12


def _distribution_counts(rows: list[dict]) -> dict[str, int]:
    return {str(row.get("key")): int(row.get("count", 0)) for row in rows}


def _render_prediction_focus(prediction_overview: dict) -> None:
    section_header("Model Prediction Priorities", compact=True)
    if not prediction_overview.get("available"):
        reason = html.escape(str(prediction_overview.get("reason", "No verifiable model results are available.")))
        st.html(
            f"""
            <section class="model-focus-unavailable" role="status" aria-label="Model result status">
              <span class="material-symbols-rounded" aria-hidden="true">model_training</span>
              <div>
                <strong>No verifiable model results are connected</strong>
                <p>{reason} This page does not derive predicted risk from the workbook's retrospective label or cutoff_time.</p>
              </div>
            </section>
            """
        )
        return

    risk_counts = _distribution_counts(prediction_overview.get("risk_distribution", []))
    total = int(prediction_overview.get("total", 0))
    positive_rate = float(prediction_overview.get("predicted_positive_rate", 0.0))
    critical_count = int(prediction_overview.get("critical_count", 0))
    critical_rate = float(prediction_overview.get("critical_rate", 0.0))
    cohort_total = int(prediction_overview.get("cohort_total", total))
    true_positive_count = int(prediction_overview.get("true_positive_count", total))
    true_positive_rate = float(prediction_overview.get("true_positive_rate", 0.0))
    is_evaluation = prediction_overview.get("overview_kind") == "evaluation_positive_cohort"
    scope = html.escape(str(prediction_overview.get("scope", "Model results")))
    risk_rule = html.escape(str(prediction_overview.get("risk_rule", "")))
    review_rule = html.escape(str(prediction_overview.get("review_rule", "")))

    split_rows = prediction_overview.get("split_distribution", [])
    window_rows = prediction_overview.get("time_window_distribution", [])
    context_row_html = ""
    if not split_rows:
        if window_rows:
            context_html = "".join(
                (
                    '<span class="model-window-chip">'
                    f'<span>{html.escape(ui_text(row.get("label", "No record")))}</span>'
                    f'<strong>{int(row.get("count", 0))} records</strong>'
                    "</span>"
                )
                for row in window_rows
            )
            context_row_html = (
                '<div class="model-window-row" aria-label="Predicted event-time distribution">'
                f"<strong>Predicted Event Window</strong><div>{context_html}</div></div>"
            )
        else:
            context_row_html = (
                '<div class="model-window-row" aria-label="Prediction result scope">'
                '<strong>Result Scope</strong><div>'
                '<span class="model-window-empty">No additional grouping is available</span>'
                "</div></div>"
            )

    second_value = critical_count if is_evaluation else int(prediction_overview.get("review_count", 0))
    second_rate = critical_rate if is_evaluation else float(prediction_overview.get("review_rate", 0.0))
    second_title = "Currently Critical" if is_evaluation else "Priority Review Recommended"
    second_copy = (
        "The model also classifies these cases as currently critical; prioritize immediate support and bedside reassessment."
        if is_evaluation
        else "Positive classifications or limited evidence require priority review against the clinical record."
    )
    cohort_value = f"{true_positive_count}/{cohort_total}" if is_evaluation else str(total)
    cohort_title = "Positive Samples / Full Cohort" if is_evaluation else "Valid Model Results"
    cohort_copy = (
        f"The true-positive rate in the full cohort is {true_positive_rate:.1%}; the uploaded file contains only these {true_positive_count} positive samples."
        if is_evaluation
        else "Includes only successfully parsed records with a usable model classification."
    )

    st.html(
        f"""
        <section class="model-focus-panel" aria-label="Model prediction priorities">
          <div class="model-focus-heading">
            <div>
              <span class="model-focus-kicker">MODEL PRIORITY OVERVIEW</span>
            </div>
            <span class="model-focus-scope">
              <span class="material-symbols-rounded" aria-hidden="true">verified</span>{scope}
            </span>
          </div>

          <div class="model-focus-grid">
            <article class="model-focus-card model-focus-card--hero">
              <div class="model-focus-card-head">
                <span class="material-symbols-rounded" aria-hidden="true">emergency_home</span>
                <span>Top Priority · High Risk</span>
              </div>
              <strong class="model-focus-value">{risk_counts.get('HIGH', 0)}<small> cases</small></strong>
              <h4>Predicted Cardiac Rupture Within 14 Days</h4>
              <p>{positive_rate:.1%} of uploaded positive results; prioritize bedside reassessment and enhanced monitoring.</p>
            </article>

            <article class="model-focus-card model-focus-card--critical">
              <div class="model-focus-card-head">
                <span class="material-symbols-rounded" aria-hidden="true">monitor_heart</span>
                <span>Immediate Status</span>
              </div>
              <strong class="model-focus-value">{second_value}<small> cases</small></strong>
              <h4>{second_title}</h4>
              <p>{second_rate:.1%} of current results. {second_copy}</p>
            </article>

            <article class="model-focus-card model-focus-card--cohort">
              <div class="model-focus-card-head">
                <span class="material-symbols-rounded" aria-hidden="true">dataset</span>
                <span>Population</span>
              </div>
              <strong class="model-focus-value model-focus-value--compact">{cohort_value}</strong>
              <h4>{cohort_title}</h4>
              <p>{cohort_copy}</p>
            </article>
          </div>

          {context_row_html}
          <div class="model-focus-note">
            <span class="material-symbols-rounded" aria-hidden="true">clinical_notes</span>
            <div><strong>Interpretation boundary:</strong> {review_rule} {risk_rule} Results support review and do not replace a physician's diagnosis.</div>
          </div>
        </section>
        """
    )

    risk_rows = prediction_overview.get("risk_distribution", [])
    critical_rows = prediction_overview.get("critical_distribution", [])
    if risk_rows:
        chart_col, status_col = st.columns([1.35, 1], gap="medium")
        risk_frame = pd.DataFrame(
            {
                "Risk Level": [ui_text(row["label"]) for row in risk_rows],
                "Patients": [int(row["count"]) for row in risk_rows],
            }
        )
        risk_frame["Share"] = risk_frame["Patients"] / max(total, 1)
        risk_chart = (
            alt.Chart(risk_frame)
            .mark_bar(cornerRadiusEnd=6, size=26)
            .encode(
                x=alt.X("Patients:Q", title="Patients", axis=alt.Axis(tickMinStep=1)),
                y=alt.Y("Risk Level:N", title=None, sort=["High Risk", "Moderate Risk", "Low Risk"]),
                color=alt.Color(
                    "Risk Level:N",
                    scale=alt.Scale(
                        domain=["High Risk", "Moderate Risk", "Low Risk"],
                        range=["#C93636", "#B76513", "#19734F"],
                    ),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("Risk Level:N"),
                    alt.Tooltip("Patients:Q", title="Patients"),
                    alt.Tooltip("Share:Q", title="Share", format=".1%"),
                ],
            )
            .properties(height=190)
        )
        with chart_col.container(border=True, key="model_risk_distribution_chart"):
            st.subheader(":material/bar_chart: Risk Distribution")
            st.altair_chart(risk_chart, width="stretch")
            st.caption(
                f"High {risk_counts.get('HIGH', 0)} | Moderate {risk_counts.get('MEDIUM', 0)} | "
                f"Low {risk_counts.get('LOW', 0)}"
            )

        with status_col.container(border=True, key="model_status_distribution_chart"):
            if critical_rows:
                critical_frame = pd.DataFrame(
                    {
                        "Current Status": [ui_text(row["label"]) for row in critical_rows],
                        "Patients": [int(row["count"]) for row in critical_rows],
                    }
                )
                critical_chart = (
                    alt.Chart(critical_frame)
                    .mark_arc(innerRadius=48, outerRadius=76)
                    .encode(
                        theta=alt.Theta("Patients:Q"),
                        color=alt.Color(
                            "Current Status:N",
                            scale=alt.Scale(
                                domain=["Critical", "Currently Stable"],
                                range=["#C93636", "#4D84A8"],
                            ),
                            legend=alt.Legend(title=None, orient="bottom"),
                        ),
                        tooltip=["Current Status:N", alt.Tooltip("Patients:Q", title="Patients")],
                    )
                    .properties(height=190)
                )
                st.subheader(":material/vital_signs: Current Acuity")
                st.altair_chart(critical_chart, width="stretch")
                st.caption(f"{critical_count} critical cases, representing {critical_rate:.1%} of uploaded results.")
            else:
                st.subheader(":material/fact_check: Review Guidance")
                st.metric(
                    "Recommended for Review",
                    int(prediction_overview.get("review_count", 0)),
                    f"{float(prediction_overview.get('review_rate', 0.0)):.1%} of valid results",
                    border=True,
                )
                st.caption("Model results support review and do not replace a physician's diagnosis.")


def _render_legend(has_live_results: bool = False) -> None:
    del has_live_results
    explanation = (
        "Colors come directly from heart_break_predict_results.json: “Yes” is high risk, "
        "“Insufficient Evidence” is moderate risk, and “No” is low risk."
    )
    st.markdown(
        f"""
        <div class="risk-legend" role="note" aria-label="Risk color legend">
          <strong>Risk Legend</strong>
          <span class="risk-badge risk-HIGH">High Risk</span>
          <span class="risk-badge risk-MEDIUM">Moderate Risk</span>
          <span class="risk-badge risk-LOW">Low Risk</span>
          <span>{explanation}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_treatment_recommendations() -> None:
    section_header("Risk-stratified Care Guidance")
    with st.container(border=True, key="risk_treatment_recommendations"):
        st.caption(
            "Use these tiered management directions alongside vital signs, bedside imaging, and the complete clinical record."
        )
        columns = st.columns(3, gap="medium")
        recommendations = (
            (
                "high",
                ":red-badge[High Risk]",
                "Urgent Management & Enhanced Monitoring",
                (
                    "Escalate continuous bedside monitoring of circulation, ECG, oxygenation, and perfusion.",
                    "Arrange prompt multidisciplinary review by cardiology, cardiac surgery, and critical care teams.",
                    "Reassess bedside echocardiography and hemodynamics frequently, watching for hypotension and pericardial effusion.",
                ),
            ),
            (
                "medium",
                ":orange-badge[Moderate Risk]",
                "Closer Observation & Additional Evidence",
                (
                    "Shorten reassessment intervals and track symptoms, vital signs, and myocardial injury markers.",
                    "Obtain or review bedside echocardiography, hemodynamics, and key progress notes before restratification.",
                    "Escalate to the high-risk pathway immediately if circulatory instability or new abnormalities emerge.",
                ),
            ),
            (
                "low",
                ":green-badge[Low Risk]",
                "Routine Monitoring & Follow-up",
                (
                    "Continue routine monitoring of symptoms, vital signs, ECG, and relevant laboratory trends.",
                    "Maintain foundational care and risk-factor management while watching for chest pain, hypotension, and heart failure.",
                    "Reassess when the condition or test results change; low risk does not mean no risk.",
                ),
            ),
        )
        for column, (level, badge, title, items) in zip(columns, recommendations):
            with column.container(
                border=True,
                height="stretch",
                key=f"treatment_advice_{level}",
            ):
                st.markdown(badge)
                st.markdown(f"#### {title}")
                for item in items:
                    st.markdown(f"- {item}")


def _filter_evaluation_frame(frame: pd.DataFrame) -> pd.DataFrame:
    with st.container(border=True, key="evaluation_patient_filters"):
        st.markdown("**Filter Patients with Model Results**")
        search_col, risk_col, status_col = st.columns(
            [1.8, 1, 1],
            gap="small",
            vertical_alignment="bottom",
        )
        keyword = search_col.text_input(
            "Search patient, diagnosis, or key evidence",
            placeholder="e.g., HB-TR-0001 or myocardial infarction",
            key="evaluation_patient_search",
        ).strip().lower()
        risk = risk_col.selectbox(
            "Risk level",
            ["全部", "高风险", "中风险", "低风险"],
            key="evaluation_risk_filter",
            format_func=ui_text,
        )
        status = status_col.selectbox(
            "Current acuity",
            ["全部", "危急", "暂时稳定"],
            key="evaluation_status_filter",
            format_func=ui_text,
        )

    filtered = frame.copy()
    if keyword:
        searchable_frame = filtered[["patient_id", "diagnosis", "core_basis"]].fillna("").astype(str)
        for column in ("diagnosis", "core_basis"):
            searchable_frame[column] = searchable_frame[column].map(display_value)
        searchable = searchable_frame.agg(" ".join, axis=1).str.lower()
        filtered = filtered.loc[searchable.str.contains(keyword, regex=False)]
    if risk != "全部":
        filtered = filtered.loc[filtered["risk_label"] == risk]
    if status != "全部":
        filtered = filtered.loc[filtered["critical_status"] == status]
    return filtered.copy()


def _sort_evaluation_frame(frame: pd.DataFrame, mode: str) -> pd.DataFrame:
    sorted_frame = frame.copy()
    if mode == "当前危急优先":
        sorted_frame["_status_rank"] = sorted_frame["critical_status"].map(
            {"危急": 0, "暂时稳定": 1}
        ).fillna(2)
        return sorted_frame.sort_values(
            ["_status_rank", "source_split", "sample_no"]
        ).drop(columns="_status_rank")
    if mode == "年龄（高到低）":
        return sorted_frame.sort_values(
            ["age", "source_split", "sample_no"],
            ascending=[False, True, True],
            na_position="last",
        )
    if mode == "样本编号":
        return sorted_frame.sort_values(["source_split", "sample_no"])
    sorted_frame["_risk_rank"] = sorted_frame["risk_level"].map(
        {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    ).fillna(3)
    sorted_frame["_status_rank"] = sorted_frame["critical_status"].map(
        {"危急": 0, "暂时稳定": 1}
    ).fillna(2)
    return sorted_frame.sort_values(
        ["_risk_rank", "_status_rank", "source_split", "sample_no"]
    ).drop(columns=["_risk_rank", "_status_rank"])


def _display_evaluation_table(page_frame: pd.DataFrame) -> None:
    icons = {"高风险": "🔴", "中风险": "🟠", "低风险": "🟢"}
    display = pd.DataFrame(
        {
            "Anonymous Patient": page_frame["patient_id"],
            "Predicted Rupture Time": page_frame["prediction_time"].map(display_value),
            "Sample No.": page_frame["sample_no"],
            "Age": page_frame["age"].astype("Int64"),
            "Sex": page_frame["gender"].map(ui_text),
            "Primary Clinical Diagnosis": page_frame["diagnosis"].map(display_value),
            "Risk Level": page_frame["risk_label"].map(
                lambda value: f"{icons.get(value, '⚪')} {ui_text(value)}"
            ),
            "Rupture Prediction": page_frame["rupture_judgement"].map(ui_text),
            "Current Acuity": page_frame["critical_status"].map(ui_text),
            "Key Evidence": page_frame["core_basis"].map(display_value),
        }
    ).reset_index(drop=True)

    def risk_row_style(row: pd.Series) -> list[str]:
        risk_text = str(row["Risk Level"])
        if "High Risk" in risk_text:
            row_style = "background-color:#FFF4F4;color:#5F3034"
            emphasis = "background-color:#F9DDE0;color:#9F1D2A;font-weight:750"
        elif "Moderate Risk" in risk_text:
            row_style = "background-color:#FFF9EE;color:#654A2B"
            emphasis = "background-color:#FCEBCB;color:#8A4B08;font-weight:750"
        else:
            row_style = "background-color:#F2FAF6;color:#315B49"
            emphasis = "background-color:#DFF2E9;color:#17613A;font-weight:750"
        return [
            emphasis if column in {"Risk Level", "Rupture Prediction", "Current Acuity"} else row_style
            for column in row.index
        ]

    st.dataframe(
        display.style.apply(risk_row_style, axis=1),
        hide_index=True,
        height="content",
        width="stretch",
        key="evaluation_patient_table",
        placeholder="No patients match the current filters",
        row_height=46,
        column_config={
            "Anonymous Patient": st.column_config.TextColumn("Anonymous Patient", pinned=True, width="medium"),
            "Predicted Rupture Time": st.column_config.TextColumn("Predicted Rupture Time", width="medium"),
            "Sample No.": st.column_config.NumberColumn("Sample No.", format="%d", width="small"),
            "Age": st.column_config.NumberColumn("Age", format="%d years", width="small"),
            "Sex": st.column_config.TextColumn("Sex", width="small"),
            "Primary Clinical Diagnosis": st.column_config.TextColumn("Primary Clinical Diagnosis", width="large"),
            "Risk Level": st.column_config.TextColumn("Risk Level", width="medium"),
            "Rupture Prediction": st.column_config.TextColumn("Rupture Prediction", width="small"),
            "Current Acuity": st.column_config.TextColumn("Current Acuity", width="medium"),
            "Key Evidence": st.column_config.TextColumn("Key Evidence", width="large"),
        },
    )


def _render_dashboard_page() -> None:
    render_header("Emergency Overview", eyebrow=None)
    with st.skeleton(height=130):
        prediction_overview = get_evaluation_prediction_overview()
        records = get_evaluation_prediction_records()
    if not prediction_overview.get("available") or not records:
        st.error(
            str(prediction_overview.get("reason") or "The uploaded model results are empty or could not be parsed."),
            icon=":material/error:",
        )
        return

    _render_prediction_focus(prediction_overview)
    _render_treatment_recommendations()

    section_header("Patient Overview")
    _render_legend(True)
    frame = pd.DataFrame(records)
    filtered = _filter_evaluation_frame(frame)
    if filtered.empty:
        st.warning(
            "No patients match the current filters. Adjust or clear the filters.",
            icon=":material/search_off:",
        )
        return

    sort_col, count_col = st.columns([1, 2], vertical_alignment="bottom")
    sort_mode = sort_col.selectbox(
        "Sort by",
        ["风险等级优先", "当前危急优先", "年龄（高到低）", "样本编号"],
        key="evaluation_sort_mode",
        format_func=lambda value: {
            "风险等级优先": "Risk Level",
            "当前危急优先": "Current Acuity",
            "年龄（高到低）": "Age (High to Low)",
            "样本编号": "Sample Number",
        }[value],
    )
    count_col.caption(
        f"Showing {len(filtered)} of {len(frame)} anonymous patients. Red indicates high risk, orange moderate risk, and green low risk."
    )
    sorted_frame = _sort_evaluation_frame(filtered, sort_mode).reset_index(drop=True)
    total_pages = max(1, math.ceil(len(sorted_frame) / ROWS_PER_PAGE))
    if st.session_state.get("evaluation_patient_page", 1) > total_pages:
        st.session_state.evaluation_patient_page = total_pages

    table_slot = st.container()
    with st.container(
        horizontal=True,
        horizontal_alignment="right",
        vertical_alignment="center",
        key="evaluation_pagination_bar",
    ):
        page_label_slot = st.empty()
        page = st.pagination(
            total_pages,
            max_visible_pages=7,
            key="evaluation_patient_page",
            persist_state="session",
        )
        page_label_slot.markdown(f"**Page {page} of {total_pages}**")
    start = (page - 1) * ROWS_PER_PAGE
    page_frame = sorted_frame.iloc[start : start + ROWS_PER_PAGE].reset_index(drop=True)
    with table_slot:
        _display_evaluation_table(page_frame)


def render() -> None:
    with st.container(key="emergency_dashboard_page", gap="small"):
        _render_dashboard_page()
