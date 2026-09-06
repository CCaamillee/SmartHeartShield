from __future__ import annotations

import streamlit as st

from components.access import require_access
from components.footer import render_footer
from components.sidebar import render_navigation
from components.styles import inject_global_styles
from config import APP_NAME
from views import about, clinical_agent, dashboard, home, patient_workspace


st.set_page_config(
    page_title=f"{APP_NAME} · Cardiac Rupture Risk Decision Support",
    page_icon="assets/smart-heart-shield-icon.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_global_styles()

if not require_access():
    st.stop()

st.session_state.setdefault("active_page", "Home")
st.session_state.setdefault("selected_encounter_key", None)
st.session_state.setdefault("chat_history", {})
st.session_state.setdefault("pending_agent_questions", {})
st.session_state.setdefault("latest_model_predictions", {})

# Legacy versions used a cross-patient global feed. Current records are isolated by encounter_key.
for obsolete_chat_key in (
    "agent_chat_feed",
    "agent_chat_feed_loaded_encounters",
    "agent_chat_started",
):
    st.session_state.pop(obsolete_chat_key, None)

page = render_navigation()

if st.session_state.get("_last_rendered_page") != page:
    st.html(
        """
        <script>
          const main = document.querySelector('[data-testid="stMain"]');
          if (main) main.scrollTo({top: 0, left: 0, behavior: 'instant'});
        </script>
        """,
        unsafe_allow_javascript=True,
    )
    st.session_state._last_rendered_page = page

ROUTES = {
    "Home": home.render,
    "Emergency Overview": dashboard.render,
    "Clinical Assistant": clinical_agent.render,
    "Patient Details": patient_workspace.render,
    "About": about.render,
}

ROUTES.get(page, home.render)()
render_footer()
