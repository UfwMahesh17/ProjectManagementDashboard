"""
ui_helpers.py — Redesigned UI: clean industrial-precision theme.
Font: DM Sans + JetBrains Mono. Palette: warm white, deep slate, amber accent.
"""

from __future__ import annotations
from datetime import date, timedelta
import streamlit as st
from modules.core import DELAY_CATEGORIES, EXTERNAL_CATEGORIES, calculate_shifted_deadline

MAIN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&family=Sora:wght@700;800&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #F5F3EF !important;
    color: #1C1C1E !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #1C2536 !important;
    border-right: none !important;
}
[data-testid="stSidebar"] * { color: #C8D0E0 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #FFFFFF !important; }

/* FIX SIDEBAR EXPANDER TEXT OVERLAP & SUMMARY */
[data-testid="stSidebar"] div[data-testid="stExpander"] {
    background: #273043 !important;
    border: 1px solid #374357 !important;
    border-radius: 8px !important;
    margin-bottom: 4px !important;
    overflow: hidden !important;
}
[data-testid="stSidebar"] div[data-testid="stExpander"] summary {
    background: transparent !important;
    padding: 8px 12px !important;
}
[data-testid="stSidebar"] div[data-testid="stExpander"] summary p {
    font-size: 0.85rem !important;
    color: #E8ECF4 !important;
    font-weight: 600 !important;
    margin: 0 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    max-width: 140px !important;
}
[data-testid="stSidebar"] div[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p {
    font-size: 0.85rem !important;
    line-height: 1.2 !important;
}
/* This hides the "keyboard_double_arrow_right" and other icon strings leaking into the text */
[data-testid="stSidebar"] div[data-testid="stExpander"] svg {
    flex-shrink: 0 !important;
}

/* FIX SIDEBAR UPLOADER MESS */
[data-testid="stSidebar"] [data-testid="stFileUploader"] > label {
    display: none !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] section {
    padding: 0 !important;
    border: none !important;
    background: transparent !important;
    min-height: unset !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] section > div {
    display: none !important;
}
/* Hide the 'Drag and drop file here' text and 'Limit 200MB' bits that cause overlap */
[data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] {
    display: none !important;
}
/* Style the browse button specifically for sidebar */
[data-testid="stSidebar"] [data-testid="stFileUploader"] button {
    width: 100% !important;
    background: #273043 !important;
    color: #E8ECF4 !important;
    border: 1px solid #374357 !important;
}

[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stNumberInput input,
[data-testid="stSidebar"] .stDateInput input {
    background: #273043 !important;
    border: 1px solid #374357 !important;
    color: #E8ECF4 !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: #273043 !important;
    border: 1px solid #374357 !important;
    color: #E8ECF4 !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] hr { border-color: #374357 !important; }
[data-testid="stSidebar"] .stButton > button {
    background: #273043 !important;
    color: #E8ECF4 !important;
    border: 1px solid #374357 !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    transition: all 0.15s !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #F59E0B !important;
    color: #1C1C1E !important;
    border-color: #F59E0B !important;
}
[data-testid="stSidebar"] .stDownloadButton > button {
    background: #F59E0B !important;
    color: #1C1C1E !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] div[data-testid="stExpander"] {
    background: #273043 !important;
    border: 1px solid #374357 !important;
    border-radius: 10px !important;
}
[data-testid="stSidebarNav"] { display: none !important; }

/* ── Top nav tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #FFFFFF !important;
    border-bottom: 2px solid #E8E4DC !important;
    padding: 0 4px !important;
    gap: 2px !important;
    box-shadow: 0 1px 0 #E8E4DC;
}
.stTabs [data-baseweb="tab"] {
    color: #6B7280 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    padding: 12px 20px !important;
    border-radius: 6px 6px 0 0 !important;
    border: none !important;
    transition: all 0.15s !important;
}
.stTabs [data-baseweb="tab"]:hover { background: #F5F3EF !important; color: #1C1C1E !important; }
.stTabs [aria-selected="true"] {
    color: #1C1C1E !important;
    background: #F5F3EF !important;
    font-weight: 700 !important;
    border-bottom: 2px solid #F59E0B !important;
}

/* ── Main content inputs ── */
.stTextInput label, .stNumberInput label, .stDateInput label, .stTextArea label {
    color: #1C1C1E !important;
    font-weight: 600 !important;
    display: block !important;
    visibility: visible !important;
}
.stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {
    background: #FFFFFF !important;
    border: 1.5px solid #E0DBD1 !important;
    border-radius: 8px !important;
    color: #1C1C1E !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
.stTextInput input:focus, .stDateInput input:focus, .stTextArea textarea:focus,
.stNumberInput input:focus {
    border-color: #F59E0B !important;
    box-shadow: 0 0 0 3px rgba(245,158,11,0.15) !important;
    outline: none !important;
}
.stSelectbox > div > div {
    background: #FFFFFF !important;
    border: 1.5px solid #E0DBD1 !important;
    border-radius: 8px !important;
}

/* ── Main buttons ── */
.stButton > button {
    background: #1C2536 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.2rem !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    background: #F59E0B !important;
    color: #1C1C1E !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(245,158,11,0.3) !important;
}
.stDownloadButton > button {
    background: #FFFFFF !important;
    color: #1C2536 !important;
    border: 2px solid #1C2536 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stDownloadButton > button:hover {
    background: #1C2536 !important;
    color: #FFFFFF !important;
}

/* ── Expanders ── */
div[data-testid="stExpander"] {
    background: #FFFFFF !important;
    border: 1.5px solid #E0DBD1 !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}

/* ── Alerts ── */
.stAlert { border-radius: 10px !important; font-family: 'DM Sans', sans-serif !important; }

/* ── Dataframes ── */
.stDataFrame { border-radius: 10px !important; overflow: hidden !important; }
[data-testid="stDataFrameResizable"] { border-radius: 10px !important; }

/* ── Custom components ── */

.wms-hero {
    background: linear-gradient(135deg, #1C2536 0%, #2D3A52 100%);
    border-radius: 16px;
    padding: 28px 32px 24px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
    color: white;
}
.wms-hero::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(245,158,11,0.2) 0%, transparent 70%);
    border-radius: 50%;
}
.wms-hero::after {
    content: '';
    position: absolute;
    bottom: -60px; left: 20%;
    width: 300px; height: 120px;
    background: rgba(245,158,11,0.05);
    border-radius: 50%;
}
.wms-hero-title {
    font-family: 'Sora', sans-serif !important;
    font-size: 1.7rem !important;
    font-weight: 800 !important;
    color: #FFFFFF !important;
    margin: 0 0 6px !important;
    line-height: 1.2 !important;
}
.wms-hero-sub { 
    color: rgba(255,255,255,0.7) !important; 
    font-size: 0.95rem !important; 
    margin: 0 !important; 
    line-height: 1.4 !important;
}
.wms-hero-accent { color: #F59E0B !important; }

.wms-kpi-row { display: flex; gap: 14px; margin-bottom: 20px; flex-wrap: wrap; }
.wms-kpi {
    flex: 1; min-width: 130px;
    background: #FFFFFF;
    border: 1.5px solid #E0DBD1;
    border-radius: 12px;
    padding: 16px 18px;
    position: relative;
    overflow: hidden;
    transition: box-shadow 0.2s, transform 0.2s;
}
.wms-kpi:hover { box-shadow: 0 6px 24px rgba(28,37,54,0.10); transform: translateY(-2px); }
.wms-kpi-accent {
    position: absolute; top: 0; left: 0;
    width: 4px; height: 100%;
    border-radius: 12px 0 0 12px;
}
.wms-kpi-label {
    font-size: 0.68rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.8px;
    color: #9CA3AF; margin-bottom: 8px; padding-left: 10px;
}
.wms-kpi-value {
    font-family: 'Sora', sans-serif;
    font-size: 2rem; font-weight: 800;
    line-height: 1; padding-left: 10px;
}
.wms-kpi-sub { font-size: 0.72rem; color: #9CA3AF; padding-left: 10px; margin-top: 4px; }

.wms-dept-banner {
    background: #FFFFFF;
    border: 1.5px solid #E0DBD1;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.wms-dept-icon {
    width: 44px; height: 44px;
    background: #1C2536;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem; flex-shrink: 0;
}
.wms-dept-name { font-family: 'Sora', sans-serif; font-size: 1.05rem; font-weight: 700; color: #1C1C1E; }
.wms-dept-meta { font-size: 0.78rem; color: #9CA3AF; margin-top: 2px; }
.wms-dept-prog-wrap { background: #F0EDE8; border-radius: 99px; height: 6px; overflow: hidden; margin-top: 6px; max-width: 200px; }
.wms-dept-prog-fill { height: 100%; border-radius: 99px; transition: width 0.4s ease; }

.wms-part-card {
    background: #FFFFFF;
    border: 1.5px solid #E0DBD1;
    border-radius: 10px;
    padding: 16px 18px 12px;
    margin-bottom: 10px;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.wms-part-card:hover { border-color: #F59E0B; box-shadow: 0 4px 16px rgba(245,158,11,0.08); }
.wms-part-card.late  { border-left: 4px solid #EF4444 !important; }
.wms-part-card.ontime { border-left: 4px solid #10B981 !important; }
.wms-part-card.progress { border-left: 4px solid #F59E0B !important; }
.wms-part-card.empty { border-left: 4px solid #D1D5DB !important; }

.wms-part-header {
    display: flex; justify-content: space-between;
    align-items: center; margin-bottom: 12px;
}
.wms-part-num {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem; font-weight: 500;
    color: #9CA3AF; text-transform: uppercase; letter-spacing: 1px;
}

.badge {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 3px 10px; border-radius: 99px;
    font-size: 0.72rem; font-weight: 600;
    font-family: 'DM Sans', sans-serif;
}
.badge-green  { background: #D1FAE5; color: #065F46; }
.badge-red    { background: #FEE2E2; color: #991B1B; }
.badge-amber  { background: #FEF3C7; color: #92400E; }
.badge-blue   { background: #DBEAFE; color: #1E40AF; }
.badge-slate  { background: #E2E8F0; color: #475569; }
.badge-purple { background: #EDE9FE; color: #5B21B6; }

.wms-pill-row { display: flex; gap: 8px; flex-wrap: wrap; margin: 10px 0 16px; }
.wms-pill {
    background: #FFFFFF;
    border: 1px solid #E0DBD1;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 0.76rem; color: #374151;
}
.wms-pill strong { color: #1C1C1E; font-weight: 600; }

.wms-section-label {
    font-size: 0.7rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.9px;
    color: #9CA3AF; margin: 20px 0 10px;
    display: flex; align-items: center; gap: 8px;
}
.wms-section-label::after { content: ''; flex: 1; height: 1px; background: #E8E4DC; }

.wms-step-row { display: flex; align-items: flex-start; gap: 0; margin: 16px 0 20px; overflow-x: auto; padding-bottom: 4px; }
.wms-step { display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 80px; }
.wms-step-dot {
    width: 28px; height: 28px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.72rem; font-weight: 700; flex-shrink: 0;
    position: relative; z-index: 1;
}
.wms-step-dot.done   { background: #F59E0B; color: #1C1C1E; }
.wms-step-dot.active { background: #1C2536; color: #FFFFFF; }
.wms-step-dot.todo   { background: #F0EDE8; color: #9CA3AF; border: 2px solid #E0DBD1; }
.wms-step-label { font-size: 0.62rem; color: #9CA3AF; margin-top: 5px; text-align: center; max-width: 72px; }
.wms-step-label.done  { color: #F59E0B; font-weight: 600; }
.wms-step-label.active { color: #1C2536; font-weight: 700; }
.wms-step-line { flex: 1; height: 2px; background: #E0DBD1; margin-top: 14px; min-width: 16px; }
.wms-step-line.done { background: #F59E0B; }

.wms-proj-card {
    background: #FFFFFF;
    border: 1.5px solid #E0DBD1;
    border-radius: 14px;
    padding: 20px 22px;
    transition: all 0.2s;
    height: 100%;
}
.wms-proj-card:hover { border-color: #F59E0B; box-shadow: 0 8px 30px rgba(28,37,54,0.08); transform: translateY(-2px); }

.wms-info-box {
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 0.84rem;
    color: #1E40AF;
    margin-bottom: 16px;
}
.wms-warn-box {
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 0.84rem;
    color: #92400E;
    margin-bottom: 10px;
}
.wms-error-box {
    background: #FEF2F2;
    border: 1px solid #FECACA;
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 0.84rem;
    color: #991B1B;
    margin-bottom: 10px;
}
.wms-success-box {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 0.84rem;
    color: #065F46;
    margin-bottom: 10px;
}

.wms-report-box {
    background: #FFFFFF;
    border: 1.5px solid #E0DBD1;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.wms-report-sheet {
    display: flex; align-items: flex-start; gap: 12px;
    padding: 10px 0; border-bottom: 1px solid #F0EDE8;
}
.wms-report-sheet:last-child { border-bottom: none; }
.wms-report-icon {
    width: 36px; height: 36px;
    background: #F5F3EF; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; flex-shrink: 0;
}

/* Sidebar branding block */
.sb-brand {
    padding: 16px 0 12px;
    border-bottom: 1px solid #374357;
    margin-bottom: 12px;
}
.sb-brand-name {
    font-family: 'Sora', sans-serif;
    font-size: 1.1rem; font-weight: 800;
    color: #FFFFFF !important;
}
.sb-brand-sub { font-size: 0.72rem; color: #6B7A99 !important; margin-top: 2px; }

/* Hide redundant sidebar element strings and check for icon leakage */
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    overflow: hidden !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary span[data-testid="stMarkdownContainer"] {
    display: none !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary p {
    display: block !important;
}

.sb-section-label {
    font-size: 0.65rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.8px;
    color: #6B7A99 !important;
    margin: 12px 0 6px;
    display: flex; align-items: center; gap: 6px;
}
.sb-section-label::after { content: ''; flex: 1; height: 1px; background: #374357; }

h1, h2, h3 { font-family: 'Sora', sans-serif !important; color: #1C1C1E !important; }
p, span, div, label { font-family: 'DM Sans', sans-serif !important; }
</style>
"""


def inject_css():
    st.markdown(MAIN_CSS, unsafe_allow_html=True)


# ── Reusable HTML helpers ─────────────────────────────────────────────────────

def hero(title: str, subtitle: str, accent: str = ""):
    subtitle_html = f'<p class="wms-hero-sub">{subtitle}</p>'
    title_html = f'<div class="wms-hero-title">{title}'
    if accent:
        title_html += f' <span class="wms-hero-accent">{accent}</span>'
    title_html += '</div>'
    
    st.markdown(
        f'<div class="wms-hero">{title_html}{subtitle_html}</div>',
        unsafe_allow_html=True,
    )


def kpi_row(items: list[tuple]):
    """items = [(label, value, sub, color), ...]"""
    cards = ""
    for label, value, sub, color in items:
        cards += f"""<div class="wms-kpi">
          <div class="wms-kpi-accent" style="background:{color}"></div>
          <div class="wms-kpi-label">{label}</div>
          <div class="wms-kpi-value" style="color:{color}">{value}</div>
          {"<div class='wms-kpi-sub'>" + sub + "</div>" if sub else ""}
        </div>"""
    st.markdown(f'<div class="wms-kpi-row">{cards}</div>', unsafe_allow_html=True)


def kpi_card(label, value, sub="", color="#1C2536"):
    st.markdown(
        f"""<div class="wms-kpi">
          <div class="wms-kpi-accent" style="background:{color}"></div>
          <div class="wms-kpi-label">{label}</div>
          <div class="wms-kpi-value" style="color:{color}">{value}</div>
          {"<div class='wms-kpi-sub'>" + sub + "</div>" if sub else ""}
        </div>""",
        unsafe_allow_html=True,
    )


def metric_card(label, value, color="#1C2536"):
    kpi_card(label, value, color=color)


def dept_header(name: str, duration: int, completion_pct: float = 0, pred_delay: int = 0):
    icons = {"Design": "✏️", "Purchase": "🛒", "Manufacturing": "🔩",
             "Assembly": "🔧", "Testing": "🧪"}
    icon = icons.get(name, "📦")
    bar_color = "#10B981" if completion_pct == 100 else "#F59E0B" if completion_pct > 0 else "#D1D5DB"
    # Delay badge is disabled for department headers as we are in manual mode
    st.markdown(
        f"""<div class="wms-dept-banner">
          <div class="wms-dept-icon">{icon}</div>
          <div style="flex:1">
            <div style="display:flex;align-items:center;gap:8px">
              <span class="wms-dept-name">{name}</span>
            </div>
            <div class="wms-dept-meta">{duration} days &nbsp;·&nbsp; {completion_pct:.0f}% complete</div>
            <div class="wms-dept-prog-wrap">
              <div class="wms-dept-prog-fill" style="width:{completion_pct}%;background:{bar_color}"></div>
            </div>
          </div>
          <div style="text-align:right">
            <div style="font-family:'Sora',sans-serif;font-size:1.6rem;font-weight:800;color:{bar_color};line-height:1">{completion_pct:.0f}<span style="font-size:0.8rem;color:#9CA3AF">%</span></div>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )


def section_label(text: str):
    st.markdown(f'<div class="wms-section-label">{text}</div>', unsafe_allow_html=True)


# alias
def section_heading(text: str):
    section_label(text)


def pill_row(items: list[tuple]):
    """items = [(label, value), ...]"""
    html = "".join(f'<div class="wms-pill"><strong>{k}:</strong> {v}</div>' for k, v in items)
    st.markdown(f'<div class="wms-pill-row">{html}</div>', unsafe_allow_html=True)


def info_pills(items):
    pill_row(items)


def step_indicator(steps: list[str], current: int):
    parts = []
    for i, label in enumerate(steps):
        if i > 0:
            line_cls = "wms-step-line done" if i <= current else "wms-step-line"
            parts.append(f'<div class="{line_cls}"></div>')
        if i < current:
            dot_cls, lbl_cls, sym = "done", "done", "✓"
        elif i == current:
            dot_cls, lbl_cls, sym = "active", "active", str(i+1)
        else:
            dot_cls, lbl_cls, sym = "todo", "", str(i+1)
        parts.append(
            f'<div class="wms-step">'
            f'<div class="wms-step-dot {dot_cls}">{sym}</div>'
            f'<div class="wms-step-label {lbl_cls}">{label}</div>'
            f'</div>'
        )
    st.markdown(f'<div class="wms-step-row">{"".join(parts)}</div>', unsafe_allow_html=True)


def page_hero(project_code, start, dept_count, total_days):
    hero(
        "Project Detail",
        f"{dept_count} departments · {total_days} days total · Started {start.strftime('%d %b %Y')}",
        accent=project_code,
    )


def progress_bar(pct, color="#F59E0B"):
    st.markdown(
        f'<div style="background:#F0EDE8;border-radius:99px;height:8px;overflow:hidden;margin:6px 0">'
        f'<div style="width:{min(pct,100):.1f}%;height:100%;background:{color};border-radius:99px;transition:width 0.4s"></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def completion_ring_html(pct: float, color: str = "#F59E0B", size: int = 72) -> str:
    r = 26; cx = cy = size // 2
    circ = 2 * 3.14159 * r
    dash = circ * pct / 100
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#F0EDE8" stroke-width="7"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="7"'
        f' stroke-dasharray="{dash:.1f} {circ:.1f}" stroke-linecap="round"'
        f' transform="rotate(-90 {cx} {cy})"/>'
        f'<text x="{cx}" y="{cy+5}" text-anchor="middle" font-size="12" font-weight="700"'
        f' fill="{color}" font-family="Sora,sans-serif">{pct:.0f}%</text>'
        f'</svg>'
    )


def badge(text: str, kind: str = "slate"):
    st.markdown(f'<span class="badge badge-{kind}">{text}</span>', unsafe_allow_html=True)


def marks_color(marks: float) -> str:
    if marks >= 80: return "#10B981"
    if marks >= 50: return "#F59E0B"
    return "#EF4444"


# ── Part inputs ───────────────────────────────────────────────────────────────

def render_part_inputs(
    dept_name, dept_duration, dept_original_end,
    predecessor_delay, parts_state, key_prefix,
):
    # DEADLINE REFINED: Every part has its own manual deadline (Planned end)
    # The department headers will still show the department planned window for context
    parts_out    = []
    to_delete    = None

    for i, part in enumerate(parts_state):
        af         = part.get("actual_finish")
        a_start    = part.get("actual_start")
        p_start    = part.get("planned_start")
        p_end      = part.get("planned_end")
        
        # SCREENSHOT FIX: DELAY IS CALCULATED B/W PLANNED END AND ACTUAL FINISH
        # Use planned_end if available, otherwise fallback to dept default
        part_deadline = p_end if p_end else dept_original_end
        
        on_time    = af and af <= part_deadline
        late       = af and af > part_deadline
        in_prog    = a_start and not af
        card_class = "ontime" if on_time else "late" if late else "progress" if in_prog else "empty"

        if on_time:   status_html = '<span class="badge badge-green">✓ On Time</span>'
        elif late:    status_html = f'<span class="badge badge-red">⚠ Late {(af - part_deadline).days}d</span>'
        elif in_prog: status_html = '<span class="badge badge-amber">⏳ In Progress</span>'
        else:         status_html = '<span class="badge badge-slate">Not Started</span>'

        st.markdown(
            f'<div class="wms-part-card {card_class}">'
            f'<div class="wms-part-header">'
            f'<span class="wms-part-num">Part {i+1}</span>'
            f'{status_html}'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # ── inputs ───────────────────────────────────────────────────────────
        st.markdown(f"##### Data Entry for {part.get('name', f'Part {i+1}')}")
        c1, c2, c3, c4, c5, cd = st.columns([2.2, 1.5, 1.5, 1.5, 1.5, 0.5])
        part_name = c1.text_input(
            "Part name", value=part.get("name", f"Part {i+1}"),
            key=f"{key_prefix}_p{i}_name", placeholder="e.g. Frame Drawing",
            label_visibility="visible"
        )
        planned_start = c2.date_input("Planned start", value=part.get("planned_start"), key=f"{key_prefix}_p{i}_ps", label_visibility="visible")
        planned_end   = c3.date_input("Planned end",   value=part.get("planned_end"),   key=f"{key_prefix}_p{i}_pe", label_visibility="visible")
        actual_start  = c4.date_input("Actual start",  value=part.get("actual_start"),  key=f"{key_prefix}_p{i}_as", label_visibility="visible")
        actual_finish = c5.date_input("Actual finish", value=part.get("actual_finish"), key=f"{key_prefix}_p{i}_af", label_visibility="visible")
        cd.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if cd.button("✕", key=f"{key_prefix}_p{i}_del", help="Remove this part"):
            to_delete = i

        # ── finish-delay logging ──────────────────────────────────────────────
        if actual_finish and actual_finish > part_deadline:
            overdue = (actual_finish - part_deadline).days
            penalty = overdue * 0.5
            st.markdown(
                f'<div class="wms-error-box">⚠️ <strong>{part_name}</strong> is '
                f'<strong>{overdue} day(s) late</strong> past its Planned End '
                f'({part_deadline.strftime("%d %b %Y")}). Please log the delay below.</div>',
                unsafe_allow_html=True,
            )
            dc1, dc2 = st.columns([2, 3])
            delay_cat = dc1.selectbox(
                "Delay category *", options=DELAY_CATEGORIES,
                index=DELAY_CATEGORIES.index(part.get("delay_category")) if part.get("delay_category") in DELAY_CATEGORIES else 0,
                key=f"{key_prefix}_p{i}_cat",
            )
            delay_reason = dc2.text_area(
                "Root cause explanation *",
                value=part.get("delay_reason") or "",
                placeholder="What caused this delay?",
                key=f"{key_prefix}_p{i}_reason", height=80,
            )
            if not delay_reason:
                st.caption("⚠️ Explanation required before running analysis.")

            is_ext = delay_cat in EXTERNAL_CATEGORIES
            if is_ext:
                st.markdown('<span class="badge badge-blue">🔵 External — No penalty applied</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span class="badge badge-red">🔴 Internal — −{penalty} marks deducted</span>', unsafe_allow_html=True)

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        parts_out.append(dict(
            name=part_name,
            original_deadline=part_deadline, # Save the part-specific deadline
            actual_finish=actual_finish,
            actual_start=actual_start,
            planned_start=planned_start,
            planned_end=planned_end,
            predecessor_delay_days=0, # Forced 0 as per Independent Mode
            delay_category=delay_cat if actual_finish and actual_finish > part_deadline else None,
            delay_reason=delay_reason if actual_finish and actual_finish > part_deadline else None,
        ))

    if to_delete is not None:
        parts_state.pop(to_delete)
        st.rerun()

    return parts_out
