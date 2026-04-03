# ConvenienceParadoxResearchModel — Design Specification

> Chinese: [ConvenienceParadoxResearchModel_design.zh.md](ConvenienceParadoxResearchModel_design.zh.md)

## 1. Design goals

`ConvenienceParadoxResearchModel` is a **research-only engine** for mechanism questions that the current stable web-facing model does not yet explain well, in particular:

- Why a low `service_cost_factor` can coincide with lower stress
- Why high delegation behaves more like a buffer than an amplifier in the current model
- Why existing experiments show little supply tightness or backlog
- Under what conditions delegation shifts from “stress relief” to “burden amplification”

The engine is **not** meant to replace the dashboard’s `ConvenienceParadoxModel`. It is a transparent, white-box experimental variant for mechanism audits, targeted reruns, and research reports.

## 2. Why the web model is not modified in place

The Dash UI and the stable model share an explicit contract:

- Controls depend on fixed `PARAMETER_DEFINITIONS` in `model/params.py`
- API inputs depend on fixed `SimulationParams` in `api/schemas.py`
- KPIs and charts depend on existing, stable metric columns
- The Analysis page still embeds some static research copy

If backlog, coordination cost, provider friction, and stricter matching were folded directly into `ConvenienceParadoxModel`, the research story would be richer but would also:

- Change what the UI semantically shows
- Risk misalignment between static Analysis text and new outputs
- Shift the interpretation boundary for sensitivity dropdowns and presets without a deliberate UI pass

This round therefore uses a **dual-model** approach:

- `ConvenienceParadoxModel`: stable web contract
- `ConvenienceParadoxResearchModel`: research experiment contract

## 3. Relationship to the stable model

### 3.1 What the stable model owns

- Web simulation control
- Page charts
- Current preset interactions
- Existing API / Dash callback contracts

### 3.2 What the research model owns

- Mechanism audits
- The `research_v2` campaign
- Targeted reruns around `service_cost_factor`
- Explanations involving backlog, capacity, and labor deltas
- Standalone English and Chinese research reports

### 3.3 How compatibility is preserved

The research model keeps the following surface so analysis scripts can swap engines at minimal cost:

- `step()`
- `get_model_dataframe()`
- `get_agent_dataframe()`
- `get_agent_states()`
- `get_params()`

Analysis code can therefore switch behaviour by **selecting the model class**, without rewriting the full aggregation and reporting pipeline.

## 4. Class structure and lifecycle

### 4.1 Class structure

- `ConvenienceParadoxResearchModel`
  - Subclasses the stable `ConvenienceParadoxModel`
  - Uses a fixed research engine label `research_v2`
  - Rebuilds a research-only `DataCollector`
  - Overrides `step()` and `_run_service_matching()`
- `ResearchResident`
  - Subclasses stable `Resident`
  - Adds backlog and coordination bookkeeping
  - Overrides `generate_and_decide()`, `_execute_task_self()`, `provide_service()`

### 4.2 Lifecycle per step

1. Reset step-level counters
2. Each agent merges `carryover_tasks` into the day’s task set
3. Sample new tasks for the day
4. For each task, choose self-serve vs. delegate
5. Delegated tasks enter `service_pool`
6. `_run_service_matching()` only assigns providers who can **finish the full service** within remaining time
7. Unmatched tasks return to the requester’s `carryover_tasks`
8. Agents update stress and delegation preference from end-of-day remaining time
9. `DataCollector` records legacy metrics plus new research metrics

## 5. Data flow: backlog / matching / stress / labor

### 5.1 Backlog

Stable-model limitation:

- `unmatched_tasks` is counted but tasks **do not** return to the requester
- Unsatisfied delegation therefore does not become **next-day** real pressure

Research-model change:

- Unmatched work does not vanish
- It is appended to the requester’s `carryover_tasks`
- Next step, the agent must face those tasks again in the decision loop

Backlog is thus a **real residual workload**, not only a retrospective statistic.

### 5.2 Matching

Stable-model limitation:

- Provider eligibility uses only `0.5 * base_time`
- The system can “always find someone” in many regimes

Research-model change:

- Eligibility requires remaining time to cover **expected** provider service duration
- Expected duration = `task.time_cost_for(0.60) * provider_service_overhead_factor`

Supply tightness becomes easier to observe and interpret.

### 5.3 Stress

The research model does **not** add ad hoc stress penalties.

Stress still comes mainly from:

- Whether end-of-day remaining time falls below `stress_threshold`
- Backlog indirectly raising pressure via “tasks carry over → still consume time tomorrow”
- Requester coordination cost entering through **real** time expenditure

Stress remains white-box and time-constraint-driven, not tuned by extra penalties to force a narrative.

### 5.4 Labor accounting

Total labor is split into three explicit components:

- `self_labor_hours`
- `service_labor_hours`
- `delegation_coordination_hours`

Two counterfactuals for delegated tasks are also logged:

- `delegated_counterfactual_self_hours`  
  Hours the requester **would** have spent if those delegated tasks were self-served
- `delegated_actual_service_hours`  
  Hours providers **actually** spent on those delegated tasks

Define:

- `delegation_labor_delta`  
  `delegated_actual_service_hours + delegation_coordination_hours - delegated_counterfactual_self_hours`

This answers directly whether delegation **saves** or **adds** system-wide labor time.

## 6. New model-level metrics

| Metric | Meaning |
|--------|---------|
| `self_labor_hours` | Total hours this step spent by requesters completing tasks themselves |
| `service_labor_hours` | Total hours this step spent by providers on delegated tasks |
| `delegation_coordination_hours` | Hours this step spent on communication, scheduling, and handover due to delegation |
| `delegated_counterfactual_self_hours` | Counterfactual self-serve hours for tasks that were delegated |
| `delegated_actual_service_hours` | Actual provider hours on those delegated tasks |
| `delegation_labor_delta` | Net change in system labor from delegation vs. self-serve counterfactual |
| `stress_breach_share` | Share of agents below the stress time threshold at day end |
| `mean_time_deficit` | Mean shortfall vs. the stress threshold across agents |
| `backlog_tasks` | Count of tasks still unresolved at step end and carried forward |
| `delegation_match_rate` | Share of delegated tasks successfully matched this step |

## 7. Web compatibility principles

This round adheres to:

- No edits under `dash_app/`
- No change to page input contracts in `api/schemas.py`
- No change to `PARAMETER_DEFINITIONS` or presets in `model/params.py`
- No research-only parameters on dashboard controls
- No requirement for web charts to consume new metrics
- No requirement to refresh static Analysis conclusions immediately to research outputs

The dashboard keeps the stable model; the research model is invoked **explicitly** from analysis scripts only.

## 8. Known limitations

- Still no endogenous price formation; `service_cost_factor` remains exogenous
- No “wait tolerance,” speed expectations, skill decay, or other deep mechanisms yet
- Single resident type; no separate professional provider vs. ordinary requester roles
- Stable and research output lines run in parallel for now—reports must state which engine was used

## 9. When to merge back into the main model

Merge research mechanisms into the stable line **only if**:

1. The research variant stays stable across reruns and clearly improves explanatory power
2. Analysis static copy is rewritten so it no longer depends on the old mechanism story
3. KPI and chart designs are reviewed and can carry backlog / match-rate semantics
4. There is a clear decision on whether API and dashboard expose research-only parameters

Until then, `ConvenienceParadoxResearchModel` remains a standalone research engine.
