from __future__ import annotations

import base64
import html
from functools import lru_cache
from pathlib import Path


BRAND_MARK_SOURCE = (
    Path(__file__).resolve().parents[1] / "assets" / "navigation-brand-logo.png"
)


@lru_cache(maxsize=1)
def _brand_mark_data_uri() -> str:
    try:
        encoded = base64.b64encode(BRAND_MARK_SOURCE.read_bytes()).decode("ascii")
    except OSError:
        return ""
    return f"data:image/png;base64,{encoded}"


def brand_logo_markup(*, modifier: str = "") -> str:
    mark_uri = _brand_mark_data_uri()
    modifier_class = f" {html.escape(modifier, quote=True)}" if modifier else ""
    mark = (
        f'<span class="brand-logo-mark" aria-hidden="true">'
        f'<img src="{html.escape(mark_uri, quote=True)}" alt=""></span>'
        if mark_uri
        else '<span class="material-symbols-rounded brand-logo-fallback" '
        'aria-hidden="true">health_and_safety</span>'
    )
    return f"""
      <span class="brand-logo{modifier_class}" role="img" aria-label="SmartHeartShield logo">
        {mark}
        <span class="brand-logo-copy" aria-hidden="true">
          <span class="brand-logo-word">SmartHeartShield</span>
          <svg class="brand-logo-pulse" viewBox="0 0 180 12" focusable="false">
            <path d="M1 6 H96 L102 6 L106 1 L111 11 L116 3 L121 6 H179" />
          </svg>
        </span>
      </span>
    """
