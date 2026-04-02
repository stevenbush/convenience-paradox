# AGENTS.md — Agent Charter for The Convenience Paradox

This file defines the operating rules, conventions, and context for any AI agent working on this project. Read this file in full before taking any action.

---

## Syncing `develop` → `main` (paths to omit on `main`)

**Policy.** The `main` branch is the public release line. The `develop` branch may keep internal or agent-facing material that must **not** reappear on `main` after a merge. Git does not filter paths during `git merge` automatically—whoever performs the sync must **remove the paths below from `main`** (or avoid bringing them in) after integrating `develop`.

**Recorded baseline (for diff provenance).** Compared `develop` at `ae49729` (*chore: remove obsolete formal report artifacts and tests*) with `main` at `c158fcd` (*chore: pre-release documentation cleanup on main*). The following paths exist on `develop` but were intentionally dropped from `main`; treat them as **develop-only** when syncing to `main`:

| Path |
|------|
| `AGENTS.md` |
| `CLAUDE.md` |
| `docs/execution_log.md` |
| `docs/Interpretation_of_Interface_Metrics.md` |
| `docs/Social_Phenomenon_Modeling_and_Design_CN.md` |
| `docs/ConvenienceParadoxResearchModel_design.en.md` |
| `docs/ConvenienceParadoxResearchModel_design.zh.md` |
| `docs/plans/00_master_plan.md` |
| `docs/plans/01_phase1_foundation.md` |
| `docs/plans/02_phase2_simulation.md` |
| `docs/plans/03_phase3_web_interface.md` |
| `docs/plans/04_phase4_llm_integration.md` |
| `docs/plans/05_phase5_agent_forums.md` |
| `docs/plans/06_phase6_analysis_portfolio.md` |

**Refresh the list after future cleanups on `main`:**

```bash
git diff --name-status main develop
```

Entries with status `A` (added when going from `main` to `develop`) are files present on `develop` but absent on `main`—verify each belongs in this develop-only set before relying on the diff alone.

**Suggested workflow after `git checkout main` and `git merge develop`:**

1. Remove the develop-only paths from the index and working tree on `main`, then commit (or amend the merge if appropriate):

```bash
git rm -f --ignore-unmatch \
  AGENTS.md CLAUDE.md \
  docs/execution_log.md \
  docs/Interpretation_of_Interface_Metrics.md \
  docs/Social_Phenomenon_Modeling_and_Design_CN.md \
  docs/ConvenienceParadoxResearchModel_design.en.md \
  docs/ConvenienceParadoxResearchModel_design.zh.md \
  docs/plans/00_master_plan.md \
  docs/plans/01_phase1_foundation.md \
  docs/plans/02_phase2_simulation.md \
  docs/plans/03_phase3_web_interface.md \
  docs/plans/04_phase4_llm_integration.md \
  docs/plans/05_phase5_agent_forums.md \
  docs/plans/06_phase6_analysis_portfolio.md

git commit -m "chore: strip develop-only paths from main after develop merge"
```

2. Extend the `git rm` list (and the table above) if new internal-only files are introduced on `develop`.

**Note.** This section lives in `AGENTS.md` on `develop` only; it is intentionally removed from `main` by the cleanup above. Agents merging or pushing should follow this checklist so `main` stays free of those artifacts.

---

## Formal research report figures (`formal_research_report.md`)

**Constraint.** `.gitignore` ignores generated outputs under `data/results/*` (except `data/results/.gitkeep`). Paths such as `data/results/campaigns/.../figures/` are **not** tracked, so GitHub cannot render images if the markdown points only there.

**Required layout (both `main` and `develop`).**

1. **Committed copies** of the formal-report SVGs live under **`docs/assets/formal_research_report/`** (`figure_01_*.svg` … `figure_15_*.svg`), plus `docs/assets/formal_research_report/README.md` (refresh instructions).
2. **`formal_research_report.md`** (repo root) must reference figures with **repository-relative** URLs from the root, e.g. `docs/assets/formal_research_report/figure_01_causal_loop.svg`, **not** `data/results/campaigns/...`.

**When regenerating figures** from `analysis/formal_campaign_report_v2.py` (or any campaign run): copy the new `figure_*.svg` files from the campaign’s `report_assets/formal_report_v2/figures/` directory into `docs/assets/formal_research_report/` (keep filenames stable), commit, and push so GitHub’s markdown preview stays correct.

**Do not** widen `.gitignore` to commit whole `data/results/campaigns/` for this purpose—campaign trees are large; the `docs/assets/...` mirror is the supported pattern.

---

## 1. Project Identity

**Full Title**: *The Convenience Paradox: Agent-Based Modeling of Service Delegation and Social Involution*

**Purpose**: A two-week rapid prototype demonstrating ABM design, LLM-enhanced interfaces, interactive data visualization, and data stewardship — targeted at the NORCE CMSS Researcher position.

**Repository owner**: Jiyuan Shi (`stevenbush` on GitHub)

**Git identity** (repo-local, never global):
- `user.name = Jiyuan Shi`
- `user.email = stevenbush@users.noreply.github.com`

---

## 2. Execution Governance

### 2.1 Always Read the Plan First

Before writing any code, always read the relevant phase plan from `docs/plans/`. The active phase plan is the authoritative specification for what to build. Do not invent features not described there.

| Phase | Plan File | Status |
|-------|-----------|--------|
| Phase 1 — Foundation | `docs/plans/01_phase1_foundation.md` | ✅ Complete |
| Phase 2 — Simulation Engine | `docs/plans/02_phase2_simulation.md` | ✅ Complete |
| Phase 3 — Web Interface | `docs/plans/03_phase3_web_interface.md` | ✅ Complete |
| Phase 4 — LLM Integration | `docs/plans/04_phase4_llm_integration.md` | ✅ Complete |
| Phase 5 — Agent Forums | `docs/plans/05_phase5_agent_forums.md` | ✅ Complete |
| Phase 6 — Analysis & Portfolio | `docs/plans/06_phase6_analysis_portfolio.md` | ✅ Complete |

Master plan: `docs/plans/00_master_plan.md`

### 2.2 Pause Points

**Do not proceed to the next phase without explicit user instruction.** Each phase boundary is a pause point. When a phase is complete:
1. Update the phase status table above.
2. Append the phase's execution record to `docs/execution_log.md` (see §11).
3. Report the deliverables summary to the user and stop. Do not auto-advance.

### 2.3 Do Not Modify Plan Files

The files in `docs/plans/` are reference documents. Do not edit them during execution. If a plan needs to change, flag the discrepancy to the user first.

---

## 3. Environment

### 3.1 Python Environment

Always use the `convenience-paradox` conda environment. Never install into base or any other environment.

```bash
# Activation
eval "$(conda shell.zsh hook)" && conda activate convenience-paradox

# Python version
Python 3.12.13

# Key packages (verified)
Mesa 3.5.1 | Mesa-LLM 0.3.0 | Dash 4.x | Plotly 6.6.0
Pandas 3.0.1 | Matplotlib 3.10.8 | Pydantic 2.12.5 | Ollama SDK 0.6.1
Dash-Bootstrap-Components | Dash-AG-Grid
```

### 3.2 Local LLM

Ollama runs as a background service (`brew services start ollama`), served at `http://localhost:11434`.

| Model | Ollama Tag | Purpose |
|-------|-----------|---------|
| Qwen 3.5 4B (primary) | `qwen3.5:4b` | All production LLM tasks |
| Qwen 3 1.7B (lightweight) | `qwen3:1.7b` | Rapid iteration / batch generation |

**Qwen 3.5 4B has a thinking mode** that consumes tokens before producing output. Use `think=False` in `ollama.chat()` for structured JSON output (faster, cleaner). Use `think=True` (default) or omit for narrative interpretation tasks where reasoning quality matters.

```python
# Structured output — disable thinking
ollama.chat(model="qwen3.5:4b", messages=[...], think=False,
            format=MyPydanticModel.model_json_schema())

# Narrative/interpretation — allow thinking
ollama.chat(model="qwen3.5:4b", messages=[...], options={"num_predict": 512})
```

**Mesa 3.x API notes** (confirmed during Phase 1–2):
- Space module: `import mesa.space` (not `mesa.spaces`)
- Model seed: `Model(rng=42)` (not deprecated `seed=42`)
- Scheduling: `self.agents.shuffle_do("method_name")` (not old Scheduler classes)

### 3.3 Hardware

MacBook Pro, M4 Pro chip, 24GB unified memory. No CUDA. Metal-accelerated inference via Ollama. All simulation runs are local — no cloud services required.

---

## 4. Project Architecture

```
convenience-paradox/
  model/          # Mesa ABM core (agents, model, params)
  api/            # LLM service layer and Pydantic schemas
  dash_app/       # Plotly Dash multi-page application
    app.py        # Dash app factory, navbar, theme, page_container
    pages/        # Individual page modules (Dash Pages)
    components/   # Reusable Dash components (charts, cards, etc.)
    callbacks/    # Callback logic separated from layout (extensibility)
    assets/       # Dash auto-served CSS/images
  analysis/       # Batch runs, sensitivity analysis, matplotlib plots
  data/
    empirical/    # ILO, OECD, WVS stylized facts (CSV/JSON) — committed
    results/      # Simulation outputs — gitignored
  tests/          # Unit tests
  docs/
    plans/        # All execution plan documents
    execution_log.md  # Phase-by-phase execution records (see §11)
```

### 4.1 Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| ABM Engine | Mesa 3.5.x + Mesa-LLM 0.3.0 | Core simulation; run headlessly |
| LLM Runtime | Ollama + Qwen 3.5 4B | Local only; cloud is fallback via LiteLLM |
| Web Framework | Plotly Dash 4.x | Multi-page app with Dash Pages |
| UI Components | dash-bootstrap-components + dash-ag-grid | Professional theming, interactive data tables |
| Visualization | Plotly (Dash-native) + matplotlib (publication) | |
| Data Layer | Pandas DataFrames + SQLite | DataCollector → DataFrames → Dash callbacks |

---

## 5. Simulation Design

### 5.1 Research Question

*How do different levels of service delegation in a society affect individual well-being and collective efficiency? Under what conditions does a "convenience spiral" (involution) emerge?*

### 5.2 Hypotheses

- **H1**: Higher delegation rates → higher total systemic labor hours.
- **H2**: A critical delegation threshold triggers an involution spiral.
- **H3**: Higher autonomy → lower perceived convenience but higher aggregate well-being.
- **H4**: Mixed systems (moderate delegation) are unstable; they drift toward extremes.

### 5.3 Agent: `Resident`

File: `model/agents.py`

| Attribute | Type | Description |
|-----------|------|-------------|
| `available_time` | float | Hours/day available after fixed commitments |
| `skill_set` | dict | `{task_type: proficiency}` |
| `delegation_preference` | float [0,1] | 0 = always self-serve; 1 = always delegate |
| `stress_level` | float [0,1] | Accumulates when time is scarce |
| `task_queue` | list | Daily tasks to resolve each step |
| `income` | float | Net earnings (service income minus delegation fees) |
| `time_spent_providing` | float | Cumulative hours spent serving others |

**Decision rules (all explicit, parameterized — no hidden LLM logic):**
1. Task generation: each step, agents receive 1–5 tasks drawn from Gaussian distribution
2. Self-serve vs. delegate: based on `delegation_preference`, skill level, time budget, and service cost
3. Service matching: model-level greedy pool matching (most-available-time-first)
4. Stress accumulation: `available_time` below `stress_threshold` → `stress_level` increases
5. Preference adaptation: `delegation_preference` shifts based on stress and peer behaviour (social conformity via network neighbours)

### 5.4 Model: `ConvenienceParadoxModel`

File: `model/model.py` — Mesa `Model` subclass. Three-phase step:
`generate_and_decide` → `_run_service_matching` → `update_state`

**DataCollector metrics (9 model-level):**
`avg_stress`, `avg_delegation_rate`, `total_labor_hours`, `social_efficiency`,
`gini_income`, `gini_available_time`, `tasks_delegated_frac`, `unmatched_tasks`, `avg_income`

**DataCollector metrics (7 agent-level):**
`available_time`, `stress_level`, `delegation_preference`, `income`,
`tasks_completed_self`, `tasks_delegated`, `time_spent_providing`

### 5.5 Parameter Presets

File: `model/params.py`

| Preset | Label | Key characteristics |
|--------|-------|---------------------|
| `TYPE_A_PRESET` | Autonomy-Oriented | delegation_mean=0.25, service_cost=0.65, conformity=0.15 |
| `TYPE_B_PRESET` | Convenience-Oriented | delegation_mean=0.72, service_cost=0.20, conformity=0.65 |
| `CUSTOM` | User-defined | Via dashboard sliders or LLM scenario parser |

Presets are informed by ILO, WVS, and OECD stylized facts. They do not calibrate to empirical data.

---

## 6. LLM Integration Rules

### 6.1 The White-Box Principle

**The ABM simulation core must remain fully transparent and rule-based.** LLM output must never directly control agent decision-making in the standard simulation mode. LLM operates at the periphery only.

### 6.2 The 5 LLM Roles

| Role | Mode | Description |
|------|------|-------------|
| Role 1 — Scenario Parser | Peripheral | Natural language → `SimulationParams` JSON |
| Role 2 — Profile Generator | Peripheral | Description → explicit numerical agent attributes |
| Role 3 — Result Interpreter | Peripheral | Sim data + user question → narrative explanation |
| Role 4 — Visualization Annotator | Peripheral | Chart data → contextual caption |
| Role 5 — Agent Forums | **Experimental** | LLM agents discuss norms; clearly labeled in UI |

### 6.3 LLM Implementation Requirements

- **Always log** every LLM interaction: model used, prompt, raw response, parsed result, timestamp. Write to `data/results/llm_logs/`.
- **Always validate** structured outputs against Pydantic schemas before using them.
- **Agent Profile Generator**: log the full prompt + output JSON for every profile generated. The mapping from LLM output to Mesa agent attributes must be fully visible in code.
- **Agent Forums (Role 5)**: maximum 3 turns per forum exchange. Clearly label as "Experimental Mode" in the UI. Document quality limitations at 4B model size.
- **Fallback**: if Ollama is unavailable, fail gracefully with a clear error message. Never silently skip LLM calls.

### 6.4 LLM Service Layer

File: `api/llm_service.py`. All Ollama calls go through this module. Never call `ollama` directly from Dash callbacks or model code.

Pydantic schemas: `api/schemas.py`. One schema per structured output type.

---

## 7. Neutrality Policy (Non-Negotiable)

This is a strict requirement. Violations must never appear in code, comments, documentation, data files, variable names, or UI text.

**Never name specific countries, regions, ethnicities, or cultures.** Use only abstract labels:

- "**Type A Society (Autonomy-Oriented)**" — never "European", "Nordic", "Western", etc.
- "**Type B Society (Convenience-Oriented)**" — never "Chinese", "Asian", "East Asian", etc.

**All data references** use dataset names only (e.g., "ILO Working Hours data"), not country-specific breakdowns.

**All analytical conclusions** are framed in terms of system properties (delegation rate, service density, conformity pressure) — never attributed to specific nations.

**README and documentation** must include: *"This model explores abstract social dynamics and is not intended to characterize or evaluate any specific society, culture, or nation."*

---

## 8. Coding Standards

### 8.0 POC Commenting Philosophy

This project is a **Proof of Concept and learning/demonstration exercise**. Code must be written to be read and understood by others — including researchers unfamiliar with the libraries used.

- **Module-level docstrings**: Every `.py` file explains its role in the architecture.
- **Class-level docstrings**: Every class explains its conceptual role in the social simulation.
- **Method docstrings**: Google style — one-line summary, Args, Returns, and a Note where the formula or design choice is non-obvious.
- **Inline comments**: Explain the *social science rationale*, not what the code mechanically does.
- **Section headers**: Use `# --- Section Name ---` banners to segment long functions.
- **Dash layouts**: Comment each major UI section with its purpose and which callback drives it.
- **Dash callbacks**: Document which data source and hypothesis each chart callback serves.

### 8.1 General

- **Python 3.12**. Type hints on all public function signatures.
- No debug `print()` statements in committed code. Use `logging`.

### 8.2 Mesa-Specific

- Use Mesa 3.x API: `AgentSet.shuffle_do()`, `mesa.space.NetworkGrid`, `Model(rng=seed)`.
- `DataCollector` is the only sanctioned way to collect simulation data.
- Keep `model.step()` thin — agent logic lives in agent methods.

### 8.3 Dash-Specific

- Use Dash Pages (`dash.register_page()`) for multi-page navigation.
- Use `dash-bootstrap-components` for layout and theming. Use a professional Bootstrap theme.
- All simulation state is managed server-side via module-level state or `dcc.Store`.
- Callbacks must be idempotent — safe to trigger on any input change.
- Use `dash-ag-grid` for interactive data tables with sorting, filtering, and row management.
- Dash callbacks call model and service functions directly via Python imports — no HTTP/REST layer.

### 8.4 Dash Callbacks and Visualization

- All interactivity is handled through Dash callbacks (`@callback`). No custom JavaScript.
- Plotly figures are created via `plotly.graph_objects` or `plotly.express` and rendered with `dcc.Graph`.
- Chart update functions must be idempotent — safe to call on every callback trigger.
- Use `dash.callback_context` to determine which input triggered a callback when multiple inputs exist.
- Reusable chart-building functions belong in `dash_app/components/`.

### 8.5 Testing

- Unit tests in `tests/`. Run with `pytest` from the project root inside the conda env.
- Test agent decision logic exhaustively — every branch of the self-serve vs. delegate decision.
- Test model-level conservation laws (total time budget, task counts).

---

## 9. Analysis and Documentation Standards

### 9.1 Hypothesis Testing

Each hypothesis (H1–H4) must be addressed with:
1. Hypothesis restatement (verbatim from master plan)
2. Experimental design (parameters varied, held constant, number of runs, steps)
3. Results (key metrics with axis labels and units)
4. Interpretation (written prose — do not let charts speak for themselves)
5. Limitations (caveats, untested ranges, model simplifications)

### 9.2 Sensitivity Analysis

Parameter sweep outputs must include a caption (axes + colour scale), a written paragraph on the most influential parameters, and explicit identification of any threshold or bifurcation point.

### 9.3 Scenario Comparison (Type A vs. Type B)

Must include: parameter table, empirical basis for preset values, metric comparison table with percentage differences, and a summary paragraph.

### 9.4 Summary Documentation

Every analytical run producing output files must have a markdown summary in `analysis/reports/YYYY-MM-DD_<description>.md` containing: date/config, key findings (3–7 bullets), figure references, conclusions, and next steps.

### 9.5 LLM-Assisted Interpretation

When Role 3 or Role 4 generates output, include a transparency note: model used, thinking mode, data context provided, and a human verification note.

---

## 10. Git Conventions

- **Branches**: `main` is the stable line for releases and public-facing history. Day-to-day development and debugging happen on **`develop`** (long-lived). Merge `develop` into `main` locally when a release-worthy snapshot is ready; **push to GitHub only when the repository owner explicitly requests it** (do not push unprompted).
- **On-Demand Commits**: Commit only when explicitly requested by the user.
- **Commit message format**: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`
- **Never commit**: `.env` files, API keys, large data files (>1MB), `data/results/` outputs.
- **Always verify** `git config user.name` and `git config user.email` before committing (repo-local config, not global).

---

## 11. Execution Records

At the completion of each phase, append a record to **`docs/execution_log.md`**.

Each phase record must include:
- Phase name and completion date
- Files created (with one-line descriptions)
- Test results (pass/fail counts)
- Key findings or technical decisions made during execution
- Any deviations from the plan and their rationale
- Status of remaining work (if paused mid-phase)

The execution log is the single source of truth for what has been built and what was discovered. `AGENTS.md` (this file) remains a concise charter only.

---

## 12. What NOT to Do

- **Do not** auto-advance to the next phase without the user's explicit instruction.
- **Do not** use external cloud LLM APIs unless explicitly instructed. Ollama is the primary runtime.
- **Do not** install packages into any conda environment other than `convenience-paradox`.
- **Do not** modify files in `docs/plans/` during execution.
- **Do not** reference any specific country, culture, or ethnicity anywhere in the project.
- **Do not** let LLM output directly control agent behaviour in standard simulation mode.
- **Do not** commit `data/results/` output files. They are gitignored.
- **Do not** exceed 3 turns in any agent forum exchange.
- **Do not** add `print()` debug statements to committed code.
