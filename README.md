# The Convenience Paradox

### Agent-Based Modeling of Service Delegation and Social Involution

> *"Does optimising for individual convenience produce collective well-being — or collective exhaustion?"*

This model explores abstract social dynamics and is not intended to characterise or evaluate any specific society, culture, or nation.

---

## Contents

- [Overview](#overview)
- [User interface demonstration](#user-interface-demonstration)
- [Architecture](#architecture)
- [Research question and hypotheses](#research-question)
- [Simulation model](#simulation-model)
- [Features](#features)
- [Setup and running](#setup-and-running)
- [Testing](#testing)
- [Repository layout](#repository-layout)
- [Empirical grounding](#empirical-grounding)
- [Reflections on ABM and LLM](#reflections-on-abm-and-llm-for-social-systems)
- [Citation and license](#citation)

---

## Overview

**The Convenience Paradox** is a computational social science project that uses **Agent-Based Modeling (ABM)** to investigate whether widespread service delegation (outsourcing daily tasks to third-party providers) produces a systemic paradox: greater convenience for individuals, but greater total labour and growing inequality at the system level — an **involution spiral**.

The project is built as a full-stack interactive research tool:

| Layer            | Technology                                          |
| ---------------- | --------------------------------------------------- |
| ABM Engine       | Mesa 3.5.x + Mesa-LLM 0.3.0                         |
| Local LLM        | Ollama + Qwen 3.5 4B                                |
| Web dashboard    | Plotly Dash 4.x + dash-bootstrap-components + dash-ag-grid |
| Visualisation    | Plotly (interactive) + Matplotlib (publication)     |
| Run history      | SQLite (`runs.db`, via `dash_app/db.py`)            |
| Environment      | Python 3.12, Miniconda3                             |

**Neutrality notice**: The model is parameterized in abstract terms only. It does not characterise, evaluate, or make claims about any specific country, culture, or people. “Type A” and “Type B” are purely abstract configuration presets.

---

## User interface demonstration

The dashboard is a four-page interactive research tool. Each page is described below, with a placeholder for a demo animation.

### Simulation Dashboard

The primary page for running and monitoring ABM simulations in real time.

<!-- 📽️ GIF placeholder — record: select a preset, click Initialize, step through 30+ steps, show KPI cards updating and charts animating -->
![Simulation Dashboard Demo](docs/assets/gifs/simulation-dashboard.gif)

**What you can do:**

- **Preset selector** — switch between *Type A (Autonomy-Oriented)* and *Type B (Convenience-Oriented)* configurations, or dial in a custom scenario with 11 parameter sliders (delegation mean, service cost, conformity pressure, task load, population size, and more).
- **Live KPI bar** — four summary cards (Avg Stress, Total Labor Hours, Social Efficiency, Income Gini) update after every simulation step.
- **10 interactive Plotly charts** covering all four research hypotheses:
  - *Total Labor Hours* time series — the primary involution signal (H1).
  - *Stress & Delegation* dual-axis trend — tracks the convenience-spiral dynamic (H2/H3).
  - *Stress Distribution* histogram + *Delegation Preferences* distribution — reveals polarisation drift (H4).
  - *Social Efficiency* trend + *Market Health* bar/line (unmatched tasks) — exposes the delegation threshold (H2).
  - *Provider vs Consumer* scatter with stress colour encoding — shows role stratification emerging live.
- **Advanced flow and topology views** — Task Flow Sankey (service pipeline per step), Fee Flow Waterfall (economic transfers), and a force-directed Network Topology where node size encodes hours spent providing services and node colour encodes stress.

---

### LLM Studio

A unified interface for all five LLM roles. Each role has an independent model selector (populated from the live Ollama instance) and its own input/output panel. Every interaction is logged to the session audit trail.

<!-- 📽️ GIF placeholder — record: cycle through all 5 role tabs, show a Scenario Parser run and the resulting params being applied, then a brief Agent Forums exchange -->
![LLM Studio Demo](docs/assets/gifs/llm-studio.gif)

| Role | Name | What it does |
| ---- | ---- | ------------ |
| **Role 1** | Scenario Parser | Paste a natural-language society description → LLM extracts five `SimulationParams` (delegation mean, service cost, conformity, tasks per step, population) → one-click apply to the Simulation Dashboard. |
| **Role 2** | Profile Generator | Describe an agent persona in plain text → LLM generates a `delegation_preference` value and four skill scores (domestic, administrative, errand, maintenance) → inspectable JSON before injection. |
| **Role 3** | Result Interpreter | Ask any research question → LLM receives six live simulation metrics and six parameter values as context → returns a narrative explanation referenced to the active hypothesis. |
| **Role 4** | Viz Annotator | Supplies the current chart's data context → LLM generates a chart caption and three key quantitative insights. |
| **Role 5** | Agent Forums *(Experimental)* | Select a participant cohort → up to three LLM dialogue turns on delegation norms → bounded preference update of ±0.06 max per agent → visible in the next simulation step. Clearly labelled as experimental in the UI. |

All structured outputs are validated against Pydantic v2 schemas before use. The **Session Audit Log** tab records every prompt, raw response, parsed result, and timestamp for full transparency.

---

### Run Manager

An experiment database with query, comparison, and deletion capabilities, powered by Dash AG Grid.

<!-- 📽️ GIF placeholder — record: show the AG Grid table, apply a preset filter, select two runs, choose a metric, click Compare, show the overlay trend chart -->
![Run Manager Demo](docs/assets/gifs/run-manager.gif)

**What you can do:**

- **Interactive AG Grid table** — sortable and filterable columns: run name, preset, agent count, steps, delegation rate, avg stress, income Gini, and timestamp.
- **Filter bar** — free-text search by run name, preset dropdown (Type A / Type B / Custom), and a date-range picker.
- **Save & delete** — name and save the current simulation run; delete selected rows with cascade to the step-level metrics table.
- **Side-by-side comparison** — select up to 6 runs, choose one metric, and click *Compare* to render a summary KPI card per run alongside an aligned trend chart overlay for time-series comparison across runs.

---

### Analysis

Research results presentation with a hypothesis scoreboard, automated A/B comparison, and an on-demand parameter sensitivity heatmap.

<!-- 📽️ GIF placeholder — record: show the 4 hypothesis cards with expandable panels, click “Run Both Presets”, show the comparison table and bar chart populating, then trigger the sensitivity heatmap -->
![Analysis Page Demo](docs/assets/gifs/analysis.gif)

**What you can do:**

- **Hypothesis scoreboard** — four cards (H1–H4), each with a status badge (*Confirmed* / *Supported* / *Partial*) and an expandable evidence panel quoting the key finding from batch experiments.
- **Type A vs Type B comparison** — one click runs both presets back-to-back server-side, then populates a six-metric comparison table (with percentage differences) and a grouped bar chart.
- **Sensitivity heatmap** — on-demand 5×5 parameter sweep across delegation mean (0.2–0.8) × service cost factor (0.1–0.8); rendered as an interactive Plotly heatmap with hover tooltips showing the exact metric value at each grid point.

---

## Architecture

The project is structured in three clearly separated layers — ABM core, LLM periphery, and data — unified by a Plotly Dash multi-page web application. Dash callbacks call simulation and service code directly via Python imports; no REST layer is involved.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      Plotly Dash 4.x  (multi-page SPA)                        │
│                                                                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  Simulation     │  │   LLM Studio    │  │ Run Manager  │  │  Analysis  │  │
│  │  Dashboard      │  │   (5 Roles)     │  │              │  │            │  │
│  └─────────────────┘  └─────────────────┘  └──────────────┘  └────────────┘  │
│                                                                                │
│  dash-bootstrap-components  (layout · grid · theming)                         │
│  dash-ag-grid  (interactive run-history table)                                 │
│  Plotly graph_objects / express  (10+ chart types: line, histogram, Sankey,   │
│    waterfall, scatter, heatmap, network, radar …)                              │
└───────────────────────────────┬────────────────────────────────────────────── ┘
                                │  Python callbacks — direct import, no HTTP
           ┌────────────────────┼─────────────────────┐
           │                    │                     │
┌──────────▼───────────┐  ┌─────▼──────────────┐  ┌──▼────────────────────────┐
│   Mesa ABM Core       │  │   LLM Layer        │  │   Data Layer               │
│   (white-box rules)   │  │   (peripheral)     │  │                            │
│                       │  │                    │  │  Pandas DataFrames         │
│   model/agents.py     │  │  api/llm_service.py│  │  SQLite  (runs.db)         │
│   model/model.py      │  │  api/schemas.py    │  │  dash_app/db.py            │
│   model/forums.py     │  │   (Pydantic v2)    │  │  Mesa DataCollector →      │
│   model/params.py     │  │                    │  │   DataFrames → callbacks   │
│                       │  │  Ollama runtime    │  │                            │
│   Mesa 3.5.x          │  │  Qwen 3.5 4B /     │  │                            │
│   Mesa-LLM 0.3.0      │  │  Qwen 3 1.7B       │  │                            │
│   NetworkX            │  │  (local, Metal)    │  │                            │
└───────────────────────┘  └────────────────────┘  └────────────────────────────┘
```

### Component summary

| Layer | Library / Tool | Role |
| ----- | -------------- | ---- |
| Web framework | Plotly Dash 4.x + Dash Pages | Multi-page SPA routing, callback system |
| UI components | dash-bootstrap-components | Responsive grid, cards, modals, badges |
| Data table | dash-ag-grid | Sortable, filterable run-history grid |
| Charts | Plotly `graph_objects` / `express` | All interactive figures (line, histogram, Sankey, waterfall, scatter, heatmap, network, radar) |
| ABM engine | Mesa 3.5.x + Mesa-LLM 0.3.0 | Rule-based agent simulation; `AgentSet`, `DataCollector`, `NetworkGrid` |
| Social network | NetworkX | Watts–Strogatz small-world graph (k=4, p=0.1) |
| LLM runtime | Ollama + Qwen 3.5 4B | Local inference; Metal-accelerated on Apple Silicon |
| Schema validation | Pydantic v2 | Structured LLM output contracts (`api/schemas.py`) |
| Persistence | SQLite via `dash_app/db.py` | Run history, step-level metrics |
| Analysis | Pandas 3.x + Matplotlib 3.x | Batch processing, publication figures |

---

## Research question

> *How do different levels of service delegation in a society affect individual well-being (leisure time, stress) and collective efficiency? Under what conditions does a "convenience spiral" (involution) emerge?*

### Hypotheses

|        | Hypothesis                                                              | Status                                                                       |
| ------ | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **H1** | Higher delegation leads to higher total systemic labour hours           | Confirmed (60-step runs: +22% labour hours in Type B)                        |
| **H2** | A critical delegation threshold triggers irreversible involution spiral | Supported in part (efficiency plateau visible; cascade requires 200+ steps)   |
| **H3** | Higher autonomy achieves lower stress and higher aggregate well-being   | Long-run phenomenon — requires 100+ steps for stress divergence to emerge  |
| **H4** | Mixed-delegation societies are unstable, drifting toward one extreme    | Partially supported — network conformity drives polarisation                 |

### Key empirical finding (batch runs)

In 60-step batch runs (5 replications each):

```
                         Type A (Autonomy)    Type B (Convenience)
Delegation Rate          0.265 ± 0.012        0.718 ± 0.007
Total Labour Hours       395 ± 5.9            482 ± 11.3       (+22%)
Social Efficiency        0.549 ± 0.008        0.576 ± 0.011
Income Gini              0.147 ± 0.026        0.243 ± 0.024    (+65%)
```

**H1**: Type B configurations generate about 22% more total labour hours — the involution pattern in quantitative form. **H3** stress divergence is a long-run emergent effect: short runs can understate systemic overhead, which motivates sensitivity analysis over run length.

---

## Simulation model

### Agent: `Resident`

- `available_time` — daily discretionary hours (reset each step)
- `delegation_preference` — tendency to delegate \([0, 1]\)
- `stress_level` — accumulates when time runs out \([0, 1]\)
- `skill_set` — proficiency in task types (affects time cost)
- `income` — net from providing services vs. paying for delegation

### Decision rule (per task)

```
If available_time < threshold → force delegate (survival choice)
Else: delegate ← Bernoulli(delegation_preference × stress_boost × cost_penalty)
```

### Preference adaptation (social conformity)

```
Δpreference = adaptation_rate × conformity_pressure × (neighbour_mean − own_preference)
```

### Environment

- **Network**: Watts–Strogatz small-world (k=4, p=0.1)
- **Service matching**: greedy pool matching; unmatched tasks contribute to stress
- **Metrics**: 9 model-level and 7 agent-level series via Mesa `DataCollector`

---

## Features

### Interactive dashboard

Four pages (Dash Pages + sidebar navigation):

- **Simulation** — Type A / Type B presets, live time series, distributions, Sankey / waterfall flows, network view, skill radar
- **LLM Studio** — per-role model choice, scenario parser, interpreter, profile generator, chart annotator, agent forums, audit trail
- **Run Manager** — AG Grid history, filter/delete, side-by-side comparison
- **Analysis** — hypothesis scoreboard, A/B runner, sensitivity heatmap

### LLM-enhanced interface (optional Ollama)

Requires a local Ollama service and pulled models (e.g. `qwen3.5:4b`, `qwen3:1.7b`). Without Ollama, the rule-based simulation and dashboard still run; LLM actions surface clear errors rather than failing silently.

### Experimental: agent communication forums

Brief LLM-driven norm discussions can apply a small bounded update (±0.06 max) to participants’ delegation preferences. The UI labels this mode as experimental; at small model sizes, dialogue quality can plateau quickly.

---

## Setup and running

### Requirements

- macOS (tested on Apple Silicon) or Linux
- [Miniconda3](https://docs.conda.io/en/latest/miniconda.html) or compatible `conda`
- [Ollama](https://ollama.com) — optional, for LLM features

### Quick start

```bash
git clone https://github.com/stevenbush/convenience-paradox.git
cd convenience-paradox

conda env create -f environment.yml
conda activate convenience-paradox

# Optional: LLM models (after `ollama serve` or brew services)
ollama pull qwen3.5:4b
ollama pull qwen3:1.7b

# From the repository root (so `model`, `api`, and `dash_app` resolve):
python -m dash_app
# → http://127.0.0.1:8050
```

CLI options: `python -m dash_app --help` (`--port`, `--host`, `--debug`).

### One-command setup (optional)

From the repository root:

```bash
bash scripts/setup.sh
```

Creates or updates the conda environment, sanity-checks imports, optionally probes Ollama, and runs the offline test suite.

### Pip-only install

If you prefer `venv` + pip:

```bash
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m dash_app
```

---

## Testing

```bash
# Default: offline-safe (Ollama-marked tests are skipped unless selected)
pytest tests/ -v -k "not ollama"

# Live LLM checks (Ollama running, models available)
pytest tests/test_llm_service.py -m ollama -v
```

Pytest configuration and custom marks live in `tests/conftest.py`.

---

## Narrative analysis campaigns

For sequel-blog and report-oriented experiment bundles, use the narrative
campaign runner:

```bash
# Fast validation run
python -m analysis.narrative_campaign --scale smoke --packages package_a_everyday_friction --skip-report

# Full campaign using the local machine's capped default worker pool (8)
python -m analysis.narrative_campaign --scale full --workers 8 --tag blog_pack
```

Outputs are written under `data/results/campaigns/<timestamp>_<tag>/` with:

- `manifest.json` for reproducibility metadata
- package folders containing `research_summary.csv`, `blog_numbers.json`, and `figure_manifest.json`
- `writing_support/` markdown assets such as the question-to-evidence crosswalk and claim-safety table

---

## Repository layout

```
convenience-paradox/
├── LICENSE
├── README.md
├── AGENTS.md / CLAUDE.md     # AI-assistant charters (tooling); not runtime deps
├── environment.yml           # Conda env (recommended)
├── requirements.txt          # Pip mirror of core dependencies
├── scripts/
│   └── setup.sh              # Optional one-step environment + smoke tests
├── model/                    # Mesa ABM: agents, model, params, forums
├── api/                      # LLM service, audit, Pydantic schemas
├── dash_app/                 # Dash app factory, pages, components, assets, db
│   └── __main__.py           # `python -m dash_app` entry point
├── analysis/                 # Batch runs, narrative campaigns, plots, reports/
├── data/
│   ├── empirical/            # Stylized facts (ILO, OECD, WVS, …) — committed
│   └── results/              # Outputs & llm_logs — gitignored
├── tests/                    # Unit + Dash shell tests; conftest.py
└── docs/
    ├── plans/                # Phase plans (reference; do not edit in execution)
    └── execution_log.md      # Build history
```

The legacy Flask-era `static/` and `templates/` trees were removed; styling and scripts live under `dash_app/assets/` and Dash components.

---

## Empirical grounding

This is an **empirically informed theoretical model**, not a calibrated predictive model. Public datasets inform plausible parameter ranges, not fitting to observed outcomes.

| Dataset                       | Role in the project                                              |
| ----------------------------- | ---------------------------------------------------------------- |
| ILO Working Hours             | Informs `available_time` ranges                                  |
| World Values Survey           | Informs delegation / conformity-style parameters                 |
| OECD Better Life Index        | Qualitative stress / well-being references                       |
| World Bank Service Employment | Context for service-sector framing                               |

Stylized inputs live in `data/empirical/`. References use dataset names only, not regional labels.

---

## Reflections on ABM and LLM for social systems

### White-box vs. black-box

The **core ABM** is fully rule-based so choices can be traced. **Roles 1–4** assist interpretation and configuration without driving agent logic. **Agent forums** (Role 5) introduce a small, bounded LLM influence *inside* the run, clearly separated in the UI from standard mode.

### The involution finding

High-delegation configurations do not necessarily show higher stress in **short** windows — convenience can “work” locally — while total labour and inequality metrics move in ways consistent with H1. Longer horizons matter for stress and efficiency dynamics; that is a methodological takeaway for ABM design.

---

## Citation

If you use this project in academic work:

```
Shi, J. (2026). The Convenience Paradox: Agent-Based Modeling of
Service Delegation and Social Involution. GitHub portfolio project.
https://github.com/stevenbush/convenience-paradox
```

## License

MIT License — see [LICENSE](LICENSE).

The empirical material under `data/empirical/` is derived from public sources (ILO, OECD, WVS, World Bank, etc.); check each file or source note for the applicable reuse terms (e.g. CC BY 4.0 where stated).
