from __future__ import annotations

import html
from datetime import datetime

import pandas as pd
import streamlit as st

from components.cards import risk_badge, status_badge
from components.header import render_header, section_header
from components.i18n import display_value, source_label, ui_text
from services.data_api import get_alerts, get_tasks


def render() -> None:
    render_header("Priority Patients")
    alerts = get_alerts(limit=40)
    overrides = st.session_state.setdefault("alert_overrides", {})
    audit = st.session_state.setdefault("audit_log", [])
    for alert in alerts:
        if alert["alert_id"] in overrides:
            alert["status"] = overrides[alert["alert_id"]]

    cols = st.columns(4)
    cols[0].metric("Pending Review", sum(row["status"] == "待复核" for row in alerts))
    cols[1].metric("In Progress", sum(row["status"] == "处理中" for row in alerts))
    cols[2].metric("Reviewed", sum(row["status"] == "已复核" for row in alerts))
    cols[3].metric("False-positive Feedback", sum(row["status"] == "已标记误报" for row in alerts))

    left, right = st.columns([1.6, 1])
    with left:
        section_header("Retrospective Priority Records")
        status = st.selectbox("Status", ["全部"] + sorted({row["status"] for row in alerts}), format_func=ui_text)
        filtered = [row for row in alerts if status == "全部" or row["status"] == status]
        table = pd.DataFrame(filtered)
        if not table.empty:
            table = table.rename(
                columns={"time": "Data Window", "patient_id": "Display ID", "level": "Priority", "reason": "Basis", "status": "Status", "owner": "Owner"}
            )[["Data Window", "Display ID", "Priority", "Basis", "Status", "Owner"]]
            for column in ("Data Window", "Basis", "Status", "Owner"):
                table[column] = table[column].map(display_value)
            st.dataframe(table, hide_index=True, width="stretch", height=390)
        else:
            st.markdown("<div class='empty-state'>No records match the current filter.</div>", unsafe_allow_html=True)
    with right:
        section_header("Review Details")
        selected_id = st.selectbox("Select a record", [row["alert_id"] for row in alerts])
        selected = next(row for row in alerts if row["alert_id"] == selected_id)
        st.markdown(
            f"<div class='alert-box'><div class='xd-card-title'>{selected['alert_id']}</div>"
            f"<div style='margin:.5rem 0'>{risk_badge(selected['level'])} {status_badge(selected['status'])}</div>"
            f"<div class='xd-card-sub'>{html.escape(selected['patient_id'])} · {html.escape(source_label(selected['source']))}</div>"
            f"<div style='font-size:12px;margin-top:.65rem;color:#334E68'>{html.escape(display_value(selected['reason']))}</div></div>",
            unsafe_allow_html=True,
        )
        st.markdown("#### Review Checklist")
        st.checkbox("Confirm cohort labels and eligibility criteria", key=f"check_label_{selected_id}")
        st.checkbox("Review key vital-sign, echocardiography, and laboratory fields", key=f"check_feature_{selected_id}")
        st.checkbox("Confirm missing data and interpretation boundaries", key=f"check_gap_{selected_id}")
        a, b, c = st.columns(3)
        for column, label, new_status in [(a, "Confirm", "已复核"), (b, "In Progress", "处理中"), (c, "False Positive", "已标记误报")]:
            if column.button(label, key=f"act_{label}_{selected_id}", width="stretch"):
                overrides[selected_id] = new_status
                audit.insert(0, {"time": datetime.now().strftime("%H:%M:%S"), "action": label, "target": selected_id, "operator": "Current User"})
                st.rerun()
        if st.button("Open Patient Details", type="primary", width="stretch"):
            st.session_state.selected_patient_id = selected["patient_id"]
            st.session_state.pending_page = "Patient Details"
            st.rerun()

    task_col, audit_col = st.columns(2)
    with task_col:
        section_header("Draft Review Tasks")
        tasks = pd.DataFrame(get_tasks(limit=16)).rename(
            columns={"title": "Task", "patient_id": "Display ID", "priority": "Priority", "due": "Due", "owner": "Owner", "status": "Status"}
        )
        for column in ("Task", "Priority", "Due", "Owner", "Status"):
            tasks[column] = tasks[column].map(display_value)
        st.dataframe(tasks[["Task", "Display ID", "Priority", "Due", "Owner", "Status"]], hide_index=True, width="stretch", height=260)
    with audit_col:
        section_header("Action Audit")
        if audit:
            st.dataframe(pd.DataFrame(audit), hide_index=True, width="stretch", height=260)
        else:
            st.markdown("<div class='empty-state'>No actions have been recorded in this session.</div>", unsafe_allow_html=True)
    st.markdown("<div class='safe-note'>This is a retrospective review workflow, not a live clinical alert system.</div>", unsafe_allow_html=True)

