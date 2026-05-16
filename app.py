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
    inject_css, hero, kpi_row, kpi_card, metric_card,
    dept_header, render_part_inputs, marks_color,
    page_hero, pill_row, info_pills, section_label, section_heading,
    step_indicator, progress_bar, completion_ring_html,
)

st.set_page_config(
    page_title="Adwik Intellimech WMS",
    page_icon="⚙️", layout="wide",
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


def _proj_fingerprint(projects: list[dict]):
    """Cheap fingerprint to detect obvious changes to projects.
    Not cryptographic — just avoids re-serializing on every rerun when
    nothing changed.
    """
    try:
        count = len(projects)
        total_parts = sum(len(p.get("parts_state", {})) if isinstance(p.get("parts_state", {}), dict) else 0 for p in projects)
        names_hash = sum(len(str(p.get("code", ""))) + len(str(p.get("description", ""))) for p in projects)
        start_count = sum(1 for p in projects if p.get("start"))
        return (count, total_parts, names_hash, start_count)
    except Exception:
        return None

for k, v in [("projects", [_new_project(1)]), ("active_project_idx", 0), ("load_feedback", "")]:
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    # Brand
    st.markdown(
        '<div class="sb-brand">'
        '<div class="sb-brand-name">⚙️ Adwik WMS</div>'
        '<div class="sb-brand-sub">Workflow Analytics System</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Save / Load ───────────────────────────────────────────────────────────
    st.markdown('<div class="sb-section-label">💾 Save & Load</div>', unsafe_allow_html=True)
    # Cache serialized bytes to avoid blocking re-renders when nothing changed
    fp = _proj_fingerprint(st.session_state.projects)
    if st.session_state.get("_save_fp") != fp or st.session_state.get("_save_bytes") is None:
        st.session_state["_save_fp"] = fp
        print("[APP] Serializing projects for save...", flush=True)
        st.session_state["_save_bytes"] = serialize_projects(st.session_state.projects)
        print(f"[APP] Serialized {len(st.session_state.projects)} project(s)", flush=True)
    save_bytes = st.session_state["_save_bytes"]

    st.download_button(
        "⬇️  Save progress (.json)",
        data=save_bytes,
        file_name=f"adwik_wms_{date.today().isoformat()}.json",
        mime="application/json",
        width='stretch',
        help="Downloads your workspace as JSON. Re-upload to restore anytime.",
    )
    uploaded = st.file_uploader(
        "Load", type=["json"], key="load_uploader",
        label_visibility="collapsed",
        help="Select a previously saved .json file",
    )
    if uploaded:
        print(f"[APP] File uploaded: {uploaded.name}, size: {len(uploaded.getvalue())} bytes", flush=True)
        content = uploaded.getvalue()
        file_hash = hash(content) if content else None
        
        # Check if this is a new file (different from previously loaded file)
        if file_hash and file_hash != st.session_state.get("_last_upload_hash"):
            print(f"[APP] New file detected (hash changed or first load)", flush=True)
            loaded, feedback = deserialize_projects(content)
            if loaded:
                print(f"[APP] Deserialization successful: {len(loaded)} project(s) loaded", flush=True)
                print(f"[APP] First project: code={loaded[0].get('code')}, name={loaded[0].get('name')}", flush=True)
                # Store the hash to prevent re-loading on every rerun
                st.session_state["_last_upload_hash"] = file_hash
                st.session_state.projects = loaded
                st.session_state.active_project_idx = 0
                st.session_state.load_feedback = f"✅ {feedback}"
                st.rerun()
            else:
                print(f"[APP] Deserialization failed: {feedback}", flush=True)
                st.session_state.load_feedback = f"❌ {feedback}"
        else:
            print(f"[APP] File not processed (same as last upload or no hash)", flush=True)
    else:
        # Clear upload hash when no file is selected
        st.session_state["_last_upload_hash"] = None

    if st.session_state.load_feedback:
        fn = st.success if st.session_state.load_feedback.startswith("✅") else st.error
        fn(st.session_state.load_feedback, icon=None)

    st.divider()

    # ── Project switcher ──────────────────────────────────────────────────────
    st.markdown('<div class="sb-section-label">📁 Projects</div>', unsafe_allow_html=True)
    proj_labels = [p["code"] for p in st.session_state.projects]
    sel_idx = st.selectbox(
        "Project", range(len(proj_labels)),
        format_func=lambda i: proj_labels[i],
        index=min(st.session_state.active_project_idx, len(proj_labels)-1),
        label_visibility="collapsed",
    )
    st.session_state.active_project_idx = sel_idx
    c1, c2 = st.columns(2)
    if c1.button("➕ New", width='stretch'):
        n = len(st.session_state.projects) + 1
        st.session_state.projects.append(_new_project(n))
        st.session_state.active_project_idx = len(st.session_state.projects) - 1
        st.rerun()
    if c2.button("🗑 Delete", width='stretch',
                 disabled=len(st.session_state.projects) <= 1):
        st.session_state.projects.pop(sel_idx)
        st.session_state.active_project_idx = max(0, sel_idx - 1)
        st.rerun()

    st.divider()

    # ── Project settings ──────────────────────────────────────────────────────
    proj = st.session_state.projects[st.session_state.active_project_idx]
    st.markdown('<div class="sb-section-label">⚙️ Project Settings</div>', unsafe_allow_html=True)
    proj["name"]        = st.text_input("Project Name",  value=proj.get("name", proj["code"]),  key="pn")
    proj["code"]        = st.text_input("Project Code",  value=proj["code"],  key="pc")
    proj["start"]       = st.date_input("Start Date",    value=proj["start"], key="ps")
    proj["description"] = st.text_input("Description",   value=proj.get("description",""), key="pd",
                                         placeholder="e.g. Hydraulic Press Build")

    st.divider()

    # ── Departments ───────────────────────────────────────────────────────────
    st.markdown('<div class="sb-section-label">🏭 Departments</div>', unsafe_allow_html=True)
    depts = proj["departments"]
    to_delete = None

    for i, dept in enumerate(depts):
        done_p  = sum(1 for p in proj["parts_state"].get(dept["name"], []) if p.get("actual_finish"))
        total_p = len(proj["parts_state"].get(dept["name"], []))
        pct     = int(done_p / total_p * 100) if total_p else 0
        col     = "#10B981" if pct == 100 else "#F59E0B" if pct > 0 else "#6B7A99"

        exp_label = f"{dept['name']} ({done_p}/{total_p})"
        with st.expander(exp_label, expanded=False):
            # Mini progress bar inside expander
            st.markdown(
                f'<div style="height:4px;background:#374357;border-radius:99px;overflow:hidden;margin-bottom:10px">'
                f'<div style="width:{pct}%;height:100%;background:{col};border-radius:99px"></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            dept["name"]     = st.text_input("Name",            value=dept["name"],     key=f"dn_{sel_idx}_{i}")
            dept["duration"] = st.number_input("Duration (days)", 1, 365, value=dept["duration"], key=f"dd_{sel_idx}_{i}")
            dept["planned_start"] = st.date_input("Planned Start", value=dept.get("planned_start"), key=f"dps_{sel_idx}_{i}")
            dept["planned_end"]   = st.date_input("Planned End",   value=dept.get("planned_end"),   key=f"dpe_{sel_idx}_{i}")
            dept["order"] = i + 1
            if st.button("Remove this department", key=f"deldept_{sel_idx}_{i}", width='stretch'):
                to_delete = i

    if to_delete is not None:
        removed = depts[to_delete]["name"]
        depts.pop(to_delete)
        proj["parts_state"].pop(removed, None)
        proj["results"].pop(removed, None)
        st.rerun()

    ca, cb = st.columns(2)
    if ca.button("➕ Add", width='stretch'):
        nm = f"Dept {len(depts)+1}"
        depts.append({"name": nm, "duration": 30, "order": len(depts)+1,
                      "planned_start": None, "planned_end": None})
        proj["parts_state"][nm] = [{"name": "Part 1"}]
        st.rerun()
    if cb.button("↩ Reset", width='stretch'):
        proj["departments"] = [d.copy() for d in DEFAULT_DEPARTMENTS]
        proj["parts_state"] = {d["name"]: [{"name": "Part 1"}] for d in DEFAULT_DEPARTMENTS}
        proj["results"] = {}
        st.rerun()

    st.divider()
    run_analysis = st.button("▶  Run Analysis", width='stretch')
    st.markdown(
        '<div style="font-size:0.7rem;color:#6B7A99;text-align:center;margin-top:6px">'
        'Enter all part dates first, then run.</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_all, tab_detail, tab_analytics, tab_report = st.tabs([
    "📁  All Projects",
    "🔧  Enter Data",
    "📊  Analytics",
    "📥  Download Report",
])


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — ALL PROJECTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_all:
    hero(
        "Project Portfolio",
        "All projects at a glance. Select a project in the sidebar to work on it.",
    )

    # Portfolio KPIs (only if any analysis done)
    all_results = [dr for p in st.session_state.projects for dr in p["results"].values()]
    if all_results:
        all_scores  = [dr.avg_marks for dr in all_results]
        total_delay = sum(dr.actual_delay_out for dr in all_results)
        all_done    = sum(1 for dr in all_results for pt in dr.parts if pt.actual_finish)
        all_total   = sum(len(v) for p in st.session_state.projects for v in p["parts_state"].values())
        port_sc     = sum(all_scores)  # Sum all department scores
        kpi_row([
            ("Total Projects",   str(len(st.session_state.projects)), "",               "#1C2536"),
            ("Portfolio Score",  f"{port_sc:.0f}",  "total",                           marks_color(port_sc / len(all_results))),
            ("Total Delay",      f"{total_delay}d", "finish delay accumulated",         "#EF4444" if total_delay else "#10B981"),
            ("Parts Completed",  f"{all_done}/{all_total}", f"{all_done/all_total*100:.0f}% done", "#F59E0B"),
        ])

    # Project cards
    section_label("Projects")
    num_projs = len(st.session_state.projects)
    cols = st.columns(min(num_projs, 3))

    for i, p in enumerate(st.session_state.projects):
        results    = list(p["results"].values())
        done_p     = sum(1 for dr in results for pt in dr.parts if pt.actual_finish)
        total_p    = sum(len(v) for v in p["parts_state"].values())
        pct        = int(done_p / total_p * 100) if total_p else 0
        marks_l    = [dr.avg_marks for dr in results]
        avg_sc     = round(sum(marks_l), 1) if marks_l else None  # Sum all department scores
        delay      = sum(dr.actual_delay_out for dr in results) if results else 0
        sc_color   = marks_color(avg_sc) if avg_sc else "#9CA3AF"
        ring       = completion_ring_html(pct, sc_color, 64)

        status_cls = "green" if results and delay==0 else "red" if delay else "blue"
        status_txt = "✓ On Track" if results and delay==0 else (f"⚠ {delay}d delay" if results else "Not analysed")
        
        display_name = p.get("name") or p["code"]

        with cols[i % 3]:
            # Construct HTML string to avoid extra P tags from Streamlit markdown triple quotes
            proj_card_html = (
                f'<div class="wms-proj-card">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px">'
                f'<div style="flex:1">'
                f'<div style="font-family:Sora,sans-serif;font-size:1.1rem;font-weight:700;color:#1C1C22">{display_name}</div>'
                f'<div style="font-size:0.85rem;color:#4B5563;margin-top:4px">{p.get("description") or "No description"}</div>'
                f'<div style="font-size:0.75rem;color:#9CA3AF;margin-top:6px">📅 {p["start"].strftime("%d %b %Y") if isinstance(p["start"],date) else p["start"]}</div>'
                f'</div>'
                f'<div style="flex-shrink:0">{ring}</div>'
                f'</div>'
                f'<div style="margin-top:16px;display:flex;gap:6px;flex-wrap:wrap;align-items:center">'
                f'<span class="badge badge-{status_cls}">{status_txt}</span>'
                f'<span class="badge badge-slate">{len(p["departments"])} depts</span>'
                f'<span class="badge badge-slate">{total_p} parts</span>' +
                (f"<span class='badge badge-purple'>Score: {avg_sc}</span>" if avg_sc else "") +
                f'</div>'
                f'</div>'
            )
            st.markdown(proj_card_html, unsafe_allow_html=True)

    # Summary table
    section_label("Full Summary")
    rows = []
    for p in st.session_state.projects:
        results = list(p["results"].values())
        marks_l = [dr.avg_marks for dr in results]
        delay   = sum(dr.actual_delay_out for dr in results) if results else 0
        rows.append({
            "Name":            p.get("name") or p["code"],
            "Code":            p["code"],
            "Description":     p.get("description","—"),
            "Start":           p["start"].strftime("%d %b %Y") if isinstance(p["start"],date) else str(p["start"]),
            "Departments":     len(p["departments"]),
            "Total Duration":  f"{sum(d['duration'] for d in p['departments'])}d",
            "Parts":           sum(len(v) for v in p["parts_state"].values()),
            "Total Score":     round(sum(marks_l),1) if marks_l else "—",
            "Total Delay":     f"{delay}d" if results else "—",
            "Status":          "On Track" if results and delay==0 else (f"{delay}d delay" if results else "Not analysed"),
        })
    st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — ENTER DATA
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

    total_parts = sum(len(v) for v in proj["parts_state"].values())
    done_parts  = sum(1 for dr in proj["results"].values() for pt in dr.parts if pt.actual_finish)
    overall_pct = int(done_parts / total_parts * 100) if total_parts else 0

    page_hero(proj.get("name") or proj["code"], proj["start"], len(DEPTS), sum(d["duration"] for d in DEPTS))

    # Step indicator
    dept_names      = [d["name"] for d in DEPTS]
    completed_depts = sum(
        1 for d in DEPTS
        if proj["parts_state"].get(d["name"])
        and all(p.get("actual_finish") for p in proj["parts_state"].get(d["name"], []))
    )
    step_indicator(dept_names, completed_depts)

    # Summary pills
    pill_row([
        ("Progress", f"{overall_pct}%"),
        ("Parts done", f"{done_parts}/{total_parts}"),
        ("Departments", str(len(DEPTS))),
        ("Analysis", "✅ Complete" if proj["results"] else "⏳ Pending — click Run Analysis"),
    ])

    # Tip box if no analysis yet
    if not proj["results"]:
        st.markdown(
            '<div class="wms-info-box">💡 <strong>How to use:</strong> '
            'Fill in the planned and actual dates for each part below, '
            'then click <strong>▶ Run Analysis</strong> in the sidebar to see scores and cascaded delays.</div>',
            unsafe_allow_html=True,
        )

    timeline        = build_department_timeline(proj["start"], DEPTS)
    dept_tabs_ui    = st.tabs([f"{d['name']}" for d in DEPTS])
    dept_part_inputs: dict[str, list[dict]] = {}

    for tab_obj, dept in zip(dept_tabs_ui, DEPTS):
        with tab_obj:
            tl_entry   = next(t for t in timeline if t["name"] == dept["name"])
            saved      = proj["results"].get(dept["name"])
            pred_delay = saved.predecessor_delay if saved else 0

            parts_state = proj["parts_state"][dept["name"]]
            done_p      = sum(1 for p in parts_state if p.get("actual_finish"))
            total_p     = len(parts_state)
            comp_pct    = done_p / total_p * 100 if total_p else 0

            dept_header(dept["name"], dept["duration"], comp_pct, pred_delay)

            # Info pills
            adj_end = tl_entry["original_end"] + timedelta(days=pred_delay)
            ps = dept.get("planned_start")
            pe = dept.get("planned_end")
            pill_row([
                ("Original end",     tl_entry["original_end"].strftime("%d %b %Y")),
                ("Adjusted end",     adj_end.strftime("%d %b %Y")),
                ("Upstream shift",   f"+{pred_delay}d" if pred_delay else "None"),
                ("Dept planned",     f"{ps.strftime('%d %b %Y') if ps else '—'} → {pe.strftime('%d %b %Y') if pe else '—'}"),
                ("Parts",            f"{done_p}/{total_p} done"),
            ])

            section_label(f"Parts — {total_p} total")

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
                f"➕  Add Part",
                key=f"addpart_{st.session_state.active_project_idx}_{dept['name']}",
            ):
                parts_state.append({"name": f"Part {len(parts_state)+1}"})
                st.rerun()

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
        st.toast(f"✅ Analysis complete for {proj['code']}! Remember to Save.", icon="📊")
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 3 — ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
with tab_analytics:
    proj    = st.session_state.projects[st.session_state.active_project_idx]
    results = list(proj["results"].values())

    # Print button using JavaScript
    st.markdown("""
    <div style="margin-bottom: 16px;">
        <button onclick="javascript:window.print();" style="
            background: #1C2536; color: #FFFFFF; border: none; border-radius: 8px;
            padding: 10px 20px; font-weight: 600; cursor: pointer; font-family: 'DM Sans', sans-serif;
            font-size: 0.95rem; transition: all 0.15s; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
            🖨️  Print Analysis
        </button>
        <p style="font-size: 0.75rem; color: #6B7A99; margin-top: 8px;">
            💡 Click button or use Cmd+P (Mac) / Ctrl+P (Windows) for print layout
        </p>
    </div>
    """, unsafe_allow_html=True)

    hero(
        "Analytics",
        "Performance breakdown across all departments and parts.",
        accent=proj.get("name") or proj["code"],
    )

    if not results:
        st.markdown(
            '<div class="wms-info-box">📊 No analysis results yet. '
            'Go to the <strong>Enter Data</strong> tab, fill in the part dates, '
            'then click <strong>▶ Run Analysis</strong> in the sidebar.</div>',
            unsafe_allow_html=True,
        )
    else:
        sorted_results = sorted(results, key=lambda r: r.order)
        all_marks      = [dr.avg_marks for dr in sorted_results]
        overall        = sum(all_marks)  # Sum all department scores
        total_delay    = sum(dr.actual_delay_out for dr in sorted_results)
        done           = sum(1 for dr in sorted_results for p in dr.parts if p.actual_finish)
        total_p        = sum(len(dr.parts) for dr in sorted_results)
        racing         = sum(1 for dr in sorted_results if getattr(dr, "any_racing", False))

        # Top KPIs
        section_label("Project KPIs")
        kpi_row([
            ("Overall Score",       f"{overall:.0f}", "total",                 marks_color(overall / len(all_marks)) if all_marks else "#9CA3AF"),
            ("Total Delay",        f"{total_delay}d", "across all depts",    "#EF4444" if total_delay else "#10B981"),
            ("Parts Complete",      f"{done}/{total_p}", f"{done/total_p*100:.0f}%", "#F59E0B"),
            ("Departments Recovered", str(racing), "late start, on-time finish", "#1C2536"),
        ])

        # Department score cards
        section_label("Department Performance")
        dcols = st.columns(len(sorted_results))
        for col, dr in zip(dcols, sorted_results):
            with col:
                ring = completion_ring_html(dr.completion_pct, marks_color(dr.avg_marks), 60)
                delay_badge = (
                    f'<span class="badge badge-red">{dr.actual_delay_out}d late</span>'
                    if dr.actual_delay_out else
                    '<span class="badge badge-green">On Time</span>'
                )
                racing_badge = (
                    '<span class="badge badge-amber">⚡ Recovered</span>'
                    if getattr(dr, "any_racing", False) else ""
                )
                st.markdown(
                    f"""<div class="wms-proj-card" style="text-align:center">
                      <div style="display:flex;justify-content:center;margin-bottom:10px">{ring}</div>
                      <div style="font-family:'Sora',sans-serif;font-weight:700;font-size:0.92rem;color:#1C1C1E">{dr.name}</div>
                      <div style="font-family:'Sora',sans-serif;font-size:1.8rem;font-weight:800;color:{marks_color(dr.avg_marks)};line-height:1.2;margin:6px 0">
                        {dr.avg_marks:.0f}<span style="font-size:0.8rem;color:#9CA3AF;font-family:'DM Sans',sans-serif"> pts</span>
                      </div>
                      <div style="display:flex;justify-content:center;gap:6px;flex-wrap:wrap">{delay_badge}{racing_badge}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

        # Charts
        section_label("Timeline — Baseline vs Actual")
        st.plotly_chart(gantt_chart(sorted_results, proj["start"]), use_container_width=True)

        section_label("Efficiency Scores")
        st.plotly_chart(efficiency_bar_chart(sorted_results), use_container_width=True)

        section_label("Performance Gauges")
        gcols = st.columns(len(sorted_results))
        for col, dr in zip(gcols, sorted_results):
            with col:
                st.plotly_chart(marks_gauge(dr.name, dr.avg_marks), use_container_width=True)

        # Planned vs Actual
        section_label("Planned vs Actual Dates")
        pva = []
        for dr in sorted_results:
            finished   = [p for p in dr.parts if p.actual_finish]
            actual_end = max(p.actual_finish for p in finished).strftime("%d %b %Y") if finished else "Pending"
            pva.append({
                "Department":     dr.name,
                "Planned Start":  dr.planned_start.strftime("%d %b %Y") if dr.planned_start else "—",
                "Planned End":    dr.planned_end.strftime("%d %b %Y")   if dr.planned_end   else "—",
                "Actual End":     actual_end,
                "Start Delay":    f"{getattr(dr,'max_start_delay',0)}d" if getattr(dr,'max_start_delay',0) else "None",
                "Finish Delay":   f"{dr.actual_delay_out}d" if dr.actual_delay_out else "✓ None",
                "Recovered":      "⚡ Yes" if getattr(dr,"any_racing",False) else "—",
                "Score":          round(dr.avg_marks, 1),
            })
        st.dataframe(pd.DataFrame(pva), width='stretch', hide_index=True)

        with st.expander("ℹ️  How cascade delay works"):
            st.markdown("""
| Scenario | Cascade to next dept |
|---|---|
| Started on time, finished on time | ✅ **0 days** |
| **Started late, finished on time** | ✅ **0 days — recovered, no cascade** |
| Started on time, finished late | ❌ **N days** |
| Started late, finished late | ❌ **finish overshoot only cascades** |

Only **finish delay** propagates. A department that starts late but delivers on time
has **zero impact** on the next department's deadline.
""")

        # Delay log
        delayed = [(dr.name, p) for dr in sorted_results
                   for p in dr.parts if p.actual_finish and p.delay_days > 0]
        if delayed:
            section_label("Delay Log")
            
            # Show cascade delay visual
            with st.expander("📊 How delays cascade through departments", expanded=True):
                st.markdown("""
### Delay Cascade Timeline
Delays propagate sequentially through departments:
- 🏭 **Design** completes **X days late** → shifts Purchase start by X days
- 🏭 **Purchase** completes **Y days late** → shifts Manufacturing start by (X+Y) days
- 🏭 **Manufacturing** → **Assembly** → **Testing**

**Mark Penalty:** Each day of delay reduces marks by **0.5 per department**.
If Design is 2 days late: All downstream departments have adjusted deadlines pushed by 2 days.
""")
                
                # Visual cascade table
                cascade_data = []
                running_delay = 0
                for dr in sorted_results:
                    cascade_data.append({
                        "Department": dr.name,
                        "Dept Delay (days)": dr.actual_delay_out if dr.actual_delay_out > 0 else 0,
                        "Accumulated Delay": running_delay if running_delay > 0 else 0,
                        "Adjusted Deadline": (dr.planned_end + timedelta(days=running_delay)).strftime("%d %b %Y") if dr.planned_end else "Not Set",
                        "Marks": int(dr.avg_marks),
                    })
                    running_delay += dr.actual_delay_out
                
                st.dataframe(pd.DataFrame(cascade_data), width='stretch', hide_index=True)
            
            d_rows = []
            for dname, p in delayed:
                d_rows.append({
                    "Department": dname,
                    "Part":       p.name,
                    "MC":         p.mc,
                    "PIC":        getattr(p, "pic", "—"),
                    "Delay Days": p.delay_days,
                    "Category":   p.delay_category or "—",
                    "Type":       "External" if p.is_external else "Internal",
                    "Penalty":    "None" if p.is_external else f"−{p.delay_days * 0.5} marks",
                    "Score":      round(p.marks, 1),
                    "Reason":     (p.delay_reason or "—")[:80],
                })
            st.dataframe(pd.DataFrame(d_rows), width='stretch', hide_index=True)
        else:
            st.markdown(
                '<div class="wms-success-box">🎉 No delays recorded for this project. All departments on track!</div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 4 — REPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab_report:
    hero(
        "Download Report",
        "Export a professional Excel workbook with all project data, scores and delay logs.",
    )

    c1, c2 = st.columns([1, 2])
    with c1:
        scope = st.radio(
            "Report scope",
            ["Active project only", "All projects"],
            label_visibility="collapsed",
        )
    proj_list = ([st.session_state.projects[st.session_state.active_project_idx]]
                 if scope == "Active project only"
                 else st.session_state.projects)
    analysed = [p for p in proj_list if p["results"]]

    if not analysed:
        st.markdown(
            '<div class="wms-info-box">Run analysis on at least one project first, '
            'then come back here to download.</div>',
            unsafe_allow_html=True,
        )
    else:
        # Report contents
        st.markdown(
            """<div class="wms-report-box">
              <div style="font-family:'Sora',sans-serif;font-weight:700;font-size:0.95rem;color:#1C1C1E;margin-bottom:12px">
                📋 What's inside the Excel file
              </div>
              <div class="wms-report-sheet">
                <div class="wms-report-icon">📊</div>
                <div>
                  <div style="font-weight:600;color:#1C1C1E;font-size:0.85rem">Sheet 1 — Projects Overview</div>
                  <div style="color:#6B7280;font-size:0.78rem;margin-top:2px">All projects with KPIs, scores and an efficiency bar chart</div>
                </div>
              </div>
              <div class="wms-report-sheet">
                <div class="wms-report-icon">📋</div>
                <div>
                  <div style="font-weight:600;color:#1C1C1E;font-size:0.85rem">Sheet 2+ — Part Detail (per project)</div>
                  <div style="color:#6B7280;font-size:0.78rem;margin-top:2px">Every part with planned dates, actual dates, delays, and marks</div>
                </div>
              </div>
              <div class="wms-report-sheet">
                <div class="wms-report-icon">⚠️</div>
                <div>
                  <div style="font-weight:600;color:#1C1C1E;font-size:0.85rem">Sheet 3+ — Delay Log (per project)</div>
                  <div style="color:#6B7280;font-size:0.78rem;margin-top:2px">Only delayed parts — category, internal/external, penalty, root cause</div>
                </div>
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
            width='stretch',
        )
        st.caption(f"Covers {len(analysed)} project(s) · Generated {date.today().strftime('%d %b %Y')}")

        section_label("Data Preview")
        prev_rows = []
        for p in analysed:
            for dr in sorted(p["results"].values(), key=lambda r: r.order):
                for pt in dr.parts:
                    prev_rows.append({
                        "Project":       p["code"],
                        "Department":    dr.name,
                        "Part":          pt.name,
                        "MC":            pt.mc,
                        "Description":   pt.description,
                        "PIC":           getattr(pt, "pic", "—"),
                        "Planned End":   pt.planned_end.strftime("%d %b %Y") if pt.planned_end else "—",
                        "Actual Start":  pt.actual_start.strftime("%d %b %Y") if getattr(pt,"actual_start",None) else "—",
                        "Original End":  pt.original_deadline.strftime("%d %b %Y"),
                        "Actual Finish": pt.actual_finish.strftime("%d %b %Y") if pt.actual_finish else "⏳ Pending",
                        "Delay (days)":  pt.delay_days if pt.actual_finish else 0,
                        "Marks":         round(pt.marks,1) if pt.actual_finish else 0,
                    })
        st.dataframe(pd.DataFrame(prev_rows), width='stretch', hide_index=True)
