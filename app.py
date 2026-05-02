"""
app.py — Adwik Intellimech | Workflow Analytics System
Run: streamlit run app.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from datetime import date, timedelta
import pandas as pd

from modules.core import (
    PartEntry, DepartmentResult,
    build_department_timeline, propagate_delays, BASE_MARKS,
    DEFAULT_DEPARTMENTS,
)
from modules.visualizations import gantt_chart, efficiency_bar_chart, marks_gauge
from modules.reporting import generate_report
from modules.ui_helpers import (
    inject_css, metric_card, dept_header, render_part_inputs, marks_color
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Adwik WMS", page_icon="⚙️",
                   layout="wide", initial_sidebar_state="expanded")
inject_css()

# ─────────────────────────────────────────────────────────────────────────────
#  SESSION STATE BOOTSTRAP
#  projects: list of {code, start, description, departments, parts_state, results}
# ─────────────────────────────────────────────────────────────────────────────
def _new_project(n: int) -> dict:
    return {
        "code":        f"PRJ-{n:03d}",
        "start":       date.today(),
        "description": "",
        "departments": [d.copy() for d in DEFAULT_DEPARTMENTS],
        # parts_state[dept_name] = list of part dicts
        "parts_state": {d["name"]: [{"name": f"Part 1"}] for d in DEFAULT_DEPARTMENTS},
        "results":     {},   # dept_name -> DepartmentResult after analysis
    }

if "projects" not in st.session_state:
    st.session_state.projects = [_new_project(1)]

if "active_project_idx" not in st.session_state:
    st.session_state.active_project_idx = 0


# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Adwik Intellimech")
    st.markdown("### Workflow Analytics System")
    st.divider()

    # Project switcher
    st.markdown("#### 📁 Projects")
    proj_labels = [f"{p['code']}" for p in st.session_state.projects]
    sel_idx = st.selectbox(
        "Active Project", range(len(proj_labels)),
        format_func=lambda i: proj_labels[i],
        index=st.session_state.active_project_idx,
        key="proj_selector",
    )
    st.session_state.active_project_idx = sel_idx

    c1, c2 = st.columns(2)
    if c1.button("➕ New Project", use_container_width=True):
        n = len(st.session_state.projects) + 1
        st.session_state.projects.append(_new_project(n))
        st.session_state.active_project_idx = len(st.session_state.projects) - 1
        st.rerun()
    if c2.button("🗑 Delete", use_container_width=True,
                 disabled=len(st.session_state.projects) <= 1):
        st.session_state.projects.pop(sel_idx)
        st.session_state.active_project_idx = max(0, sel_idx - 1)
        st.rerun()

    st.divider()

    # Active project settings
    proj = st.session_state.projects[st.session_state.active_project_idx]
    proj["code"]        = st.text_input("Project Code",  value=proj["code"],  key="pc")
    proj["start"]       = st.date_input("Start Date",    value=proj["start"], key="ps")
    proj["description"] = st.text_input("Description",   value=proj.get("description",""), key="pd")
    st.divider()

    # Department editor for active project
    st.markdown("#### 🏭 Departments")
    st.caption("Edit name, duration & planned dates per department.")
    depts     = proj["departments"]
    to_delete = None

    for i, dept in enumerate(depts):
        with st.expander(f"{dept['name']}  ({dept['duration']} days)", expanded=False):
            dept["name"]     = st.text_input("Name", value=dept["name"], key=f"dn_{sel_idx}_{i}")
            dept["duration"] = st.number_input("Duration (days)", 1, 365,
                                               value=dept["duration"], key=f"dd_{sel_idx}_{i}")
            dept["planned_start"] = st.date_input(
                "Planned Start", value=dept.get("planned_start"),
                key=f"dps_{sel_idx}_{i}", help="Planned start date for this department")
            dept["planned_end"] = st.date_input(
                "Planned End", value=dept.get("planned_end"),
                key=f"dpe_{sel_idx}_{i}", help="Planned end date for this department")
            dept["order"] = i + 1

            if st.button("🗑 Remove Dept", key=f"deldept_{sel_idx}_{i}",
                         use_container_width=True):
                to_delete = i

    if to_delete is not None:
        removed_name = depts[to_delete]["name"]
        depts.pop(to_delete)
        proj["parts_state"].pop(removed_name, None)
        proj["results"].pop(removed_name, None)
        st.rerun()

    if st.button("➕ Add Department", use_container_width=True):
        new_name = f"Dept {len(depts)+1}"
        depts.append({"name": new_name, "duration": 30, "order": len(depts)+1,
                      "planned_start": None, "planned_end": None})
        proj["parts_state"][new_name] = [{"name": "Part 1"}]
        st.rerun()

    if st.button("↩ Reset Departments", use_container_width=True):
        proj["departments"] = [d.copy() for d in DEFAULT_DEPARTMENTS]
        proj["parts_state"] = {d["name"]: [{"name": "Part 1"}] for d in DEFAULT_DEPARTMENTS}
        proj["results"]     = {}
        st.rerun()

    st.divider()
    run_analysis = st.button("▶  Run Analysis", use_container_width=True)
    st.caption("Enter data in tabs then click Run Analysis.")


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN AREA — TOP-LEVEL TABS
# ─────────────────────────────────────────────────────────────────────────────
top_tabs = st.tabs(["📁 All Projects", "🔧 Project Detail", "📊 Analytics", "📥 Report"])


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — ALL PROJECTS OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with top_tabs[0]:
    st.markdown("## 📁 All Projects")
    st.caption("Overview of every project. Switch the active project in the sidebar.")

    rows = []
    for i, p in enumerate(st.session_state.projects):
        results  = list(p["results"].values())
        dept_n   = len(p["departments"])
        dur      = sum(d["duration"] for d in p["departments"])
        parts_t  = sum(len(v) for v in p["parts_state"].values())
        done_p   = sum(1 for dr in results for pt in dr.parts if pt.actual_finish)
        marks_l  = [dr.avg_marks for dr in results] if results else []
        avg_sc   = round(sum(marks_l)/len(marks_l), 1) if marks_l else "—"
        delay    = sum(dr.actual_delay_out for dr in results) if results else 0
        status   = ("✅ On Track" if delay == 0 and results else
                    f"⚠️ {delay}d delay" if results else "🕐 Not Analysed")
        rows.append({
            "#":            i + 1,
            "Project Code": p["code"],
            "Description":  p.get("description", ""),
            "Start Date":   p["start"].strftime("%d %b %Y"),
            "Departments":  dept_n,
            "Duration (days)": dur,
            "Parts Tracked": parts_t,
            "Parts Done":   done_p,
            "Avg Score":    avg_sc,
            "Total Delay":  f"{delay}d" if results else "—",
            "Status":       status,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Quick KPI cards across all projects
    if any(p["results"] for p in st.session_state.projects):
        st.divider()
        st.markdown("### 📊 Portfolio KPIs")
        all_scores = [
            dr.avg_marks
            for p in st.session_state.projects
            for dr in p["results"].values()
        ]
        total_delays = sum(
            dr.actual_delay_out
            for p in st.session_state.projects
            for dr in p["results"].values()
        )
        k1, k2, k3, k4 = st.columns(4)
        with k1: metric_card("Total Projects",    str(len(st.session_state.projects)), "#1ABC9C")
        with k2: metric_card("Portfolio Avg Score",
                             f"{sum(all_scores)/len(all_scores):.1f}" if all_scores else "—",
                             marks_color(sum(all_scores)/len(all_scores)) if all_scores else "#aaa")
        with k3: metric_card("Total Portfolio Delay", f"{total_delays}d",
                             "#E74C3C" if total_delays else "#27AE60")
        with k4:
            all_done = sum(1 for p in st.session_state.projects
                           for dr in p["results"].values()
                           for pt in dr.parts if pt.actual_finish)
            all_total = sum(len(v) for p in st.session_state.projects
                            for v in p["parts_state"].values())
            metric_card("Total Parts Done", f"{all_done} / {all_total}", "#1ABC9C")


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — PROJECT DETAIL (department tabs + part entry)
# ══════════════════════════════════════════════════════════════════════════════
with top_tabs[1]:
    proj  = st.session_state.projects[st.session_state.active_project_idx]
    DEPTS = proj["departments"]

    st.markdown(
        f"## 🔧 <span style='color:#1ABC9C'>{proj['code']}</span>"
        f"{'  — ' + proj['description'] if proj['description'] else ''}",
        unsafe_allow_html=True,
    )
    total_days = sum(d["duration"] for d in DEPTS)
    st.caption(f"Start: {proj['start'].strftime('%d %b %Y')}  |  "
               f"Departments: {len(DEPTS)}  |  Total Duration: {total_days} days")
    st.divider()

    if not DEPTS:
        st.warning("No departments. Add one in the sidebar.")
        st.stop()

    # Ensure parts_state has keys for every current department
    for dept in DEPTS:
        if dept["name"] not in proj["parts_state"]:
            proj["parts_state"][dept["name"]] = [{"name": "Part 1"}]

    timeline = build_department_timeline(proj["start"], DEPTS)
    dept_tabs_inner = st.tabs([f"📋 {d['name']}" for d in DEPTS])
    dept_part_inputs: dict[str, list[dict]] = {}

    for tab_obj, dept in zip(dept_tabs_inner, DEPTS):
        with tab_obj:
            tl_entry   = next(t for t in timeline if t["name"] == dept["name"])
            saved      = proj["results"].get(dept["name"])
            pred_delay = saved.predecessor_delay if saved else 0

            dept_header(dept["name"], dept["duration"])

            # Info bar
            ic = st.columns(5)
            ic[0].info(f"**Original End:** {tl_entry['original_end'].strftime('%d %b %Y')}")
            ic[1].info(f"**Duration:** {dept['duration']} days")
            adj_end = tl_entry["original_end"] + timedelta(days=pred_delay)
            ic[2].info(f"**Adjusted End:** {adj_end.strftime('%d %b %Y')}")
            ic[3].info(f"**Predecessor Shift:** +{pred_delay} days")
            # Planned dates
            ps_str = dept.get("planned_start")
            pe_str = dept.get("planned_end")
            ic[4].info(
                f"**Planned:** "
                f"{ps_str.strftime('%d %b %Y') if ps_str else '—'} → "
                f"{pe_str.strftime('%d %b %Y') if pe_str else '—'}"
            )

            # Parts — dynamic add
            parts_state = proj["parts_state"][dept["name"]]
            st.markdown(f"##### Parts ({len(parts_state)})")

            raw_parts = render_part_inputs(
                dept_name=dept["name"],
                dept_duration=dept["duration"],
                dept_original_end=tl_entry["original_end"],
                predecessor_delay=pred_delay,
                parts_state=parts_state,
                key_prefix=f"{st.session_state.active_project_idx}_{dept['name']}",
            )
            dept_part_inputs[dept["name"]] = raw_parts

            if st.button("➕ Add Part", key=f"addpart_{st.session_state.active_project_idx}_{dept['name']}"):
                parts_state.append({"name": f"Part {len(parts_state)+1}"})
                st.rerun()

    # Run Analysis
    if run_analysis:
        raw_results: list[DepartmentResult] = []
        for dept in DEPTS:
            tl_entry = next(t for t in timeline if t["name"] == dept["name"])
            parts    = dept_part_inputs.get(dept["name"], [])
            dr = DepartmentResult(
                name=dept["name"],
                duration=dept["duration"],
                order=dept["order"],
                project_start=tl_entry["original_start"],
                predecessor_delay=0,
                planned_start=dept.get("planned_start"),
                planned_end=dept.get("planned_end"),
                parts=[PartEntry(**p) for p in parts],
            )
            raw_results.append(dr)

        final = propagate_delays(raw_results)
        for dr in final:
            proj["results"][dr.name] = dr
        st.toast(f"✅ Analysis complete for {proj['code']}!", icon="📊")
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 3 — ANALYTICS (active project)
# ══════════════════════════════════════════════════════════════════════════════
with top_tabs[2]:
    proj    = st.session_state.projects[st.session_state.active_project_idx]
    results = list(proj["results"].values())

    st.markdown(f"## 📊 Analytics — {proj['code']}")

    if not results:
        st.info("Click **▶ Run Analysis** in the sidebar after entering part data.")
    else:
        sorted_results = sorted(results, key=lambda r: r.order)

        # Per-dept KPI cards
        st.markdown("### 📈 Department Scores")
        kpi_cols = st.columns(len(sorted_results))
        for col, dr in zip(kpi_cols, sorted_results):
            with col:
                metric_card(dr.name, f"{dr.avg_marks:.0f}", color=marks_color(dr.avg_marks))

        st.markdown("")
        all_marks   = [dr.avg_marks for dr in sorted_results]
        overall     = sum(all_marks) / len(all_marks)
        total_delay = sum(dr.actual_delay_out for dr in sorted_results)

        k1, k2, k3 = st.columns(3)
        with k1: metric_card("Overall Score", f"{overall:.1f} / 100", marks_color(overall))
        with k2: metric_card("Total Cascaded Delay", f"{total_delay} days",
                             "#E74C3C" if total_delay else "#27AE60")
        with k3:
            done = sum(1 for dr in sorted_results for p in dr.parts if p.actual_finish)
            total_p = sum(len(dr.parts) for dr in sorted_results)
            metric_card("Parts Complete", f"{done} / {total_p}", "#1ABC9C")

        st.divider()
        st.plotly_chart(gantt_chart(sorted_results, proj["start"]), use_container_width=True)
        st.plotly_chart(efficiency_bar_chart(sorted_results), use_container_width=True)

        st.markdown("### 🎯 Per-Department Gauges")
        g_cols = st.columns(len(sorted_results))
        for col, dr in zip(g_cols, sorted_results):
            with col:
                st.plotly_chart(marks_gauge(dr.name, dr.avg_marks), use_container_width=True)

        # Planned vs Actual table
        st.markdown("### 📅 Planned vs Actual")
        pva_rows = []
        for dr in sorted_results:
            ps = dr.planned_start.strftime("%d %b %Y") if dr.planned_start else "—"
            pe = dr.planned_end.strftime("%d %b %Y")   if dr.planned_end   else "—"
            finished = [p for p in dr.parts if p.actual_finish]
            actual_end = (max(p.actual_finish for p in finished).strftime("%d %b %Y")
                          if finished else "Pending")
            pva_rows.append({
                "Department": dr.name,
                "Planned Start": ps,
                "Planned End": pe,
                "Shifted End": dr.shifted_end.strftime("%d %b %Y"),
                "Actual End": actual_end,
                "Delay (days)": dr.actual_delay_out or "—",
                "Score": round(dr.avg_marks, 1),
            })
        st.dataframe(pd.DataFrame(pva_rows), use_container_width=True, hide_index=True)

        # Delay summary
        delayed = [(dr.name, p) for dr in sorted_results
                   for p in dr.parts if p.actual_finish and p.delay_days > 0]
        if delayed:
            st.markdown("### ⚠️ Delay Log")
            d_rows = []
            for dname, p in delayed:
                d_rows.append({
                    "Department": dname, "Part": p.name,
                    "Delay Days": p.delay_days,
                    "Category":  p.delay_category or "—",
                    "Type":      "External 🔵" if p.is_external else "Internal 🔴",
                    "Marks":     round(p.marks, 1),
                    "Reason":    (p.delay_reason or "—")[:60],
                })
            st.dataframe(pd.DataFrame(d_rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 4 — REPORT DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════════
with top_tabs[3]:
    st.markdown("## 📥 Download Excel Report")

    # Scope selector
    scope = st.radio(
        "Report Scope",
        ["Active Project Only", "All Projects"],
        horizontal=True,
    )

    if scope == "Active Project Only":
        proj_list = [st.session_state.projects[st.session_state.active_project_idx]]
    else:
        proj_list = st.session_state.projects

    analysed = [p for p in proj_list if p["results"]]

    if not analysed:
        st.info("Run analysis on at least one project first.")
    else:
        all_proj_data = [
            {
                "project_code":  p["code"],
                "project_start": p["start"],
                "dept_results":  sorted(p["results"].values(), key=lambda r: r.order),
            }
            for p in analysed
        ]

        report_bytes = generate_report(all_proj_data)
        fname = (f"Adwik_WMS_{analysed[0]['code']}_{date.today().isoformat()}.xlsx"
                 if len(analysed) == 1
                 else f"Adwik_WMS_AllProjects_{date.today().isoformat()}.xlsx")

        st.download_button(
            label="⬇️  Download Excel Report (.xlsx)",
            data=report_bytes,
            file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.caption(f"Includes {len(analysed)} project(s) — "
                   "Sheet 1: All Projects Overview, then Part Detail + Delay Log per project.")

        # Preview
        st.markdown("#### Preview")
        prev_rows = []
        for p in analysed:
            for dr in sorted(p["results"].values(), key=lambda r: r.order):
                for pt in dr.parts:
                    prev_rows.append({
                        "Project":       p["code"],
                        "Department":    dr.name,
                        "Part":          pt.name,
                        "Planned Start": pt.planned_start.strftime("%d %b %Y") if pt.planned_start else "—",
                        "Planned End":   pt.planned_end.strftime("%d %b %Y")   if pt.planned_end   else "—",
                        "Adj. Deadline": pt.adjusted_deadline.strftime("%d %b %Y"),
                        "Actual Finish": pt.actual_finish.strftime("%d %b %Y") if pt.actual_finish else "Pending",
                        "Delay Days":    pt.delay_days if pt.actual_finish else "—",
                        "Marks":         round(pt.marks, 1) if pt.actual_finish else "—",
                    })
        st.dataframe(pd.DataFrame(prev_rows), use_container_width=True, hide_index=True)
