"""
ui_helpers.py — Reusable Streamlit UI components.
"""

from __future__ import annotations
from datetime import date
from typing import Optional

import streamlit as st

from modules.core import (
    DELAY_CATEGORIES, EXTERNAL_CATEGORIES, calculate_shifted_deadline, BASE_MARKS
)

DARK_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');

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
  .stTabs [data-baseweb="tab"] { color: #aaa !important; font-weight: 600; }
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
      background: #111827; border: 1px solid #1F3044;
      border-radius: 10px; padding: 16px 20px; text-align: center;
  }
  .metric-card .label {
      font-size: 0.72rem; color: #aaa;
      text-transform: uppercase; letter-spacing: 1px;
  }
  .metric-card .value { font-size: 1.9rem; font-weight: 700; line-height: 1.2; }
  .dept-header {
      background: linear-gradient(90deg, #1B4F72 0%, #0D1B2A 100%);
      border-left: 4px solid #1ABC9C;
      padding: 8px 16px; border-radius: 4px;
      font-weight: 700; font-size: 1.05rem; margin-bottom: 8px;
  }
  .part-row {
      background: #111827; border: 1px solid #1F3044;
      border-radius: 8px; padding: 12px 16px; margin-bottom: 10px;
  }
  .part-label {
      font-size: 0.75rem; color: #1ABC9C;
      text-transform: uppercase; letter-spacing: 1px; font-weight: 700;
      margin-bottom: 6px;
  }
  .delay-badge-external {
      background: #154360; color: #85C1E9;
      padding: 2px 10px; border-radius: 20px;
      font-size: 0.78rem; font-weight: 600;
  }
  .delay-badge-internal {
      background: #4A0E0E; color: #F1948A;
      padding: 2px 10px; border-radius: 20px;
      font-size: 0.78rem; font-weight: 600;
  }
  .project-card {
      background: #111827; border: 1px solid #1F3044;
      border-left: 4px solid #1ABC9C;
      border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;
  }
  .stButton>button {
      background: #1ABC9C; color: #0D1B2A;
      font-weight: 700; border: none; border-radius: 6px;
  }
  .stButton>button:hover { background: #17A589; }
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
        f'<div class="dept-header">📦 {name} &nbsp;'
        f'<span style="color:#1ABC9C;font-size:0.85rem;">({duration} days)</span></div>',
        unsafe_allow_html=True,
    )


def render_part_inputs(
    dept_name: str,
    dept_duration: int,
    dept_original_end: date,
    predecessor_delay: int,
    parts_state: list[dict],   # list of part dicts from session state
    key_prefix: str,
) -> list[dict]:
    """
    Render dynamic part rows. parts_state is the live list from session state.
    Returns updated list of raw part dicts.
    """
    adj_deadline = calculate_shifted_deadline(dept_original_end, predecessor_delay)
    parts_out = []
    to_delete = None

    for i, part in enumerate(parts_state):
        st.markdown(f'<div class="part-label">Part {i+1}</div>', unsafe_allow_html=True)
        with st.container():
            # Row 1: name, planned start, planned end, actual finish, remove btn
            c1, c2, c3, c4, c5 = st.columns([2, 1.6, 1.6, 1.6, 0.7])

            part_name = c1.text_input(
                "Part Name", value=part.get("name", f"Part {i+1}"),
                key=f"{key_prefix}_p{i}_name",
            )
            planned_start = c2.date_input(
                "Planned Start", value=part.get("planned_start"),
                key=f"{key_prefix}_p{i}_ps",
                help="Planned start date for this part",
            )
            planned_end = c3.date_input(
                "Planned End", value=part.get("planned_end"),
                key=f"{key_prefix}_p{i}_pe",
                help="Planned end date for this part",
            )
            actual_finish = c4.date_input(
                "Actual Finish", value=part.get("actual_finish"),
                key=f"{key_prefix}_p{i}_af",
                help="Leave blank if not yet complete",
            )
            c5.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if c5.button("🗑", key=f"{key_prefix}_p{i}_del", help="Remove this part"):
                to_delete = i

            # Delay handling
            delay_cat = part.get("delay_category")
            delay_reason = part.get("delay_reason")

            if actual_finish and actual_finish > adj_deadline:
                overdue = (actual_finish - adj_deadline).days
                st.warning(
                    f"⚠️ **{part_name}** is **{overdue} day(s)** past the adjusted deadline "
                    f"({adj_deadline.strftime('%d %b %Y')}). Categorise below.",
                    icon=None,
                )
                dc1, dc2 = st.columns([2, 3])
                delay_cat = dc1.selectbox(
                    "Delay Category *", options=DELAY_CATEGORIES,
                    index=DELAY_CATEGORIES.index(delay_cat) if delay_cat in DELAY_CATEGORIES else 0,
                    key=f"{key_prefix}_p{i}_cat",
                )
                delay_reason = dc2.text_area(
                    "Explanation *", value=delay_reason or "",
                    placeholder="Briefly describe the cause...",
                    key=f"{key_prefix}_p{i}_reason", height=68,
                )
                if not delay_reason:
                    st.error("An explanation is required before proceeding.", icon="🚫")

                badge_cls = ("delay-badge-external" if delay_cat in EXTERNAL_CATEGORIES
                             else "delay-badge-internal")
                badge_txt = ("External — No Penalty" if delay_cat in EXTERNAL_CATEGORIES
                             else "Internal — Penalty Applied")
                st.markdown(f'<span class="{badge_cls}">{badge_txt}</span>',
                            unsafe_allow_html=True)

            st.divider()

            parts_out.append(dict(
                name=part_name,
                original_deadline=dept_original_end,
                actual_finish=actual_finish,
                planned_start=planned_start,
                planned_end=planned_end,
                predecessor_delay_days=predecessor_delay,
                delay_category=delay_cat,
                delay_reason=delay_reason,
            ))

    if to_delete is not None:
        parts_state.pop(to_delete)
        st.rerun()

    return parts_out


def marks_color(marks: float) -> str:
    if marks >= 80:
        return "#27AE60"
    if marks >= 50:
        return "#F39C12"
    return "#E74C3C"
