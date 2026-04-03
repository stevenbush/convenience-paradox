# Interpretation of Dashboard Metrics

This document explains what the Simulation Dashboard numbers and charts **mean in experimental terms**, and how **on-screen elements relate to each other**. It complements `docs/dashboard_design_plan.md` and `docs/dashboard_design_system.md`, which specify layout and UX.

---

## 1. Total Labor Hours — KPI Card vs Time Series Chart

### 1.1 What the value **514.7** in the card represents

The **TOTAL LABOR HOURS** KPI card shows **labour for a single simulation step only** — specifically, the **most recently completed step** — **not** the sum of labour across the whole experiment.

Implementation: the card reads the **last row** of the model-level DataCollector dataframe and formats `total_labor_hours` from that row (see `update_kpis` in `dash_app/pages/simulation.py`, which uses `df.iloc[-1]`).

So if the status line reads “Step 100 (ran 100)”, **514.7** is the **system-wide total labour hours recorded for step 100** (one “day” in the model), rounded to one decimal place.

### 1.2 What the line chart shows

The **Total Labor Hours** chart (subtitle: H1 — Delegation paradox) plots the **same variable** (`total_labor_hours`) **for every recorded step**: one point per step on the x-axis (“Step”), y-axis in hours.

Each y-value is again **per-step collective labour**, not a cumulative total. The series answers: “How did daily systemic labour evolve over the run?”

### 1.3 Relationship between the card and the chart

| Element | Quantity |
|--------|----------|
| KPI card | `total_labor_hours` at the **latest** step only |
| Chart | `total_labor_hours` at **each** step (full history) |

Therefore **514.7** should match the **rightmost point** of the labour curve (final step). It is **not** the integral or sum of labour over steps 1…100.

If you need **cumulative labour over the entire run** for a custom analysis, that value is **not** shown on the dashboard; you would sum `total_labor_hours` across rows of the model dataframe (or export runs and aggregate offline).

### 1.4 Experimental meaning (brief)

For each step, `total_labor_hours` is the sum over all agents of `(initial_available_time − available_time)` after that step: **total hours all residents collectively spent on tasks that step**, including self-service and time spent providing services to others. It is the primary **H1** outcome: higher delegation settings are expected to associate with **higher** per-step systemic labour under comparable task pressure, illustrating the “convenience paradox” at the system level.

---

## 2. Stress & Delegation (dual-axis chart, H2 / H3)

### 2.1 Which line is which

- **Avg Stress** (red, **left** axis “Stress”): mean of all agents’ `stress_level` at each step, in **[0, 1]**. It is a **fast-moving** state variable driven by whether agents finish the step with time below the stress threshold, plus recovery.
- **Avg Delegation** (orange, **right** axis “Delegation Preference”): the dashboard series is `avg_delegation_rate` in the DataFrame, which is the **mean delegation preference** (`delegation_preference`) across agents — **not** the realised fraction of tasks delegated (`tasks_delegated_frac`).

### 2.2 Reading the chart relative to H2 and H3

- **H3** uses **avg stress** to compare well-being pressure across scenarios (e.g. autonomy-oriented vs convenience-oriented presets). A single run shows how mean stress **fluctuates** as random tasks and matching play out.
- **H2** (threshold / involution narratives) is usually assessed with **parameter sweeps** and complementary series (e.g. `social_efficiency`, `total_labor_hours`, `unmatched_tasks`), not from this chart alone.

### 2.3 “Straight line” confusion — stress vs delegation

On a typical run, **Avg Stress is jagged**, not horizontal: each step draws new tasks and different matches, so the cross-sectional mean stress moves.

If the **orange** series appears as a **perfectly flat** line while stress wiggles, that is **Avg Delegation** (mean preference), not Avg Stress. That pattern is **usually normal**: preferences update slowly via `adaptation_rate` and conformity toward neighbours; if the population is **homogeneous** (similar initial preferences, tight network mixing), the **population mean** of `delegation_preference` can remain **almost constant** for many steps even while stress varies.

**Avg Stress** as a **true horizontal line** (zero variance across all steps) would be **unusual** in this model and would warrant checking that the simulation is stepping correctly and that the plotted column is `avg_stress`.

### 2.4 Why mean stress can look very small on the left axis

The left axis may auto-scale to a narrow band (e.g. 0–0.03) when the **population mean** stays low on the 0–1 scale. That does **not** mean stress is “off”; it means the **average** agent is only mildly stressed relative to the full range. Individual agents can still be more stressed (see the stress distribution histogram elsewhere on the page).

---

## 3. Social Efficiency (H2 — Involution threshold)

### 3.1 Definition

The chart plots **`social_efficiency`** each step. In code it is **tasks successfully completed this step** divided by **total collective labour hours this step** (`tasks_done / total_labor`).

So the y-axis label **“Tasks / Hour”** means **tasks completed per system-wide labour-hour** in that step (not per individual worker).

**Numerator (`tasks_done`)** counts:

- Tasks handled by the owner (**self-served**): total tasks generated minus those marked as delegated.
- Plus **delegated tasks that were successfully matched** to a provider this step.

**Excluded**: delegated tasks that **failed to match** (`unmatched_tasks` are not counted as completed).

**Denominator** is the same **`total_labor_hours`** as in §1 (sum over agents of time consumed that step).

### 3.2 Experimental meaning

- **Higher** efficiency: more useful task completions per unit of collective time — the system is “getting more done” for the hours it burns.
- **Lower** efficiency (involution narrative): collective labour stays high or rises while **completed** tasks do not keep pace — people are busy but **effective throughput** suffers.

That is why this series is grouped under **H2** alongside threshold stories: when the matching pool is overloaded or delegation creates overhead, you may see **labour up** (H1) while **efficiency down** or volatile.

### 3.3 How to read a typical trajectory (e.g. jump then flat band)

An initial point at **zero** often reflects the **first DataCollector row** (step 0) before meaningful labour is recorded, or zero labour in that row; the series then jumps to a **positive plateau** once the first full step completes.

A **narrow band** of fluctuation (e.g. ~0.5–0.58) with no strong drift usually means the run has reached a **stochastic steady state**: random task counts and matching jitter the ratio step-to-step, but the **average productivity of collective time** is stable. Comparing this level across **presets or parameter sweeps** is more informative for H2 than interpreting a single run in isolation.

---

## 4. Market Health — Unmatched Tasks + Delegation Fraction

### 4.1 Purpose of the panel

This chart combines **service-market tightness** (left axis) with **realised delegation behaviour** (right axis). The subtitle **“Unmatched tasks”** highlights the bar series: delegated demand that could not be served in a given step.

### 4.2 Unmatched Tasks (`unmatched_tasks`)

**Definition** (per step, integer ≥ 0): delegated tasks this step minus delegated tasks successfully matched to a provider this step. Equivalently: **count of delegated tasks that found no eligible provider** with enough remaining time after the model’s greedy matching.

Non-zero values indicate **capacity shortfall** in the informal service market — a leading indicator of involution-style stress when demand cannot be served.

### 4.3 Delegation Fraction (`tasks_delegated_frac`)

**Definition** (per step, in **[0, 1]**): (tasks marked delegated this step) / (total tasks generated this step).

This is **realised behaviour** — the share of all new tasks agents actually chose to delegate. It is **not** the same as mean **delegation preference** (§2’s `avg_delegation_rate`): preference is a propensity; this fraction is the outcome after decisions (cost, time, skills can widen or narrow the gap).

### 4.4 Why unmatched bars can be invisible — bug or normal?

The dashboard draws **Unmatched Tasks** as **bars** with height `unmatched_tasks` each step (`dash_app/pages/simulation.py`).

If **every step has `unmatched_tasks == 0`**, every bar has **height zero** and **nothing is visible**. The legend entry still appears; Plotly’s **left-axis auto-range** can look odd (e.g. a narrow band around zero) when all bar values are zero.

This is **usually not a bug**: with many agents and enough spare time, greedy matching often clears **all** delegated tasks. **Non-zero** unmatched counts tend to appear when delegation demand **exceeds** provider availability (higher task load, less `initial_available_time`, smaller `num_agents`, or bad draws).

**Sanity check**: increase task pressure or delegation and re-run; if bars appear, the series was present all along.

---

## 5. Provider vs Consumer (scatter plot)

### 5.1 Title meaning

**Provider vs Consumer** is a **role-mix diagram**, not two separate populations. Every resident is **both** a potential service consumer (delegates tasks) and a potential provider (serves others). The chart places each **agent** in a 2D space defined by how much they have **consumed via delegation** (x) versus how much they have **supplied as a provider** (y), **cumulated from the start of the run through the current step**.

### 5.2 Axes

| Axis | Dashboard label | Agent field | Meaning |
|------|-----------------|-------------|---------|
| **X** | Tasks Delegated (cumul.) | `tasks_delegated` | **Cumulative** number of tasks this agent **chose to delegate** over all completed steps (each such task enters the service pool). |
| **Y** | Hours Providing (cumul.) | `time_spent_providing` | **Cumulative** hours this agent spent **performing services for other agents** (matched provider work). |

Both axes are **stock variables** updated each step; after a reset or new initialisation they start from zero again.

### 5.3 Each point

- **One dot = one agent** (one `Resident`) at the **current** moment of the simulation (when the dashboard last refreshed after stepping).
- **Position**: read as a **provider–consumer balance** for that individual:
  - **High y, low x** → has done **much more providing** than delegating → relatively **provider-heavy**.
  - **High x, low y** → has **delegated many tasks** but spent little time serving others → relatively **consumer-heavy**.
  - **High x, high y** → active on **both sides** (typical in a mixed service economy).
- **Positive correlation** across agents (as in many runs) often appears because heavy delegators still draw tasks and may be matched as providers, and busy providers may also delegate some of their own workload — but the exact cloud shape depends on parameters and the matching rule.

### 5.4 Colour (Stress)

Marker colour encodes **`stress_level`** for that agent at the **current step** — a **level** in **[0, 1]**, **not** cumulative. The colour bar’s numeric endpoints follow **Plotly’s auto-scale to the data** (e.g. if no agent exceeds 0.2, the bar may show ~0–0.2 even though the variable can reach 1).

**Contrast**: the **Avg Stress** time series is the **mean** of this same variable across agents at each step; the scatter shows **who** sits at which stress level **now**, while exposing inequality hidden in the average.

### 5.5 Relation to other metrics

- This chart does **not** show **Delegation Fraction** (`tasks_delegated_frac`, a **system-level** ratio per step) or **unmatched tasks**; it shows **individual cumulative** delegation counts and providing hours.
- **Income** and **net balance** appear in separate flow charts (Sankey / waterfall) on the same page, not on this scatter.

---

## 6. Task Flow (Sankey) — Service pipeline

### 6.1 What this chart is

**Task Flow** / **Service pipeline** is a **Sankey diagram** of **one simulation step** — specifically the **most recently completed** `model.step()`. It is **not** cumulative over the whole run.

The dashboard reads `model._step_tasks_total`, `_step_tasks_delegated`, `_step_tasks_matched` after the last step (`dash_app/pages/simulation.py`). Those counters are **reset at the start of each step**, then filled during that step’s task generation and matching.

### 6.2 Nodes (states)

| Node | Meaning |
|------|---------|
| **Generated** | All tasks created for agents in that step (`total`). |
| **Self-Served** | Tasks handled by their owner (`total − delegated`). |
| **Delegated** | Tasks the owner chose to delegate (`delegated`). |
| **Matched** | Delegated tasks that received a provider (`matched`). |
| **Unmatched** | Delegated tasks with **no** available provider that step (`delegated − matched`). |

**Accounting identity** for that step: `Generated = Self-Served + Delegated`, and `Delegated = Matched + Unmatched`.

### 6.3 How to read link widths

Link thickness is proportional to **task count** (integer flows). Wider = more tasks on that path.

- **Generated → Self-Served**: volume of **non-delegated** resolution.
- **Generated → Delegated**: volume entering the **service pool**.
- **Delegated → Matched**: served demand.
- **Delegated → Unmatched**: **shortfall** (same count as `unmatched_tasks` in §4).

### 6.4 Quick ratios (same step)

- **Delegation fraction** = (flow into **Delegated**) / (**Generated**) = `tasks_delegated_frac`.
- **Match rate among delegated** = **Matched** / **Delegated** (1.0 when **Unmatched** link has value 0).

### 6.5 When “Unmatched” seems absent

If **Unmatched** is **0**, Plotly may draw a **zero-width** link or tuck the node out of sight; the diagram can look like “all delegated tasks became matched,” which is **consistent** with a healthy matching step — not an error.

After **Run to completion** or many steps, the Sankey still shows **only the last step’s** pipeline. To see how unmatched evolve, use the **Market Health** time series (`unmatched_tasks`) or the model dataframe over steps.

---

## 7. Fee Flow (waterfall) — Economic transfer

### 7.1 What this chart is

**Fee Flow** / **Economic transfer** is a **Plotly waterfall** built from **each agent’s cumulative `income`** at the **current** simulation state (after the latest refresh). It summarises **who holds net positive vs net negative cumulative income** across the population, not a single-step cash flow.

Implementation (`dash_app/pages/simulation.py`):

- **Provider Earnings** bar: sum of `income` over agents with **`income > 0`** (net lifetime earners from the service economy).
- **Delegator Fees** bar: sum of `income` over agents with **`income < 0`** — this is a **negative** number (delegators / net payers).
- **Net Balance**: `provider_earnings + delegator_costs` (algebraic sum).

### 7.2 What `income` means on an agent

Each `Resident` keeps **cumulative net income** (`model/agents.py`):

- When an agent **delegates** a task, they **pay** a fee `task.base_time × service_cost_factor` (**subtracted** from `income`).
- When an agent **provides** a matched service, they **receive** the same fee formula (**added** to `income`).

So money flows **from delegating requesters to providing agents** for each **successfully matched** delegated task. Self-served tasks do not move `income`.

### 7.3 How to read the three bars

| Bar | Reading |
|-----|---------|
| **Provider Earnings** | Total **positive** cumulative balances — aggregate **service income** accumulated by net providers. |
| **Delegator Fees** | Total **negative** cumulative balances — aggregate **net fees paid** (and not offset by earning) by agents who are net payers. Displayed as a **downward** step in the waterfall. |
| **Net Balance** | **Sum of all agents’ `income`**. In a run where **every fee paid is received by some provider** (no leakage), this is **0** by construction: the model uses the same fee for payer and earner per matched task. |

A **Net Balance of 0.0** (as in many long runs with full matching) means **closed-book conservation** of the fee accounting across agents — **not** “economic profit for society,” and **not** the same concept as **Delegation Fraction** (which is a task-count ratio per step, §4).

### 7.4 When Net Balance may differ from zero

If **unmatched** delegated tasks occur, requesters may still **pay** the fee when entering the pool while **no provider** credits the matching income for that task; the bookkeeping can leave **aggregate `income` ≠ 0**. Non-zero **Net Balance** therefore can signal **service shortfall** episodes worth cross-checking against `unmatched_tasks` (§4, §6).

### 7.5 Contrast with other charts

- **Task Flow (Sankey)**: task **counts** for the **last step** only.
- **Fee Flow**: **cumulative money metric** (`income`) **aggregated across agents** at the current time — composition (who is net provider vs net payer) drives the two main bars.
