"""
core.py — Business logic: deadline shifting, mark deduction, scoring.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

# ── Department catalogue ──────────────────────────────────────────────────────
DEPARTMENTS: list[dict] = [
    {"name": "Design",       "duration": 30,  "order": 1},
    {"name": "Purchase",     "duration": 45,  "order": 2},
    {"name": "Manufacturing","duration": 60,  "order": 3},
    {"name": "Assembly",     "duration": 10,  "order": 4},
    {"name": "Testing",      "duration": 7,   "order": 5},
]

DELAY_CATEGORIES = [
    "Material Shortage",
    "Labor Unavailability",
    "Design Revision",
    "Client Approval Lag",
    "Client Change Request",
    "Machine Breakdown",
    "Supply Chain Disruption",
    "Other",
]

EXTERNAL_CATEGORIES = {"Client Approval Lag", "Client Change Request"}

MARKS_PER_DAY_DEDUCTION = 5
BASE_MARKS = 100


# ── Data models ───────────────────────────────────────────────────────────────
@dataclass
class PartEntry:
    name: str
    original_deadline: date          # absolute date
    actual_finish: Optional[date]
    predecessor_delay_days: int      # days shifted from upstream dept
    delay_category: Optional[str] = None
    delay_reason: Optional[str] = None

    # computed (set by calculate_marks)
    adjusted_deadline: date = field(init=False)
    delay_days: int = field(init=False, default=0)
    marks: float = field(init=False, default=float(BASE_MARKS))
    is_external: bool = field(init=False, default=False)

    def __post_init__(self):
        self.adjusted_deadline = self.original_deadline + timedelta(
            days=self.predecessor_delay_days
        )
        self._calculate()

    def _calculate(self):
        if self.actual_finish is None:
            self.delay_days = 0
            self.marks = BASE_MARKS
            self.is_external = False
            return

        self.is_external = self.delay_category in EXTERNAL_CATEGORIES

        if self.actual_finish > self.adjusted_deadline:
            self.delay_days = (self.actual_finish - self.adjusted_deadline).days
            if self.is_external:
                self.marks = BASE_MARKS  # no penalty
            else:
                deduction = self.delay_days * MARKS_PER_DAY_DEDUCTION
                self.marks = max(0.0, BASE_MARKS - deduction)
        else:
            self.delay_days = 0
            self.marks = BASE_MARKS


@dataclass
class DepartmentResult:
    name: str
    duration: int
    order: int
    project_start: date
    predecessor_delay: int           # total upstream delay pushed into this dept
    parts: list[PartEntry] = field(default_factory=list)

    @property
    def original_start(self) -> date:
        return self.project_start

    @property
    def original_end(self) -> date:
        return self.project_start + timedelta(days=self.duration - 1)

    @property
    def shifted_start(self) -> date:
        return self.project_start + timedelta(days=self.predecessor_delay)

    @property
    def shifted_end(self) -> date:
        return self.shifted_start + timedelta(days=self.duration - 1)

    @property
    def avg_marks(self) -> float:
        if not self.parts:
            return BASE_MARKS
        finished = [p for p in self.parts if p.actual_finish is not None]
        if not finished:
            return BASE_MARKS
        return sum(p.marks for p in finished) / len(finished)

    @property
    def actual_delay_out(self) -> int:
        """Days this dept delivers late beyond its shifted end — cascades forward."""
        finished = [p for p in self.parts if p.actual_finish is not None]
        if not finished:
            return 0
        latest_finish = max(p.actual_finish for p in finished)
        overshoot = (latest_finish - self.shifted_end).days
        return max(0, overshoot)

    @property
    def completion_pct(self) -> float:
        finished = [p for p in self.parts if p.actual_finish is not None]
        if not self.parts:
            return 0.0
        return (len(finished) / len(self.parts)) * 100


# ── Core calculation functions ────────────────────────────────────────────────

def calculate_shifted_deadline(
    original_deadline: date,
    predecessor_delay_days: int,
) -> date:
    """
    Shift the department's deadline forward by the accumulated upstream delay
    so it always receives its full contracted duration.
    """
    return original_deadline + timedelta(days=predecessor_delay_days)


def calculate_marks(
    actual_finish: Optional[date],
    adjusted_deadline: date,
    delay_category: Optional[str],
) -> tuple[float, int, bool]:
    """
    Returns (marks, delay_days, is_external).

    Rules:
    - On time  → 100 marks, 0 delay days
    - External → 100 marks, N delay days logged
    - Internal → 100 - (delay_days × 5) marks, min 0
    """
    if actual_finish is None:
        return float(BASE_MARKS), 0, False

    is_external = delay_category in EXTERNAL_CATEGORIES
    delay_days = max(0, (actual_finish - adjusted_deadline).days)

    if delay_days == 0:
        return float(BASE_MARKS), 0, is_external

    if is_external:
        return float(BASE_MARKS), delay_days, True

    marks = max(0.0, BASE_MARKS - delay_days * MARKS_PER_DAY_DEDUCTION)
    return marks, delay_days, False


def build_department_timeline(
    project_start: date,
    departments: list[dict] = DEPARTMENTS,
) -> list[dict]:
    """
    Returns a list of dicts with original start/end for each dept.
    Used to seed the Gantt baseline.
    """
    timeline = []
    cursor = project_start
    for dept in departments:
        timeline.append(
            {
                "name": dept["name"],
                "order": dept["order"],
                "duration": dept["duration"],
                "original_start": cursor,
                "original_end": cursor + timedelta(days=dept["duration"] - 1),
            }
        )
        cursor += timedelta(days=dept["duration"])
    return timeline


def propagate_delays(
    dept_results: list[DepartmentResult],
) -> list[DepartmentResult]:
    """
    Walk departments in order. Each dept's predecessor_delay = sum of all
    actual delays from prior departments (cascading shift).
    Returns the same list mutated with updated predecessor_delay values.
    """
    cumulative_delay = 0
    for dr in sorted(dept_results, key=lambda d: d.order):
        dr.predecessor_delay = cumulative_delay
        # re-compute parts with new predecessor_delay
        for part in dr.parts:
            part.predecessor_delay_days = cumulative_delay
            part.adjusted_deadline = calculate_shifted_deadline(
                part.original_deadline, cumulative_delay
            )
            part._calculate()
        cumulative_delay += dr.actual_delay_out
    return dept_results
