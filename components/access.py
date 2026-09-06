from __future__ import annotations

import hmac
import os

import streamlit as st


def _configured_password() -> str:
    environment_value = os.getenv("APP_ACCESS_PASSWORD", "").strip()
    if environment_value:
        value = environment_value
    else:
        try:
            secret_value = st.secrets.get("APP_ACCESS_PASSWORD", "")
            value = str(secret_value).strip() if secret_value else ""
        except Exception:
            value = ""
    if any(term in value.lower() for term in ("replace", "替换", "changeme", "example")):
        return ""
    return value


def require_access() -> bool:
    """Apply an optional shared-password gate for private demonstrations."""
    expected = _configured_password()
    if not expected:
        return True
    if st.session_state.get("access_authenticated") is True:
        return True

    st.markdown("## SmartHeartShield · Restricted Access")
    st.caption("This demo contains de-identified clinical summaries. Enter the password shared by your instructor or project team.")
    with st.form("access_login", border=True):
        supplied = st.text_input("Access password", type="password")
        submitted = st.form_submit_button("Enter", type="primary", width="stretch")
    if submitted:
        if hmac.compare_digest(supplied, expected):
            st.session_state.access_authenticated = True
            st.rerun()
        else:
            st.error("Incorrect access password.")
    return False
