from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st


HOME_BACKGROUND_PATH = (
    Path(__file__).resolve().parents[1] / "assets" / "home-heart-background.png"
)


GLOBAL_CSS = """
<style>
:root {
  --primary: #0b5ea8;
  --primary-dark: #0a487e;
  --primary-soft: #eaf3fb;
  --nav: #0b4f8a;
  --text: #172b3a;
  --muted: #5f7180;
  --border: #d8e1e8;
  --surface: #ffffff;
  --surface-soft: #f5f8fb;
  --red: #c93636;
  --orange: #b76513;
  --green: #19734f;
  --violet: #7048b7;
  --gray: #66788a;
}

html, body, .stApp {
  font-family: "Microsoft YaHei UI", "PingFang SC", "Noto Sans CJK SC", sans-serif;
}
.material-symbols-rounded {
  font-family: "Material Symbols Rounded" !important;
  font-weight: 400;
  font-style: normal;
  line-height: 1;
  letter-spacing: normal;
  text-transform: none;
  white-space: nowrap;
  word-wrap: normal;
  direction: ltr;
  font-feature-settings: "liga";
  -webkit-font-feature-settings: "liga";
  -webkit-font-smoothing: antialiased;
}
.stApp { background: #f5f7fa; color: var(--text); }
[data-testid="stSidebar"] { display: none; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMain"] { overflow-x: clip; }
.block-container {
  max-width: 1440px;
  min-height: 100vh;
  padding: 1rem 2rem 0;
  display: flex;
  flex-direction: column;
}

/* Global navigation */
.st-key-top_navigation {
  position: relative;
  width: 100vw;
  min-width: 100vw;
  max-width: none;
  flex: 0 0 auto !important;
  box-sizing: border-box;
  margin: -1rem calc(50% - 50vw) 1.25rem;
  padding: .72rem 2rem;
  color: #fff;
  background: #0a568d;
  border-bottom: 1px solid rgba(255,255,255,.16);
  box-shadow: 0 4px 16px rgba(17, 48, 75, .18);
}
.stApp:has(.st-key-emergency_dashboard_page) .st-key-top_navigation,
.stApp:has(.st-key-clinical_agent_page) .st-key-top_navigation,
.stApp:has(.st-key-patient_detail_page) .st-key-top_navigation {
  margin-bottom: .9rem;
}
.st-key-top_navigation::after {
  display: none;
}
.st-key-top_navigation [data-testid="stHorizontalBlock"] > div:has(.st-key-brand_lockup) {
  flex: 0 0 252px !important;
  width: 252px !important;
  min-width: 252px !important;
  padding-right: .9rem;
  border-right: 1px solid rgba(255,255,255,.2);
}
.st-key-top_navigation [data-testid="stHorizontalBlock"] > div:has(.st-key-desktop_navigation) {
  flex: 1 1 auto !important;
  width: auto !important;
  min-width: 0 !important;
}
.st-key-top_navigation [data-testid="stHorizontalBlock"] > div:has(.st-key-mobile_navigation) {
  flex: 0 0 0 !important;
  width: 0 !important;
  min-width: 0 !important;
  overflow: hidden;
}
.st-key-brand_lockup [data-testid="stHtml"] { width: 100%; }
.brand-logo {
  width: 100%;
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: .42rem;
  color: #fff;
  line-height: 1;
}
.brand-logo-mark {
  width: 49px;
  height: 59px;
  flex: 0 0 49px;
  display: block;
  overflow: hidden;
}
.brand-logo-mark img {
  width: auto;
  max-width: none;
  height: 59px;
  display: block;
  filter: grayscale(1) brightness(0) invert(1);
}
.brand-logo-fallback {
  flex: 0 0 43px;
  color: #fff;
  font-size: 2.4rem;
}
.brand-logo-copy {
  min-width: 0;
  display: inline-flex;
  flex-direction: column;
  justify-content: center;
}
.brand-logo-word {
  color: #fff;
  font-family: "Arial Narrow", "Bahnschrift Condensed", "Segoe UI", sans-serif;
  font-size: 1.28rem;
  font-style: italic;
  font-weight: 800;
  letter-spacing: -.055em;
  white-space: nowrap;
}
.brand-logo-pulse {
  width: 100%;
  height: 10px;
  margin-top: .08rem;
  display: block;
  overflow: visible;
}
.brand-logo-pulse path {
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2.2;
}
.st-key-desktop_navigation {
  padding: 4px;
  background: rgba(4, 37, 65, .3);
  border: 1px solid rgba(255,255,255,.15);
  border-radius: 11px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.04);
}
.st-key-desktop_navigation .stButton > button {
  min-height: 2.35rem;
  color: #eef7ff;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  font-size: .86rem;
  font-weight: 600;
  white-space: nowrap;
}
.st-key-desktop_navigation .stButton > button:hover {
  color: #fff;
  background: rgba(255,255,255,.12);
  border-color: rgba(255,255,255,.16);
}
.st-key-desktop_navigation .stButton > button[kind="primary"] {
  color: var(--primary-dark);
  background: #fff;
  border-color: #fff;
  box-shadow: 0 2px 7px rgba(3, 37, 64, .18);
}
.st-key-desktop_navigation .stButton > button[kind="primary"]:hover {
  color: var(--primary-dark);
  background: #f5f9fc;
}
.st-key-mobile_navigation { display: none; }

/* Headings and sections */
.page-header { margin: .15rem 0 1.1rem; }
.stApp:has(.page-header--compact) .st-key-top_navigation { margin-bottom: .35rem; }
.stApp:has(.page-header--compact) .block-container > [data-testid="stVerticalBlock"] {
  gap: .45rem;
}
.page-header--compact { margin: 0 0 .2rem; }
.page-header--compact .page-title { margin-top: .18rem; }
.page-header--compact .page-description {
  margin-top: .28rem;
  line-height: 1.55;
}
.page-eyebrow { color: var(--primary); font-size: .72rem; font-weight: 750; letter-spacing: .12em; }
.page-title {
  margin-top: .25rem;
  color: var(--text);
  font-size: clamp(1.6rem, 2.35vw, 2.2rem);
  font-weight: 750;
  line-height: 1.25;
}
.page-description {
  max-width: 920px;
  margin-top: .42rem;
  color: var(--muted);
  font-size: .91rem;
  line-height: 1.72;
}
.section-head { margin: 1.35rem 0 .65rem; }
.section-head--compact { margin: .3rem 0 .42rem; }
.section-title {
  display: flex;
  align-items: center;
  gap: .5rem;
  color: var(--text);
  font-size: 1.05rem;
  font-weight: 720;
}
.section-title::before {
  content: "";
  width: 4px;
  height: 1.05rem;
  border-radius: 4px;
  background: var(--primary);
}

/* Home and about */
.home-hero {
  padding: clamp(1.2rem, 2.4vw, 1.85rem);
  background: linear-gradient(110deg, #f8fbfe 0%, #edf5fb 100%);
  border: 1px solid #d4e2ec;
  border-radius: 16px;
  box-shadow: 0 10px 28px rgba(23, 65, 99, .07);
}
.hero-kicker { color: var(--primary); font-size: .76rem; font-weight: 750; letter-spacing: .11em; }
.hero-title {
  max-width: 780px;
  margin: .38rem 0 .55rem;
  color: #12324c;
  font-size: clamp(1.75rem, 3vw, 2.65rem);
  font-weight: 760;
  line-height: 1.25;
}
.hero-copy { max-width: 780px; color: #50697d; font-size: .94rem; line-height: 1.72; }
.hero-meta { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .78rem; }
.hero-meta span {
  padding: .35rem .58rem;
  color: #315e82;
  font-size: .75rem;
  background: rgba(255,255,255,.82);
  border: 1px solid #d3e2ed;
  border-radius: 999px;
}
.stApp:has(.st-key-home_page) {
  background-color: #edf4f8;
  background-image:
    linear-gradient(180deg, rgba(244,248,251,.14), rgba(235,243,248,.24)),
    __HOME_BACKGROUND_IMAGE__;
  background-repeat: no-repeat;
  background-position: center top;
  background-size: cover;
  background-attachment: fixed;
}
.st-key-home_page {
  gap: .7rem;
  flex: 1 0 auto;
  padding: 0;
  background: transparent;
}
.st-key-home_page .home-hero {
  background:
    linear-gradient(110deg, rgba(251,253,255,.92), rgba(237,246,252,.86));
  backdrop-filter: blur(5px);
}
.st-key-home_page [data-testid="stVerticalBlockBorderWrapper"] {
  background: rgba(255,255,255,.88);
  border-radius: 13px;
  box-shadow: 0 3px 12px rgba(20, 54, 80, .035);
}
.st-key-home_page [data-testid="stVerticalBlockBorderWrapper"]:has(.home-feature-heading) {
  min-height: 190px;
  padding: .8rem .9rem;
  background: rgba(255,255,255,.88);
  border: 1.5px solid #5f93b3 !important;
  box-shadow: 0 4px 14px rgba(20, 74, 108, .1);
  transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
}
.st-key-home_page [data-testid="stVerticalBlockBorderWrapper"]:has(.home-feature-heading):hover {
  transform: translateX(3px);
  border-color: #397b9f !important;
  box-shadow: 0 8px 20px rgba(20, 74, 108, .15);
}
.st-key-home_page [data-testid="stVerticalBlockBorderWrapper"]:has(.home-feature-heading) > div {
  gap: .52rem;
}
.stApp:has(.st-key-home_page) .st-key-global_footer {
  width: 100vw;
  margin-right: calc(50% - 50vw);
  margin-left: calc(50% - 50vw);
  background: #0a568d;
  backdrop-filter: none;
}
.home-feature-heading {
  min-height: 46px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: .65rem;
}
.feature-icon {
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
  background: var(--primary-soft);
  border-radius: 10px;
}
.feature-icon .material-symbols-rounded {
  font-family: "Material Symbols Rounded" !important;
  font-size: 1.45rem;
  font-weight: 500;
  font-style: normal;
  line-height: 1;
  letter-spacing: normal;
  text-transform: none;
  white-space: nowrap;
  word-wrap: normal;
  direction: ltr;
  font-feature-settings: "liga";
  -webkit-font-feature-settings: "liga";
  -webkit-font-smoothing: antialiased;
}
.feature-title {
  color: var(--text);
  font-size: 1.02rem;
  font-weight: 720;
  line-height: 1.35;
  white-space: nowrap;
}
.home-feature-copy {
  min-height: 4.55rem;
  color: var(--muted);
  font-size: .82rem;
  line-height: 1.5;
}
[class*="st-key-home_feature_action_"] {
  width: 100%;
  margin-top: .28rem;
}
[class*="st-key-home_feature_action_"] .stButton > button {
  min-height: 2.35rem;
  padding: .4rem .72rem;
  color: #fff;
  background: #0b67a5;
  border: 1px solid #0b67a5;
  border-radius: 9px;
  box-shadow: 0 4px 11px rgba(11, 103, 165, .2);
  transition: transform .16s ease, background-color .16s ease, box-shadow .16s ease;
}
[class*="st-key-home_feature_action_"] .stButton > button:hover {
  color: #fff;
  background: #084f84;
  border-color: #084f84;
  transform: translateY(-1px);
  box-shadow: 0 7px 15px rgba(8, 79, 132, .24);
}
[class*="st-key-home_feature_action_"] .stButton > button:active {
  transform: translateY(0);
}
[class*="st-key-about_card_"] {
  position: relative;
  min-height: 410px;
  overflow: hidden;
  isolation: isolate;
  background: #073d70;
  border: 1px solid rgba(123, 194, 235, .38);
  border-radius: 16px;
  box-shadow: 0 12px 30px rgba(17, 55, 84, .16);
}
[class*="st-key-about_card_"]::after {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  background:
    linear-gradient(180deg, rgba(3, 35, 65, .22) 0%, rgba(3, 35, 65, .62) 55%, rgba(3, 30, 56, .92) 100%),
    linear-gradient(105deg, rgba(5, 45, 81, .86), rgba(5, 45, 81, .12));
}
[class*="st-key-about_card_"] > [data-testid="stElementContainer"]:has([data-testid="stImage"]) {
  position: absolute;
  inset: 0;
  z-index: 0;
  width: 100%;
  height: 100%;
}
[class*="st-key-about_card_"] [data-testid="stImage"],
[class*="st-key-about_card_"] [data-testid="stImage"] > div,
[class*="st-key-about_card_"] [data-testid="stImage"] img {
  width: 100% !important;
  height: 100% !important;
}
[class*="st-key-about_card_"] [data-testid="stImage"] img { object-fit: cover; }
[class*="st-key-about_card_"] > [data-testid="stElementContainer"]:has(.about-feature-content) {
  position: relative;
  z-index: 2;
  height: 100%;
}
.about-feature-content {
  min-height: 410px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  padding: 1.35rem;
  color: #fff;
}
.about-feature-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #e8fbff;
  background: rgba(35, 176, 212, .22);
  border: 1px solid rgba(158, 231, 247, .42);
  border-radius: 13px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.18);
  backdrop-filter: blur(8px);
}
.about-feature-icon .material-symbols-rounded { font-size: 1.55rem; }
.about-feature-title {
  margin-top: 1rem;
  color: #fff;
  font-size: 1.32rem;
  font-weight: 750;
}
.about-feature-copy {
  margin-top: .68rem;
  color: rgba(239, 248, 255, .9);
  font-size: .91rem;
  line-height: 1.78;
}
.about-feature-points {
  display: grid;
  gap: .58rem;
  margin-top: 1.15rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(196, 234, 250, .2);
}
.about-feature-point {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr);
  gap: .48rem;
  align-items: start;
  color: rgba(244, 250, 255, .94);
  font-size: .85rem;
  line-height: 1.62;
}
.about-feature-point .material-symbols-rounded {
  margin-top: .08rem;
  color: #7ee1ee;
  font-size: 1.08rem;
}
.st-key-about_clinical_notice {
  padding: 1.05rem 1.15rem;
  color: #355267;
  background: linear-gradient(120deg, #f8fbfd, #edf6fb);
  border-color: #cfdee8 !important;
  border-left: 4px solid var(--primary) !important;
  border-radius: 13px;
  box-shadow: 0 5px 16px rgba(23, 65, 99, .05);
}
.st-key-about_clinical_notice ul { margin-bottom: 0; }
.st-key-about_clinical_notice li { margin-bottom: .35rem; line-height: 1.65; }
.about-callout,
.instruction-panel {
  padding: 1rem 1.1rem;
  color: #2f536d;
  background: #eef6fc;
  border: 1px solid #cee0ed;
  border-left: 4px solid var(--primary);
  border-radius: 11px;
  line-height: 1.7;
}
.about-callout {
  padding: 1.2rem 1.35rem;
  font-size: .95rem;
  line-height: 1.8;
}
.about-callout-title {
  margin-bottom: .45rem;
  color: #173f5c;
  font-size: 1.08rem;
  font-weight: 760;
}
.about-callout p { margin: 0; }
.about-callout p + p { margin-top: .48rem; }
.about-callout code {
  padding: .08rem .32rem;
  color: #075d95;
  background: rgba(255,255,255,.74);
  border: 1px solid #d1e2ed;
  border-radius: 5px;
}
.instruction-panel strong { color: #173f60; }

/* Patient detail workspace */
.st-key-emergency_dashboard_page { gap: .72rem; }
.st-key-patient_detail_page { gap: .72rem; }
.st-key-patient_detail_page .page-header { margin-bottom: .25rem; }
.st-key-detail_selection_panel {
  padding: .95rem 1rem;
  background: linear-gradient(120deg, #fff 0%, #f7fafc 100%);
  border-color: #d5e1e9 !important;
  border-radius: 14px;
  box-shadow: 0 7px 22px rgba(23, 65, 99, .055);
}
.st-key-detail_selection_panel [data-testid="stExpander"] {
  background: #f7fafc;
  border-color: #d8e3ea;
}
.detail-patient-summary {
  overflow: hidden;
  background: #fff;
  border: 1px solid #d4e0e8;
  border-radius: 15px;
  box-shadow: 0 8px 24px rgba(23, 65, 99, .06);
}
.detail-summary-heading {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr) auto;
  gap: .8rem;
  align-items: center;
  padding: 1rem 1.1rem;
  color: #fff;
  background: linear-gradient(105deg, #0a4f88 0%, #0b67a8 62%, #1684ad 100%);
}
.detail-summary-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #e9fbff;
  background: rgba(255,255,255,.12);
  border: 1px solid rgba(255,255,255,.25);
  border-radius: 13px;
}
.detail-summary-icon .material-symbols-rounded { font-size: 1.5rem; }
.detail-summary-eyebrow {
  color: rgba(233, 247, 255, .78);
  font-size: .7rem;
  font-weight: 700;
  letter-spacing: .08em;
}
.detail-summary-title { margin-top: .2rem; font-size: 1.15rem; font-weight: 750; }
.detail-encounter-chip {
  display: flex;
  align-items: center;
  gap: .35rem;
  padding: .45rem .65rem;
  color: #f4fbff;
  font-size: .76rem;
  font-weight: 650;
  background: rgba(1, 35, 62, .22);
  border: 1px solid rgba(255,255,255,.2);
  border-radius: 999px;
}
.detail-encounter-chip .material-symbols-rounded { font-size: 1rem; }
.detail-summary-grid {
  display: grid;
  grid-template-columns: .8fr 1.2fr 2fr 1fr;
  gap: 1px;
  background: #dce5eb;
}
.detail-summary-item { min-width: 0; padding: .85rem .95rem; background: #fff; }
.detail-summary-label { color: #718391; font-size: .7rem; }
.detail-summary-value {
  margin-top: .25rem;
  color: #1d3b51;
  font-size: .82rem;
  font-weight: 650;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

/* Clinical agent workspace */
.st-key-clinical_agent_page {
  width: 100vw;
  min-width: 100vw;
  max-width: none;
  flex: 1 0 auto !important;
  box-sizing: border-box;
  margin: -1.25rem calc(50% - 50vw) 0;
  padding: 1rem 2rem 1.35rem;
  gap: .7rem;
  background: #f3f7fa;
}
.st-key-clinical_agent_page .page-header { margin: .15rem 0 .55rem; }
.st-key-clinical_agent_page .page-description { max-width: none; }
.st-key-agent_patient_panel,
.st-key-agent_chat_panel {
  height: 100%;
  padding: .92rem;
  background: rgba(255,255,255,.98);
  border-color: #d5e1e9 !important;
  border-radius: 14px;
  box-shadow: 0 8px 24px rgba(23, 65, 99, .06);
}
.st-key-agent_patient_panel .profile-strip {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: .45rem 0 .68rem;
}
.st-key-agent_patient_panel .profile-item { padding: .65rem .7rem; }
.st-key-agent_patient_panel .profile-value { font-size: .78rem; }
.st-key-agent_patient_panel [data-testid="stForm"] { margin-bottom: .1rem; }
.st-key-agent_chat_panel > [data-testid="stElementContainer"]:last-child {
  margin-top: auto;
  padding-top: .7rem;
}
.st-key-agent_chat_feed {
  scrollbar-gutter: stable;
  overscroll-behavior: contain;
  background: #fbfdfe;
  border: 1px solid #e3ebf0;
  border-radius: 10px;
}
.agent-question-scroll-anchor {
  display: block;
  width: 100%;
  height: 0;
  scroll-margin-top: .75rem;
}
.st-key-agent_empty_prompt {
  flex: 1 1 auto !important;
  min-height: 0;
  justify-content: center;
}
.agent-empty-state {
  min-height: 255px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: .48rem;
  padding: 2rem 1rem;
  color: #64798a;
  text-align: center;
  background: linear-gradient(180deg, #fff 0%, #f8fbfd 100%);
  border: 1px solid #dfe8ee;
  border-radius: 12px;
}
.agent-empty-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  color: #fff;
  font-size: 1.55rem;
  font-weight: 700;
  line-height: 1;
  background: linear-gradient(135deg, #1779c6, #17a7b9);
  border-radius: 14px;
  box-shadow: 0 7px 16px rgba(16, 111, 169, .18);
}
.agent-empty-state strong {
  color: #173c57;
  font-size: 1.08rem;
}
.agent-empty-state > span:last-child {
  max-width: 360px;
  font-size: .78rem;
  line-height: 1.55;
}

/* Metrics, badges, profile */
[data-testid="stMetric"] {
  min-width: 190px;
  background: #fff;
  border-color: var(--border) !important;
  box-shadow: 0 3px 12px rgba(20, 54, 80, .04);
}
[data-testid="stMetricValue"] { color: #163751; font-weight: 720; }
[data-testid="stMetricLabel"] { color: #536b7d; font-weight: 600; }
.model-focus-panel {
  margin: .15rem 0 .95rem;
  padding: 1rem;
  background: linear-gradient(145deg, rgba(255,255,255,.98), rgba(245,249,252,.98));
  border: 1px solid #d4e1ea;
  border-radius: 14px;
  box-shadow: 0 9px 26px rgba(22, 55, 81, .07);
}
.model-focus-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: .82rem;
}
.model-focus-kicker {
  display: block;
  margin-bottom: .22rem;
  color: #0b67ac;
  font-size: .67rem;
  font-weight: 760;
  letter-spacing: .11em;
}
.model-focus-heading h3 {
  margin: 0;
  color: #173c57;
  font-size: 1.05rem;
  line-height: 1.4;
}
.model-focus-heading p {
  margin: .26rem 0 0;
  color: #64798a;
  font-size: .76rem;
  line-height: 1.55;
}
.model-focus-scope {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: .3rem;
  padding: .38rem .62rem;
  color: #165d8c;
  font-size: .72rem;
  font-weight: 700;
  background: #eaf4fb;
  border: 1px solid #cce1ef;
  border-radius: 999px;
}
.model-focus-scope .material-symbols-rounded { font-size: 1rem; }
.model-focus-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: .72rem;
}
.model-focus-card {
  position: relative;
  min-width: 0;
  padding: .85rem .9rem .82rem;
  overflow: hidden;
  background: #f5f8fb;
  border: 1px solid #d8e3ea;
  border-radius: 12px;
}
.model-focus-card::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: var(--model-accent, #4f7f9f);
}
.model-focus-card-head {
  display: flex;
  align-items: center;
  gap: .32rem;
  color: var(--model-accent, #4f6f87);
  font-size: .7rem;
  font-weight: 760;
}
.model-focus-card-head .material-symbols-rounded { font-size: 1rem; }
.model-focus-value {
  display: block;
  margin-top: .34rem;
  color: var(--model-value, #173c57);
  font-size: 2rem;
  font-weight: 800;
  line-height: 1;
}
.model-focus-card h4 {
  margin: .4rem 0 .18rem;
  color: #203c50;
  font-size: .83rem;
  line-height: 1.35;
}
.model-focus-card p {
  margin: 0;
  color: #5f7383;
  font-size: .69rem;
  line-height: 1.55;
}
.model-focus-card--review {
  grid-column: span 5;
  --model-accent: #bd2f3b;
  --model-value: #a61f2d;
  background: linear-gradient(135deg, #fff0f1, #fff7f7);
  border-color: #efc6ca;
}
.model-focus-card--review .model-focus-value { font-size: 2.8rem; }
.model-focus-card--positive {
  grid-column: span 4;
  --model-accent: #d05239;
  --model-value: #b43b27;
  background: linear-gradient(135deg, #fff3ef, #fff9f7);
  border-color: #efcfc5;
}
.model-focus-card--positive .model-focus-value { font-size: 2.45rem; }
.model-focus-card--total {
  grid-column: span 3;
  --model-accent: #1c6fa9;
  background: linear-gradient(135deg, #edf6fc, #f7fbfe);
  border-color: #cbdfea;
}
.model-focus-card--high {
  grid-column: span 6;
  --model-accent: #c93636;
  --model-value: #ad2727;
  background: linear-gradient(135deg, #ffeded, #fff8f8);
  border-color: #efc1c1;
}
.model-focus-card--high .model-focus-value { font-size: 2.55rem; }
.model-focus-card--medium {
  grid-column: span 4;
  --model-accent: #b76513;
  --model-value: #9d550f;
  background: linear-gradient(135deg, #fff5e5, #fffbf4);
  border-color: #edd6ad;
}
.model-focus-card--medium .model-focus-value { font-size: 2.15rem; }
.model-focus-card--low {
  grid-column: span 2;
  --model-accent: #19734f;
  --model-value: #176545;
  background: linear-gradient(135deg, #eaf7f1, #f7fcfa);
  border-color: #c5e3d7;
}
.model-focus-card--hero {
  grid-column: span 5;
  min-height: 176px;
  padding: 1rem 1.05rem;
  --model-accent: #bd2f3b;
  --model-value: #9f1f2c;
  background: linear-gradient(135deg, #fde9eb 0%, #fff4f4 62%, #fffafa 100%);
  border-color: #eab9be;
  box-shadow: 0 10px 24px rgba(172, 39, 52, .11);
}
.model-focus-card--hero .model-focus-value { font-size: 3.35rem; }
.model-focus-card--hero h4 { font-size: .92rem; }
.model-focus-card--critical {
  grid-column: span 3;
  --model-accent: #d05239;
  --model-value: #ad3826;
  background: linear-gradient(135deg, #fff0eb, #fff9f7);
  border-color: #edc9bf;
}
.model-focus-card--critical .model-focus-value { font-size: 2.55rem; }
.model-focus-card--cohort {
  grid-column: span 4;
  --model-accent: #1c6fa9;
  --model-value: #175b8a;
  background: linear-gradient(135deg, #edf6fc, #f8fbfe);
  border-color: #c9dfed;
}
.model-focus-value small { font-size: .78rem; font-weight: 700; }
.model-focus-value--compact { font-size: 1.72rem; letter-spacing: -.035em; }
.model-window-row {
  display: flex;
  align-items: center;
  gap: .7rem;
  margin-top: .72rem;
  padding: .68rem .76rem;
  color: #3f5d72;
  font-size: .72rem;
  background: #fff;
  border: 1px solid #dde7ed;
  border-radius: 10px;
}
.model-window-row > strong { flex: 0 0 auto; color: #244962; }
.model-window-row > div { display: flex; flex-wrap: wrap; gap: .42rem; }
.model-window-chip {
  display: inline-flex;
  align-items: center;
  gap: .38rem;
  padding: .28rem .5rem;
  color: #42647b;
  background: #f1f7fb;
  border: 1px solid #d6e6f0;
  border-radius: 999px;
}
.model-window-chip strong { color: #145f95; }
.model-window-empty { color: #758796; }
.model-focus-note {
  display: flex;
  align-items: flex-start;
  gap: .42rem;
  margin-top: .65rem;
  padding: .66rem .72rem;
  color: #6f4b22;
  font-size: .7rem;
  line-height: 1.6;
  background: #fff9eb;
  border-left: 3px solid #d59a37;
  border-radius: 8px;
}
.model-focus-note .material-symbols-rounded { margin-top: .08rem; font-size: 1rem; }
.model-focus-source {
  margin: .48rem .1rem 0;
  color: #7a8c99;
  font-size: .66rem;
}
.model-focus-unavailable {
  display: flex;
  align-items: flex-start;
  gap: .7rem;
  margin: .1rem 0 .9rem;
  padding: .88rem 1rem;
  color: #607687;
  background: #f5f8fa;
  border: 1px solid #dce5eb;
  border-radius: 12px;
}
.model-focus-unavailable > .material-symbols-rounded { color: #678092; font-size: 1.35rem; }
.model-focus-unavailable strong { color: #294b63; font-size: .84rem; }
.model-focus-unavailable p { margin: .24rem 0 0; font-size: .72rem; line-height: 1.6; }
.st-key-risk_treatment_recommendations {
  margin-bottom: .95rem;
  background: linear-gradient(145deg, #fff, #f7fafc);
  box-shadow: 0 7px 20px rgba(22, 55, 81, .05);
}
.st-key-treatment_advice_high,
.st-key-treatment_advice_medium,
.st-key-treatment_advice_low {
  min-height: 100%;
  box-shadow: 0 4px 14px rgba(22, 55, 81, .04);
}
.st-key-treatment_advice_high {
  background: #fff5f5;
  border-left: 4px solid #c93636 !important;
}
.st-key-treatment_advice_medium {
  background: #fff9ee;
  border-left: 4px solid #b76513 !important;
}
.st-key-treatment_advice_low {
  background: #f2faf6;
  border-left: 4px solid #19734f !important;
}
.st-key-treatment_advice_high h4,
.st-key-treatment_advice_medium h4,
.st-key-treatment_advice_low h4 {
  margin-top: .35rem;
  color: #24475e;
  font-size: .92rem;
}
.st-key-treatment_advice_high li,
.st-key-treatment_advice_medium li,
.st-key-treatment_advice_low li {
  color: #506978;
  font-size: .75rem;
  line-height: 1.62;
}
.risk-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: .55rem;
  padding: .72rem .82rem;
  color: var(--muted);
  font-size: .78rem;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 10px;
}
.risk-badge {
  display: inline-flex;
  align-items: center;
  gap: .3rem;
  padding: .25rem .5rem;
  font-size: .74rem;
  font-weight: 700;
  border: 1px solid currentColor;
  border-radius: 999px;
}
.risk-badge::before { content: "●"; font-size: .58rem; }
.risk-HIGH { color: var(--red); background: #fff1f1; }
.risk-MEDIUM { color: var(--orange); background: #fff6e9; }
.risk-LOW { color: var(--green); background: #edf8f3; }
.risk-UNKNOWN { color: var(--gray); background: #f1f4f6; }
.patient-risk-panel {
  --patient-risk-accent: #66788a;
  --patient-risk-soft: #f3f6f8;
  margin-bottom: .75rem;
  padding: 1rem;
  overflow: hidden;
  background: linear-gradient(140deg, var(--patient-risk-soft), #fff 70%);
  border: 1px solid color-mix(in srgb, var(--patient-risk-accent) 30%, white);
  border-left: 6px solid var(--patient-risk-accent);
  border-radius: 13px;
  box-shadow: 0 8px 22px rgba(23, 55, 79, .07);
}
.patient-risk-panel--high { --patient-risk-accent: #c93636; --patient-risk-soft: #fdebed; }
.patient-risk-panel--medium { --patient-risk-accent: #b76513; --patient-risk-soft: #fff3df; }
.patient-risk-panel--low { --patient-risk-accent: #19734f; --patient-risk-soft: #eaf7f1; }
.patient-risk-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: .8rem;
  margin-bottom: .78rem;
}
.patient-risk-kicker {
  display: block;
  color: var(--patient-risk-accent);
  font-size: .64rem;
  font-weight: 780;
  letter-spacing: .1em;
}
.patient-risk-heading h3 { margin: .2rem 0 0; color: #173c57; font-size: 1.02rem; }
.patient-risk-grid {
  display: grid;
  grid-template-columns: 1.45fr repeat(3, minmax(0, 1fr));
  gap: .58rem;
}
.patient-risk-primary,
.patient-risk-fact {
  min-width: 0;
  padding: .72rem .78rem;
  background: rgba(255,255,255,.8);
  border: 1px solid rgba(137, 158, 173, .25);
  border-radius: 9px;
}
.patient-risk-primary > span,
.patient-risk-fact > span { display: block; color: #718391; font-size: .68rem; }
.patient-risk-primary > strong {
  display: block;
  margin-top: .25rem;
  color: var(--patient-risk-accent);
  font-size: 1.65rem;
  line-height: 1.15;
}
.patient-risk-primary p { margin: .28rem 0 0; color: #536b7d; font-size: .7rem; line-height: 1.45; }
.patient-risk-fact > strong {
  display: block;
  margin-top: .34rem;
  color: #294b63;
  font-size: .9rem;
  line-height: 1.4;
  overflow-wrap: anywhere;
}
.rupture-forecast {
  --forecast-accent: #a52c37;
  --forecast-heading: #8f222d;
  --forecast-soft: #fff1f2;
  --forecast-border: #edc2c6;
  --forecast-copy: #775b5f;
  margin: .82rem 0;
  padding: 1rem;
  background: linear-gradient(135deg, var(--forecast-soft), #fff);
  border: 1px solid var(--forecast-border);
  border-radius: 13px;
}
.rupture-forecast--failure {
  --forecast-accent: #c93643;
  --forecast-heading: #8f222d;
  --forecast-soft: #fff0f1;
  --forecast-border: #efb9bf;
  --forecast-copy: #75565a;
}
.rupture-forecast--success {
  --forecast-accent: #248b5c;
  --forecast-heading: #17603f;
  --forecast-soft: #edf9f2;
  --forecast-border: #a9dbc0;
  --forecast-copy: #536b61;
}
.rupture-forecast-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: .8rem;
}
.rupture-forecast-kicker {
  color: var(--forecast-accent);
  font-size: .65rem;
  font-weight: 780;
  letter-spacing: .1em;
}
.rupture-forecast-heading h4 { margin: .25rem 0 0; color: var(--forecast-heading); font-size: 1rem; }
.rupture-forecast-chip {
  flex: 0 0 auto;
  padding: .28rem .5rem;
  color: #fff;
  font-size: .67rem;
  font-weight: 720;
  background: var(--forecast-accent);
  border: 1px solid var(--forecast-accent);
  border-radius: 999px;
}
.rupture-forecast-disclaimer {
  margin: .52rem 0 .75rem;
  color: var(--forecast-copy);
  font-size: .7rem;
  line-height: 1.55;
}
.rupture-forecast-track {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.rupture-forecast-item {
  --forecast-node: #4d7e9e;
  --forecast-node-soft: #bdd0dc;
  position: relative;
  min-width: 0;
}
.rupture-forecast-item--failure {
  --forecast-node: #c93643;
  --forecast-node-soft: #e7b4bb;
}
.rupture-forecast-item--success {
  --forecast-node: #248b5c;
  --forecast-node-soft: #a9d8c2;
}
.rupture-forecast-time { color: var(--forecast-node); font-size: .7rem; font-weight: 760; }
.rupture-forecast-rail {
  position: relative;
  height: 18px;
  margin: .16rem 0 .2rem;
}
.rupture-forecast-rail::after {
  content: "";
  position: absolute;
  top: 8px;
  right: 0;
  left: 0;
  height: 2px;
  background: var(--forecast-node-soft);
}
.rupture-forecast-item:last-child .rupture-forecast-rail::after { right: 50%; }
.rupture-forecast-rail span {
  position: absolute;
  z-index: 1;
  top: 3px;
  left: 0;
  width: 12px;
  height: 12px;
  background: #fff;
  border: 3px solid var(--forecast-node);
  border-radius: 50%;
}
.rupture-forecast-copy { padding-right: .65rem; }
.rupture-forecast-copy strong { display: block; color: var(--forecast-node); font-size: .73rem; }
.rupture-forecast-copy span { display: block; margin-top: .18rem; color: var(--forecast-copy); font-size: .66rem; line-height: 1.48; }
.profile-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  margin: .8rem 0 1rem;
  overflow: hidden;
  background: var(--border);
  border: 1px solid var(--border);
  border-radius: 12px;
}
.profile-item { min-width: 0; padding: .82rem .9rem; background: #fff; }
.profile-label { color: #708292; font-size: .72rem; }
.profile-value {
  margin-top: .28rem;
  color: #1b394f;
  font-size: .88rem;
  font-weight: 650;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

/* Record cards and timeline */
.record-card {
  padding: .82rem .9rem;
  margin-bottom: .62rem;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 10px;
}
.record-label { color: #315a78; font-size: .78rem; font-weight: 720; }
.record-value { margin-top: .35rem; color: #344f63; font-size: .84rem; line-height: 1.72; }
.record-source { margin-top: .45rem; color: #81909c; font-size: .68rem; }
.timeline-item {
  display: grid;
  grid-template-columns: 142px 26px minmax(0, 1fr);
  gap: .55rem;
  align-items: stretch;
}
.timeline-time { padding-top: .8rem; color: #526a7d; font-size: .75rem; text-align: right; }
.timeline-rail { position: relative; display: flex; justify-content: center; }
.timeline-rail::after {
  content: "";
  position: absolute;
  top: 1.35rem;
  bottom: -.2rem;
  width: 2px;
  background: #d9e2e9;
}
.timeline-dot {
  position: relative;
  z-index: 1;
  width: 13px;
  height: 13px;
  margin-top: 1.05rem;
  background: #fff;
  border: 4px solid var(--event-color);
  border-radius: 50%;
  box-shadow: 0 0 0 3px #f5f7fa;
}
.timeline-card {
  padding: .72rem .82rem;
  margin: .25rem 0 .5rem;
  background: #fff;
  border: 1px solid var(--border);
  border-left: 4px solid var(--event-color);
  border-radius: 9px;
}
.timeline-title { color: var(--text); font-size: .88rem; font-weight: 720; }
.timeline-summary { margin-top: .3rem; color: #506779; font-size: .8rem; line-height: 1.65; }
.source-tag {
  display: inline-block;
  margin-top: .5rem;
  padding: .2rem .4rem;
  color: #63798b;
  font-size: .67rem;
  background: #f2f6f8;
  border-radius: 5px;
}
.empty-state {
  padding: 1.5rem;
  color: var(--muted);
  text-align: center;
  background: #fff;
  border: 1px dashed #cbd7e0;
  border-radius: 10px;
}

/* Native element refinement */
[data-testid="stForm"],
[data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--border); }
.stButton > button { border-radius: 8px; font-weight: 620; }
.stButton > button:hover { border-color: var(--primary); color: var(--primary); }
.stButton > button[kind="primary"] { color: #fff; background: var(--primary); border-color: var(--primary); }
.stButton > button[kind="primary"]:hover { color: #fff; background: var(--primary-dark); }
button:focus-visible, input:focus-visible, [role="option"]:focus-visible,
[role="row"]:focus-visible, a:focus-visible {
  outline: 3px solid #75b6e6 !important;
  outline-offset: 2px !important;
}
[data-testid="stDataFrame"] {
  overflow: hidden;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 10px;
}
.stTabs [data-baseweb="tab-list"] { gap: 4px; overflow-x: auto; border-bottom: 1px solid var(--border); }
.stTabs [data-baseweb="tab"] { min-width: max-content; font-size: .82rem; }
.stTabs [aria-selected="true"] { color: var(--primary); font-weight: 700; }

/* Footer */
.st-key-global_footer {
  width: 100vw;
  max-width: none;
  box-sizing: border-box;
  margin: auto calc(50% - 50vw) 0;
  padding: 0;
  color: #eaf6fd;
  background: #0a568d;
  border-top: 1px solid rgba(255,255,255,.18);
  box-shadow: 0 -5px 18px rgba(9, 54, 88, .11);
}
.st-key-global_footer::before {
  content: "";
  position: absolute;
  top: -1px;
  left: 50%;
  width: min(340px, 34vw);
  height: 2px;
  transform: translateX(-50%);
  background: linear-gradient(90deg, transparent, #1b80bc, transparent);
}
.global-footer-content {
  width: 100%;
  max-width: 1440px;
  min-height: 74px;
  box-sizing: border-box;
  margin: 0 auto;
  padding: .9rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
}
.global-footer-brand {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: .85rem;
}
.brand-logo--footer {
  width: 238px;
  flex: 0 0 238px;
}
.brand-logo--footer .brand-logo-mark {
  width: 54px;
  height: 65px;
  flex-basis: 54px;
}
.brand-logo--footer .brand-logo-mark img { height: 65px; }
.brand-logo--footer .brand-logo-word { font-size: 1.34rem; }
.global-footer-icon {
  width: 38px;
  height: 38px;
  flex: 0 0 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 1.25rem;
  background: linear-gradient(145deg, #0b66a5, #1194b4);
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(11, 94, 168, .16);
}
.global-footer-brand-copy {
  min-width: 0;
  display: block;
}
.global-footer-brand-copy strong {
  color: #f4fbff;
  font-size: .86rem;
  font-weight: 720;
  line-height: 1.35;
}
.global-footer-meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 1rem;
  color: #e3f2fa;
  font-size: .76rem;
  line-height: 1.45;
  text-align: left;
}
.global-footer-attribution {
  display: flex;
  align-items: center;
  gap: .72rem;
  color: #eaf6fd;
  font-size: .84rem;
  font-weight: 650;
  white-space: nowrap;
}
.global-footer-attribution i {
  width: 2px;
  height: 1.25rem;
  display: block;
  background: rgba(211, 239, 251, .62);
}
.global-footer-team {
  display: grid;
  justify-items: start;
  gap: .14rem;
  padding-left: 1rem;
  text-align: left;
  border-left: 2px solid rgba(211, 239, 251, .62);
}
.global-footer-meta a {
  color: #bfe9fb;
  font-size: .72rem;
  text-decoration: none;
}
.global-footer-meta a:hover,
.global-footer-meta a:focus-visible {
  color: #fff;
  text-decoration: underline;
}

@media (max-width: 960px) {
  .block-container { padding-left: 1.1rem; padding-right: 1.1rem; }
  [data-testid="stHorizontalBlock"]:has([class*="st-key-home_feature_card_"]) {
    flex-direction: column;
  }
  [data-testid="stHorizontalBlock"]:has([class*="st-key-home_feature_card_"]) > [data-testid="stColumn"] {
    width: 100% !important;
    flex: 0 0 auto !important;
  }
  .model-focus-card--review,
  .model-focus-card--high { grid-column: span 12; }
  .model-focus-card--positive,
  .model-focus-card--medium { grid-column: span 7; }
  .model-focus-card--total,
  .model-focus-card--low { grid-column: span 5; }
  .model-focus-card--hero { grid-column: span 12; }
  .model-focus-card--critical { grid-column: span 6; }
  .model-focus-card--cohort { grid-column: span 6; }
  .patient-risk-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  [data-testid="stHorizontalBlock"]:has([class*="st-key-about_card_"]) {
    flex-direction: column;
  }
  [data-testid="stHorizontalBlock"]:has([class*="st-key-about_card_"]) > [data-testid="stColumn"] {
    width: 100% !important;
    flex: 0 0 auto !important;
  }
  [class*="st-key-about_card_"] {
    flex: 0 0 auto !important;
    height: auto !important;
    min-height: 0;
    align-self: stretch;
  }
  [class*="st-key-about_card_"] > [data-testid="stElementContainer"]:has(.about-feature-content) {
    height: auto;
  }
  .about-feature-content { min-height: 0; }
  .detail-summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .st-key-clinical_agent_page { padding-left: 1.1rem; padding-right: 1.1rem; }
  .st-key-top_navigation {
    width: 100vw;
    margin-left: calc(50% - 50vw);
    margin-right: calc(50% - 50vw);
    padding-left: 1.1rem;
    padding-right: 1.1rem;
  }
  .st-key-top_navigation::after { right: 1.1rem; left: 1.1rem; }
  .st-key-top_navigation [data-testid="stHorizontalBlock"] > div:has(.st-key-brand_lockup) {
    flex-basis: 230px !important;
    width: 230px !important;
    min-width: 230px !important;
  }
  .brand-logo--header .brand-logo-word { font-size: 1.16rem; }
  .global-footer-content { padding-right: 1.1rem; padding-left: 1.1rem; }
  .profile-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 760px) {
  .block-container { padding-top: .75rem; }
  .model-focus-panel { padding: .8rem; }
  .model-focus-heading { flex-direction: column; }
  .model-focus-grid { grid-template-columns: 1fr; }
  .model-focus-card--review,
  .model-focus-card--positive,
  .model-focus-card--total,
  .model-focus-card--high,
  .model-focus-card--medium,
  .model-focus-card--low { grid-column: 1; }
  .model-focus-card--hero,
  .model-focus-card--critical,
  .model-focus-card--cohort { grid-column: 1; }
  .model-window-row { align-items: flex-start; flex-direction: column; }
  .patient-risk-heading,
  .rupture-forecast-heading { flex-direction: column; }
  .patient-risk-grid { grid-template-columns: 1fr; }
  .rupture-forecast-track { grid-template-columns: 1fr; gap: .42rem; }
  .rupture-forecast-item { display: grid; grid-template-columns: 64px 18px minmax(0, 1fr); }
  .rupture-forecast-time { padding-top: .1rem; }
  .rupture-forecast-rail { width: 18px; height: 100%; margin: 0; }
  .rupture-forecast-rail::after {
    top: 0;
    right: auto;
    bottom: -.5rem;
    left: 5px;
    width: 2px;
    height: auto;
  }
  .rupture-forecast-item:last-child .rupture-forecast-rail::after { display: none; }
  .rupture-forecast-rail span { top: 2px; left: 0; }
  .detail-summary-heading {
    grid-template-columns: 46px minmax(0, 1fr);
    padding: .85rem;
  }
  .detail-summary-icon { width: 42px; height: 42px; }
  .detail-encounter-chip {
    grid-column: 1 / -1;
    width: fit-content;
  }
  .detail-summary-grid { grid-template-columns: 1fr; }
  .st-key-detail_selection_panel { padding: .75rem; }
  .st-key-clinical_agent_page {
    margin-top: -.35rem;
    padding: .65rem 1rem 1rem;
  }
  .st-key-agent_patient_panel,
  .st-key-agent_chat_panel {
    padding: .7rem;
    border-radius: 12px;
  }
  .st-key-agent_patient_panel .profile-strip { grid-template-columns: 1fr; }
  .agent-empty-state { min-height: 180px; }
  .st-key-top_navigation {
    margin-top: -.75rem;
    padding-top: .55rem;
    padding-bottom: .55rem;
    background: #0a568d;
  }
  .st-key-top_navigation [data-testid="stHorizontalBlock"] { align-items: center; }
  .st-key-top_navigation [data-testid="stHorizontalBlock"] > div:has(.st-key-desktop_navigation) { display: none; }
  .st-key-top_navigation [data-testid="stHorizontalBlock"] > div:has(.st-key-mobile_navigation) { flex: 0 0 92px !important; width: 92px !important; }
  .st-key-top_navigation [data-testid="stHorizontalBlock"] > div:has(.st-key-brand_lockup) {
    flex: 1 1 auto !important;
    width: auto !important;
    min-width: 0 !important;
    padding-right: 0;
    border-right: 0;
  }
  .st-key-top_navigation [data-testid="stHorizontalBlock"] > div:has(.st-key-mobile_navigation) {
    min-width: 92px !important;
    overflow: visible;
  }
  .st-key-desktop_navigation { display: none; }
  .st-key-mobile_navigation { display: block; }
  .st-key-mobile_navigation button {
    color: #fff;
    border-color: rgba(255,255,255,.45);
    background: rgba(255,255,255,.08);
  }
  .brand-logo--header .brand-logo-mark { width: 39px; height: 48px; flex-basis: 39px; }
  .brand-logo--header .brand-logo-mark img { height: 48px; }
  .brand-logo--header .brand-logo-word { font-size: .98rem; }
  .page-title { font-size: 1.55rem; }
  .profile-strip { grid-template-columns: 1fr; }
  .timeline-item { grid-template-columns: 24px minmax(0, 1fr); gap: .42rem; }
  .timeline-time { grid-column: 2; padding: .25rem .05rem 0; text-align: left; font-weight: 650; }
  .timeline-rail { grid-column: 1; grid-row: 1 / span 2; }
  .timeline-card { grid-column: 2; margin-top: 0; }
  .st-key-home_page { gap: .6rem; }
  .st-key-home_page {
    padding: 0;
  }
  .home-hero { padding: 1.1rem; }
  .st-key-home_page [data-testid="stHorizontalBlock"] > div:has(.st-key-home_hero_logo) {
    display: none;
  }
  .home-feature-heading { min-height: 0; }
  .home-feature-copy { min-height: 0; }
  [class*="st-key-home_feature_action_"] .stButton > button {
    border-radius: 10px;
  }
  .global-footer-content {
    min-height: 0;
    padding-top: 1rem;
    padding-bottom: 1rem;
    flex-direction: column;
    gap: .72rem;
    text-align: center;
  }
  .global-footer-brand {
    justify-content: center;
    flex-direction: column;
    gap: .4rem;
  }
  .brand-logo--footer { width: 220px; flex-basis: auto; }
  .global-footer-meta {
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: .55rem;
    white-space: normal;
  }
  .global-footer-attribution { flex-wrap: wrap; justify-content: center; }
  .global-footer-team {
    justify-items: start;
    padding-top: .55rem;
    padding-left: 0;
    border-top: 1px solid rgba(211, 239, 251, .48);
    border-left: 0;
  }
  .global-footer-contact { text-align: center; }
}
</style>
"""


@lru_cache(maxsize=1)
def _home_background_css() -> str:
    try:
        encoded = base64.b64encode(HOME_BACKGROUND_PATH.read_bytes()).decode("ascii")
    except OSError:
        return "none"
    return f"url('data:image/png;base64,{encoded}')"


def inject_global_styles() -> None:
    st.html(
        GLOBAL_CSS.replace(
            "__HOME_BACKGROUND_IMAGE__",
            _home_background_css(),
        )
    )
