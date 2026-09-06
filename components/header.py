from __future__ import annotations

import streamlit as st


def render_header(
    title: str,
    description: str = "",
    eyebrow: str | None = "SmartHeartShield",
    *,
    compact: bool = False,
) -> None:
    compact_class = " page-header--compact" if compact else ""
    st.markdown(
        f"""
        <div class="page-header{compact_class}">
          {f'<div class="page-eyebrow">{eyebrow}</div>' if eyebrow else ''}
          <div class="page-title">{title}</div>
          {f'<div class="page-description">{description}</div>' if description else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, *, compact: bool = False) -> None:
    compact_class = " section-head--compact" if compact else ""
    st.markdown(
        f'<div class="section-head{compact_class}"><div class="section-title">{title}</div></div>',
        unsafe_allow_html=True,
    )
