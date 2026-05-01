"""
ui_helpers.py — Reusable Streamlit UI components.
"""

from __future__ import annotations
from datetime import date
from typing import Optional

import streamlit as st

from modules.core import (
    DELAY_CATEGORIES, EXTERNAL_CATEGORIES, PartEntry, BASE_MARKS
)


# ── CSS injection ─────────────────────────────────────────────────────────────
DARK_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

  html, body, [data-testid="stAppViewContainer"] {
      background: #0D1B2A !important;
      color: #E0E0E0 !important;
      font-family: 'Space Grotesk', sans-serif;
  }
  [data-testid="stSidebar"] {
      background: #111827 !important;
      border-right: 1px solid #1F3044;
  }
  .stTabs [data-baseweb="tab-list"] {
      background-color: #111827 !important;
      border-bottom: 2px solid #1ABC9C;
  }
  .stTabs [data-baseweb="tab"] {
      color: #aaa !important;
      font-weight: 600;
  }
  .stTabs [aria-selected="true"] {
      color: #1ABC9C !important;
      background-color: #0D1B2A !important;
  }
  div[data-testid="stExpander"] {
      background: #111827;
      border: 1px solid #1F3044;
      border-radius: 8px;
  }
  .metric-card {
      background: #111827;
      border: 1px solid #1F3044;
      border-radius: 10px;
      padding: 16px 20px;
      text-align: center;
  }
  .metric-card .label {
      font-size: 0.72rem;
      color: #aaa;
      text-transform: uppercase;
      letter-spacing: 1px;
  }
  .metric-card .value {
      font-size: 1.9rem;
      font-weight: 700;
      line-height: 1.2;
  }
  .dept-header {
      background: linear-gradient(90deg, #1B4F72 0%, #0D1B2A 100%);
      border-left: 4px solid #1ABC9C;
      padding: 8px 16px;
      border-radius: 4px;
      font-weight: 700;
      font-size: 1.05rem;
      margin-bottom: 8px;
  }
  .delay-badge-external {
      background: #154360;
      color: #85C1E9;
      padding: 2px 10px;
      border-radius: 20px;
      font-size: 0.78rem;
      font-weight: 600;
  }
  .delay-badge-internal {
      background: #4A0E0E;
      color: #F1948A;
      padding: 2px 10px;
      border-radius: 20px;
      font-size: 0.78rem;
      font-weight: 600;
  }
  .stButton>button {
      background: #1ABC9C;
      color: #0D1B2A;
      font-weight: 700;
      border: none;
      border-radius: 6px;
  }
  .stButton>button:hover {
      background: #17A589;
  }
  h1, h2, h3 { color: #E0E0E0 !important; }
  .stNumberInput input, .stTextInput input, .stSelectbox select {
      background: #1F3044 !important;
      color: #E0E0E0 !important;
      border: 1px solid #2C3E50 !important;
  }
</style>
"""


def inject_css():
    st.markdown(DARK_CSS, unsafe_allow_html=True)


def metric_card(label: str, value: str, color: str = "#1ABC9C"):
    st.markdown(
        f"""<div class="metric-card">
              <div class="label">{label}</div>
              <div class="value" style="color:{color}">{value}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def dept_header(name: str, duration: int):
    st.markdown(
        f'<div class="dept-header">📦 {name} &nbsp;<span style="color:#1ABC9C;font-size:0.85rem;">({duration} days)</span></div>',
        unsafe_allow_html=True,
    )


def render_part_inputs(
    dept_name: str,
    dept_duration: int,
    dept_original_end: date,
    predecessor_delay: int,
    num_parts: int,
    key_prefix: str,
) -> list[dict]:
    """
    Render input widgets for each part in a department.
    Returns a list of raw part dicts ready to be converted to PartEntry.
    """
    parts = []
    adjusted_end = dept_original_end  # will be updated with predecessor_delay in core

    for i in range(num_parts):
        part_key = f"{key_prefix}_part_{i}"
        with st.container():
            cols = st.columns([2, 2, 2, 1])
            part_name = cols[0].text_input(
                "Part Name",
                value=f"Part {i+1}",
                key=f"{part_key}_name",
            )
            actual_finish = cols[1].date_input(
                "Actual Finish Date",
                value=None,
                key=f"{part_key}_finish",
                help="Leave blank if not yet complete",
            )
            delay_cat: Optional[str] = None
            delay_reason: Optional[str] = None

            # Check if delay is needed
            from modules.core import calculate_shifted_deadline
            adj_deadline = calculate_shifted_deadline(dept_original_end, predecessor_delay)

            if actual_finish and actual_finish > adj_deadline:
                st.warning(
                    f"⚠️ **{part_name}** is {(actual_finish - adj_deadline).days} day(s) past "
                    f"the adjusted deadline ({adj_deadline.strftime('%d %b %Y')}). "
                    "Please categorise the delay below.",
                    icon=None,
                )
                cols2 = st.columns([2, 3])
                delay_cat = cols2[0].selectbox(
                    "Delay Category *",
                    options=DELAY_CATEGORIES,
                    key=f"{part_key}_cat",
                )
                delay_reason = cols2[1].text_area(
                    "Explanation *",
                    placeholder="Briefly describe the cause...",
                    key=f"{part_key}_reason",
                    height=68,
                )
                if not delay_reason:
                    st.error("An explanation is required before proceeding.", icon="🚫")

                badge_cls = (
                    "delay-badge-external"
                    if delay_cat in EXTERNAL_CATEGORIES
                    else "delay-badge-internal"
                )
                badge_txt = "External — No Penalty" if delay_cat in EXTERNAL_CATEGORIES else "Internal — Penalty Applied"
                st.markdown(
                    f'<span class="{badge_cls}">{badge_txt}</span>',
                    unsafe_allow_html=True,
                )

            st.divider()

            parts.append(dict(
                name=part_name,
                original_deadline=dept_original_end,
                actual_finish=actual_finish,
                predecessor_delay_days=predecessor_delay,
                delay_category=delay_cat,
                delay_reason=delay_reason,
            ))

    return parts


def marks_color(marks: float) -> str:
    if marks >= 80:
        return "#27AE60"
    if marks >= 50:
        return "#F39C12"
    return "#E74C3C"
