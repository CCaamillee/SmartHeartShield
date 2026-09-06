from __future__ import annotations

import html

import streamlit as st

from components.header import render_header, section_header
from config import APP_NAME, APP_SUBTITLE


ABOUT_CARD_IMAGES = {
    "emergency": "assets/about-emergency-overview.png",
    "diagnosis": "assets/about-assisted-diagnosis.png",
    "timeline": "assets/about-patient-timeline.png",
}


def _about_card(
    container: st.delta_generator.DeltaGenerator,
    *,
    slug: str,
    icon: str,
    title: str,
    text: str,
    points: tuple[str, ...],
) -> None:
    point_markup = "".join(
        "<div class='about-feature-point'>"
        "<span class='material-symbols-rounded' aria-hidden='true'>check_circle</span>"
        f"<span>{html.escape(point)}</span>"
        "</div>"
        for point in points
    )
    with container.container(
        border=False,
        height="stretch",
        key=f"about_card_{slug}",
    ):
        st.image(ABOUT_CARD_IMAGES[slug], width="stretch")
        st.html(
            f"""
            <article class="about-feature-content">
              <div class="about-feature-icon" aria-hidden="true">
                <span class="material-symbols-rounded">{icon}</span>
              </div>
              <div class="about-feature-title">{html.escape(title)}</div>
              <div class="about-feature-copy">{html.escape(text)}</div>
              <div class="about-feature-points">{point_markup}</div>
            </article>
            """
        )


def render() -> None:
    render_header(
        "About",
        f"Learn about {APP_NAME}, its capabilities, and its principles for clinical use.",
        eyebrow=None,
    )

    st.markdown(
        f"""
        <div class="about-callout">
          <div class="about-callout-title">{APP_SUBTITLE}</div>
          <p>
            {APP_NAME} supports clinical review and research related to cardiac rupture. It structures real encounter data
            from uploaded workbooks and brings together demographics, diagnoses, examinations, laboratory tests,
            treatments, and progress notes so clinicians can find information, verify key records, and review an encounter efficiently.
          </p>
          <p>
            Each encounter is treated as a separate review scope. The system uses <code>regno</code> to identify a patient and
            <code>admno</code> to distinguish different encounters, preventing records from separate visits from being merged.
            Pages show only workbook fields and results that the current logic can verify. Missing information is marked as
            “No record” or “Undetermined.” The system organizes evidence; it does not replace clinical judgment or care decisions.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    section_header("Core Pages")
    cards = st.columns(3, gap="medium")
    _about_card(
        cards[0],
        slug="emergency",
        icon="emergency",
        title="Emergency Overview",
        text=(
            "The Emergency Overview is the central entry point for browsing real patients and encounters. It summarizes cohort size, encounter coverage, and verifiable key fields. "
            "Clinicians can identify records that need attention, then narrow the list by identifier, diagnosis, and time."
        ),
        points=(
            "Summarizes real-data coverage for patients, encounters, target-event labels, and procedures",
            "Supports combined searches using patient IDs, encounter IDs, and available clinical fields",
            "Provides sorting and pagination for efficient review of large record sets",
            "Carries a stable identifier directly into the selected patient and encounter",
        ),
    )
    _about_card(
        cards[1],
        slug="diagnosis",
        icon="clinical_notes",
        title="Clinical Assistant",
        text=(
            "The Clinical Assistant combines patient selection, record review, and agent Q&A in one workspace, always scoped to the selected encounter. "
            "Use the left panel to find a patient and inspect structured records, and the right panel to ask questions about notes, tests, the clinical timeline, and risk-result boundaries."
        ),
        points=(
            "Searches by patient ID, encounter ID, and available workbook fields",
            "Groups demographics, diagnoses, tests, treatments, and progress notes",
            "Provides common questions for quick review of records, tests, and the timeline",
            "Restricts agent answers to the current encounter and flags unavailable or insufficient evidence",
        ),
    )
    _about_card(
        cards[2],
        slug="timeline",
        icon="timeline",
        title="Patient Details",
        text=(
            "Patient Details organizes a complete encounter by category, including demographics, diagnoses, tests, treatments, procedures, and progress notes. "
            "A longitudinal timeline uses real workbook timestamps so users can review the course from outpatient, emergency, or admission events through discharge or the data-window cutoff."
        ),
        points=(
            "Uses regno for patient identity and admno to separate encounters",
            "Orders timeline events by real workbook timestamps without inventing missing events or times",
            "Shows event type, summary, and source category, with details available on demand",
            "Groups demographics, diagnoses, tests, treatments, progress notes, and risk-related fields",
        ),
    )

    section_header("Principles for Clinical Use")
    with st.container(border=True, key="about_clinical_notice"):
        st.subheader(":material/health_and_safety: Clinical Notice")
        st.markdown(
            """
            - The system supports clinical review and research; it does not replace diagnosis, management, or treatment decisions.
            - Risk results must be interpreted alongside the complete record, examinations, laboratory tests, and bedside findings.
            - Missing fields are shown as “No record” or “Undetermined”; missing data must not be treated as normal or negative.
            - `label` is a retrospective target-event label, and `cutoff_time` is the end of a 15-day data window. Neither represents a probability, risk tier, or predicted rupture time.
            """
        )
