from __future__ import annotations

import html

import streamlit as st

from components.brand import brand_logo_markup
from config import APP_SUBTITLE, ORGANIZATION_NAME


def render_footer() -> None:
    logo_markup = brand_logo_markup(modifier="brand-logo--footer")
    with st.container(key="global_footer"):
        st.html(
            f"""
            <footer class="global-footer-content" aria-label="Copyright and project information">
              <div class="global-footer-brand">
                {logo_markup}
                <div class="global-footer-brand-copy">
                  <strong>{html.escape(APP_SUBTITLE)}</strong>
                </div>
              </div>
              <div class="global-footer-meta">
                <div class="global-footer-attribution">
                  <span>© 2026 {html.escape(ORGANIZATION_NAME)}</span>
                </div>
                <div class="global-footer-team">
                  <span>Team members: Wen Long&nbsp;&nbsp;Jin Minghui&nbsp;&nbsp;Zhang Yixin</span>
                  <span>Supervisor: Liao Xingyu</span>
                  <span>Email: <a href="mailto:liaoxingyu@nwpu.edu.cn">liaoxingyu@nwpu.edu.cn</a></span>
                </div>
              </div>
            </footer>
            """
        )
