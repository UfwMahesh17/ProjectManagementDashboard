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
    Cascade Gantt: Shows each department starting EXACTLY when the previous one actually finished.
    Each department bar is visually positioned in cascade sequence on the timeline.
    Blue bars = Planned baseline | Teal bars = Actual cascade path
    """
    rows = []
    sorted_depts = sorted(dept_results, key=lambda d: d.order, reverse=True)

    # Calculate actual cascade starts based on predecessor actual finishes
    actual_starts = {}
    cumulative_actual_end = project_start
    
    for dr in sorted(dept_results, key=lambda d: d.order):
        # Get the actual finish date of this department
        finished_parts = [p for p in dr.parts if p.actual_finish is not None]
        if finished_parts:
            dept_actual_end = max(p.actual_finish for p in finished_parts)
        else:
            # If not finished, use a theoretical end (planned_end or original_end)
            dept_actual_end = dr.planned_end if dr.planned_end else dr.original_end
        
        # This department starts from when the previous one actually ended
        actual_starts[dr.name] = cumulative_actual_end
        # Update cumulative for next department
        cumulative_actual_end = dept_actual_end + timedelta(days=1)

    # First pass: add planned baseline bars (for reference, less prominent)
    for dr in sorted_depts:
        rows.append(dict(
            Task=f"{dr.name}",
            Start=dr.original_start,
            Finish=dr.original_end + timedelta(days=1),
            Type="Planned Baseline",
            Marks=None,
        ))

    # Second pass: add actual cascade bars (main focus - prominently positioned)
    for dr in sorted_depts:
        # Actual cascade bar (starts from when previous dept actually finished)
        actual_start = actual_starts.get(dr.name, dr.original_start)
        finished_parts = [p for p in dr.parts if p.actual_finish is not None]
        if finished_parts:
            actual_end = max(p.actual_finish for p in finished_parts)
            rows.append(dict(
                Task=f"{dr.name}",
                Start=actual_start,
                Finish=actual_end + timedelta(days=1),
                Type="Actual Cascade",
                Marks=None,
            ))

    df = pd.DataFrame(rows)

    color_map = {
        "Planned Baseline": "#34495E",  # Muted blue-grey
        "Actual Cascade": PALETTE["shifted"],  # Bright teal
    }

    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="Type",
        color_discrete_map=color_map,
        title="<b>Project Timeline — Planned vs Actual Cascade</b>",
    )
    
    # Style the bars: Planned baseline is subtle, Actual Cascade is prominent
    for trace in fig.data:
        if trace.name == "Planned Baseline":
            trace.update(opacity=0.35, marker_line_width=0.5)
        else:  # Actual Cascade
            trace.update(opacity=0.95, marker_line_width=2,
                        marker_line_color="rgba(255,255,255,0.5)")

    # Actual finish markers (scatter) - show with small diamonds
    for dr in sorted_depts:
        finished = [p for p in dr.parts if p.actual_finish is not None]
        if not finished:
            continue
        latest = max(p.actual_finish for p in finished)
        
        # Compare against planned end (not original)
        planned_deadline = dr.planned_end if dr.planned_end else dr.original_end
        on_time = latest <= planned_deadline
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
        height=400,
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
    """Mini gauge widget for a single department with cumulative marks."""
    # Color based on efficiency relative to expected max (100 per part)
    # For a single-part department, 80+ is green, 50+ is amber, <50 is red
    # For multi-part departments, scale accordingly
    color = "#27AE60" if marks >= 80 else ("#F39C12" if marks >= 50 else "#E74C3C")
    
    # Set gauge range based on marks value
    # If marks > 100, scale the range to accommodate it
    max_range = max(100, int(marks * 1.2) + 20)  # Show some headroom
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=marks,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": dept_name, "font": {"color": "#E0E0E0", "size": 13}},
        number={"font": {"color": color, "size": 26}},
        gauge={
            "axis": {"range": [0, max_range], "tickcolor": "#aaa",
                     "tickfont": {"size": 9}},
            "bar": {"color": color},
            "bgcolor": "#1F3044",
            "bordercolor": "#2C3E50",
            "steps": [
                {"range": [0, max_range * 0.5],  "color": "#2D1515"},
                {"range": [max_range * 0.5, max_range * 0.8], "color": "#2D2215"},
                {"range": [max_range * 0.8, max_range], "color": "#152D1D"},
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
