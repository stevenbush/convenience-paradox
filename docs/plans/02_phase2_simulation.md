# Phase 2: Core ABM Simulation Engine (Days 2-4)

**Goal**: Working simulation that can be run headlessly with meaningful data output.

## Tasks

### Day 2: Agent and Model Foundation

- [ ] Implement `Resident` agent class (`model/agents.py`) with attributes:
  - `available_time`: float (hours per day available for tasks/leisure)
  - `skill_set`: dict (task_type -> proficiency level)
  - `delegation_preference`: float (0=always self-service, 1=always delegate)
  - `stress_level`: float (0=relaxed, 1=maximum stress)
  - `task_queue`: list of daily tasks to handle
  - `income`: float (earnings from providing services)
  - `is_service_provider`: bool (whether agent accepts delegated tasks)
- [ ] Implement `ConvenienceParadoxModel` class (`model/model.py`):
  - Mesa Model subclass with environment and service network
  - Agent initialization with configurable heterogeneity
  - Step function coordinating agent actions

### Day 3: Decision Logic and Mechanics

- [ ] Implement agent decision rules (transparent, parameterized):
  - Task generation: each tick, agents receive daily tasks of varying complexity
  - Self-service vs. delegate decision: based on delegation_preference, skill level, available time, and cost
  - Service acceptance: agents who accept delegated tasks earn income but spend time
  - Stress accumulation: when available_time drops below personal threshold
  - Preference adaptation: agents adjust delegation_preference based on stress and peer behavior (social conformity)
- [ ] Implement service matching mechanism (how delegated tasks find providers)

### Day 4: Data Collection, Presets, and Empirical Grounding

- [ ] Configure `DataCollector` with metrics:
  - Agent-level: available_time, stress_level, delegation_preference, income, tasks_completed_self, tasks_delegated
  - Model-level: avg_stress, total_labor_hours, avg_delegation_rate, social_efficiency, gini_coefficient
- [ ] Define parameter presets (`model/params.py`):
  - Type A (Autonomy-Oriented): informed by ILO/WVS data for high-autonomy regions
  - Type B (Convenience-Oriented): informed by ILO/WVS data for high-delegation regions
  - Custom: user-defined parameters
- [ ] Pull and commit empirical grounding data (`data/empirical/`):
  - ILO working hours stylized facts
  - WVS autonomy/conformity dimension values
  - OECD Better Life Index reference values
- [ ] Implement `batch_run` support for parameter sweeps
- [ ] Write basic unit tests (`tests/test_agents.py`, `tests/test_model.py`)

## Deliverable

Headless simulation producing DataFrames of time-series metrics for Type A/B presets. Runnable via:

```python
from model.model import ConvenienceParadoxModel
from model.params import TYPE_A_PRESET, TYPE_B_PRESET

model = ConvenienceParadoxModel(**TYPE_A_PRESET)
for _ in range(500):
    model.step()
df = model.datacollector.get_model_dataframe()
```
