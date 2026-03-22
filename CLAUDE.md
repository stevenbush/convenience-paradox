# CLAUDE.md — Agent Charter for The Convenience Paradox

This file defines the operating rules, conventions, and context for any AI agent working on this project. Read this file in full before taking any action.

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
| Phase 1 — Foundation | `docs/plans/01_phase1_foundation.md` | Complete |
| Phase 2 — Simulation Engine | `docs/plans/02_phase2_simulation.md` | Next |
| Phase 3 — Web Interface | `docs/plans/03_phase3_web_interface.md` | Pending |
| Phase 4 — LLM Integration | `docs/plans/04_phase4_llm_integration.md` | Pending |
| Phase 5 — Agent Forums | `docs/plans/05_phase5_agent_forums.md` | Pending |
| Phase 6 — Analysis & Portfolio | `docs/plans/06_phase6_analysis_portfolio.md` | Pending |

Master plan: `docs/plans/00_master_plan.md`

### 2.2 Pause Points

**Do not proceed to the next phase without explicit user instruction.** Each phase boundary is a pause point. When a phase is complete, report its deliverable and stop. Do not auto-advance.

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
Mesa 3.5.1 | Mesa-LLM 0.3.0 | Flask 3.1.3 | Plotly 6.6.0
Pandas 3.0.1 | Matplotlib 3.10.8 | Pydantic 2.12.5 | Ollama SDK 0.6.1
```

### 3.2 Local LLM

Ollama runs as a background service (`brew services start ollama`), served at `http://localhost:11434`.

| Model | Ollama Tag | Purpose |
|-------|-----------|---------|
| Qwen 3.5 4B (primary) | `qwen3.5:4b` | All production LLM tasks |
| Qwen 3 1.7B (lightweight) | `qwen3:1.7b` | Rapid iteration / batch generation |

**Qwen 3.5 4B has a thinking mode** that consumes tokens before producing output. Use `think=False` in `ollama.chat()` for structured JSON output (faster, cleaner). Use `think=True` (default) or omit for narrative interpretation tasks where reasoning quality matters.

```python
# Structured output -- disable thinking
ollama.chat(model="qwen3.5:4b", messages=[...], think=False,
            format=MyPydanticModel.model_json_schema())

# Narrative/interpretation -- allow thinking
ollama.chat(model="qwen3.5:4b", messages=[...], options={"num_predict": 512})
```

### 3.3 Hardware

MacBook Pro, M4 Pro chip, 24GB unified memory. No CUDA. Metal-accelerated inference via Ollama. All simulation runs are local — no cloud services required.

---

## 4. Project Architecture

```
convenience-paradox/
  model/          # Mesa ABM core (agents, model, params)
  api/            # Flask REST API and LLM service layer
  static/         # CSS and JavaScript (Plotly.js, chat widget)
  templates/      # Jinja2 HTML templates
  analysis/       # Batch runs, sensitivity analysis, matplotlib plots
  data/
    empirical/    # ILO, OECD, WVS stylized facts (CSV/JSON) — committed
    results/      # Simulation outputs — gitignored
  tests/          # Unit tests
  docs/
    plans/        # All execution plan documents
```

### 4.1 Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| ABM Engine | Mesa 3.5.x + Mesa-LLM 0.3.0 | Core simulation; run headlessly |
| LLM Runtime | Ollama + Qwen 3.5 4B | Local only; cloud is fallback via LiteLLM |
| Web Backend | Flask | REST API + Jinja2 templates |
| Visualization | Plotly.js (interactive) + matplotlib (publication) | |
| Data Layer | Pandas DataFrames + SQLite | DataCollector → DataFrames → API → JS |
| Frontend | Vanilla JS + Plotly.js + chat widget | No JS frameworks |

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
| `income` | float | Earnings from providing services to others |
| `is_service_provider` | bool | Whether agent accepts delegated tasks |

**Decision rules (all explicit, parameterized — no hidden LLM logic):**
1. Task generation: each step, agents receive tasks of varying complexity
2. Self-serve vs. delegate: based on `delegation_preference`, skill level, time budget, and service cost
3. Service acceptance: provider agents accept tasks → earn income but spend time
4. Stress accumulation: `available_time` below personal threshold → `stress_level` increases
5. Preference adaptation: `delegation_preference` shifts based on stress and peer behaviour (social conformity)

### 5.4 Model: `ConvenienceParadoxModel`

File: `model/model.py` — Mesa `Model` subclass.

**DataCollector metrics:**
- Agent-level: `available_time`, `stress_level`, `delegation_preference`, `income`, `tasks_completed_self`, `tasks_delegated`
- Model-level: `avg_stress`, `total_labor_hours`, `avg_delegation_rate`, `social_efficiency`, `gini_coefficient`

### 5.5 Parameter Presets

File: `model/params.py`

| Preset | Label | Key characteristics |
|--------|-------|---------------------|
| `TYPE_A_PRESET` | Autonomy-Oriented | Low delegation preference, moderate service cost, low conformity |
| `TYPE_B_PRESET` | Convenience-Oriented | High delegation preference, low service cost, high conformity |
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

File: `api/llm_service.py`. All Ollama calls go through this module. Never call `ollama` directly from `routes.py` or model code.

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

This project is a **Proof of Concept and learning/demonstration exercise**. Code must therefore be written to be read and understood by others — including researchers who may be unfamiliar with the specific libraries or techniques used. Apply the following commenting standards throughout:

**Module-level docstrings**: Every `.py` file begins with a module docstring explaining the file's role within the overall architecture and how it relates to the simulation design.

**Class-level docstrings**: Every class (especially `Resident`, `ConvenienceParadoxModel`) includes a docstring explaining its conceptual role in the model, not just its technical function. For agents, explain what the class represents in the social simulation.

**Method/function docstrings**: All public functions use Google-style docstrings with a one-line summary, an `Args` block, a `Returns` block, and a `Note` or `Design` section where the choice of algorithm or formula is non-obvious.

**Inline comments for model logic**: Agent decision rules, formula choices, and parameter interactions must be commented with the *social science rationale*, not just the mathematics. For example:
```python
# Agents with higher stress are more likely to delegate to save time,
# even if it costs more — modelling the "convenience trap" feedback loop.
delegation_boost = self.stress_level * self.conformity_sensitivity
```

**Section headers in long functions**: Use comment banners (`# --- Phase: Task Generation ---`) to segment the logical phases of complex step functions.

**JavaScript**: Every Plotly chart definition includes a comment explaining what the chart is intended to show in the context of the research hypotheses.

**HTML templates**: Comment each major UI section with its purpose and which Flask endpoint or JS function drives it.

### 8.1 General

- **Python 3.12**. Type hints on all public function signatures.
- **Docstrings** on all public classes and methods (Google style: one-line summary, Args, Returns).
- Inline comments explain *why* (social science rationale, formula derivation, design trade-offs), not *what* the code mechanically does.
- No debug `print()` statements in committed code. Use `logging` if runtime output is needed.

### 8.2 Mesa-Specific

- Use Mesa 3.x API. The agent scheduling API changed from 2.x — use `AgentSet`, not the old `Scheduler` classes.
- `DataCollector` is the only sanctioned way to collect simulation data. Do not accumulate data in model-level lists.
- Keep `model.step()` thin — agent logic lives in `agent.step()`.

### 8.3 Flask-Specific

- All API responses are JSON. Use `flask.jsonify()`.
- Use the application factory pattern (`create_app()` in `api/app.py`).
- All simulation state is managed server-side. The frontend is stateless.
- Endpoints follow REST conventions: `POST /api/simulation/init`, `POST /api/simulation/step`, etc.

### 8.4 JavaScript

- Vanilla JS only. No frameworks (no React, Vue, etc.).
- Plotly.js for all charts. Do not use D3.js directly.
- Chart update functions must be idempotent — safe to call on every data refresh.

### 8.5 Testing

- Unit tests in `tests/`. Run with `pytest` from the project root inside the conda env.
- Test agent decision logic exhaustively — every branch of the self-serve vs. delegate decision.
- Test model-level conservation laws (total time budget, task counts).

---

## 9. Analysis and Documentation Standards

This section governs all hypothesis testing, experimental analysis, and results documentation. Because this is a POC and demonstration project, every analytical output must stand alone as a readable, self-explanatory artefact.

### 9.1 Hypothesis Testing

Each hypothesis (H1–H4) must be addressed with a dedicated analysis block containing:

1. **Hypothesis restatement**: Quote the hypothesis verbatim from the master plan.
2. **Experimental design**: Describe which parameters were varied, what was held constant, the number of runs, and the number of simulation steps per run.
3. **Results**: Present the key metrics (tables or plots) with axis labels and units.
4. **Interpretation**: Written prose explaining what the data shows and whether it supports or refutes the hypothesis. Do not let charts speak for themselves.
5. **Limitations**: Note any caveats — e.g., sensitivity to initial conditions, parameter ranges not tested, model simplifications that may affect the conclusion.

### 9.2 Sensitivity Analysis

Parameter sweep outputs (heatmaps, phase diagrams) must include:

- A caption explaining the axes and colour scale in plain language.
- A written paragraph identifying the most influential parameters and the direction of their effect.
- Explicit identification of any threshold or bifurcation point observed (e.g., the involution threshold for H2).

### 9.3 Scenario Comparison (Type A vs. Type B)

Side-by-side comparisons must include:

- A parameter table showing the exact values used for each preset.
- An explanation of how those values were informed by empirical stylised facts (ILO, OECD, WVS).
- Metric comparison tables with percentage differences, not just raw values.
- A summary paragraph: what does this comparison reveal about the model's behaviour and the underlying social mechanism?

### 9.4 Summary Documentation

Every experimental run or analysis that produces output files must be accompanied by a markdown summary document saved to `analysis/reports/`. The document must include:

- **Date and run configuration** (random seed, parameter values, steps, num agents)
- **Key findings** in bullet-point form (3–7 bullets)
- **Figures** referenced by filename with captions
- **Conclusions** — what this run tells us about the research question
- **Next steps** — what question this analysis raises or what experiment to run next

File naming convention: `analysis/reports/YYYY-MM-DD_<short-description>.md`

### 9.5 LLM-Assisted Interpretation Documentation

When Role 3 (Result Interpreter) or Role 4 (Visualization Annotator) is used to generate narrative explanations, include a transparency note alongside each output:

- The LLM model used and whether thinking mode was enabled
- The data context window provided to the LLM (which metrics, which time range)
- A brief human verification note confirming the narrative is consistent with the rule-based simulation logs

This demonstrates responsible use of LLM in the ABM cycle, consistent with Vanhée et al. (2507.05723).

---

## 10. Git Conventions

- **Commit often** — at minimum after completing each named task in the phase plan.
- **Commit message format**:
  - `feat:` new feature or capability
  - `fix:` bug fix
  - `chore:` setup, config, tooling
  - `docs:` documentation only
  - `test:` adding or fixing tests
  - `refactor:` code restructure without behaviour change
- **Never commit**: `.env` files, API keys, large data files (>1MB), `data/results/` outputs.
- **Always verify** `git config user.name` and `git config user.email` are set correctly before committing (repo-local config, not global).

---

## 11. What NOT to Do

- **Do not** auto-advance to the next phase without the user's explicit instruction.
- **Do not** use external cloud LLM APIs unless explicitly instructed. Ollama is the primary runtime.
- **Do not** install packages into any conda environment other than `convenience-paradox`.
- **Do not** modify files in `docs/plans/` during execution.
- **Do not** reference any specific country, culture, or ethnicity anywhere in the project.
- **Do not** let LLM output directly control agent behaviour in standard simulation mode.
- **Do not** commit `data/results/` output files. They are gitignored.
- **Do not** exceed 3 turns in any agent forum exchange.
- **Do not** add `print()` debug statements to committed code.
