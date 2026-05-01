"""
app.py — Adwik Intellimech | Workflow Analytics System
Run: streamlit run app.py
"""

# ── PATH FIX (must be before all local imports) ───────────────────────────────
# Streamlit Cloud runs from a different cwd than the repo root.
# This ensures `modules/` is always found relative to THIS file.
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
from datetime import date, timedelta

from modules.core import (
    DEPARTMENTS, PartEntry, DepartmentResult,
    build_department_timeline, propagate_delays, BASE_MARKS,
)
from modules.visualizations import gantt_chart, efficiency_bar_chart, marks_gauge
from modules.reporting import generate_report
from modules.ui_helpers import (
    inject_css, metric_card, dept_header, render_part_inputs, marks_color
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Adwik WMS",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ── Sidebar : Project Setup ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Adwik Intellimech")
    st.markdown("### Workflow Analytics System")
    st.divider()

    project_code = st.text_input("Project Code", value="A24017")
    project_start = st.date_input("Project Start Date", value=date(2024, 1, 15))
    st.divider()

    st.markdown("#### Parts per Department")
    dept_part_counts: dict[str, int] = {}
    for dept in DEPARTMENTS:
        dept_part_counts[dept["name"]] = st.number_input(
            dept["name"],
            min_value=1, max_value=10, value=3,
            key=f"nparts_{dept['name']}",
        )

    st.divider()
    run_analysis = st.button("▶  Run Analysis", use_container_width=True)
    st.caption("Fill in part data across tabs, then click Run Analysis.")


# ── Build baseline timeline ───────────────────────────────────────────────────
timeline = build_department_timeline(project_start, DEPARTMENTS)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f"<h1 style='margin-bottom:4px'>Workflow Analytics — <span style='color:#1ABC9C'>{project_code}</span></h1>",
    unsafe_allow_html=True,
)
st.caption(f"Project Start: {project_start.strftime('%d %b %Y')}  |  Departments: {len(DEPARTMENTS)}  |  Total Duration: {sum(d['duration'] for d in DEPARTMENTS)} days")
st.divider()

# ── Tabs: one per department ──────────────────────────────────────────────────
dept_tabs = st.tabs([f"📋 {d['name']}" for d in DEPARTMENTS] + ["📊 Analytics", "📥 Report"])

if "dept_results" not in st.session_state:
    st.session_state.dept_results = {}

predecessor_delay_map: dict[str, int] = {d["name"]: 0 for d in DEPARTMENTS}

# ── Render each Department tab ────────────────────────────────────────────────
dept_part_inputs: dict[str, list[dict]] = {}

for tab_obj, dept in zip(dept_tabs[:len(DEPARTMENTS)], DEPARTMENTS):
    with tab_obj:
        tl_entry = next(t for t in timeline if t["name"] == dept["name"])
        saved = st.session_state.dept_results.get(dept["name"])
        pred_delay = saved.predecessor_delay if saved else predecessor_delay_map[dept["name"]]

        dept_header(dept["name"], dept["duration"])

        info_cols = st.columns(4)
        info_cols[0].info(f"**Original End:** {tl_entry['original_end'].strftime('%d %b %Y')}")
        info_cols[1].info(f"**Duration:** {dept['duration']} days")
        adj_end = tl_entry["original_end"] + timedelta(days=pred_delay)
        info_cols[2].info(f"**Adjusted End:** {adj_end.strftime('%d %b %Y')}")
        info_cols[3].info(f"**Predecessor Shift:** +{pred_delay} days")

        st.markdown(f"##### Enter data for {dept_part_counts[dept['name']]} part(s)")

        raw_parts = render_part_inputs(
            dept_name=dept["name"],
            dept_duration=dept["duration"],
            dept_original_end=tl_entry["original_end"],
            predecessor_delay=pred_delay,
            num_parts=dept_part_counts[dept["name"]],
            key_prefix=dept["name"],
        )
        dept_part_inputs[dept["name"]] = raw_parts


# ── Run Analysis ──────────────────────────────────────────────────────────────
if run_analysis:
    raw_results: list[DepartmentResult] = []
    for dept in DEPARTMENTS:
        tl_entry = next(t for t in timeline if t["name"] == dept["name"])
        dr = DepartmentResult(
            name=dept["name"],
            duration=dept["duration"],
            order=dept["order"],
            project_start=tl_entry["original_start"],
            predecessor_delay=0,
            parts=[PartEntry(**p) for p in dept_part_inputs[dept["name"]]],
        )
        raw_results.append(dr)

    final_results = propagate_delays(raw_results)
    for dr in final_results:
        st.session_state.dept_results[dr.name] = dr
    st.toast("✅ Analysis complete! See the Analytics tab.", icon="📊")


# ── Analytics Tab ─────────────────────────────────────────────────────────────
with dept_tabs[-2]:
    results = list(st.session_state.dept_results.values())
    if not results:
        st.info("Click **▶ Run Analysis** in the sidebar after entering part data.")
    else:
        sorted_results = sorted(results, key=lambda r: r.order)

        st.markdown("### 📈 Project KPIs")
        kpi_cols = st.columns(5)
        for col, dr in zip(kpi_cols, sorted_results):
            with col:
                metric_card(dr.name, f"{dr.avg_marks:.0f}", color=marks_color(dr.avg_marks))
        st.markdown("")

        all_marks = [dr.avg_marks for dr in sorted_results]
        overall = sum(all_marks) / len(all_marks) if all_marks else 0
        total_delay = sum(dr.actual_delay_out for dr in sorted_results)

        kpi2 = st.columns(3)
        with kpi2[0]:
            metric_card("Overall Score", f"{overall:.1f} / 100", color=marks_color(overall))
        with kpi2[1]:
            metric_card("Total Cascaded Delay", f"{total_delay} days",
                        color="#E74C3C" if total_delay > 0 else "#27AE60")
        with kpi2[2]:
            complete = sum(1 for dr in sorted_results for p in dr.parts if p.actual_finish)
            total_p = sum(len(dr.parts) for dr in sorted_results)
            metric_card("Parts Complete", f"{complete} / {total_p}", color="#1ABC9C")

        st.divider()
        st.plotly_chart(gantt_chart(sorted_results, project_start), use_container_width=True)
        st.plotly_chart(efficiency_bar_chart(sorted_results), use_container_width=True)

        st.markdown("### 🎯 Per-Department Marks")
        g_cols = st.columns(len(sorted_results))
        for col, dr in zip(g_cols, sorted_results):
            with col:
                st.plotly_chart(marks_gauge(dr.name, dr.avg_marks), use_container_width=True)

        delayed_parts = [
            (dr.name, p) for dr in sorted_results
            for p in dr.parts if p.actual_finish and p.delay_days > 0
        ]
        if delayed_parts:
            st.markdown("### ⚠️ Delay Summary")
            import pandas as pd
            rows = []
            for dept_name, p in delayed_parts:
                rows.append({
                    "Department": dept_name, "Part": p.name,
                    "Delay Days": p.delay_days,
                    "Category": p.delay_category or "—",
                    "Type": "External 🔵" if p.is_external else "Internal 🔴",
                    "Marks": round(p.marks, 1),
                    "Reason": (p.delay_reason or "—")[:60],
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ── Report Tab ────────────────────────────────────────────────────────────────
with dept_tabs[-1]:
    results = list(st.session_state.dept_results.values())
    st.markdown("### 📥 Download Excel Report")
    if not results:
        st.info("Run the analysis first to generate a report.")
    else:
        report_bytes = generate_report(
            project_code=project_code,
            project_start=project_start,
            dept_results=sorted(results, key=lambda r: r.order),
        )
        st.download_button(
            label="⬇️  Download Full Excel Report (.xlsx)",
            data=report_bytes,
            file_name=f"Adwik_WMS_{project_code}_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.caption("Report includes: Summary Dashboard, Part Detail, and Delay Log sheets.")

        st.markdown("#### Preview — Part Detail")
        import pandas as pd
        rows = []
        for dr in sorted(results, key=lambda r: r.order):
            for p in dr.parts:
                rows.append({
                    "Project": project_code, "Department": dr.name, "Part": p.name,
                    "Orig. Deadline": p.original_deadline.strftime("%d %b %Y"),
                    "Pred. Delay": f"+{p.predecessor_delay_days}d",
                    "Adj. Deadline": p.adjusted_deadline.strftime("%d %b %Y"),
                    "Actual Finish": p.actual_finish.strftime("%d %b %Y") if p.actual_finish else "Pending",
                    "Delay Days": p.delay_days if p.actual_finish else "—",
                    "Marks": round(p.marks, 1) if p.actual_finish else "—",
                })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
