# The Convenience Paradox

### Agent-Based Modeling of Service Delegation and Social Involution

> *"Does optimising for individual convenience produce collective well-being — or collective exhaustion?"*

---

## Overview

**The Convenience Paradox** is a computational social science project that uses **Agent-Based Modeling (ABM)** to investigate whether widespread service delegation (outsourcing daily tasks to third-party providers) produces a systemic paradox: greater convenience for individuals, but greater total labour and growing inequality at the system level — an **involution spiral**.

The project is built as a full-stack interactive research tool:


| Layer            | Technology                                         |
| ---------------- | -------------------------------------------------- |
| ABM Engine       | Mesa 3.5.x                                         |
| Local LLM        | Ollama + Qwen 3.5 4B                               |
| Web Backend      | Flask REST API                                     |
| Visualisation    | Plotly.js (interactive) + Matplotlib (publication) |
| Data Persistence | SQLite                                             |
| Environment      | Python 3.12, Miniconda3                            |


> **Neutrality notice**: This model explores abstract social dynamics in terms of configurable parameters. It does not characterise, evaluate, or make claims about any specific country, culture, or people. "Type A" and "Type B" are purely abstract parameter configurations.

---

## Research Question

> *How do different levels of service delegation in a society affect individual well-being (leisure time, stress) and collective efficiency? Under what conditions does a "convenience spiral" (involution) emerge?*

### Hypotheses


|        | Hypothesis                                                              | Status                                                                       |
| ------ | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **H1** | Higher delegation leads to higher total systemic labour hours           | ✅ Confirmed (60-step runs: +22% labour hours in Type B)                      |
| **H2** | A critical delegation threshold triggers irreversible involution spiral | 🔶 Supported (efficiency plateau visible; cascade requires 200+ steps)       |
| **H3** | Higher autonomy achieves lower stress and higher aggregate well-being   | 🔶 Long-run phenomenon — requires 100+ steps for stress divergence to emerge |
| **H4** | Mixed-delegation societies are unstable, drifting toward one extreme    | 🔶 Partially supported — network conformity drives polarisation              |


### Key Empirical Finding

In 60-step batch runs (5 replications each):

```
                         Type A (Autonomy)    Type B (Convenience)
Delegation Rate          0.265 ± 0.012        0.718 ± 0.007
Total Labour Hours       395 ± 5.9            482 ± 11.3       (+22%)
Social Efficiency        0.549 ± 0.008        0.576 ± 0.011
Income Gini              0.147 ± 0.026        0.243 ± 0.024    (+65%)
```

**H1 is confirmed**: Type B societies generate 22% more total labour hours — the involution paradox in quantitative form. H3's stress divergence is a long-run emergent phenomenon not visible in short runs, which is itself a methodologically important finding: convenience reduces short-run stress while building systemic overhead that drives long-run involution.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                 Frontend (Flask Templates + JS)               │
│  Dashboard · Plotly.js Charts · LLM Chat · Parameter Sliders │
└───────────────────────┬──────────────────────────────────────┘
                        │  HTTP / JSON
┌───────────────────────▼──────────────────────────────────────┐
│                    Flask REST API                             │
│  /api/simulation/* · /api/llm/* · /api/runs/*                │
└───────┬───────────────────────────────────┬──────────────────┘
        │                                   │
┌───────▼────────────┐          ┌───────────▼──────────────────┐
│  Mesa ABM Engine   │          │   LLM Service Layer           │
│  (White-box core)  │          │   (Peripheral roles 1–4)      │
│  agents.py         │          │   llm_service.py              │
│  model.py          │          │   Ollama + Qwen 3.5 4B        │
│  forums.py (exp.)  │          └───────────────────────────────┘
└────────────────────┘
        │
┌───────▼────────────┐
│  Data Layer        │
│  Pandas DataFrames │
│  SQLite (runs.db)  │
└────────────────────┘
```

### LLM Integration (White-Box Principle)

The LLM operates **at the periphery** of the simulation. The ABM core is a transparent, rule-based white box. This implements the interpretability position articulated by Vanhee et al. (2507.05723).


| Role                            | Position                 | Description                                                 |
| ------------------------------- | ------------------------ | ----------------------------------------------------------- |
| **Role 1** — Scenario Parser    | Input layer              | Natural language → model parameters                         |
| **Role 2** — Profile Generator  | Input layer              | Demographic text → agent attributes                         |
| **Role 3** — Result Interpreter | Output layer             | Data + question → narrative explanation                     |
| **Role 4** — Viz Annotator      | Output layer             | Chart metrics → auto-generated captions                     |
| **Role 5** — Agent Forums       | **Experimental** in-loop | Agents discuss delegation norms; small bounded norm updates |


---

## Simulation Model

### Agent: `Resident`

Each resident agent holds:

- `available_time` — daily discretionary hours budget (reset each step)
- `delegation_preference` — probability of delegating a task [0, 1]
- `stress_level` — accumulated when time runs out [0, 1]
- `skill_set` — proficiency in 4 task types (determines time cost)
- `income` — earnings from providing services to others

### Decision Rule (per task)

```
If available_time < threshold → force delegate (survival choice)
Else: delegate ← Bernoulli(delegation_preference × stress_boost × cost_penalty)
```

### Preference Adaptation (Social Conformity)

Each step, agents update their delegation preference toward their network neighbours' mean:

```
Δpreference = adaptation_rate × conformity_pressure × (neighbour_mean − own_preference)
```

This produces **norm convergence dynamics** — the mechanism behind H4.

### Environment

- **Network**: Watts-Strogatz small-world graph (k=4, p=0.1) — realistic social influence structure
- **Service matching**: delegates are matched to providers in the network; unmatched tasks → stress
- **Metrics collected**: 9 model-level (avg_stress, total_labor_hours, social_efficiency, gini_income, ...) and 7 agent-level metrics

---

## Features

### Interactive Dashboard

- **Preset buttons**: Type A (Autonomy-Oriented) and Type B (Convenience-Oriented)
- **5 parameter sliders**: delegation preference, service cost, conformity pressure, task load, population
- **6 Plotly.js charts**: time-series, labour hours, efficiency, stress distribution, delegation distribution, Gini
- **Run history**: saved runs from SQLite, overlay on current charts for comparison

### LLM-Enhanced Interface (requires Ollama)

- **Chat panel**: ask questions about the results; the LLM provides grounded narrative explanations
- **Scenario parser**: describe a society in plain English → parameters are auto-extracted
- **Chart annotations**: after each run, key insights are auto-generated for each chart
- **Profile generator**: describe a demographic type → numerical agent attributes (with audit log)

### Experimental: Agent Communication Forums

Agents discuss delegation norms in brief LLM-driven dialogues. Norm signals from dialogues apply a small bounded update (±0.06 max) to participating agents' delegation preferences. The dashboard shows the full dialogue audit trail.

> ⚠️ This feature is clearly labelled experimental. At 1B–4B parameter scale, agents may sound similar and dialogue can become repetitive after 2–3 exchanges. This limitation is documented as an honest acknowledgment of the white-box vs. black-box trade-off.

---

## Setup

### Requirements

- macOS (tested on M4 Pro, 24 GB RAM) or Linux
- [Miniconda3](https://docs.conda.io/en/latest/miniconda.html)
- [Ollama](https://ollama.com) (for LLM features)

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/stevenbush/convenience-paradox.git
cd convenience-paradox

# 2. Create and activate the conda environment
conda env create -f environment.yml
conda activate convenience-paradox

# 3. (Optional) Start Ollama and pull the LLM model
ollama serve &
ollama pull qwen3.5:4b
ollama pull qwen3:1.7b   # lightweight secondary model

# 4. Run the dashboard
python run.py
# → Open http://127.0.0.1:5000 in your browser
```

### Manual Dependency Install

```bash
conda create -n convenience-paradox python=3.12 -y
conda activate convenience-paradox
pip install mesa==3.5.* mesa-llm==0.3.* flask plotly pandas matplotlib \
            pydantic ollama scipy networkx
```

### Running Tests

```bash
# All unit and integration tests (no Ollama required)
pytest tests/ -v -k "not ollama"

# Live LLM integration tests (Ollama must be running)
pytest tests/test_llm_service.py -m ollama -v
```

---

## Project Structure

```
convenience-paradox/
├── README.md
├── run.py                    # Flask entry point
├── environment.yml           # Conda environment spec
├── requirements.txt          # pip requirements
├── setup.sh                  # One-step setup script
├── CLAUDE.md                 # AI assistant charter
├── model/
│   ├── agents.py             # Resident agent class
│   ├── model.py              # ConvenienceParadoxModel
│   ├── params.py             # Type A / Type B presets, parameter metadata
│   └── forums.py             # Agent Communication Forums (Phase 5 experimental)
├── api/
│   ├── app.py                # Flask application factory
│   ├── routes.py             # REST API endpoints (simulation + forums)
│   ├── llm_service.py        # Ollama integration (Roles 1–4)
│   ├── llm_routes.py         # Flask LLM endpoints
│   └── schemas.py            # Pydantic schemas for validation
├── static/
│   ├── css/style.css         # Dashboard stylesheet
│   └── js/
│       ├── dashboard.js      # Plotly.js charts, controls, data fetching
│       └── chat.js           # LLM chat widget
├── templates/
│   └── index.html            # Single-page dashboard
├── analysis/
│   ├── batch_runs.py         # Parameter sweep scripts (H1–H4)
│   ├── sensitivity.py        # Sensitivity analysis, heatmaps
│   ├── plots.py              # Matplotlib publication-quality plots
│   └── reports/              # Markdown analysis reports
├── data/
│   ├── empirical/            # Stylized facts (ILO, OECD, WVS, World Bank)
│   └── results/              # Saved plots and simulation outputs
├── tests/
│   ├── test_agents.py        # Agent unit tests (22 tests)
│   ├── test_model.py         # Model integration tests (37 tests)
│   └── test_llm_service.py   # LLM service tests (21 + 3 live)
└── docs/
    ├── plans/                # Phase execution plans (00–06)
    └── execution_log.md      # Detailed record of what was built
```

---

## Empirical Grounding

This is an **Empirically Informed Theoretical Model** — not a calibrated predictive model. Real-world data is used to inform plausible parameter ranges, not to calibrate the model to fit specific outcomes.


| Dataset                       | Role                                                             |
| ----------------------------- | ---------------------------------------------------------------- |
| ILO Working Hours             | Informs `available_time` ranges                                  |
| World Values Survey           | Informs `delegation_preference` and `social_conformity_pressure` |
| OECD Better Life Index        | Qualitative validation reference for stress outcomes             |
| World Bank Service Employment | Contextualises delegation dynamics                               |


All stylized facts are committed to `data/empirical/`. Sources are referenced by dataset name only; regional breakdowns are aggregated into abstract categories.

---

## Reflections on ABM and LLM for Social Systems

### White-Box vs. Black-Box

A central question in computational social science is: **should the agents in our model be rule-based (transparent, interpretable) or LLM-driven (richer, but opaque)?**

This project deliberately explores both positions:

- The **core ABM** is rule-based — every decision is an explicit equation. This preserves interpretability: we can trace why any agent made any choice.
- **LLM roles 1–4** enhance the interface without touching the simulation logic. The LLM helps users interact with the model, but does not drive agent behaviour.
- **Agent forums** (experimental) insert a small, bounded LLM influence *into* the simulation. The dashboard shows both modes side-by-side, making the difference visible and auditable.

This architecture implements the position argued by Vanhee et al. (2507.05723, Gurcan et al.): LLMs are best used as *social context providers* at the periphery, not as the decision engine of the agents themselves.

### The Involution Finding

The most unexpected result from the simulations is that **Type B societies (high delegation) do not show higher stress in the short run** — they actually show lower stress. Convenience works. But total labour hours are systematically higher (H1 confirmed), and income inequality grows (Gini +65%). The stress divergence (H3) is a long-run emergent property, requiring time for the service economy overhead to compound into capacity saturation.

This has a methodological implication: short simulation runs can **mislead**. The involution paradox is invisible at 30 steps and visible at 150+. This is why sensitivity analysis across run lengths is critical for ABM validation.

---

## Citation

If you use this project for academic work, please cite:

```
Shi, J. (2026). The Convenience Paradox: Agent-Based Modeling of
Service Delegation and Social Involution. GitHub portfolio project.
https://github.com/stevenbush/convenience-paradox
```

---

## License

MIT License. See LICENSE for details.

The empirical data in `data/empirical/` is derived from:

- ILO Statistics (CC BY 4.0)
- OECD Better Life Index (CC BY 4.0)
- World Values Survey (free for academic use)
- World Bank Open Data (CC BY 4.0)

---

*This model explores abstract social dynamics and is not intended to characterise or evaluate any specific society, culture, or people.*