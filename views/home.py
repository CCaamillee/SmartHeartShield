from __future__ import annotations

import streamlit as st

from config import APP_NAME, APP_POSITIONING, APP_SUBTITLE


HERO_ILLUSTRATION_PATH = "assets/home-hero-heart-cartoon.png"


def _go(page: str) -> None:
    st.session_state.pending_page = page


def _feature_card(
    container,
    *,
    card_key: str,
    title: str,
    description: str,
    icon: str,
    page: str,
) -> None:
    with container.container(
        border=True,
        height="stretch",
        gap="xsmall",
        key=f"home_feature_card_{card_key}",
    ):
        st.html(
            f"""
            <div class="home-feature-heading">
              <div class="feature-icon" aria-hidden="true">
                <span class="material-symbols-rounded">{icon}</span>
              </div>
              <div class="feature-title">{title}</div>
            </div>
            """
        )
        st.html(f'<div class="home-feature-copy">{description}</div>')
        with st.container(key=f"home_feature_action_{card_key}"):
            st.button(
                f"Open {title}",
                type="primary",
                width="stretch",
                key=f"home_to_{page}",
                on_click=_go,
                args=(page,),
            )


def render() -> None:
    with st.container(key="home_page", gap="small"):
        hero_text, hero_logo = st.columns(
            [3.25, 1.3],
            gap="medium",
            vertical_alignment="center",
        )
        with hero_text:
            st.html(
                f"""
                <div class="home-hero">
                  <div class="hero-kicker">CLINICAL DECISION SUPPORT</div>
                  <div class="hero-title">{APP_NAME}｜{APP_SUBTITLE}</div>
                  <div class="hero-copy">{APP_POSITIONING}. The system organizes only the real encounter records in the uploaded workbook, helping clinicians find information, verify risk signals, and follow the course of care.</div>
                  <div class="hero-meta">
                    <span>Cardiac Rupture Risk Monitoring</span>
                    <span>Emergency Cohort Overview</span>
                    <span>Assisted Clinical Review</span>
                    <span>Encounter-level Timeline</span>
                  </div>
                </div>
                """
            )
        with hero_logo:
            with st.container(
                horizontal_alignment="center",
                key="home_hero_logo",
            ):
                st.image(HERO_ILLUSTRATION_PATH, width=300)

        cards = st.columns(3, gap="small", vertical_alignment="top")
        _feature_card(
            cards[0],
            card_key="overview",
            title="Emergency Overview",
            description="Summarize patients, encounters, risk tiers, and priority records so clinicians can quickly identify cases that need review.",
            icon="emergency",
            page="Emergency Overview",
        )
        _feature_card(
            cards[1],
            card_key="assistant",
            title="Clinical Assistant",
            description="Bring together clinical notes, diagnoses, tests, treatments, and model results, with guided Q&A for evidence review.",
            icon="clinical_notes",
            page="Clinical Assistant",
        )
        _feature_card(
            cards[2],
            card_key="detail",
            title="Patient Details",
            description="Review demographics, diagnoses, tests, treatments, procedures, progress notes, and risk predictions for one encounter in chronological order.",
            icon="timeline",
            page="Patient Details",
        )

        st.info(
            "This system supports clinical review and research. It does not replace a physician's diagnosis, management, or treatment decisions.",
            icon=":material/info:",
        )
