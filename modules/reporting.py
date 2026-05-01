"""
reporting.py — Professional Excel report generation with openpyxl.
"""

from __future__ import annotations
import io
from datetime import date
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, GradientFill
)
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference

from modules.core import DepartmentResult, BASE_MARKS

# ── Palette ───────────────────────────────────────────────────────────────────
DARK_NAVY   = "0D1B2A"
STEEL_BLUE  = "1B4F72"
ACCENT_TEAL = "1ABC9C"
LIGHT_ROW   = "EBF5FB"
WHITE       = "FFFFFF"
DANGER_RED  = "E74C3C"
WARN_ORANGE = "F39C12"
SUCCESS_GRN = "27AE60"
HEADER_FG   = "FFFFFF"

thin = Side(style="thin", color="CCCCCC")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)


def _cell_color(marks: Optional[float]) -> str:
    if marks is None:
        return WHITE
    if marks >= 80:
        return "D5F5E3"   # green tint
    if marks >= 50:
        return "FDEBD0"   # amber tint
    return "FADBD8"       # red tint


def generate_report(
    project_code: str,
    project_start: date,
    dept_results: list[DepartmentResult],
) -> bytes:
    """
    Build and return an in-memory .xlsx report as bytes.
    """
    wb = Workbook()

    # ── Sheet 1 : Summary Dashboard ──────────────────────────────────────────
    ws_summary = wb.active
    ws_summary.title = "Summary Dashboard"
    _build_summary(ws_summary, project_code, project_start, dept_results)

    # ── Sheet 2 : Detailed Part Data ─────────────────────────────────────────
    ws_detail = wb.create_sheet("Part Detail")
    _build_detail(ws_detail, project_code, dept_results)

    # ── Sheet 3 : Delay Log ───────────────────────────────────────────────────
    ws_log = wb.create_sheet("Delay Log")
    _build_delay_log(ws_log, project_code, dept_results)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
def _hdr_style(ws, row: int, cols: list[str], bg: str = STEEL_BLUE):
    for col in cols:
        cell = ws[f"{col}{row}"]
        cell.font = Font(bold=True, color=HEADER_FG, name="Calibri", size=10)
        cell.fill = PatternFill("solid", start_color=bg)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER


def _data_style(ws, row: int, cols: list[str], bg: str = WHITE):
    for col in cols:
        cell = ws[f"{col}{row}"]
        cell.font = Font(name="Calibri", size=10)
        cell.fill = PatternFill("solid", start_color=bg)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER


def _build_summary(ws, project_code, project_start, dept_results):
    # Title banner
    ws.merge_cells("A1:H1")
    ws["A1"] = f"ADWIK INTELLIMECH — WORKFLOW ANALYTICS REPORT"
    ws["A1"].font = Font(bold=True, size=14, color=WHITE, name="Calibri")
    ws["A1"].fill = PatternFill("solid", start_color=DARK_NAVY)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    ws.merge_cells("A2:H2")
    ws["A2"] = f"Project: {project_code}  |  Start Date: {project_start.strftime('%d %b %Y')}"
    ws["A2"].font = Font(bold=True, size=11, color=WHITE, name="Calibri")
    ws["A2"].fill = PatternFill("solid", start_color=STEEL_BLUE)
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 22

    # KPI row headers
    headers = ["Department", "Duration\n(days)", "Original End", "Shifted End",
               "Parts\nTracked", "Parts\nComplete", "Avg\nMarks", "Efficiency\n%"]
    cols = list("ABCDEFGH")
    ws.row_dimensions[4].height = 36
    for i, (col, h) in enumerate(zip(cols, headers)):
        ws[f"{col}4"] = h
    _hdr_style(ws, 4, cols)

    for r_idx, dr in enumerate(
        sorted(dept_results, key=lambda d: d.order), start=5
    ):
        finished = [p for p in dr.parts if p.actual_finish is not None]
        avg_marks = dr.avg_marks
        eff_pct = (avg_marks / BASE_MARKS) * 100
        bg = LIGHT_ROW if r_idx % 2 == 0 else WHITE

        row_data = [
            dr.name,
            dr.duration,
            dr.original_end.strftime("%d %b %Y"),
            dr.shifted_end.strftime("%d %b %Y"),
            len(dr.parts),
            len(finished),
            round(avg_marks, 1),
            f"{eff_pct:.1f}%",
        ]
        for col, val in zip(cols, row_data):
            ws[f"{col}{r_idx}"] = val
        _data_style(ws, r_idx, cols, bg)
        # colour-code marks cell
        marks_cell = ws[f"G{r_idx}"]
        marks_cell.fill = PatternFill("solid", start_color=_cell_color(avg_marks))

    # Column widths
    widths = [18, 10, 14, 14, 8, 10, 10, 12]
    for col, w in zip(cols, widths):
        ws.column_dimensions[col].width = w

    # Embed a simple bar chart of efficiency
    last_row = 4 + len(dept_results)
    chart = BarChart()
    chart.type = "col"
    chart.title = "Departmental Efficiency %"
    chart.y_axis.title = "Efficiency %"
    chart.x_axis.title = "Department"
    chart.style = 10
    chart.width = 18
    chart.height = 12

    data_ref = Reference(ws, min_col=8, min_row=4, max_row=last_row)
    cats_ref = Reference(ws, min_col=1, min_row=5, max_row=last_row)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    ws.add_chart(chart, f"A{last_row + 3}")


def _build_detail(ws, project_code, dept_results):
    ws.merge_cells("A1:I1")
    ws["A1"] = f"PART-LEVEL DETAIL — {project_code}"
    ws["A1"].font = Font(bold=True, size=12, color=WHITE, name="Calibri")
    ws["A1"].fill = PatternFill("solid", start_color=DARK_NAVY)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    headers = [
        "Project Code", "Department", "Part Name",
        "Original Deadline", "Predecessor\nDelay (days)",
        "Adjusted Deadline", "Actual Finish",
        "Delay\nDays", "Marks",
    ]
    cols = list("ABCDEFGHI")
    ws.row_dimensions[3].height = 36
    for col, h in zip(cols, headers):
        ws[f"{col}3"] = h
    _hdr_style(ws, 3, cols)

    row_num = 4
    for dr in sorted(dept_results, key=lambda d: d.order):
        for part in dr.parts:
            bg = LIGHT_ROW if row_num % 2 == 0 else WHITE
            row_data = [
                project_code,
                dr.name,
                part.name,
                part.original_deadline.strftime("%d %b %Y"),
                part.predecessor_delay_days,
                part.adjusted_deadline.strftime("%d %b %Y"),
                part.actual_finish.strftime("%d %b %Y") if part.actual_finish else "Pending",
                part.delay_days if part.actual_finish else "—",
                round(part.marks, 1) if part.actual_finish else "—",
            ]
            for col, val in zip(cols, row_data):
                ws[f"{col}{row_num}"] = val
            _data_style(ws, row_num, cols, bg)
            if part.actual_finish:
                ws[f"I{row_num}"].fill = PatternFill(
                    "solid", start_color=_cell_color(part.marks)
                )
            row_num += 1

    widths = [14, 16, 20, 16, 14, 16, 14, 10, 10]
    for col, w in zip(cols, widths):
        ws.column_dimensions[col].width = w


def _build_delay_log(ws, project_code, dept_results):
    ws.merge_cells("A1:G1")
    ws["A1"] = f"DELAY LOG — {project_code}"
    ws["A1"].font = Font(bold=True, size=12, color=WHITE, name="Calibri")
    ws["A1"].fill = PatternFill("solid", start_color=DARK_NAVY)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    headers = [
        "Department", "Part Name", "Delay Days",
        "Category", "Type", "Penalty Applied", "Reason / Notes",
    ]
    cols = list("ABCDEFG")
    ws.row_dimensions[3].height = 36
    for col, h in zip(cols, headers):
        ws[f"{col}3"] = h
    _hdr_style(ws, 3, cols, bg=DANGER_RED)

    row_num = 4
    for dr in sorted(dept_results, key=lambda d: d.order):
        for part in dr.parts:
            if part.actual_finish and part.delay_days > 0:
                bg = "FEF9E7" if part.is_external else "FADBD8"
                penalty = "None (External)" if part.is_external else f"−{int(part.delay_days * 5)} marks"
                delay_type = "External" if part.is_external else "Internal"
                row_data = [
                    dr.name, part.name, part.delay_days,
                    part.delay_category or "—",
                    delay_type, penalty,
                    part.delay_reason or "—",
                ]
                for col, val in zip(cols, row_data):
                    ws[f"{col}{row_num}"] = val
                _data_style(ws, row_num, cols, bg)
                row_num += 1

    if row_num == 4:
        ws.merge_cells("A4:G4")
        ws["A4"] = "✓  No delays recorded."
        ws["A4"].font = Font(bold=True, color="27AE60", name="Calibri")
        ws["A4"].alignment = Alignment(horizontal="center")

    widths = [16, 20, 12, 22, 12, 18, 40]
    for col, w in zip(cols, widths):
        ws.column_dimensions[col].width = w
