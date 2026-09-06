from __future__ import annotations

import html

import streamlit as st

from components.cards import status_badge
from components.evidence import render_evidence_list
from components.header import render_header, section_header
from components.i18n import display_value
from components.timeline import render_timeline
from services.data_api import get_case_replay, get_patient_page, get_patient_summary


def _move_replay(key: str, delta: int, maximum: int) -> None:
    st.session_state[key] = max(0, min(maximum, st.session_state.get(key, 0) + delta))


def _reset_replay(key: str) -> None:
    st.session_state[key] = 0


def render() -> None:
    render_header("Clinical Course Review")
    lookup_col, lookup_action = st.columns([4, 1], vertical_alignment="bottom")
    lookup_id = lookup_col.text_input(
        "Load a rupture-cohort case by display ID",
        placeholder="e.g., XD-AB12CD34EF",
        key="case_replay_lookup_id",
    )
    if lookup_action.button("Load Case", width="stretch"):
        try:
            lookup_patient = get_patient_summary(lookup_id.strip().upper())
            if lookup_patient["cohort_label"] != 1:
                st.error("Clinical course review currently supports only retrospective cardiac rupture records.")
            else:
                st.session_state.selected_patient_id = lookup_patient["patient_id"]
        except (KeyError, ValueError):
            st.error("The de-identified display ID was not found. Check it and try again.")

    requested_page = int(st.session_state.get("case_replay_page", 1))
    patient_page = get_patient_page(page=requested_page, page_size=100, cohort_label=1)
    current_page = int(patient_page["page"])
    total_pages = int(patient_page["total_pages"])
    if requested_page != current_page:
        st.session_state.case_replay_page = current_page
    page_col, page_note = st.columns([1, 4], vertical_alignment="bottom")
    page_col.number_input(
        "Case page",
        min_value=1,
        max_value=total_pages,
        step=1,
        key="case_replay_page",
    )
    page_note.caption(
        f"{patient_page['total']:,} encounters in the retrospective rupture cohort · Page {current_page} of {total_pages}"
    )

    candidates = list(patient_page["items"])
    requested_patient = st.session_state.get("selected_patient_id")
    candidate_ids = {row["patient_id"] for row in candidates}
    if requested_patient and requested_patient not in candidate_ids:
        try:
            requested_summary = get_patient_summary(requested_patient)
            if requested_summary["cohort_label"] == 1:
                candidates.insert(0, requested_summary)
        except KeyError:
            pass
    patient_ids = [row["patient_id"] for row in candidates]
    default_id = requested_patient if requested_patient in patient_ids else patient_ids[0]
    candidate_map = {row["patient_id"]: row for row in candidates}
    selected = st.selectbox(
        "Select a retrospective rupture-cohort case",
        patient_ids,
        index=patient_ids.index(default_id),
        format_func=lambda patient_id: (
            f"{patient_id} · {candidate_map[patient_id]['age']} years · {display_value(candidate_map[patient_id]['diagnosis'])}"
        ),
    )
    st.session_state.selected_patient_id = selected
    replay = get_case_replay(selected)
    snapshots = replay["snapshots"]
    if not snapshots:
        st.warning("This patient has no structured snapshots available for course review.", icon=":material/event_busy:")
        return

    key = f"replay_step_{selected}"
    st.session_state.setdefault(key, 0)
    max_step = len(snapshots) - 1
    stored_step = int(st.session_state.get(key, 0))
    if stored_step < 0 or stored_step > max_step:
        st.session_state[key] = 0

    if max_step == 0:
        step = 0
        st.info(
            "No longitudinal structured events can be reconstructed for this patient. A single structured snapshot is shown.",
            icon=":material/info:",
        )
    else:
        step = st.slider("Clinical course", 0, max_step, format="Time point %d", key=key)
    snapshot = snapshots[step]

    if max_step == 0:
        st.caption(f"Current relative time: {display_value(snapshot['time'])} · Single snapshot · No earlier or later points available")
    else:
        prev_col, next_col, reset_col, meta_col = st.columns([0.8, 0.8, 0.8, 3])
        prev_col.button(
            "← Previous",
            width="stretch",
            disabled=step == 0,
            on_click=_move_replay,
            args=(key, -1, max_step),
        )
        next_col.button(
            "Next →",
            type="primary",
            width="stretch",
            disabled=step == max_step,
            on_click=_move_replay,
            args=(key, 1, max_step),
        )
        reset_col.button("Reset", width="stretch", on_click=_reset_replay, args=(key,))
        meta_col.caption(
            f"Current relative time: {display_value(snapshot['time'])} · {len(snapshot['visible_events'])} events loaded"
        )

    section_header("Current Clinical Course")
    state_col, action_col = st.columns([1.7, 1], vertical_alignment="center")
    with state_col:
        st.markdown(
            f"<div class='info-box'><div class='risk-eyebrow' style='color:#71869A'>CURRENT SNAPSHOT</div>"
            f"<div style='font-size:28px;font-weight:800;margin:.45rem 0'>{snapshot['visible_event_count']} visible events</div>"
            f"<div>{status_badge('不计算时点风险')}</div>"
            f"<div style='font-size:12px;color:#4D657A;margin-top:.8rem'>{html.escape(display_value(snapshot['event']))}</div></div>",
            unsafe_allow_html=True,
        )
    with action_col:
        st.info("The retrospective outcome label is used only for case selection and is not part of historical risk or signal calculations.")
        if st.button("Open Clinical Assistant", width="stretch"):
            st.session_state.selected_patient_id = selected
            st.session_state.agent_scope_selector = selected
            st.session_state.pending_page = "Clinical Assistant"
            st.rerun()

    timeline_col, evidence_col = st.columns([1.5, 1])
    with timeline_col:
        section_header("Clinical Events Through the Current Time")
        render_timeline(snapshot["visible_events"], expandable=False)
    with evidence_col:
        section_header("Currently Visible Evidence")
        evidence_items = [
            {"title": event["title"], "detail": event["summary"], "time": event["time"], "source": event["source"]}
            for event in snapshot["visible_events"]
        ][-5:]
        render_evidence_list(evidence_items, "supporting")
        if step == max_step:
            section_header("Data Gaps")
            render_evidence_list(replay["detail"]["evidence"]["missing"], "missing")
    st.markdown(
        "<div class='safe-note'>Clinical course review shows only recorded relative times and structured summaries, with direct identifiers hidden.</div>",
        unsafe_allow_html=True,
    )

