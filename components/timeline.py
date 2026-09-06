from __future__ import annotations

import html

import streamlit as st

from components.i18n import display_value, field_label, source_label


EVENT_COLORS = {
    "门诊就诊": "#2563A8",
    "急诊就诊": "#1D4F91",
    "就诊记录": "#4776A8",
    "入院": "#176BCE",
    "入院记录": "#4668A8",
    "诊断": "#315C8D",
    "检查": "#157A8A",
    "检验": "#7756B3",
    "用药": "#A66A22",
    "医嘱": "#7A6B30",
    "病程": "#5A6C7D",
    "查房": "#486A74",
    "模型预测": "#7C3AED",
    "高风险预警": "#C93636",
    "手术": "#197653",
    "出院": "#23865B",
    "不良结局": "#8B2D2D",
    "窗口截止": "#728197",
}

AGGREGATED_DETAIL_NOTICE = (
    "该行以分号聚合了多个时间或内容，工作簿没有事件级关联键；"
    "下列内容仅表示本次就诊范围内有记录，不按列表位置与时间强行配对："
)


def render_timeline(events: list[dict], expandable: bool = True) -> None:
    if not events:
        st.markdown('<div class="empty-state">No clinical events are available in the current time window.</div>', unsafe_allow_html=True)
        return
    for event in events:
        color = EVENT_COLORS.get(event["type"], "#4C6B88")
        st.markdown(
            f"""
            <div class="timeline-item" style="--event-color:{color}">
              <div class="timeline-time">{html.escape(display_value(event['time']))}</div>
              <div class="timeline-rail"><div class="timeline-dot"></div></div>
              <div class="timeline-card">
                <div class="timeline-title">{html.escape(display_value(event['title']))}</div>
                <div class="timeline-summary">{html.escape(display_value(event['summary']))}</div>
                <span class="source-tag">{html.escape(display_value(event['type']))} · Source: {html.escape(field_label(event['source_field']))}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if expandable:
            with st.expander("View details", icon=":material/expand_more:"):
                st.caption(
                    f"Data category: {source_label(event['source'])} | Source field: {field_label(event['source_field'])}"
                )
                detail = str(event.get("detail") or event["summary"])
                if detail.startswith(AGGREGATED_DETAIL_NOTICE):
                    detail = detail.removeprefix(AGGREGATED_DETAIL_NOTICE).lstrip()
                st.write(display_value(detail))
