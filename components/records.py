from __future__ import annotations

import html

import streamlit as st

from components.i18n import display_value, field_label, source_label


def render_record_cards(
    records: list[dict],
    empty_message: str = "No records in this category",
    *,
    show_source: bool = True,
) -> None:
    if not records:
        st.markdown(f"<div class='empty-state'>{html.escape(empty_message)}</div>", unsafe_allow_html=True)
        return
    for index, item in enumerate(records):
        raw_field = str(item.get("field") or "Unnamed field")
        label = html.escape(field_label(raw_field))
        value = display_value(item.get("value") or "No record")
        source = html.escape(source_label(item.get("source") or "Workbook"))
        source_markup = (
            f"<div class='record-source'>{source}</div>" if show_source else ""
        )
        if item.get("is_long"):
            preview = html.escape(value[:220] + ("…" if len(value) > 220 else ""))
            st.markdown(
                f"<div class='record-card'><div class='record-label'>{label}</div>"
                f"<div class='record-value'>{preview}</div>"
                f"{source_markup}</div>",
                unsafe_allow_html=True,
            )
            with st.expander(
                f"View full text · {field_label(raw_field)}",
                icon=":material/article:",
                key=f"record_{index}_{item.get('field')}",
            ):
                st.write(value)
                if show_source:
                    st.caption(source)
        else:
            st.markdown(
                f"<div class='record-card'><div class='record-label'>{label}</div>"
                f"<div class='record-value'>{html.escape(value)}</div>"
                f"{source_markup}</div>",
                unsafe_allow_html=True,
            )
