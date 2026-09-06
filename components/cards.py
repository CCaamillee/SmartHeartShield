from __future__ import annotations

import html

import streamlit as st

from config import RISK_LABELS
from components.i18n import display_value, ui_text


def render_kpi_card(label: str, value: str | int, delta: str, icon: str, color: str = "#176BCE", soft: str = "#EDF5FF", trend: str = "neutral") -> None:
    delta_class = "delta-up" if trend == "up" else "delta-down" if trend == "down" else ""
    st.markdown(
        f"""
        <div class="kpi-card" style="--kpi-color:{color};--kpi-soft:{soft}">
          <div class="kpi-top"><span class="kpi-label">{html.escape(label)}</span><span class="kpi-icon">{icon}</span></div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-delta {delta_class}">{html.escape(delta)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def risk_badge(level: str) -> str:
    level = level if level in RISK_LABELS else "UNKNOWN"
    return f'<span class="risk-badge risk-{level}">{RISK_LABELS[level]}</span>'


def status_badge(status: str) -> str:
    return f'<span class="status-badge">{html.escape(ui_text(status))}</span>'


def render_profile_strip(profile: dict) -> None:
    items = [
        ("Patient ID", display_value(profile["regno"])),
        ("Encounter ID", display_value(profile["admno"])),
        ("Age / Sex", f"{profile['age'] if profile['age'] is not None else 'Not available'} years / {ui_text(profile['gender'])}"),
        ("Admission / Encounter Time", display_value(profile["admission_time"])),
        ("Primary Diagnosis", display_value(profile["diagnosis"])),
        ("Department", display_value(profile["department"])),
    ]
    body = "".join(f'<div class="profile-item"><div class="profile-label">{html.escape(k)}</div><div class="profile-value">{html.escape(str(v))}</div></div>' for k, v in items)
    st.markdown(f'<div class="profile-strip">{body}</div>', unsafe_allow_html=True)


def render_review_hero(review: dict) -> None:
    label_text = "Rupture Cohort" if review["cohort_label"] == 1 else "Non-rupture Cohort"
    st.markdown(
        f"""
        <div class="risk-hero">
          <div class="risk-eyebrow">Structured Record Review · Not a Model Prediction</div>
          <div class="risk-level">{risk_badge(review['level'])}</div>
          <div class="risk-score">{review['signal_count']}<span style="font-size:14px;font-weight:600"> review signals</span></div>
          <div class="risk-meta">Retrospective label: {label_text} · {html.escape(display_value(review['basis']))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
