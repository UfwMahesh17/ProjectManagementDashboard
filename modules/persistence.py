"""
persistence.py — Save/load all project state as a portable JSON file.

Strategy: serialize everything to plain JSON (dates as ISO strings,
DepartmentResult objects reconstructed from their raw inputs).
The file is downloaded by the user and re-uploaded to restore state.
"""

from __future__ import annotations
import json
import io
from datetime import date, datetime
from typing import Any

from modules.core import DEFAULT_DEPARTMENTS

# ── Serialization helpers ─────────────────────────────────────────────────────

def _to_json_safe(obj: Any) -> Any:
    """Recursively convert date objects to ISO strings for JSON."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json_safe(i) for i in obj]
    return obj


def _from_json_safe(obj: Any) -> Any:
    """
    Recursively restore ISO date strings back to date objects.
    Only converts strings that look like dates (YYYY-MM-DD).
    """
    if isinstance(obj, str):
        try:
            # Flexible date parsing
            if "-" in obj and len(obj) >= 10:
                # Try full isoformat first
                return datetime.fromisoformat(obj).date() if len(obj) > 10 else date.fromisoformat(obj[:10])
        except Exception:
            pass
        return obj
    if isinstance(obj, dict):
        return {k: _from_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_from_json_safe(i) for i in obj]
    return obj


# ── Public API ────────────────────────────────────────────────────────────────

def serialize_projects(projects: list[dict]) -> bytes:
    """
    Convert the full projects list (from session_state) into
    a downloadable JSON bytes payload.

    Only raw input data is saved — DepartmentResult objects (analysis
    results) are NOT saved because they can be perfectly reconstructed
    by clicking Run Analysis. This keeps the file small and avoids
    serializing dataclass internals.
    """
    saveable = []
    for p in projects:
        saveable.append({
            "code":        p.get("code", ""),
            "name":        p.get("name", ""),
            "start":       p.get("start"),
            "description": p.get("description", ""),
            "departments": p.get("departments", []),
            "parts_state": p.get("parts_state", {}),
            # results intentionally omitted — user clicks Run Analysis to regenerate
        })

    payload = {
        "version":   "1.0",
        "saved_at":  datetime.now().isoformat(),
        "projects":  _to_json_safe(saveable),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def deserialize_projects(raw_bytes: bytes) -> tuple[list[dict], str]:
    """
    Parse a previously saved JSON file back into a projects list.
    Returns (projects, error_message). error_message is "" on success.
    """
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return [], f"Invalid file format: {e}"

    if "projects" not in payload:
        return [], "File is missing the 'projects' key. Is this a valid Adwik WMS save file?"

    try:
        projects = _from_json_safe(payload["projects"])
    except Exception as e:
        return [], f"Failed to parse project data: {e}"

    # Validate & backfill any missing keys (forward-compatibility)
    clean = []
    for p in projects:
        # Ensure we don't crash if p is not a dict
        if not isinstance(p, dict):
            continue
            
        # Ensure dates are actually date objects, backfill with current if missing
        project_start = p.get("start")
        if isinstance(project_start, str):
            try: project_start = date.fromisoformat(project_start[:10])
            except: project_start = date.today()
        elif not isinstance(project_start, date):
            project_start = date.today()

        # Backfill empty departments with defaults
        departments = p.get("departments", [])
        if not departments or not isinstance(departments, list):
            departments = [d.copy() for d in DEFAULT_DEPARTMENTS]
        else:
            # Ensure each department has required fields
            for i, dept in enumerate(departments):
                if not isinstance(dept, dict):
                    continue
                if "order" not in dept:
                    dept["order"] = i + 1
                if "duration" not in dept:
                    dept["duration"] = 30
                if "planned_start" not in dept:
                    dept["planned_start"] = None
                if "planned_end" not in dept:
                    dept["planned_end"] = None
        
        # Reconstruct parts_state with proper structure
        parts_state = p.get("parts_state", {})
        if not parts_state or not isinstance(parts_state, dict):
            # Create default parts for each department
            parts_state = {d["name"]: [{"name": "Part 1"}] for d in departments}
        else:
            # Ensure all departments have corresponding parts_state entries
            for dept in departments:
                dept_name = dept.get("name", "")
                if dept_name not in parts_state:
                    parts_state[dept_name] = [{"name": "Part 1"}]
                else:
                    # Ensure each part has the expected fields
                    for j, part in enumerate(parts_state[dept_name]):
                        if not isinstance(part, dict):
                            parts_state[dept_name][j] = {"name": f"Part {j+1}"}
                        else:
                            if "name" not in part:
                                part["name"] = f"Part {j+1}"
                            # Ensure date fields are present (can be None)
                            for date_field in ["actual_start", "actual_finish", "planned_start", "planned_end"]:
                                if date_field not in part:
                                    part[date_field] = None

        clean.append({
            "code":        p.get("code", "PRJ-001"),
            "name":        p.get("name", p.get("code", "New Project")),
            "start":       project_start,
            "description": p.get("description", ""),
            "departments": departments,
            "parts_state": parts_state,
            "results":     {},   # always start fresh — user re-runs analysis
        })

    saved_at = payload.get("saved_at", "unknown time")
    return clean, f"Loaded {len(clean)} project(s) — saved {saved_at[:19].replace('T', ' at ')}"
