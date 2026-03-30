# The Convenience Paradox

### Agent-Based Modeling of Service Delegation and Social Involution

> *"Does optimising for individual convenience produce collective well-being — or collective exhaustion?"*

This model explores abstract social dynamics and is not intended to characterise or evaluate any specific society, culture, or nation.

---

## Contents

- [Overview](#overview)
- [Research question and hypotheses](#research-question)
- [Architecture](#architecture)
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

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│               Plotly Dash 4.x dashboard                      │
│  Simulation · LLM Studio · Run Manager · Analysis          │
│  dash_app/pages/ · dash_app/components/ · dash_app/assets/   │
└────────────────────────┬─────────────────────────────────────┘
                         │  Python callbacks (direct import)
          ┌──────────────┼──────────────┐
          │              │              │
┌─────────▼──────┐  ┌────▼──────────┐  ┌───▼───────────────────────┐
│ Mesa ABM core  │  │ LLM layer     │  │ Data layer                 │
│ (white-box)    │  │ (peripheral)  │  │ Pandas · SQLite            │
│ agents.py      │  │ llm_service.py│  │ dash_app/db.py             │
│ model.py       │  │ Ollama + Qwen │  └────────────────────────────┘
│ forums.py      │  └───────────────┘
└────────────────┘
```

### LLM integration (white-box principle)

The LLM sits **at the periphery** of the simulation. The ABM core remains a transparent, rule-based model. This follows the interpretability stance discussed by Vanhee et al. (arXiv:2507.05723).

| Role                            | Position                 | Description                                                 |
| ------------------------------- | ------------------------ | ----------------------------------------------------------- |
| **Role 1** — Scenario parser    | Input                    | Natural language → model parameters                         |
| **Role 2** — Profile generator  | Input                    | Text description → explicit agent attributes                |
| **Role 3** — Result interpreter | Output                   | Metrics + question → narrative explanation                  |
| **Role 4** — Viz annotator      | Output                   | Chart context → captions / insights                         |
| **Role 5** — Agent forums       | **Experimental** in-loop | Short norm dialogues; bounded preference updates            |

All structured LLM outputs are validated with Pydantic (`api/schemas.py`); calls are logged under `data/results/llm_logs/` (gitignored).

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
├── analysis/                 # Batch runs, sensitivity, plots, reports/
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
