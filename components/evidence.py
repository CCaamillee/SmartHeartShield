from __future__ import annotations

import html

import streamlit as st

from components.i18n import display_value, source_label


COLORS = {"supporting": "#D64545", "counter": "#23865B", "missing": "#D9912B"}


def render_evidence_list(items: list[dict], kind: str) -> None:
    if not items:
        st.markdown('<div class="empty-state">No evidence available</div>', unsafe_allow_html=True)
        return
    color = COLORS.get(kind, "#176BCE")
    for item in items:
        st.markdown(
            f"""
            <div class="evidence-card" style="--evidence-color:{color}">
              <div class="evidence-title">{html.escape(display_value(item['title']))}</div>
              <div class="evidence-detail">{html.escape(display_value(item['detail']))}</div>
              <div class="evidence-meta">{html.escape(display_value(item['time']))} · {html.escape(source_label(item['source']))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
