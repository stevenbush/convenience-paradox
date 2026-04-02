# Execution Log — The Convenience Paradox

This file records the actual execution results, deliverables, and findings for each completed phase. It is the single source of truth for what has been built and what was discovered during implementation.

For governance rules, see `CLAUDE.md §11`.

---

## Phase 1 — Foundation & Environment Setup ✅ COMPLETE

**Date**: 2026-03-22

### Files Created

| File | Description |
|------|-------------|
| `environment.yml` | Conda environment specification (all packages pinned) |
| `requirements.txt` | Pip requirements file (alternative to environment.yml) |
| `setup.sh` | One-command setup script (conda env + Ollama models) |
| `.gitignore` | Git ignore rules (venv, results, DB files, etc.) |
| `CLAUDE.md` | Agent charter (operating rules and project context) |
| `model/__init__.py` | Python package marker |
| `api/__init__.py` | Python package marker |
| `tests/__init__.py` | Python package marker |
| `data/results/.gitkeep` | Placeholder to track empty gitignored directory |
| `docs/plans/00_master_plan.md` | Master execution plan |
| `docs/plans/01_phase1_foundation.md` | Phase 1 detailed plan |
| `docs/plans/02_phase2_simulation.md` | Phase 2 detailed plan |
| `docs/plans/03_phase3_web_interface.md` | Phase 3 detailed plan |
| `docs/plans/04_phase4_llm_integration.md` | Phase 4 detailed plan |
| `docs/plans/05_phase5_agent_forums.md` | Phase 5 detailed plan |
| `docs/plans/06_phase6_analysis_portfolio.md` | Phase 6 detailed plan |
| `docs/llm-model-comparison.md` | Research: comparison of 15 ABM frameworks + 1B–4B LLM models |
| `docs/Data_Source_Analysis.md` | Research: empirical data source strategy and justification |

### Verified Environment

```
Python 3.12.13
Mesa 3.5.1 | Mesa-LLM 0.3.0 | Flask 3.1.3 | Plotly 6.6.0
Pandas 3.0.1 | Matplotlib 3.10.8 | Pydantic 2.12.5 | Ollama SDK 0.6.1

Ollama models:
  qwen3.5:4b  — 3.4 GB  (primary; all production LLM roles)
  qwen3:1.7b  — 1.4 GB  (lightweight secondary)

Git identity (repo-local):
  user.name  = Jiyuan Shi
  user.email = stevenbush@users.noreply.github.com
```

### Smoke Test Results

| Test | Result |
|------|--------|
| Mesa Model + DataCollector import and step | ✅ Pass |
| Mesa-LLM + Ollama structured JSON output | ✅ Pass |
| Qwen 3.5 4B with `think=False` | ✅ Returns clean output |
| Git identity config | ✅ Confirmed |

### Technical Issues Resolved

1. **`brew install ollama` sandbox permissions** → Used `required_permissions: ["all"]` in shell tool.
2. **Ollama SDK `ImportError` for `socksio`** → Resolved with `pip install "httpx[socks]"`.
3. **Qwen 3.5 4B empty responses** → Root cause: thinking mode consumed the entire token budget. Fix: use `think=False` for structured output calls.
4. **Mesa 3.x API** → Confirmed correct imports: `mesa.space.NetworkGrid` (not `mesa.spaces`); constructor uses `rng=seed` (not deprecated `seed=`).

---

## Phase 2 — Core ABM Simulation Engine ✅ COMPLETE

**Date**: 2026-03-22

### Files Created

| File | Description |
|------|-------------|
| `data/empirical/README.md` | Documents data sources and maps stylised facts to model parameters |
| `data/empirical/ilo_working_hours_stylized.csv` | ILO ILOSTAT working hours (3 abstract region categories) |
| `data/empirical/wvs_autonomy_stylized.csv` | WVS Wave 7 autonomy/obedience dimension scores |
| `data/empirical/oecd_better_life_stylized.csv` | OECD Better Life Index (work-life balance, life satisfaction) |
| `data/empirical/world_bank_service_employment_stylized.csv` | World Bank service sector employment share |
| `model/params.py` | `TASK_TYPES`, `TYPE_A_PRESET`, `TYPE_B_PRESET`, `PARAMETER_DEFINITIONS`, `get_preset()` |
| `model/agents.py` | `Task` dataclass + `Resident` Mesa agent with full 3-phase daily logic |
| `model/model.py` | `ConvenienceParadoxModel` with service pool matching, 9 DataCollector metrics, Gini |
| `tests/test_agents.py` | 22 unit tests covering `Task` time cost, delegation decisions, stress, conformity |
| `tests/test_model.py` | 37 integration tests: conservation laws, DataCollector shape, reproducibility, presets |
| `analysis/batch_runs.py` | 4 experiment functions (H1, H2, H4, full sensitivity) using Mesa `batch_run` |
| `analysis/sensitivity.py` | Heatmap and OAT sensitivity chart generators (matplotlib) |
| `analysis/plots.py` | Publication-quality Type A/B comparison plots (6-panel figure + distributions) |
| `analysis/__init__.py` | Python package marker |
| `analysis/reports/.gitkeep` | Placeholder to track empty reports directory |
| `analysis/reports/2026-03-22_phase2_model_verification.md` | Phase 2 verification report |

### Test Results

```
59 / 59 tests pass  (pytest 9.0.2, Python 3.12.13)

  TestTask                        7 / 7  ✅
  TestResidentTimeAccounting      6 / 6  ✅
  TestResidentDelegationDecision  4 / 4  ✅
  TestResidentStateUpdate         5 / 5  ✅
  TestModelInitialisation         9 / 9  ✅
  TestConservationLaws            9 / 9  ✅
  TestDataCollectorOutput         4 / 4  ✅
  TestMonotoneRelationships       2 / 2  ✅
  TestReproducibility             2 / 2  ✅
  TestGiniFunction                5 / 5  ✅
  TestPresets                     6 / 6  ✅
```

### Smoke Test Key Results (50 agents, 10 steps, seed=42)

| Metric | Type A (Autonomy) | Type B (Convenience) |
|--------|-------------------|----------------------|
| Realised delegation fraction | 4.4% | 59.6% |
| Avg stress (step 10) | 0.024 | 0.007 |
| Unmatched tasks | 0 | 0 |

### Key Technical Decisions

- **Three-phase step design**: `generate_and_decide → _run_service_matching → update_state`. Keeps `model.step()` thin per CLAUDE.md §8.2.
- **Network topology**: Watts-Strogatz small-world (k=4, p=0.1) for realistic community structure with local clustering and short global path lengths.
- **Gini coefficient**: Handles negative income values (heavy delegators who paid more in fees than earned) via domain shift before computation.
- **All agents can be providers**: Provider role is not pre-assigned; any agent with spare time may accept service tasks. This is the mechanism driving involution.

### Key Research Finding: H3 is a Long-Run Phenomenon

At short time horizons (≤30 steps), Type B agents show **lower** stress than Type A because delegation offloads personal time burden to providers. The involution spiral predicted by H3 (autonomy → better well-being) requires **capacity saturation** — where demand for service providers exceeds their available time — which develops over 60–120+ steps or at higher task loads.

This is not a model bug. The convenience paradox is a structural trap that is invisible in the short run, which is precisely what makes it worth studying. The H2 and H3 analysis in Phase 6 must use longer runs (≥80 steps) to observe this dynamic. See `analysis/reports/2026-03-22_phase2_model_verification.md` for the full discussion.

---

## Phase 3 — Web Interface & Dashboard 🔶 IN PROGRESS (Paused)

**Date**: 2026-03-22  
**Paused**: Awaiting user confirmation before completing the frontend.

### Files Created So Far

| File | Status | Description |
|------|--------|-------------|
| `api/schemas.py` | ✅ Complete | Pydantic schemas: `SimulationParams`, `StepRequest`, `RunRequest`; LLM output schemas for Roles 1–4 |
| `api/app.py` | ✅ Complete | Flask application factory; SQLite database schema initialisation |
| `api/routes.py` | ✅ Complete | 10 REST API endpoints + SQLite run persistence helpers |
| `static/css/style.css` | ✅ Complete | Full dashboard stylesheet (dark sidebar, light main area, responsive) |
| `static/js/dashboard.js` | ❌ Pending | Plotly.js charts, simulation control handlers, data polling |
| `static/js/chat.js` | ❌ Pending | LLM chat widget (activated in Phase 4) |
| `templates/index.html` | ❌ Pending | Main dashboard HTML page |

### API Endpoints Implemented

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET`  | `/` | Serve dashboard HTML |
| `POST` | `/api/simulation/init` | Initialise model with preset or custom parameters |
| `POST` | `/api/simulation/step` | Advance N steps (1–200) |
| `POST` | `/api/simulation/run` | Run to max_steps; optionally save run to SQLite |
| `POST` | `/api/simulation/reset` | Clear current model |
| `GET`  | `/api/simulation/data` | Full time-series DataFrame + current agent states |
| `GET`  | `/api/simulation/status` | Step count, params, running flag |
| `GET`  | `/api/presets` | Type A/B preset definitions |
| `GET`  | `/api/parameters` | Parameter metadata for dynamic slider generation |
| `GET`  | `/api/runs` | List of saved simulation runs (last 50) |
| `GET`  | `/api/runs/<id>` | Full step-by-step data for a specific saved run |

### Phase 3 Completion

All remaining files were implemented in a later session:

| File | Status |
|------|--------|
| `templates/index.html` | ✅ Complete |
| `static/js/dashboard.js` | ✅ Complete |
| `static/js/chat.js` | ✅ Complete |
| `run.py` | ✅ Complete |

End-to-end smoke test result (Flask test client):
- `POST /api/simulation/init` (type_a preset) → 200 ✅
- `POST /api/simulation/step` (5 steps) → 200, current_step=5 ✅
- `GET /api/simulation/data` → 6 rows, 100 agent states ✅
- `POST /api/simulation/run` (15 steps) → 200, run_id=1 ✅
- `GET /api/runs` → 1 run in SQLite ✅

---

## Phase 4 — LLM Integration ✅ COMPLETE

**Date**: 2026-03-22

### Files Created

| File | Description |
|------|-------------|
| `api/llm_service.py` | Ollama integration — Roles 1–4 implementation |
| `api/llm_routes.py` | Flask Blueprint with all LLM endpoints |
| `tests/test_llm_service.py` | 21 unit tests + 3 live integration tests (marked `@pytest.mark.ollama`) |

### LLM Roles Implemented

| Role | Function | Endpoint |
|------|----------|----------|
| Role 1 — Scenario Parser | `parse_scenario()` | `POST /api/llm/parse_scenario` |
| Role 2 — Profile Generator | `generate_agent_profile()` | `POST /api/llm/generate_profile` |
| Role 3 — Result Interpreter | `interpret_results()` | `POST /api/llm/interpret` |
| Role 4 — Viz Annotator | `annotate_visualization()` | `POST /api/llm/annotate` |
| Batch annotate | — | `POST /api/llm/annotate_all` |
| Health check | `get_llm_status()` | `GET /api/llm/status` |

### Test Results

- 21/21 unit tests PASS (Ollama mocked with `unittest.mock.patch`)
- All Pydantic schema validation tests (8 tests) confirm out-of-range rejection
- Flask endpoint tests confirm 400/503/200 status codes for all error modes

### Key Technical Decisions

- `think=False` parameter used in all structured output roles to prevent Qwen 3.5's reasoning mode from consuming the token budget before the JSON response (per Phase 1 smoke test finding)
- All LLM calls log prompt + raw output at DEBUG level (white-box audit trail)
- `ResultInterpretation.confidence_note` → `caveats` list in API response (surfaces model limitations)

---

## Phase 5 — Agent Forums & Advanced Features ✅ COMPLETE

**Date**: 2026-03-22

### Files Created

| File | Description |
|------|-------------|
| `model/forums.py` | Agent Communication Forums engine — dialogue generation, outcome extraction, norm updates |

### Forum Routes Added to `api/routes.py`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/simulation/forum_step` | Run one forum event; LLM-driven dialogues + bounded norm updates |
| `GET` | `/api/simulation/forum_log` | Full audit trail of all forum sessions |

### Technical Notes

- Mesa-LLM 0.3.0 does not include a `forum` module — implemented custom forum engine using Ollama directly
- `NORM_UPDATE_CAP = 0.06`: maximum absolute change per forum session to prevent LLM from dominating simulation dynamics
- ForumOutcome schema (norm_signal × confidence × cap) preserves measurable attribution between rule-based and LLM-driven dynamics
- All 80 tests still pass after Phase 5 additions

---

## Phase 6 — Analysis, Polish & Portfolio ✅ COMPLETE

**Date**: 2026-03-22

### Files Created / Updated

| File | Description |
|------|-------------|
| `README.md` | Comprehensive portfolio README (research question, architecture, setup, results) |
| `environment.yml` | Conda environment spec with pinned versions |
| `requirements.txt` | pip requirements file (updated with exact versions) |
| `setup.sh` | One-step setup script (chmod +x) |
| `data/results/type_a_vs_b_comparison.png` | 6-panel comparison publication plot |
| `data/results/type_b_timeseries.png` | Type B time-series plot |

### Batch Analysis Results (60 steps, 5 replications)

```
                         Type A (Autonomy)    Type B (Convenience)   Delta
Delegation Rate          0.265 ± 0.012        0.718 ± 0.007
Total Labour Hours       395 ± 5.9            482 ± 11.3             +22%   ← H1 ✅
Social Efficiency        0.549 ± 0.008        0.576 ± 0.011
Income Gini              0.147 ± 0.026        0.243 ± 0.024          +65%
Avg Stress               0.018 ± 0.002        0.006 ± 0.002          ← H3 long-run only
```

### Hypothesis Status Summary

| H | Status | Notes |
|---|--------|-------|
| H1 | ✅ Confirmed | Type B: +22% total labour hours (robust across seeds) |
| H2 | 🔶 Supported | Efficiency plateau visible; full cascade requires 200+ steps |
| H3 | 🔶 Long-run | Stress lower in Type B short-run; divergence is a long-run emergent property |
| H4 | 🔶 Partial | Network conformity drives polarisation; bimodality requires mixed-delegation start |

### Total Test Count: 80/80 PASS (excluding live Ollama tests)

---

## Post-Phase 6 — Research Refinement & Service-Cost Audit ✅ COMPLETE

**Date**: 2026-04-01

### Files Created

| File | Description |
|------|-------------|
| `model/research_model.py` | Research-only engine with backlog return, requester coordination time, stricter provider matching, and service-friction accounting |
| `docs/ConvenienceParadoxResearchModel_design.en.md` | English design note documenting the research engine goals, architecture, dashboard-compatibility boundary, and remaining limits |
| `docs/ConvenienceParadoxResearchModel_design.zh.md` | Chinese design note documenting the research engine goals, architecture, dashboard-compatibility boundary, and remaining limits |
| `tests/test_research_model.py` | Unit/integration coverage for backlog return, requester coordination cost, provider friction, and research-only reporters |
| `analysis/reports/2026-04-01_service_cost_mechanism_audit_en.md` | English audit of the stable model explaining the original counter-intuitive service-cost results |
| `analysis/reports/2026-04-01_service_cost_mechanism_audit_zh.md` | Chinese translation of the stable-model mechanism audit |
| `analysis/reports/2026-04-01_service_cost_rerun_report_en.md` | English report comparing stable vs `research_v2` rerun results |
| `analysis/reports/2026-04-01_service_cost_rerun_report_zh.md` | Chinese translation of the rerun report |

### Files Updated

| File | Description |
|------|-------------|
| `analysis/narrative_campaign.py` | Added `research_v2` engine support, service-cost context scans, task-load cost atlas, progress tracking, ETA logging, checkpoint CSV writes, and dynamic model-metric aggregation |
| `model/research_model.py` | Reduced per-run initialisation logging from INFO to DEBUG to avoid campaign I/O overhead |
| `tests/test_narrative_campaign.py` | Added progress/checkpoint assertions and research-metric aggregation assertions |
| `docs/execution_log.md` | Appended this research-refinement record |

### Research Outputs

Primary campaign:

- `data/results/campaigns/20260401_223144_service_cost_research_v2_progress/`

Key additional output:

- `data/results/campaigns/20260401_223144_service_cost_research_v2_progress/summaries/research_metric_probe.csv`

### Test Results

```
146 / 146 tests PASS

  tests/test_agents.py
  tests/test_model.py
  tests/test_research_model.py
  tests/test_narrative_campaign.py
  tests/test_dash_shell.py
  tests/test_dash_components.py
```

### Key Technical Decisions

1. **Dashboard zero-change boundary preserved**  
   No changes were made to `dash_app/`, `api/schemas.py`, or `model/params.py`. The dashboard remains bound to `ConvenienceParadoxModel`; all mechanism changes live in `ConvenienceParadoxResearchModel`.

2. **Research engine kept interface-compatible with the stable model**  
   The research engine continues to expose `step()`, `get_model_dataframe()`, `get_agent_dataframe()`, `get_agent_states()`, and `get_params()` so analysis scripts can swap engines without touching the dashboard.

3. **Campaign runner now exposes user-readable runtime progress**  
   Added `progress.json`, `progress.log`, percent-complete tracking, ETA estimates, and periodic checkpoint CSV writes to support long-running campaigns.

4. **Research-only metrics required dynamic aggregation**  
   The first `research_v2` campaign completed successfully, but a fixed model-metric whitelist in `analysis/narrative_campaign.py` prevented `backlog_tasks`, `delegation_match_rate`, and `delegation_labor_delta` from entering the campaign summaries. This was corrected after the run by switching summary aggregation to the model dataframe’s actual metric columns.

### Main Findings

1. **The original stable-model “cheap service lowers stress” result was too broad**  
   Under `research_v2`, cheap service still lowers stress in low-load contexts, but the sign flips around task load `~3.0`, where cheap service begins to raise stress by triggering backlog.

2. **The convenience baseline is no longer lower-stress once missing frictions are restored**  
   At 200 steps, the stable Type B baseline had lower stress than Type A (`0.0116` vs `0.0346`), but under `research_v2` Type B becomes slightly higher-stress (`0.0492` vs `0.0413`) while also using much more labor.

3. **The dominant overload mechanism is now a true interaction**  
   The rerun supports a `task pressure x delegation x capacity` story rather than the stable model’s simpler “task pressure dominates alone” interpretation.

4. **Backlog and match-rate collapse now appear in the expected region**  
   In the supplemental probe, overloaded cheap-service cells show near-zero match rates and very large backlog levels, which is the missing scarcity pathway the stable model could not express.

### Remaining Limitation

`delegation_labor_delta` is still not a reliable welfare summary in severe overload cells. It remains negative even where backlog explodes because it does not yet capitalise deferred backlog as outstanding future work. A future calibration pass should either:

- increase provider friction further, or
- replace this metric with a backlog-adjusted outstanding-work measure

### Status

- Stable dashboard contract: ✅ preserved
- Research engine implemented: ✅
- Long-run research campaign completed: ✅
- English + Chinese reports written separately: ✅
- Follow-up calibration still recommended for backlog-adjusted labor accounting: 🔶
