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
            if len(obj) == 10 and obj[4] == '-' and obj[7] == '-':
                return date.fromisoformat(obj)
        except ValueError:
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
        clean.append({
            "code":        p.get("code", "PRJ-001"),
            "start":       p.get("start", date.today()),
            "description": p.get("description", ""),
            "departments": p.get("departments", []),
            "parts_state": p.get("parts_state", {}),
            "results":     {},   # always start fresh — user re-runs analysis
        })

    saved_at = payload.get("saved_at", "unknown time")
    return clean, f"Loaded {len(clean)} project(s) — saved {saved_at[:19].replace('T', ' at ')}"
