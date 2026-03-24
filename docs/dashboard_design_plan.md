# Dashboard Design Plan — The Convenience Paradox

**Date**: 2026-03-24
**Status**: Approved for implementation
**Framework**: Plotly Dash 4.x (multi-page application)

---

## 1. Design Goals

Every element on the dashboard must demonstrably serve at least one of these three goals:

- **Goal A**: Demonstrate interactive application and user interface development
- **Goal B**: Demonstrate dashboards, visual analytics, and interactive web front-ends for research results
- **Goal C**: Demonstrate development of crucial components — computational models, LLM-enhanced user interfaces, and advanced data visualization — for internal strategic infrastructures

The result should feel like an **internal research tool at a well-funded institute**: professional, information-dense where needed, but never cluttered. White space is an asset.

**Extensibility** is a first-class requirement. The architecture, API surface, and UI layout must support future additions without structural rework.

---

## 2. Technology Stack

| Package | Version | Role |
|---------|---------|------|
| `dash` | 4.x | Core framework; multi-page app via Dash Pages |
| `dash-bootstrap-components` | latest | Professional theming (e.g. LUX / FLATLY / COSMO), responsive grid |
| `dash-ag-grid` | latest | Run History table: filtering, sorting, row selection, batch deletion |
| `plotly` | 6.6.0 (installed) | All charting — native Dash integration |
| `pandas` | 3.0.1 (installed) | DataFrames for model output and batch results |
| `pydantic` | 2.12.5 (installed) | LLM output validation schemas |

### Architectural Decision: Dash Replaces Flask Frontend

The previous Flask + vanilla JS + Jinja2 frontend is **removed**. The following legacy files will be deleted:

- `api/app.py` (Flask application factory)
- `api/routes.py` (Flask REST endpoints)
- `api/llm_routes.py` (Flask LLM endpoints)
- `templates/index.html` (Jinja2 template)
- `static/` directory (CSS/JS assets — already empty)

**Retained under `api/`** (used by Dash callbacks via direct Python import):

- `api/llm_service.py` — LLM service layer (all Ollama calls)
- `api/llm_audit.py` — Audit recorder
- `api/schemas.py` — Pydantic schemas

Dash callbacks call model and service functions **directly via Python imports** — no HTTP round-trip. This is both simpler and faster than the previous REST API pattern.

### Data Flow

```
Dash Callback (user interaction)
  → Python function call (model.step(), llm_service.interpret_results(), etc.)
    → Return data (DataFrame, dict, ForumSession)
      → Plotly figure / Dash component update
        → Browser renders
```

---

## 3. Application Structure

```
convenience-paradox/
  dash_app/
    app.py              # Dash app factory, navbar, theme, page_container
    pages/
      simulation.py     # Page 1: Simulation Dashboard
      llm_studio.py     # Page 2: LLM Studio
      run_manager.py    # Page 3: Run Manager
      analysis.py       # Page 4: Analysis
    components/         # Reusable Dash components (charts, cards, etc.)
    callbacks/          # Callback logic separated from layout (extensibility)
    assets/             # Dash auto-serves CSS/images from this directory
  model/                # Mesa ABM core (unchanged)
  api/                  # LLM service layer + schemas (retained)
  analysis/             # Batch runs, sensitivity (unchanged)
  data/                 # Empirical + results (unchanged)
  tests/                # Unit tests (extended for Dash)
  run_dash.py           # Entry point: python run_dash.py
```

The `pages/`, `components/`, and `callbacks/` directories provide clear extension points. Adding a new dashboard page requires only a new file in `pages/` with `dash.register_page()`.

---

## 4. Page Specifications

### 4.1 Page 1: Simulation Dashboard

**Goals served**: A (interactive controls), B (visual analytics), C (computational model)

This is the hero page — parameter configuration, simulation control, and live visualization in one cohesive layout.

#### 4.1.1 Parameter Controls

Source: `model/params.py` — `PARAMETER_DEFINITIONS`, `get_preset()`

- **Preset selector**: Type A (Autonomy-Oriented) / Type B (Convenience-Oriented) / Custom — with description tooltips
- **6 primary sliders** (the most impactful parameters per sensitivity analysis):
  - `delegation_preference_mean` [0.0, 1.0]
  - `service_cost_factor` [0.05, 1.0]
  - `social_conformity_pressure` [0.0, 1.0]
  - `tasks_per_step_mean` [1.0, 6.0]
  - `initial_available_time` [4.0, 12.0]
  - `num_agents` [20, 500]
- **Advanced section** (collapsible): `delegation_preference_std`, `tasks_per_step_std`, `stress_threshold`, `stress_recovery_rate`, `adaptation_rate`
- **Network type toggle**: small_world / random
- **Simulation controls**: Initialize / Step N / Run to Completion / Reset

#### 4.1.2 Core Time Series Charts (5 charts)

Source: `DataCollector` model reporters via `model.get_model_dataframe()`

| Chart | Metric(s) | Hypothesis | Purpose |
|-------|-----------|------------|---------|
| Labor Hours | `total_labor_hours` | H1 | The central paradox metric |
| Stress and Delegation | `avg_stress` + `avg_delegation_rate` (dual-axis) | H2, H3 | Convenience-stress tradeoff |
| Social Efficiency | `social_efficiency` | H2 | Involution threshold signal |
| Income Inequality | `gini_income` | Distributional | Universally understood inequality measure |
| Market Health | `unmatched_tasks` + `tasks_delegated_frac` (dual-axis) | H2 | Service market saturation |

All charts: Plotly `go.Scatter` with step-aligned x-axis, hover tooltips, responsive sizing. Updated after each step or run completion.

#### 4.1.3 Agent Distribution Panels (3 views)

Source: `DataCollector` agent reporters via `model.get_agent_dataframe()` or `model.get_agent_states()`

| Visualization | Data | Type |
|---------------|------|------|
| Stress Distribution | `stress_level` all agents, current step | Histogram |
| Delegation Preference Distribution | `delegation_preference` all agents | Histogram — shows polarization (H4) |
| Provider vs. Consumer Scatter | `income` vs `time_spent_providing` | Scatter — reveals agent role stratification |

#### 4.1.4 Service Flow Diagram (advanced visualization)

Source: model step accumulators (`_step_tasks_total`, `_step_tasks_delegated`, `_step_tasks_matched`)

- **Task Flow Sankey**: Tasks Generated -> Self-Served / Delegated -> Matched / Unmatched
- **Fee Flow Waterfall**: Income transferred from delegators to providers per step — computed from `tasks matched * service_cost_factor * task.base_time`
- Updates each step; visually communicates the delegation pipeline and economic flow

#### 4.1.5 Network Topology Graph

Source: `model.grid.G` (NetworkX graph via Mesa NetworkGrid)

- **Force-directed network visualization** using Plotly `go.Scatter` for nodes and edges
- **Node color**: mapped to agent attribute (selectable: stress_level / delegation_preference / income)
- **Node size**: proportional to another attribute (e.g. time_spent_providing)
- Static topology properties displayed as annotation: node count, edge count, average degree, clustering coefficient
- Refreshes when attribute mapping changes or after simulation steps

#### 4.1.6 Skill Radar Charts

Source: agent `skill_set` dict (`{domestic, administrative, errand, maintenance}` proficiency values)

- **Per-agent radar chart**: click an agent node in the network graph or select from a dropdown to display their skill profile
- Plotly `go.Scatterpolar` with the 4 task-type axes
- Shows alongside agent summary card (delegation_preference, stress, income, tasks completed/delegated)
- Demonstrates sophisticated, visually appealing dashboard design

---

### 4.2 Page 2: LLM Studio

**Goals served**: A (interactive UI), C (LLM-enhanced interface)

Showcases all 5 LLM roles as a unified AI research assistant interface. Primary differentiator for the "LLM-enhanced user interfaces" goal.

#### 4.2.1 Scenario Parser (Role 1)

- **Input**: Text area for natural language scenario description (max 500 chars)
- **Output**: Parsed parameters table with `scenario_summary` and `reasoning`
- **Action**: "Apply to Dashboard" button pushes parsed params to Page 1 sliders
- Source: `api/llm_service.py` → `parse_scenario()`

#### 4.2.2 Result Interpreter Chat (Role 3)

- **Input**: Chat interface with message history
- **Output**: `answer`, `hypothesis_connection`, `confidence_note`
- **Context**: Automatically injects current simulation metrics
- Display: Chat bubble UI with hypothesis badges and confidence caveats

#### 4.2.3 Agent Profile Generator (Role 2)

- **Input**: Demographic description text field
- **Output**: Profile card with delegation preference + 4 skill values (radar chart) + description
- **Audit trail**: Shows the full prompt/output pair for transparency (white-box principle)
- Source: `api/llm_service.py` → `generate_agent_profile()`

#### 4.2.4 Visualization Annotations (Role 4)

- **Trigger**: "Annotate All Charts" button (or automatic after a run completes)
- **Output**: Auto-generated captions for the 5 main charts, displayed below each chart on Page 1
- Source: `api/llm_service.py` → `annotate_visualization()` / batch via `annotate_all` logic

#### 4.2.5 Agent Forums (Role 5 — Experimental)

- **Controls**: `forum_fraction` slider [0.05, 0.5], `group_size` selector [2, 4], `num_turns` selector [1, 3]
- **Output**: Dialogue transcript in chat-bubble format per group
- **Metrics**: norm_signal gauge per group, before/after preference comparison per participating agent, participation rate
- **Label**: Clearly marked "Experimental Mode" badge
- Source: `model/forums.py` → `run_forum_step()`

#### 4.2.6 LLM Audit Log Viewer

- **Display**: Tabular log of all LLM interactions during the current session
- **Columns**: timestamp, role, model, think mode, elapsed_seconds, schema_validation status, prompt preview, response preview
- **Detail view**: Click a row to expand full prompt, raw response, parsed output, and any error
- **Filtering**: By role, by success/failure, by time range
- Source: `api/llm_audit.py` → `LlmAuditRecorder` (wired into all LLM calls from the Dash app)
- Demonstrates rigorous LLM integration practices and observability

#### 4.2.7 LLM Status Indicator

- Ollama availability, model readiness — always visible in navbar
- Reflects the currently selected models (see 4.2.8)
- Source: `api/llm_service.py` → `get_llm_status()`

#### 4.2.8 LLM Model Selector (Per-Role)

Source: Ollama API (`ollama.list()`) for dynamic model discovery; `api/llm_service.py` for current assignments

- **Model discovery**: On page load (and via a "Refresh" button), query Ollama for all locally installed models. Display each model's name, parameter size, and quantization level.
- **Per-role dropdowns**: One dropdown selector for each of the 5 LLM roles:
  - Role 1 — Scenario Parser
  - Role 2 — Profile Generator
  - Role 3 — Result Interpreter
  - Role 4 — Visualization Annotator
  - Role 5 — Agent Forums
- **Defaults**: Role 2 defaults to the lightweight model (currently `qwen3:1.7b`); all other roles default to the primary model (currently `qwen3.5:4b`). Defaults are applied on page load.
- **Live switching**: Changing a role's model takes effect immediately for the next LLM call to that role. No restart required.
- **Persistence**: Model selections are stored in `dcc.Store` (session-scoped). They do not persist across browser refreshes unless the user explicitly saves a configuration.
- **Backend change**: `api/llm_service.py` functions (`parse_scenario`, `generate_agent_profile`, `interpret_results`, `annotate_visualization`) must accept an optional `model` parameter to override the module-level default. The `model/forums.py` `FORUM_MODEL` constant must similarly accept an override. This is an additive, backward-compatible change — existing code that omits the parameter continues to use the defaults.
- **UI layout**: A collapsible "Model Configuration" panel at the top of the LLM Studio page, showing all 5 role selectors in a compact grid. Each selector shows the model name and a status badge (ready / not found).

---

### 4.3 Page 3: Run Manager

**Goals served**: A (interactive application), B (data management front-end)

Demonstrates data stewardship with full query and management capabilities on the experiment database.

#### 4.3.1 Run History Table — Dash AG Grid

Source: SQLite `runs` table

- **Columns**: run_id, created_at, label, preset, steps_run, final_avg_stress, final_total_labor_hours, final_social_efficiency, final_gini_income, final_avg_delegation_rate
- **Column sorting**: All columns sortable
- **Text filtering / search**: Label, preset, date range
- **Row selection**: Single-click for detail view; multi-select (checkbox) for batch operations
- **Single row delete**: Right-click context menu or action button on selected row, with confirmation modal
- **Batch delete**: "Delete Selected" button for all checked rows, with confirmation modal listing affected runs; cascades to `run_steps` table
- **Pagination**: For large result sets

#### 4.3.2 Run Comparison

- **Interaction**: Select 2+ runs from the AG Grid via checkboxes
- **Display**: Side-by-side metric comparison cards with delta percentages
- **Chart overlay**: "Compare on Charts" button renders selected runs as overlaid time series (stress, labor, delegation, efficiency)
- Source: SQLite `runs` + `run_steps` tables

#### 4.3.3 Run Detail View

- Click a run row to expand: full parameter set used, step-by-step time series charts, editable label field
- Source: SQLite `runs` + `run_steps` tables

---

### 4.4 Page 4: Analysis

**Goals served**: B (visual analytics for research results), C (advanced data visualization)

Presents the research conclusions — the "so what" of the simulation.

#### 4.4.1 Hypothesis Scoreboard

- **Display**: 4 cards (H1–H4), each with:
  - Status badge (Confirmed / Supported / Pending)
  - One-line evidence summary
  - Key metric value from current or saved runs
- **Interaction**: Click to expand with supporting chart and detailed explanation
- Data: Hardcoded status from research findings + live metrics from current/saved runs

#### 4.4.2 Type A vs Type B Comparison

- **Display**: Side-by-side comparison panel
  - Parameter table with highlighted differences
  - 4–6 key metrics with bar chart comparison and percentage deltas
  - Matches the README's empirical finding table format
- **Interaction**: "Run Both" button initializes and runs both presets, then displays comparison
- This is the single most important research result visualization

#### 4.4.3 Interactive Sensitivity Heatmap

- **Display**: Interactive Plotly `imshow` heatmap
  - X-axis: selectable parameter (dropdown from PARAMETER_DEFINITIONS)
  - Y-axis: selectable parameter (dropdown)
  - Color: selectable outcome metric (dropdown: avg_stress, total_labor_hours, social_efficiency, gini_income, etc.)
- **Data source**: Pre-computed batch CSVs from `data/results/` loaded on demand, or lightweight on-demand sweep triggered from the UI
- Demonstrates advanced parameter space exploration

---

## 5. Extensibility Architecture

### 5.1 Adding a New Page

1. Create `dash_app/pages/new_page.py`
2. Call `dash.register_page(__name__, path="/new-page", name="New Page")`
3. Define `layout` variable or function
4. The navbar auto-populates from `dash.page_registry`

### 5.2 Adding a New Chart to an Existing Page

1. Create a reusable chart function in `dash_app/components/`
2. Add a `dcc.Graph(id="new-chart")` to the page layout
3. Add a callback in `dash_app/callbacks/` that updates the figure
4. Register the callback in the page module

### 5.3 Adding a New Data Source

1. Create a data access function (in `model/`, `api/`, or a new `dash_app/data/` module)
2. Call it from a Dash callback
3. Return the data as a Plotly figure or Dash component

### 5.4 Adding New LLM Roles

1. Add the LLM function to `api/llm_service.py` with Pydantic schema
2. Add a UI section in `dash_app/pages/llm_studio.py`
3. Wire a callback that calls the new function and updates the display

---

## 6. Database Enhancements

The current SQLite schema (append-only) needs the following management capabilities:

### 6.1 Delete Operations

- **Single run delete**: `DELETE FROM run_steps WHERE run_id = ?; DELETE FROM runs WHERE id = ?;`
- **Batch delete**: Same queries wrapped in a transaction for multiple run IDs
- **Confirmation**: All deletes require user confirmation via a Dash modal

### 6.2 Search and Filter

- **By label**: `LIKE` query on `label` column
- **By preset**: Exact match on `preset` column
- **By date range**: `BETWEEN` on `created_at`
- **By metric range**: Filter on `final_*` columns (e.g. "show runs where final_avg_stress > 0.5")

These are implemented as Python functions called directly by Dash callbacks — no REST endpoints needed.

---

## 7. Files to Delete (Legacy Flask Frontend)

| File | Reason |
|------|--------|
| `api/app.py` | Flask application factory — replaced by Dash app |
| `api/routes.py` | Flask REST endpoints — replaced by Dash callbacks |
| `api/llm_routes.py` | Flask LLM endpoints — replaced by Dash callbacks |
| `templates/index.html` | Jinja2 template — replaced by Dash layouts |
| `static/` directory | Vanilla JS/CSS — replaced by Dash assets/ and dash-bootstrap-components |

---

## 8. Visual Elements Summary

| Page | Visual Elements | Data Points |
|------|----------------|-------------|
| Simulation Dashboard | 5 time series + 3 distributions + 1 Sankey + 1 waterfall + 1 network graph + 1 radar chart + parameter panel | ~35 active metrics |
| LLM Studio | 5 role interfaces + audit log viewer + per-role model selector + status indicator | ~25 interaction types |
| Run Manager | 1 AG Grid table + comparison panel + detail view | ~10 columns + time series overlay |
| Analysis | 4 hypothesis cards + A/B comparison + interactive heatmap | ~20 metrics |

**Total: ~90 curated data points** — focused, professional, extensible.
