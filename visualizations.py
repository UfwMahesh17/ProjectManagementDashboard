"""
visualizations.py — Plotly charts: Gantt baseline vs actual, efficiency bar chart.
"""

from __future__ import annotations
from datetime import date, timedelta

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from modules.core import DepartmentResult, BASE_MARKS

PALETTE = {
    "baseline": "#1B4F72",
    "shifted":  "#1ABC9C",
    "actual":   "#E74C3C",
    "grid":     "#2C3E50",
    "bg":       "#0D1B2A",
    "paper":    "#111827",
    "text":     "#E0E0E0",
}


def gantt_chart(
    dept_results: list[DepartmentResult],
    project_start: date,
) -> go.Figure:
    """
    Dual-bar Gantt: Original Baseline (navy) vs Shifted Window (teal).
    Actual finish markers overlaid as scatter points.
    """
    rows = []
    sorted_depts = sorted(dept_results, key=lambda d: d.order, reverse=True)

    for dr in sorted_depts:
        dept_label = dr.name

        # Original baseline bar
        rows.append(dict(
            Task=dept_label,
            Start=dr.original_start,
            Finish=dr.original_end + timedelta(days=1),
            Type="Original Baseline",
            Marks=None,
        ))

        # Shifted bar (only if there is a shift)
        if dr.predecessor_delay > 0:
            rows.append(dict(
                Task=dept_label,
                Start=dr.shifted_start,
                Finish=dr.shifted_end + timedelta(days=1),
                Type="Shifted Window",
                Marks=None,
            ))

    df = pd.DataFrame(rows)

    color_map = {
        "Original Baseline": PALETTE["baseline"],
        "Shifted Window":    PALETTE["shifted"],
    }

    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="Type",
        color_discrete_map=color_map,
        title="<b>Project Timeline — Baseline vs Shifted Path</b>",
    )
    fig.update_traces(opacity=0.82, marker_line_width=1,
                      marker_line_color="rgba(255,255,255,0.3)")

    # Actual finish markers (scatter)
    for dr in sorted_depts:
        finished = [p for p in dr.parts if p.actual_finish is not None]
        if not finished:
            continue
        latest = max(p.actual_finish for p in finished)
        on_time = latest <= dr.shifted_end
        marker_color = "#27AE60" if on_time else PALETTE["actual"]
        label = "On Time ✓" if on_time else "Late ✗"

        fig.add_scatter(
            x=[latest],
            y=[dr.name],
            mode="markers+text",
            marker=dict(symbol="diamond", size=12, color=marker_color,
                        line=dict(width=1.5, color="white")),
            text=[label],
            textposition="top center",
            textfont=dict(size=9, color=marker_color),
            name=f"{dr.name} Actual",
            showlegend=False,
        )

    _apply_dark_theme(fig)
    fig.update_layout(
        height=380,
        xaxis_title="Date",
        yaxis_title="",
        legend_title_text="Legend",
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        xaxis=dict(showgrid=True, gridcolor="#1F3044", tickfont=dict(size=10)),
    )
    return fig


def efficiency_bar_chart(dept_results: list[DepartmentResult]) -> go.Figure:
    """
    Horizontal bar chart of departmental efficiency scores.
    Colour-coded: ≥80 green, ≥50 amber, <50 red.
    """
    sorted_depts = sorted(dept_results, key=lambda d: d.order)
    names  = [dr.name for dr in sorted_depts]
    scores = [round(dr.avg_marks, 1) for dr in sorted_depts]
    eff    = [round((s / BASE_MARKS) * 100, 1) for s in scores]

    bar_colors = [
        "#27AE60" if s >= 80 else ("#F39C12" if s >= 50 else "#E74C3C")
        for s in scores
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=eff,
        y=names,
        orientation="h",
        marker_color=bar_colors,
        marker_line_color="rgba(255,255,255,0.2)",
        marker_line_width=1,
        text=[f"{s:.0f} marks  ({e:.1f}%)" for s, e in zip(scores, eff)],
        textposition="auto",
        textfont=dict(color="white", size=11),
    ))

    # Reference line at 100%
    fig.add_vline(x=100, line_dash="dot", line_color="rgba(255,255,255,0.3)",
                  annotation_text="Max", annotation_font_color="#aaa")

    fig.update_layout(
        title="<b>Departmental Efficiency Scores</b>",
        xaxis=dict(range=[0, 110], title="Efficiency %",
                   showgrid=True, gridcolor="#1F3044"),
        yaxis_title="",
        height=320,
    )
    _apply_dark_theme(fig)
    return fig


def marks_gauge(dept_name: str, marks: float) -> go.Figure:
    """Mini gauge widget for a single department."""
    color = "#27AE60" if marks >= 80 else ("#F39C12" if marks >= 50 else "#E74C3C")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=marks,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": dept_name, "font": {"color": "#E0E0E0", "size": 13}},
        number={"font": {"color": color, "size": 26}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#aaa",
                     "tickfont": {"size": 9}},
            "bar": {"color": color},
            "bgcolor": "#1F3044",
            "bordercolor": "#2C3E50",
            "steps": [
                {"range": [0, 50],  "color": "#2D1515"},
                {"range": [50, 80], "color": "#2D2215"},
                {"range": [80, 100],"color": "#152D1D"},
            ],
            "threshold": {
                "line": {"color": "white", "width": 2},
                "thickness": 0.8,
                "value": marks,
            },
        },
    ))
    fig.update_layout(
        height=180,
        margin=dict(t=40, b=10, l=20, r=20),
        paper_bgcolor=PALETTE["paper"],
        font_color=PALETTE["text"],
    )
    return fig


def _apply_dark_theme(fig: go.Figure):
    fig.update_layout(
        plot_bgcolor=PALETTE["bg"],
        paper_bgcolor=PALETTE["paper"],
        font=dict(color=PALETTE["text"], family="Calibri, sans-serif"),
        title_font=dict(color=PALETTE["text"], size=14),
        margin=dict(t=60, b=40, l=20, r=20),
    )
