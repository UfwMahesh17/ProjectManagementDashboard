"""
core.py — Business logic: deadline shifting, mark deduction, scoring.

Delay cascade rule:
  Only FINISH delay propagates forward.
  If a dept starts late but finishes on time → zero cascade to next dept.
  If a dept starts late and finishes late   → finish overshoot cascades.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional
from typing import List

# ── Department catalogue (defaults) ──────────────────────────────────────────
DEFAULT_DEPARTMENTS: list[dict] = [
    {"name": "Design",        "duration": 30, "order": 1},
    {"name": "Purchase",      "duration": 45, "order": 2},
    {"name": "Manufacturing", "duration": 60, "order": 3},
    {"name": "Assembly",      "duration": 10, "order": 4},
    {"name": "Testing",       "duration": 7,  "order": 5},
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

MARKS_PER_DAY_DEDUCTION = 0.5
BASE_MARKS = 100


# ── PartEntry ─────────────────────────────────────────────────────────────────
@dataclass
class PartEntry:
    name: str
    original_deadline: date          # absolute planned end date for this dept
    actual_finish: Optional[date]    # None = still in progress
    predecessor_delay_days: int = 0  # FORCE to 0 to disable cascading
    planned_start: Optional[date] = None   # dept planned start
    planned_end:   Optional[date] = None   # dept planned end
    actual_start:  Optional[date] = None   # NEW: when did work actually begin?
    pic:           str = ""                # NEW: Person In Charge
    mc:            str = ""                # Machine/Material Code
    description:   str = ""                # Part description
    delay_category: Optional[str] = None
    delay_reason:   Optional[str] = None
    # Specific delay events (e.g., Rework, Missed out drawing)
    delay_events: List["DelayEvent"] = field(default_factory=list)

    # ── computed fields (never passed in) ────────────────────────────────────
    adjusted_deadline: date  = field(init=False)

    # Start-side metrics
    start_delay_days: int    = field(init=False, default=0)
    # "buffer remaining" = duration - days actually spent working
    # positive → finished with time to spare; negative → overran
    buffer_days: int         = field(init=False, default=0)
    # True when dept started late but is still within its window
    racing_to_finish: bool   = field(init=False, default=False)

    # Finish-side metrics
    delay_days: int          = field(init=False, default=0)
    marks: float             = field(init=False, default=float(BASE_MARKS))
    is_external: bool        = field(init=False, default=False)
    # Sum of explicit delay events attached to this part (days)
    delay_events_total: int  = field(init=False, default=0)

    def __post_init__(self):
        self.adjusted_deadline = self.original_deadline + timedelta(
            days=self.predecessor_delay_days
        )
        self._calculate()

    # ── adjusted start = planned start pushed by the same upstream shift ──────
    @property
    def adjusted_start(self) -> Optional[date]:
        if self.planned_start is None:
            return None
        return self.planned_start + timedelta(days=self.predecessor_delay_days)

    def _calculate(self):
        # FORCE cascading to 0 for calculation
        self.predecessor_delay_days = 0 
        self.adjusted_deadline = self.original_deadline
        
        # ── Start-delay analysis ──────────────────────────────────────────────
        adj_start = self.planned_start  # Use planned start directly
        if self.actual_start and adj_start:
            self.start_delay_days = max(0, (self.actual_start - adj_start).days)
        else:
            self.start_delay_days = 0

        # ── Finish analysis ───────────────────────────────────────────────────
        if self.actual_finish is None:
            self.delay_days      = 0
            self.marks           = BASE_MARKS
            self.is_external     = False
            self.buffer_days     = 0

            # Racing-to-finish: started late, not finished yet
            if self.actual_start and adj_start and self.actual_start > adj_start:
                self.racing_to_finish = True
            return

        self.is_external = self.delay_category in EXTERNAL_CATEGORIES

        # Days actually spent working (actual_start → actual_finish)
        if self.actual_start:
            days_worked = (self.actual_finish - self.actual_start).days + 1
        else:
            days_worked = None

        # SCREENSHOT FIX: DELAY IS CALCULATED B/W PLANNED END AND ACTUAL FINISH
        # Each part now calculates its own specific delay independently.
        part_deadline = self.planned_end if self.planned_end else self.original_deadline
        
        if self.actual_finish > part_deadline:
            self.delay_days = max(0, (self.actual_finish - part_deadline).days)
            if self.is_external:
                self.marks = BASE_MARKS          # no penalty for client delays
            else:
                self.marks = max(0.0, BASE_MARKS - self.delay_days * MARKS_PER_DAY_DEDUCTION)
        else:
            self.delay_days = 0
            self.marks      = BASE_MARKS

        # Buffer: how many days ahead/behind the adjusted deadline it finished
        # positive = finished early, negative = finished late
        self.buffer_days = (part_deadline - self.actual_finish).days

        # Racing-to-finish: started late but still managed to finish on time
        adj_start = self.adjusted_start
        if (self.actual_start and adj_start
                and self.actual_start > adj_start
                and self.delay_days == 0):
            self.racing_to_finish = True
        else:
            self.racing_to_finish = False

        # Calculate explicit delay events total (days)
        total_ev = 0
        for ev in getattr(self, "delay_events", []):
            if getattr(ev, "start", None) and getattr(ev, "end", None):
                d = max(0, (ev.end - ev.start).days + 1)
                total_ev += d
        self.delay_events_total = total_ev


@dataclass
class DelayEvent:
    """Represents a named delay interval for a part (rework, missed drawing, etc.)."""
    type: str
    pic: str
    start: Optional[date]
    end:   Optional[date]
    notes: Optional[str] = None

    @property
    def days(self) -> int:
        if not self.start or not self.end:
            return 0
        return max(0, (self.end - self.start).days + 1)

# ── DepartmentResult ──────────────────────────────────────────────────────────
@dataclass
class DepartmentResult:
    name: str
    duration: int
    order: int
    project_start: date
    predecessor_delay: int
    planned_start: Optional[date] = None
    planned_end:   Optional[date] = None
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
        """Total marks for all finished parts (sum, not average)."""
        finished = [p for p in self.parts if p.actual_finish is not None]
        if not finished:
            return BASE_MARKS
        return sum(p.marks for p in finished)

    @property
    def actual_delay_out(self) -> int:
        """
        The ONLY number that cascades to the next department.
        REFINED: Based on the max delay of any individual part'S PLANNED END.
        """
        finished = [p for p in self.parts if p.actual_finish is not None]
        if not finished:
            return 0
            
        # CALCULATE MAX DELAY OFFSET
        max_delay = 0
        for p in finished:
            # Use the same effective deadline logic as PartEntry and UI
            # Fix: Use original_deadline as the fallback for part-level calculation
            deadline = p.planned_end if p.planned_end else p.original_deadline
            delay = (p.actual_finish - deadline).days
            if delay > max_delay:
                max_delay = delay
        return max_delay

    @property
    def max_start_delay(self) -> int:
        """Largest start delay across all parts — informational only."""
        return max((p.start_delay_days for p in self.parts), default=0)

    @property
    def any_racing(self) -> bool:
        """True if any part started late but finished on time."""
        return any(p.racing_to_finish for p in self.parts)

    @property
    def completion_pct(self) -> float:
        finished = [p for p in self.parts if p.actual_finish is not None]
        if not self.parts:
            return 0.0
        return (len(finished) / len(self.parts)) * 100


# ── Pure functions ────────────────────────────────────────────────────────────

def calculate_shifted_deadline(original_deadline: date, predecessor_delay_days: int) -> date:
    """Push a deadline forward by the accumulated upstream finish-delay."""
    return original_deadline + timedelta(days=predecessor_delay_days)


def calculate_marks(
    actual_finish: Optional[date],
    adjusted_deadline: date,
    delay_category: Optional[str],
) -> tuple[float, int, bool]:
    """
    Returns (marks, finish_delay_days, is_external).
    Start delay does NOT affect marks — only finish delay does.
    """
    if actual_finish is None:
        return float(BASE_MARKS), 0, False

    is_external = delay_category in EXTERNAL_CATEGORIES
    delay_days  = max(0, (actual_finish - adjusted_deadline).days)

    if delay_days == 0:
        return float(BASE_MARKS), 0, is_external
    if is_external:
        return float(BASE_MARKS), delay_days, True

    marks = max(0.0, BASE_MARKS - delay_days * MARKS_PER_DAY_DEDUCTION)
    return marks, delay_days, False


def build_department_timeline(
    project_start: date,
    departments: list[dict] = DEFAULT_DEPARTMENTS,
) -> list[dict]:
    """
    Fixed timeline where departments have fixed end dates 
    (no sequential cursor shifting).
    """
    timeline = []
    for dept in departments:
        # Each department now has its own fixed end date based on duration from project start
        # unless you want them to be manually staggered in build_department_timeline.
        # But to avoid cascading, we treat each one as independent.
        timeline.append({
            "name":           dept["name"],
            "order":          dept["order"],
            "duration":       dept["duration"],
            "original_start": project_start,
            "original_end":   project_start + timedelta(days=dept["duration"] - 1),
            "planned_start":  dept.get("planned_start"),
            "planned_end":    dept.get("planned_end"),
        })
    return timeline


def propagate_delays(dept_results: list[DepartmentResult]) -> list[DepartmentResult]:
    """
    Walk departments in order.
    Update: Deadline cascading is disabled. Each department uses its individual dates.
    """
    for dr in sorted(dept_results, key=lambda d: d.order):
        dr.predecessor_delay = 0
        for part in dr.parts:
            part.predecessor_delay_days = 0
            part.adjusted_deadline = part.original_deadline
            part._calculate()
    return dept_results
