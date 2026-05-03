"""
app.py — Adwik Intellimech | Workflow Analytics System
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from datetime import date, timedelta
import pandas as pd

from modules.core import (
    PartEntry, DepartmentResult,
    build_department_timeline, propagate_delays, BASE_MARKS, DEFAULT_DEPARTMENTS,
)
from modules.visualizations import gantt_chart, efficiency_bar_chart, marks_gauge
from modules.reporting import generate_report
from modules.persistence import serialize_projects, deserialize_projects
from modules.ui_helpers import (
    inject_css, metric_card, kpi_card, dept_header, render_part_inputs,
    marks_color, page_hero, info_pills, section_heading, step_indicator,
    progress_bar, completion_ring_html, badge,
)

st.set_page_config(
    page_title="Adwik Intellimech WMS",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()


# ── Session state ─────────────────────────────────────────────────────────────
def _new_project(n: int) -> dict:
    return {
        "code":        f"PRJ-{n:03d}",
        "start":       date.today(),
        "description": "",
        "departments": [d.copy() for d in DEFAULT_DEPARTMENTS],
        "parts_state": {d["name"]: [{"name": "Part 1"}] for d in DEFAULT_DEPARTMENTS},
        "results":     {},
    }

for key, val in [
    ("projects",           [_new_project(1)]),
    ("active_project_idx", 0),
    ("load_feedback",      ""),
]:
    if key not in st.session_state:
        st.session_state[key] = val


# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='padding:16px 0 8px'>"
        "<span style='font-size:1.3rem;font-weight:700;color:#1A1F36'>⚙️ Adwik WMS</span><br>"
        "<span style='font-size:0.78rem;color:#718096'>Workflow Analytics System</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── 💾 Save / Load ────────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.72rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.7px;color:#718096;margin-bottom:8px'>💾 Save & Load</div>",
        unsafe_allow_html=True,
    )
    save_bytes = serialize_projects(st.session_state.projects)
    st.download_button(
        "⬇️  Save progress (.json)",
        data=save_bytes,
        file_name=f"adwik_wms_{date.today().isoformat()}.json",
        mime="application/json",
        use_container_width=True,
        help="Saves your entire workspace. Re-upload anytime to restore.",
    )
    uploaded = st.file_uploader(
        "Load saved file", type=["json"],
        key="load_uploader", label_visibility="collapsed",
    )
    if uploaded:
        loaded, feedback = deserialize_projects(uploaded.read())
        if loaded:
            st.session_state.projects = loaded
            st.session_state.active_project_idx = 0
            st.session_state.load_feedback = f"✅ {feedback}"
            st.rerun()
        else:
            st.session_state.load_feedback = f"❌ {feedback}"
    if st.session_state.load_feedback:
        fn = st.success if st.session_state.load_feedback.startswith("✅") else st.error
        fn(st.session_state.load_feedback, icon=None)

    st.divider()

    # ── Projects ──────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.72rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.7px;color:#718096;margin-bottom:8px'>📁 Projects</div>",
        unsafe_allow_html=True,
    )
    proj_labels = [p["code"] for p in st.session_state.projects]
    sel_idx = st.selectbox(
        "Active project", range(len(proj_labels)),
        format_func=lambda i: proj_labels[i],
        index=min(st.session_state.active_project_idx, len(proj_labels)-1),
        label_visibility="collapsed",
    )
    st.session_state.active_project_idx = sel_idx

    c1, c2 = st.columns(2)
    if c1.button("➕ New", use_container_width=True):
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

    # ── Active project settings ───────────────────────────────────────────────
    proj = st.session_state.projects[st.session_state.active_project_idx]
    st.markdown(
        "<div style='font-size:0.72rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.7px;color:#718096;margin-bottom:8px'>⚙️ Project Settings</div>",
        unsafe_allow_html=True,
    )
    proj["code"]        = st.text_input("Project Code",  value=proj["code"],  key="pc")
    proj["start"]       = st.date_input("Start Date",    value=proj["start"], key="ps")
    proj["description"] = st.text_input("Description",   value=proj.get("description",""), key="pd",
                                         placeholder="e.g. Hydraulic Press Build")
    st.divider()

    # ── Department editor ─────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.72rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.7px;color:#718096;margin-bottom:8px'>🏭 Departments</div>",
        unsafe_allow_html=True,
    )
    depts     = proj["departments"]
    to_delete = None

    for i, dept in enumerate(depts):
        done_parts  = sum(1 for p in proj["parts_state"].get(dept["name"], [])
                          if p.get("actual_finish"))
        total_parts = len(proj["parts_state"].get(dept["name"], []))
        pct         = int(done_parts / total_parts * 100) if total_parts else 0
        color       = "#059669" if pct == 100 else "#3B5BDB" if pct > 0 else "#A0AEC0"

        with st.expander(f"{dept['name']} — {done_parts}/{total_parts} parts done", expanded=False):
            st.markdown(
                f'<div style="margin-bottom:8px">'
                f'<div style="font-size:0.72rem;color:#718096;margin-bottom:3px">'
                f'Completion</div>'
                f'<div style="background:#E5E9F2;border-radius:99px;height:6px;overflow:hidden">'
                f'<div style="width:{pct}%;height:100%;background:{color};border-radius:99px">'
                f'</div></div></div>',
                unsafe_allow_html=True,
            )
            dept["name"]     = st.text_input("Name",     value=dept["name"],     key=f"dn_{sel_idx}_{i}")
            dept["duration"] = st.number_input("Duration (days)", 1, 365,
                                               value=dept["duration"],           key=f"dd_{sel_idx}_{i}")
            dept["planned_start"] = st.date_input("Planned Start",
                value=dept.get("planned_start"), key=f"dps_{sel_idx}_{i}")
            dept["planned_end"]   = st.date_input("Planned End",
                value=dept.get("planned_end"),   key=f"dpe_{sel_idx}_{i}")
            dept["order"] = i + 1
            if st.button("Remove department", key=f"deldept_{sel_idx}_{i}",
                         use_container_width=True):
                to_delete = i

    if to_delete is not None:
        removed = depts[to_delete]["name"]
        depts.pop(to_delete)
        proj["parts_state"].pop(removed, None)
        proj["results"].pop(removed, None)
        st.rerun()

    col_a, col_b = st.columns(2)
    if col_a.button("➕ Add Dept", use_container_width=True):
        nm = f"Dept {len(depts)+1}"
        depts.append({"name": nm, "duration": 30, "order": len(depts)+1,
                      "planned_start": None, "planned_end": None})
        proj["parts_state"][nm] = [{"name": "Part 1"}]
        st.rerun()
    if col_b.button("↩ Reset", use_container_width=True):
        proj["departments"] = [d.copy() for d in DEFAULT_DEPARTMENTS]
        proj["parts_state"] = {d["name"]: [{"name": "Part 1"}] for d in DEFAULT_DEPARTMENTS}
        proj["results"] = {}
        st.rerun()

    st.divider()
    run_analysis = st.button("▶  Run Analysis", use_container_width=True)
    st.caption("💡 Save your progress anytime using ⬇️ above.")


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_all, tab_detail, tab_analytics, tab_report = st.tabs([
    "📁  All Projects",
    "🔧  Project Detail",
    "📊  Analytics",
    "📥  Report",
])


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — ALL PROJECTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_all:
    # Hero
    st.markdown(
        "<div class='page-hero'>"
        "<h1>📁 All Projects</h1>"
        "<p>Your complete project portfolio at a glance. "
        "Select a project in the sidebar to edit it.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    # Portfolio KPI strip
    all_results = [dr for p in st.session_state.projects for dr in p["results"].values()]
    if all_results:
        all_scores   = [dr.avg_marks for dr in all_results]
        total_delay  = sum(dr.actual_delay_out for dr in all_results)
        all_done     = sum(1 for dr in all_results for pt in dr.parts if pt.actual_finish)
        all_total    = sum(len(v) for p in st.session_state.projects for v in p["parts_state"].values())
        portfolio_sc = sum(all_scores) / len(all_scores)

        k1, k2, k3, k4 = st.columns(4)
        with k1: kpi_card("Total Projects",    str(len(st.session_state.projects)), color="#3B5BDB")
        with k2: kpi_card("Portfolio Score",   f"{portfolio_sc:.0f}",
                           sub="out of 100", color=marks_color(portfolio_sc))
        with k3: kpi_card("Total Delay",       f"{total_delay}d",
                           color="#DC2626" if total_delay else "#059669")
        with k4: kpi_card("Parts Completed",   f"{all_done}/{all_total}", color="#3B5BDB")
        st.markdown("<div style='margin-bottom:16px'></div>", unsafe_allow_html=True)

    # Project cards grid
    cols = st.columns(min(len(st.session_state.projects), 3))
    for i, p in enumerate(st.session_state.projects):
        results     = list(p["results"].values())
        done_parts  = sum(1 for dr in results for pt in dr.parts if pt.actual_finish)
        total_parts = sum(len(v) for v in p["parts_state"].values())
        pct         = int(done_parts / total_parts * 100) if total_parts else 0
        marks_l     = [dr.avg_marks for dr in results]
        avg_sc      = round(sum(marks_l)/len(marks_l), 1) if marks_l else None
        delay       = sum(dr.actual_delay_out for dr in results) if results else 0
        sc_color    = marks_color(avg_sc) if avg_sc else "#A0AEC0"
        status      = "✅ On Track" if results and delay == 0 else (
                      f"⚠️ {delay}d delay" if results else "⏳ Not analysed")
        ring        = completion_ring_html(pct, sc_color)

        with cols[i % 3]:
            st.markdown(
                f"""<div class="wms-card" style="cursor:pointer">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                      <div style="font-size:1rem;font-weight:700;color:#1A1F36">{p['code']}</div>
                      <div style="font-size:0.78rem;color:#718096;margin-top:2px">
                        {p.get('description','') or 'No description'}</div>
                      <div style="font-size:0.75rem;color:#A0AEC0;margin-top:4px">
                        Started {p['start'].strftime('%d %b %Y') if isinstance(p['start'],date) else p['start']}
                      </div>
                    </div>
                    {ring}
                  </div>
                  <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">
                    <span class="badge badge-{'green' if results and delay==0 else 'red' if delay else 'blue'}">{status}</span>
                    <span class="badge badge-purple">{len(p['departments'])} depts</span>
                    {'<span class="badge badge-blue">Score: '+str(avg_sc)+'</span>' if avg_sc else ''}
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )

    # Summary table
    section_heading("Detailed Summary")
    rows = []
    for i, p in enumerate(st.session_state.projects):
        results = list(p["results"].values())
        marks_l = [dr.avg_marks for dr in results]
        delay   = sum(dr.actual_delay_out for dr in results) if results else 0
        rows.append({
            "Code":       p["code"],
            "Description": p.get("description","—"),
            "Start":      p["start"].strftime("%d %b %Y") if isinstance(p["start"],date) else str(p["start"]),
            "Depts":      len(p["departments"]),
            "Duration":   f"{sum(d['duration'] for d in p['departments'])}d",
            "Parts":      sum(len(v) for v in p["parts_state"].values()),
            "Avg Score":  round(sum(marks_l)/len(marks_l),1) if marks_l else "—",
            "Delay":      f"{delay}d" if results else "—",
            "Status":     "On Track" if results and delay==0 else (f"{delay}d delay" if results else "Not analysed"),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — PROJECT DETAIL
# ══════════════════════════════════════════════════════════════════════════════
with tab_detail:
    proj  = st.session_state.projects[st.session_state.active_project_idx]
    DEPTS = proj["departments"]

    if not DEPTS:
        st.warning("No departments defined. Add one in the sidebar.")
        st.stop()

    for dept in DEPTS:
        if dept["name"] not in proj["parts_state"]:
            proj["parts_state"][dept["name"]] = [{"name": "Part 1"}]

    # Hero with overall progress
    total_parts = sum(len(v) for v in proj["parts_state"].values())
    done_parts  = sum(1 for dr in proj["results"].values()
                      for pt in dr.parts if pt.actual_finish)
    overall_pct = int(done_parts / total_parts * 100) if total_parts else 0
    page_hero(proj["code"], proj["start"], len(DEPTS), sum(d["duration"] for d in DEPTS))

    # Step indicator showing which departments have been completed
    dept_names = [d["name"] for d in DEPTS]
    completed_depts = sum(
        1 for d in DEPTS
        if all(p.get("actual_finish") for p in proj["parts_state"].get(d["name"], []))
        and proj["parts_state"].get(d["name"])
    )
    step_indicator(dept_names, completed_depts)

    # Overall project progress bar
    info_pills([
        ("Overall Progress", f"{overall_pct}%"),
        ("Parts Done", f"{done_parts}/{total_parts}"),
        ("Departments", str(len(DEPTS))),
        ("Analysis", "✅ Ready" if proj["results"] else "⏳ Pending"),
    ])

    timeline = build_department_timeline(proj["start"], DEPTS)
    dept_tabs_ui = st.tabs([f"{d['name']}" for d in DEPTS])
    dept_part_inputs: dict[str, list[dict]] = {}

    for tab_obj, dept in zip(dept_tabs_ui, DEPTS):
        with tab_obj:
            tl_entry   = next(t for t in timeline if t["name"] == dept["name"])
            saved      = proj["results"].get(dept["name"])
            pred_delay = saved.predecessor_delay if saved else 0

            parts_state  = proj["parts_state"][dept["name"]]
            done_p       = sum(1 for p in parts_state if p.get("actual_finish"))
            total_p      = len(parts_state)
            comp_pct     = done_p / total_p * 100 if total_p else 0

            dept_header(dept["name"], dept["duration"], comp_pct, pred_delay)

            # Info pills
            adj_end = tl_entry["original_end"] + timedelta(days=pred_delay)
            ps = dept.get("planned_start")
            pe = dept.get("planned_end")
            info_pills([
                ("Original End",     tl_entry["original_end"].strftime("%d %b %Y")),
                ("Adjusted End",     adj_end.strftime("%d %b %Y")),
                ("Predecessor Shift",f"+{pred_delay}d"),
                ("Planned",          f"{ps.strftime('%d %b %Y') if ps else '—'} → {pe.strftime('%d %b %Y') if pe else '—'}"),
                ("Parts",            f"{done_p}/{total_p} done"),
            ])

            section_heading(f"Parts ({total_p})")

            raw_parts = render_part_inputs(
                dept_name=dept["name"],
                dept_duration=dept["duration"],
                dept_original_end=tl_entry["original_end"],
                predecessor_delay=pred_delay,
                parts_state=parts_state,
                key_prefix=f"{st.session_state.active_project_idx}_{dept['name']}",
            )
            dept_part_inputs[dept["name"]] = raw_parts

            if st.button(
                f"➕  Add Part to {dept['name']}",
                key=f"addpart_{st.session_state.active_project_idx}_{dept['name']}",
            ):
                parts_state.append({"name": f"Part {len(parts_state)+1}"})
                st.rerun()

    # Run analysis
    if run_analysis:
        with st.spinner("Running analysis and cascading delays..."):
            raw_results: list[DepartmentResult] = []
            for dept in DEPTS:
                tl_entry = next(t for t in timeline if t["name"] == dept["name"])
                parts    = dept_part_inputs.get(dept["name"], [])
                dr = DepartmentResult(
                    name=dept["name"], duration=dept["duration"],
                    order=dept["order"], project_start=tl_entry["original_start"],
                    predecessor_delay=0,
                    planned_start=dept.get("planned_start"),
                    planned_end=dept.get("planned_end"),
                    parts=[PartEntry(**p) for p in parts],
                )
                raw_results.append(dr)
            final = propagate_delays(raw_results)
            for dr in final:
                proj["results"][dr.name] = dr
        st.toast(f"✅ Analysis done for {proj['code']}! Remember to Save.", icon="📊")
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 3 — ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
with tab_analytics:
    proj    = st.session_state.projects[st.session_state.active_project_idx]
    results = list(proj["results"].values())

    st.markdown(
        f"<div class='page-hero'>"
        f"<h1>📊 Analytics — {proj['code']}</h1>"
        f"<p>Performance breakdown across all departments and parts.</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if not results:
        st.info("👈  Enter part data in the **Project Detail** tab, then click **▶ Run Analysis** in the sidebar.")
    else:
        sorted_results = sorted(results, key=lambda r: r.order)
        all_marks      = [dr.avg_marks for dr in sorted_results]
        overall        = sum(all_marks) / len(all_marks)
        total_delay    = sum(dr.actual_delay_out for dr in sorted_results)
        done           = sum(1 for dr in sorted_results for p in dr.parts if p.actual_finish)
        total_p        = sum(len(dr.parts) for dr in sorted_results)

        # Top KPIs
        section_heading("Project KPIs")
        k1, k2, k3, k4 = st.columns(4)
        with k1: kpi_card("Overall Score",    f"{overall:.0f}",
                           sub="out of 100", color=marks_color(overall))
        with k2: kpi_card("Cascaded Delay",   f"{total_delay}d",
                           sub="finish delay only", color="#DC2626" if total_delay else "#059669")
        with k3: kpi_card("Parts Complete",   f"{done}/{total_p}",
                           sub=f"{done/total_p*100:.0f}% done", color="#3B5BDB")
        with k4:
            racing = sum(1 for dr in sorted_results if getattr(dr, "any_racing", False))
            kpi_card("Late Start / On Time", str(racing),
                     sub="departments recovered", color="#D97706")

        st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

        # Department score cards
        section_heading("Department Scores")
        dcols = st.columns(len(sorted_results))
        for col, dr in zip(dcols, sorted_results):
            with col:
                ring  = completion_ring_html(dr.completion_pct, marks_color(dr.avg_marks), 64)
                delay_badge = (
                    f'<span class="badge badge-red">{dr.actual_delay_out}d cascade</span>'
                    if dr.actual_delay_out else
                    '<span class="badge badge-green">No cascade</span>'
                )
                racing_badge = (
                    '<span class="badge badge-yellow">⚡ Recovered</span>'
                    if getattr(dr, "any_racing", False) else ""
                )
                st.markdown(
                    f"""<div class="wms-card" style="text-align:center">
                      <div style="display:flex;justify-content:center;margin-bottom:8px">{ring}</div>
                      <div style="font-weight:700;color:#1A1F36;font-size:0.9rem">{dr.name}</div>
                      <div style="font-size:1.5rem;font-weight:700;color:{marks_color(dr.avg_marks)};margin:4px 0">
                        {dr.avg_marks:.0f}<span style="font-size:0.8rem;color:#A0AEC0"> /100</span></div>
                      <div style="display:flex;justify-content:center;gap:6px;flex-wrap:wrap;margin-top:6px">
                        {delay_badge}{racing_badge}
                      </div>
                    </div>""",
                    unsafe_allow_html=True,
                )

        # Charts
        section_heading("Timeline")
        st.plotly_chart(gantt_chart(sorted_results, proj["start"]), use_container_width=True)

        section_heading("Efficiency")
        st.plotly_chart(efficiency_bar_chart(sorted_results), use_container_width=True)

        # Gauges
        section_heading("Performance Gauges")
        gcols = st.columns(len(sorted_results))
        for col, dr in zip(gcols, sorted_results):
            with col:
                st.plotly_chart(marks_gauge(dr.name, dr.avg_marks), use_container_width=True)

        # Planned vs Actual table
        section_heading("Planned vs Actual")
        pva = []
        for dr in sorted_results:
            finished   = [p for p in dr.parts if p.actual_finish]
            actual_end = max(p.actual_finish for p in finished).strftime("%d %b %Y") if finished else "Pending"
            pva.append({
                "Department":           dr.name,
                "Planned Start":        dr.planned_start.strftime("%d %b %Y") if dr.planned_start else "—",
                "Planned End":          dr.planned_end.strftime("%d %b %Y")   if dr.planned_end   else "—",
                "Adjusted End":         dr.shifted_end.strftime("%d %b %Y"),
                "Actual End":           actual_end,
                "Start Delay (days)":   getattr(dr, "max_start_delay", 0) or "—",
                "Cascade Delay (days)": dr.actual_delay_out or "✅ 0",
                "Recovered?":           "⚡ Yes" if getattr(dr, "any_racing", False) else "—",
                "Score":                round(dr.avg_marks, 1),
            })
        st.dataframe(pd.DataFrame(pva), use_container_width=True, hide_index=True)

        with st.expander("ℹ️  How cascade delay is calculated"):
            st.markdown("""
| Scenario | Cascade to next dept |
|---|---|
| Started on time, finished on time | **0 days** |
| **Started late, finished on time ⚡** | **0 days — no cascade** |
| Started on time, finished late | **N days** |
| Started late, finished late | **finish overshoot only** |

Only finish delay propagates forward. A department that started late but
recovered and delivered on time has **zero impact** on the next department.
""")

        # Delay log
        delayed = [(dr.name, p) for dr in sorted_results
                   for p in dr.parts if p.actual_finish and p.delay_days > 0]
        if delayed:
            section_heading("Delay Log")
            d_rows = []
            for dname, p in delayed:
                d_rows.append({
                    "Department": dname,
                    "Part":       p.name,
                    "Delay Days": p.delay_days,
                    "Category":   p.delay_category or "—",
                    "Type":       "External" if p.is_external else "Internal",
                    "Penalty":    "None" if p.is_external else f"−{p.delay_days*5} marks",
                    "Marks":      round(p.marks, 1),
                    "Reason":     (p.delay_reason or "—")[:80],
                })
            st.dataframe(pd.DataFrame(d_rows), use_container_width=True, hide_index=True)
        else:
            st.success("🎉  No delays recorded for this project.", icon=None)


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 4 — REPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab_report:
    st.markdown(
        "<div class='page-hero'>"
        "<h1>📥 Download Report</h1>"
        "<p>Export your project data as a professional Excel workbook.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    scope = st.radio(
        "Report scope",
        ["Active project only", "All projects"],
        horizontal=True,
        label_visibility="collapsed",
    )
    proj_list = ([st.session_state.projects[st.session_state.active_project_idx]]
                 if scope == "Active project only"
                 else st.session_state.projects)
    analysed = [p for p in proj_list if p["results"]]

    if not analysed:
        st.info("Run analysis on at least one project first, then come back here to download.")
    else:
        # What's inside callout
        st.markdown(
            """<div class="wms-card-blue">
              <div style="font-weight:700;color:#1E3A8A;margin-bottom:10px">📋 Report Contents</div>
              <div style="font-size:0.85rem;color:#1E40AF;line-height:1.8">
                <b>Sheet 1 — Projects Overview</b>: All projects with KPIs and efficiency chart<br>
                <b>Sheet 2+ — Part Detail</b>: Every part with planned/actual dates, delays, marks<br>
                <b>Sheet 3+ — Delay Log</b>: Only delayed parts with category and reason
              </div>
            </div>""",
            unsafe_allow_html=True,
        )

        all_proj_data = [
            {
                "project_code":  p["code"],
                "project_start": p["start"],
                "dept_results":  sorted(p["results"].values(), key=lambda r: r.order),
            }
            for p in analysed
        ]
        report_bytes = generate_report(all_proj_data)
        fname = (
            f"Adwik_WMS_{analysed[0]['code']}_{date.today().isoformat()}.xlsx"
            if len(analysed) == 1
            else f"Adwik_WMS_AllProjects_{date.today().isoformat()}.xlsx"
        )
        st.download_button(
            "⬇️  Download Excel Report (.xlsx)",
            data=report_bytes,
            file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.caption(f"Covering {len(analysed)} project(s) · Generated {date.today().strftime('%d %b %Y')}")

        # Preview
        section_heading("Preview")
        prev_rows = []
        for p in analysed:
            for dr in sorted(p["results"].values(), key=lambda r: r.order):
                for pt in dr.parts:
                    prev_rows.append({
                        "Project":    p["code"],
                        "Dept":       dr.name,
                        "Part":       pt.name,
                        "Planned End": pt.planned_end.strftime("%d %b %Y") if pt.planned_end else "—",
                        "Actual Start": pt.actual_start.strftime("%d %b %Y") if getattr(pt,"actual_start",None) else "—",
                        "Adj. Deadline": pt.adjusted_deadline.strftime("%d %b %Y"),
                        "Actual Finish": pt.actual_finish.strftime("%d %b %Y") if pt.actual_finish else "Pending",
                        "Delay Days": pt.delay_days if pt.actual_finish else "—",
                        "Marks":      round(pt.marks,1) if pt.actual_finish else "—",
                    })
        st.dataframe(pd.DataFrame(prev_rows), use_container_width=True, hide_index=True)
