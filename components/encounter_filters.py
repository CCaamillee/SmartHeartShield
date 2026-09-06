from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from components.i18n import display_value


def _clear_filter_state(prefix: str) -> None:
    suffixes = (
        "query",
        "age",
        "gender",
        "admission_dates",
        "discharge_dates",
        "diagnosis",
        "departments",
        "surgery",
    )
    for suffix in suffixes:
        st.session_state.pop(f"{prefix}_{suffix}", None)


def render_encounter_filters(
    frame: pd.DataFrame,
    *,
    prefix: str,
    include_discharge: bool = False,
    expanded: bool = True,
) -> pd.DataFrame:
    """Render a batched, workbook-backed encounter filter form."""
    if frame.empty:
        return frame

    ages = frame["age"].dropna().astype(int)
    minimum_age = int(ages.min()) if not ages.empty else 0
    maximum_age = int(ages.max()) if not ages.empty else 120
    gender_options = sorted(
        (
            value
            for value in frame["gender"].dropna().unique().tolist()
            if value != "暂无记录"
        ),
        key=display_value,
    )
    department_options = sorted(
        (
            value
            for value in frame["department"].dropna().unique().tolist()
            if value != "暂无记录"
        ),
        key=display_value,
    )

    with st.expander(
        "Search & Filters",
        icon=":material/filter_list:",
        expanded=expanded,
    ):
        with st.form(f"{prefix}_filter_form", border=False):
            row1 = st.columns([1.35, 1, 1], vertical_alignment="bottom")
            query = row1[0].text_input(
                "Patient or encounter ID",
                placeholder="Enter regno or admno",
                key=f"{prefix}_query",
            )
            age_range = row1[1].slider(
                "Age range",
                minimum_age,
                maximum_age,
                (minimum_age, maximum_age),
                key=f"{prefix}_age",
            )
            genders = row1[2].multiselect(
                "Sex",
                gender_options,
                key=f"{prefix}_gender",
                placeholder="All sexes",
                format_func=display_value,
            )

            row2 = st.columns([1, 1, 1], vertical_alignment="bottom")
            admission_dates = row2[0].date_input(
                "Admission / encounter date",
                value=(),
                key=f"{prefix}_admission_dates",
                help="Select a start and end date. Encounters without a recorded date are excluded from date-filtered results.",
            )
            diagnosis = row2[1].text_input(
                "Diagnosis",
                placeholder="Enter a diagnosis keyword",
                key=f"{prefix}_diagnosis",
            )
            departments = row2[2].multiselect(
                "Department",
                department_options,
                key=f"{prefix}_departments",
                placeholder="All departments",
                format_func=display_value,
            )

            row3 = st.columns([1, 1, 1], vertical_alignment="bottom")
            surgery = row3[0].text_input(
                "Procedure or intervention",
                placeholder="Enter a procedure keyword",
                key=f"{prefix}_surgery",
            )
            discharge_dates: tuple[date, ...] | date | list[date] = ()
            if include_discharge:
                discharge_dates = row3[1].date_input(
                    "Discharge date",
                    value=(),
                    key=f"{prefix}_discharge_dates",
                )
            else:
                row3[1].caption("The workbook has no bed field, so bed filtering is unavailable.")
            with row3[2].container(horizontal=True, horizontal_alignment="right"):
                st.form_submit_button(
                    "Clear",
                    icon=":material/restart_alt:",
                    on_click=_clear_filter_state,
                    args=(prefix,),
                )
                st.form_submit_button(
                    "Apply filters",
                    type="primary",
                    icon=":material/search:",
                )

        st.caption(
            "Risk filtering is hidden because the workbook has no verifiable model risk tier. All available filters can be combined."
        )

    filtered = frame.copy()
    identifier_query = str(query or "").strip().lower()
    if identifier_query:
        filtered = filtered.loc[
            filtered["regno"].str.lower().str.contains(identifier_query, regex=False)
            | filtered["admno"].str.lower().str.contains(identifier_query, regex=False)
        ]
    filtered = filtered.loc[
        filtered["age"].isna()
        | filtered["age"].between(age_range[0], age_range[1], inclusive="both")
    ]
    if genders:
        filtered = filtered.loc[filtered["gender"].isin(genders)]
    if departments:
        filtered = filtered.loc[filtered["department"].isin(departments)]
    diagnosis_query = str(diagnosis or "").strip().lower()
    if diagnosis_query:
        translated_diagnoses = filtered["diagnosis"].fillna("").astype(str).map(display_value).str.lower()
        filtered = filtered.loc[
            filtered["diagnosis"].str.lower().str.contains(diagnosis_query, regex=False)
            | translated_diagnoses.str.contains(diagnosis_query, regex=False)
        ]
    surgery_query = str(surgery or "").strip().lower()
    if surgery_query:
        translated_surgeries = filtered["surgery"].fillna("").astype(str).map(display_value).str.lower()
        filtered = filtered.loc[
            filtered["surgery"].str.lower().str.contains(surgery_query, regex=False)
            | translated_surgeries.str.contains(surgery_query, regex=False)
        ]

    filtered = _filter_date_range(filtered, "admission_datetime", admission_dates)
    if include_discharge:
        filtered = _filter_date_range(filtered, "discharge_datetime", discharge_dates)
    return filtered.reset_index(drop=True)


def _filter_date_range(
    frame: pd.DataFrame,
    column: str,
    selected: tuple[date, ...] | date | list[date],
) -> pd.DataFrame:
    if not selected:
        return frame
    values = list(selected) if isinstance(selected, (tuple, list)) else [selected]
    if not values:
        return frame
    start = pd.Timestamp(values[0])
    end = pd.Timestamp(values[-1]) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    parsed = pd.to_datetime(frame[column], errors="coerce")
    return frame.loc[parsed.between(start, end, inclusive="both")]
