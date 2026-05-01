Workflow Analytics System

> A Streamlit-based project management dashboard for tracking multi-department manufacturing workflows with dynamic deadline shifting, weighted performance scoring, and professional Excel reporting.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Live Demo](#live-demo)
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [How to Use](#how-to-use)
- [Business Logic](#business-logic)
- [Configuration](#configuration)
- [Excel Report](#excel-report)
- [Tech Stack](#tech-stack)
- [Troubleshooting](#troubleshooting)

---

## Overview

Adwik Intellimech WMS tracks complex machinery projects (e.g. **A24017**) through sequential manufacturing departments. Each department contains up to 10 parts. The system automatically cascades deadline shifts when upstream departments finish late, scores each department's performance out of 100, and distinguishes between internal delays (penalised) and client-caused delays (logged only).

---

## Live Demo

Deployed on Streamlit Cloud:
**[→ Open App ( https://projectmanagementdashbord.streamlit.app/ ) ]**

> Replace the link above with your actual Streamlit Cloud URL after deployment.

---

## Features

| Feature | Description |
|---|---|
| 🏭 **Dynamic Departments** | Add, remove, rename, or change duration of any department from the sidebar — no code changes needed |
| 📅 **Baseline Shifting** | If Dept A finishes late, Dept B's deadline automatically shifts so it always gets its full contracted duration |
| 🎯 **Weighted Scoring** | Each department scored out of 100 — internal delays cost 5 marks/day, client delays are logged with zero penalty |
| 📦 **Multi-Part Tracking** | 1–10 parts per department; departmental score = average of all part scores |
| ⚠️ **Forced Delay Logging** | Late parts require a delay category and written explanation before analysis can run |
| 📊 **Gantt Chart** | Side-by-side view of Original Baseline vs Shifted timeline with actual finish markers |
| 📈 **Efficiency Charts** | Bar chart and per-department gauge widgets showing performance at a glance |
| 📥 **Excel Export** | 3-sheet professional report: Summary Dashboard, Part Detail, and Delay Log |

---

## Project Structure

```
projectmanagementdashboard/
│
├── app.py                  # Main Streamlit app — UI layout and flow
├── requirements.txt        # Python dependencies
├── README.md               # This file
│
└── modules/
    ├── __init__.py         # Package marker
    ├── core.py             # Business logic: deadline shifting, mark calculation
    ├── ui_helpers.py       # Reusable Streamlit widgets and CSS styling
    ├── visualizations.py   # Plotly charts: Gantt, bar chart, gauges
    └── reporting.py        # Excel report generation with openpyxl
```

### What Each File Does

**`app.py`** — Orchestrates the entire UI. Reads department config from session state, builds the tab layout, collects part inputs, triggers analysis, and renders results. Has zero business logic of its own.

**`modules/core.py`** — Pure Python, zero Streamlit imports. Contains the `PartEntry` and `DepartmentResult` dataclasses, the `calculate_shifted_deadline()` function, the `calculate_marks()` function, and the `propagate_delays()` cascade engine.

**`modules/ui_helpers.py`** — Dark-theme CSS injection, `metric_card()` components, department header banners, and the `render_part_inputs()` function that dynamically renders part rows and forces delay categorisation.

**`modules/visualizations.py`** — All Plotly figures. `gantt_chart()` renders the dual-baseline timeline. `efficiency_bar_chart()` shows departmental scores. `marks_gauge()` renders individual mini gauges.

**`modules/reporting.py`** — Builds the downloadable `.xlsx` file with formatted headers, colour-coded cells, and an embedded bar chart on the Summary sheet.

---

## Installation

### Prerequisites

- Python 3.9 or higher
- pip

### Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-username/projectmanagementdashboard.git
cd projectmanagementdashboard

# 2. (Optional) Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501` in your browser.

### Streamlit Cloud Deployment

1. Push the repository to GitHub (ensure `modules/` folder with all 5 files is committed)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → select your repo → set main file to `app.py`
4. Click **Deploy**

> ⚠️ Make sure your GitHub repo contains the `modules/` folder. The most common deployment error (`ModuleNotFoundError: No module named 'modules'`) is caused by the folder missing from the repo.

---

## How to Use

### Step 1 — Configure Your Project

In the **left sidebar**:
- Enter your **Project Code** (e.g. `A24017`)
- Set the **Project Start Date**

### Step 2 — Set Up Departments

Still in the sidebar under **🏭 Departments**:
- Click any department name to expand it
- Edit the **Name**, **Duration (days)**, and **number of Parts**
- Click **➕ Add Department** to add a new stage
- Click **🗑 Remove** inside a department to delete it
- Click **↩ Reset to Defaults** to restore the original 5-department setup

### Step 3 — Enter Part Data

Each department has its own tab in the main area. For every part:
- Edit the **Part Name**
- Select the **Actual Finish Date** (leave blank if still in progress)

If a part's finish date is **past its adjusted deadline**, the system will display:
- A warning showing how many days late it is
- A required **Delay Category** dropdown
- A required **Explanation** text field
- A badge showing whether the delay is **Internal 🔴** (penalised) or **External 🔵** (no penalty)

### Step 4 — Run Analysis

Click **▶ Run Analysis** in the sidebar. The system will:
1. Build all `PartEntry` objects from your inputs
2. Run `propagate_delays()` to cascade deadline shifts across departments
3. Calculate marks for every part
4. Save results to session state

### Step 5 — View Analytics

Go to the **📊 Analytics** tab to see:
- KPI cards for each department (marks out of 100)
- Overall project score, total cascaded delay, parts completion ratio
- Gantt chart (Original Baseline vs Shifted Path)
- Efficiency bar chart
- Per-department gauge widgets
- Delay summary table (only late parts)

### Step 6 — Download Report

Go to the **📥 Report** tab and click **⬇️ Download Full Excel Report** to get a formatted `.xlsx` file with three sheets.

---

## Business Logic

### Deadline Shifting Formula

When a department finishes late, every downstream department's deadline shifts forward by the accumulated upstream delay:

```
Adjusted Deadline = Original Deadline + Total Predecessor Delay Days
```

This guarantees each department always receives its **full contracted duration** before any penalty applies.

**Example:**

| Department | Duration | Original End | Upstream Delay | Adjusted End |
|---|---|---|---|---|
| Design | 30 days | Day 30 | 0 days | Day 30 |
| Purchase | 45 days | Day 75 | +8 days (Design ran late) | Day 83 |
| Manufacturing | 60 days | Day 135 | +8 days | Day 143 |

### Mark Deduction Rules

| Situation | Marks |
|---|---|
| Finished on or before adjusted deadline | **100** |
| Finished late — client caused it (Approval Lag / Change Request) | **100** (logged as External, no penalty) |
| Finished late — internal cause | **100 − (days late × 5)**, minimum **0** |

**Examples:**
- 2 days late internally → 100 − 10 = **90 marks**
- 7 days late internally → 100 − 35 = **65 marks**
- 25 days late internally → 100 − 125 = **0 marks** (floor)

### Departmental Score

```
Department Score = Average marks of all finished parts in that department
```

Unfinished parts (no actual finish date entered) are excluded from the average.

### Delay Categories

| Category | Type | Penalty |
|---|---|---|
| Material Shortage | Internal | Yes — 5 marks/day |
| Labor Unavailability | Internal | Yes — 5 marks/day |
| Design Revision | Internal | Yes — 5 marks/day |
| Machine Breakdown | Internal | Yes — 5 marks/day |
| Supply Chain Disruption | Internal | Yes — 5 marks/day |
| Other | Internal | Yes — 5 marks/day |
| **Client Approval Lag** | **External** | **No penalty** |
| **Client Change Request** | **External** | **No penalty** |

---

## Configuration

### Changing Default Departments

Edit `modules/core.py`, the `DEFAULT_DEPARTMENTS` list:

```python
DEFAULT_DEPARTMENTS = [
    {"name": "Design",        "duration": 30, "order": 1},
    {"name": "Purchase",      "duration": 45, "order": 2},
    {"name": "Manufacturing", "duration": 60, "order": 3},
    {"name": "Assembly",      "duration": 10, "order": 4},
    {"name": "Testing",       "duration": 7,  "order": 5},
]
```

These are the defaults that appear on first load. Users can override them live via the sidebar without touching code.

### Changing the Penalty Rate

In `modules/core.py`:

```python
MARKS_PER_DAY_DEDUCTION = 5   # change this value
BASE_MARKS = 100
```

### Adding New Delay Categories

In `modules/core.py`:

```python
DELAY_CATEGORIES = [
    "Material Shortage",
    "Labor Unavailability",
    "Design Revision",
    "Client Approval Lag",      # External
    "Client Change Request",    # External
    "Machine Breakdown",
    "Supply Chain Disruption",
    "Other",
    "Your New Category Here",   # add here
]

# If it should be external (no penalty), also add to:
EXTERNAL_CATEGORIES = {
    "Client Approval Lag",
    "Client Change Request",
    "Your New External Category",
}
```

---

## Excel Report

The downloaded `.xlsx` contains three sheets:

### Sheet 1 — Summary Dashboard
- Project code and start date banner
- One row per department: duration, original end, shifted end, parts tracked, parts complete, average marks, efficiency %
- Colour-coded marks cells (green ≥80, amber ≥50, red <50)
- Embedded bar chart of departmental efficiency

### Sheet 2 — Part Detail
Columns: Project Code · Department · Part Name · Original Deadline · Predecessor Delay · Adjusted Deadline · Actual Finish · Delay Days · Marks

### Sheet 3 — Delay Log
Only contains parts that finished late. Columns: Department · Part Name · Delay Days · Category · Type (Internal/External) · Penalty Applied · Reason/Notes

---

## Tech Stack

| Library | Version | Purpose |
|---|---|---|
| `streamlit` | ≥1.35.0 | Web UI framework |
| `plotly` | ≥5.22.0 | Interactive charts (Gantt, bar, gauges) |
| `pandas` | ≥2.2.0 | DataFrame handling for tables |
| `openpyxl` | ≥3.1.4 | Excel report generation |

All standard library — no external APIs, no database, no authentication required.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'modules'`
Your GitHub repo is missing the `modules/` folder. Make sure all 5 files are committed:
- `modules/__init__.py`
- `modules/core.py`
- `modules/ui_helpers.py`
- `modules/visualizations.py`
- `modules/reporting.py`

### App resets all data when I change a department
This is intentional. Changing department structure (add/remove) clears previous analysis results because the tab layout has changed and old data would be mismatched.

### Delay fields not appearing for a late part
Make sure the **Actual Finish Date** is set to a date strictly after the **Adjusted End** shown in the blue info box at the top of that department's tab. The adjusted end already accounts for upstream delays.

### Excel report downloads but charts look empty
Charts only appear after clicking **▶ Run Analysis**. Visit the Analytics tab first to confirm results loaded, then download.

---

## Author

Built  by a Senior Project Management Consultant & Full-Stack Python Developer.

---

*Last updated: May 2026*
