# The Convenience Paradox -- Master Execution Plan

**Full Title**: *"The Convenience Paradox: Agent-Based Modeling of Service Delegation and Social Involution"*

**Scenario**: Service Convenience vs. Autonomy ("Involution Dynamics")

**Environment**: MacBook Pro M4 Pro, 24GB RAM, Miniconda3, local execution

---

## Project Overview

This project builds an Agent-Based Model (ABM) exploring how different levels of service delegation in a society affect individual well-being and collective efficiency. It investigates whether high-delegation systems produce "involution spirals" where everyone works more to provide convenience for each other, ultimately reducing everyone's well-being.

The project demonstrates competence in: ABM design, interactive web application development (Flask + Plotly.js), LLM-enhanced user interfaces (local Ollama deployment), data visualization, and data stewardship.

## Architecture

- **ABM Engine**: Mesa 3.5.x + Mesa-LLM 0.3.0
- **Local LLM**: Ollama + Qwen 3.5 4B (primary) / Qwen 3 1.7B (lightweight)
- **Web Backend**: Flask (REST API, Jinja2 templates)
- **Visualization**: Plotly.js (interactive) + matplotlib (publication-quality)
- **Data Layer**: Pandas DataFrames + SQLite
- **Environment**: Miniconda3 conda environment (Python 3.12)

## LLM Integration (5 Roles)

Core principle: LLM operates at the periphery. The ABM engine remains a transparent, rule-based "white box."

1. **Role 1 -- Scenario Parser** (peripheral): Natural language to structured simulation parameters
2. **Role 2 -- Agent Profile Generator** (peripheral): Diverse agent profiles as explicit numerical parameters
3. **Role 3 -- Result Interpreter** (peripheral): Narrative explanations of simulation results
4. **Role 4 -- Visualization Annotator** (peripheral): Auto-generated chart captions
5. **Role 5 -- Agent Communication Forums** (experimental, in-loop): Agents discuss delegation norms in 1-3 turn exchanges; toggleable experimental mode

## Neutrality Policy

All references use abstract social system labels. No specific country, region, or culture is named.

- **Type A Society (Autonomy-Oriented)**: High self-service, strong individual boundaries, moderate service availability
- **Type B Society (Convenience-Oriented)**: High delegation, abundant services, strong social conformity pressure

## Research Question

*How do different levels of service delegation in a society affect individual well-being (leisure time, stress) and collective efficiency? Under what conditions does a "convenience spiral" (involution) emerge?*

## Hypotheses

- **H1**: Higher service delegation rates lead to higher total systemic labor hours.
- **H2**: A critical delegation threshold exists beyond which the system enters an involution spiral.
- **H3**: Higher individual autonomy achieves lower perceived convenience but higher aggregate well-being.
- **H4**: Mixed systems (moderate delegation) may be unstable, tending to drift toward extremes.

## Data Strategy: "Empirically Informed Theoretical Modeling"

Real-world data informs (does not calibrate) the model. Stylized facts from ILO, OECD, WVS, and World Bank set plausible parameter ranges for Type A/B presets.

## Execution Phases

| Phase | Days | Focus |
|-------|------|-------|
| Phase 1 | Day 1 | Foundation & Environment Setup |
| Phase 2 | Days 2-4 | Core ABM Simulation Engine |
| Phase 3 | Days 5-7 | Web Interface & Dashboard |
| Phase 4 | Days 8-10 | LLM Integration |
| Phase 5 | Days 11-12 | Agent Forums & Advanced Features |
| Phase 6 | Days 13-14 | Analysis, Polish & Portfolio |

Each phase has a separate detailed execution plan in this directory.
