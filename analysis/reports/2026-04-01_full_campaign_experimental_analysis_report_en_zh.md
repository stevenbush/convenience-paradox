# Full-Campaign Experimental Analysis Report

**Date**: 2026-04-01  
**Campaign**: `20260401_125557_full_campaign`  
**Code Version**: `d667ddf83a7f96968aae5d77a12b68f49b516237`  
**Execution Mode**: local multi-process run with 8 workers  
**Primary Output Basis**: `data/results/campaigns/20260401_125557_full_campaign/`

---

## English Version

### 1. Purpose

This report analyses the current full-campaign simulation results of *The Convenience Paradox* and compares them with the questions raised in the earlier reflection memo. The memo is treated here as a source of research questions, not as a premise to be confirmed. All inferences below are derived from the simulation outputs themselves.

The analysis remains fully abstract. It uses only the project's neutral labels, `Type A` and `Type B`, and does not treat the model as evidence about any named real-world society.

### 2. Experimental Basis

The full campaign used the narrative-first analysis pipeline and executed four experiment packages:

| Package | Main design | Scale |
| --- | --- | --- |
| Package A: Everyday Friction | Type A / Type B horizon comparison | 2 presets x 4 horizons x 12 seeds |
| Package B: Convenience Transfer | delegation x task-load atlas + threshold refinement | 9 x 5 atlas x 8 seeds; 5 x 5 refinement x 20 seeds |
| Package C: Cheap Service Trap | delegation x service-cost atlas + preset decomposition | 9 x 9 atlas x 8 seeds; 8 decomposition scenarios x 10 seeds |
| Package D: Norm Lock-in | delegation x conformity atlas + mixed-system deep dive | 9 x 5 atlas x 8 seeds; 3 x 3 deep dive x 20 seeds |

Core quantitative analysis used 2,224 summary runs, plus 60 additional story-case runs for representative trajectories and blog-ready visual material. All runs used the current Mesa model with 100 agents, a small-world network, explicit rule-based behaviour, and exogenous service pricing.

### 3. Model Scope and Boundaries

Three boundaries are critical for interpreting the findings:

1. `service_cost_factor` is exogenous. The model can test how external price friction changes behaviour, but it cannot endogenise price formation.
2. The model has no direct variable for delay tolerance, patience, or cultural expectation. Those ideas can only be approximated through delegation convergence and realised delegation behaviour.
3. The model measures labour, stress, efficiency, and inequality proxies. It does not measure creativity, scientific innovation, policy quality, or named labour-market institutions.

### 4. Results

#### 4.1 Baseline comparison: convenience reallocates labour, but does not automatically worsen average well-being

Across all horizon scans from 60 to 300 steps, the `Type B` baseline consistently produced more total labour than `Type A`, but lower average stress and lower inequality in available time.

| Horizon | Type B vs Type A total labour | Type B vs Type A average stress | Type B vs Type A time inequality | Type B minus Type A delegated task share |
| --- | --- | --- | --- | --- |
| 60 steps | +17.8% | -69.0% | -38.4% | +54.0 percentage points |
| 120 steps | +18.8% | -69.3% | -36.7% | +54.1 percentage points |
| 200 steps | +17.3% | -66.6% | -38.1% | +54.2 percentage points |
| 300 steps | +17.4% | -69.7% | -38.6% | +54.4 percentage points |

This is one of the most important results in the current campaign. The model supports the claim that a convenience-heavy system can require more total labour overall. However, under the current preset assumptions, that extra labour does not translate into higher average stress at baseline. In fact, the opposite happens: `Type B` delivers lower mean stress and slightly higher social efficiency than `Type A` throughout the observed horizon.

This means the current model does **not** support a blanket conclusion that the convenience-oriented baseline is systemically worse for average well-being. What it supports is narrower and more precise: convenience shifts the labour structure upward, but the stress burden can remain low if task pressure and service capacity remain within manageable bounds.

#### 4.2 Convenience is better understood as labour transfer than labour elimination

The story-case outputs make the transfer mechanism concrete. In the selected representative runs:

| Story case | Tail total labour hours | Tail average stress | Final mean provider time | Final mean delegated tasks |
| --- | --- | --- | --- | --- |
| Autonomy Baseline | 421.8 | 0.0330 | 121.8 | 59.6 |
| Convenience Baseline | 502.3 | 0.0110 | 953.8 | 536.4 |
| Threshold Pressure | 550.0 | 0.0442 | 696.8 | 385.6 |
| Overloaded Convenience | 611.1 | 0.5486 | 1454.8 | 822.5 |

Relative to the autonomy baseline, the convenience baseline generated:

- 19.1% higher total labour
- 7.83 times as much mean provider time
- 66.7% lower mean stress

Relative to the autonomy baseline, the overloaded convenience case generated:

- 11.95 times as much mean provider time
- much higher stress once task pressure was pushed upward

This supports a strong version of the "labour transfer" argument. In the current model, convenience is not primarily a disappearance of work. It is a redistribution of work into provider time, matching capacity, and service throughput. The convenience baseline looks efficient to the consumer side because the provider side absorbs the system cost.

#### 4.3 Task pressure is the dominant overload driver in the current model

Package B shows that overload is driven much more strongly by task pressure than by delegation alone.

Average results by task-load level were:

| Task load | Mean stress | Mean total labour | Mean time inequality | Mean delegated-task share |
| --- | --- | --- | --- | --- |
| 1.5 | 0.0074 | 303.1 | 0.1580 | 0.2844 |
| 2.0 | 0.0154 | 381.3 | 0.1909 | 0.2902 |
| 2.5 | 0.0340 | 469.0 | 0.2245 | 0.3008 |
| 3.0 | 0.1073 | 554.1 | 0.2581 | 0.3266 |
| 3.5 | 0.7913 | 632.3 | 0.2801 | 0.5199 |

The threshold refinement confirms the same pattern. Within the targeted delegation band, mean stress rose from `0.1511` at task load `3.0` to `0.9134` at task load `3.5`, while mean labour rose from `563.2` to `643.0`.

The highest-stress cells were not the highest-delegation cells. They clustered around very high task load (`3.5`) with low-to-moderate delegation (`0.15` to `0.35`). That is an important correction to a simplistic narrative. The current model does not say that "more delegation always creates more overload." It says that when the system is pushed into a high-throughput regime, overload emerges sharply, and delegation then interacts with that pressure rather than solely creating it.

#### 4.4 Cheap service matters, but it is not the whole explanation

Package C isolates the effect of external price friction. When `service_cost_factor` was low, realised delegation was clearly higher:

| Service cost factor | Mean delegated-task share | Mean total labour | Mean stress |
| --- | --- | --- | --- |
| 0.10 | 0.4504 | 462.3 | 0.0199 |
| 0.20 | 0.4566 | 459.9 | 0.0186 |
| 0.50 | 0.3643 | 467.5 | 0.0295 |
| 0.65 | 0.2078 | 475.5 | 0.0497 |
| 0.90 | 0.2870 | 471.3 | 0.0447 |

Lower cost therefore pushes the system toward more delegation and, on average, lower stress. But the effect size is moderate relative to task-pressure changes. The preset decomposition is especially informative:

| Scenario | Tail stress | Tail labour | Tail delegated fraction |
| --- | --- | --- | --- |
| Type A baseline | 0.034 | 429.1 | 0.091 |
| Type A with economic-friction swap | 0.023 | 420.3 | 0.182 |
| Type A with task-pressure swap | 0.114 | 531.4 | 0.125 |
| Type B baseline | 0.012 | 503.6 | 0.635 |
| Type B with economic-friction swap | 0.018 | 512.2 | 0.529 |
| Type B with task-pressure swap | 0.003 | 398.9 | 0.632 |

Two conclusions follow.

First, cheap service is a real driver in the model, because lowering service cost increases realised delegation. Second, cheap service is not a sufficient explanation by itself. Task-pressure changes moved labour and stress more strongly than norm-family swaps, and often more strongly than price-friction swaps. The current evidence therefore supports the claim that cheap service is one enabling condition inside a broader system, not the single master cause.

#### 4.5 Mixed systems are somewhat less stable, but the effect is moderate

Package D provides partial support for the idea that middle states are less stable than extremes. The highest cross-seed variation in final delegation rate appeared in the mid-range initial conditions:

| Initial delegation preference | Mean final delegation std |
| --- | --- |
| 0.10 | 0.0073 |
| 0.40 | 0.0065 |
| 0.45 | 0.0113 |
| 0.50 | 0.0083 |
| 0.55 | 0.0113 |
| 0.80 | 0.0055 |
| 0.90 | 0.0039 |

By conformity level, the mean final-delegation standard deviation rose from `0.0060` at conformity `0.0` to about `0.0075` in the `0.2` to `0.6` range.

The most unstable mixed-start cell was:

- initial delegation preference `0.45`
- conformity `0.4`
- final delegation mean `0.4540`
- final delegation std `0.0113`
- final delegation range across seeds `0.4343` to `0.4769`

This does indicate that middle zones are more variable than extreme zones in the current model. However, the spread is still fairly narrow. The model does **not** show a dramatic bifurcation into sharply separated camps under the current parameterisation. The strongest defensible statement is therefore:

- `H4` receives **partial support**
- the mixed region is less stable than the extremes
- but the instability is mild to moderate, not a strong split into distinct basins

#### 4.6 What the current model can and cannot say about "trained speed expectations"

The earlier reflection asked whether systems can train people to expect faster response times. The current model cannot test that directly, because it has no explicit delay-tolerance variable. What it can show is more limited:

- lower cost and higher conformity make realised delegation easier to sustain
- high-convenience regimes make non-delegation less common in practice
- moderate states can become more path-sensitive under norm pressure

These are reasonable proxies for lock-in, but not direct evidence of changing patience, emotional response to waiting, or perceived entitlement to immediacy. Any stronger claim would go beyond the present model.

### 5. Comparison With the Earlier Reflection Questions

The earlier reflection note raised several broad questions. The current campaign gives the following answers.

| Question reframed in abstract terms | Judgment from current results | Comment |
| --- | --- | --- |
| Are small daily frictions signs of deeper system structure rather than isolated annoyances? | Supported | The preset horizon scans show stable differences in labour allocation, delegation, and time inequality across horizons. |
| Does convenience save labour or relocate it? | Strongly supported as relocation | Total labour and provider time both increase in convenience-heavy regimes. |
| Is cheap service the main cause of convenience dependence? | Partially supported | Lower cost increases delegation, but task pressure is the stronger overload driver. |
| Does the system train faster expectations and make exit harder? | Indirectly supported only | The model shows norm convergence and convenience lock-in proxies, not direct delay-tolerance change. |
| Are mixed systems unstable? | Partially supported | Mid-range starting points are more variable, but not strongly bifurcated in the current version. |
| Can this model explain higher-level outcomes such as creativity, science, or macro-development trajectories? | Not supported | Those outcomes are outside the model's variables. |

### 6. Main Conclusions

The most rigorous summary of the current full-campaign evidence is as follows.

1. The model supports a **convenience transfer** thesis more strongly than a general **convenience harm** thesis.
2. Under the current presets, the convenience-heavy baseline requires more total labour, but it does not produce higher average stress. It produces lower average stress.
3. The clearest overload mechanism is **high task pressure**, not delegation alone.
4. Cheap service matters, but in the current model it is an enabling factor inside a broader feedback system rather than the sole cause.
5. Mixed systems are somewhat less stable than extremes, but the current evidence is moderate rather than dramatic.

### 7. Implications for the Reflection Memo

The earlier reflection was analytically productive because it identified the right kinds of system-level questions. But the current simulation does not validate every intuitive suspicion equally.

It validates the idea that convenience can be socially expensive in total labour terms. It also validates the intuition that consumer ease can be built on invisible provider work. But it does not validate a stronger claim that the convenience-oriented baseline necessarily creates worse average welfare under the present assumptions. Nor does it validate claims about creativity, science, or civilisational outcomes.

The current results therefore narrow the argument. They suggest that the most defensible story is not "convenience is bad," but rather:

> convenience can remain subjectively comfortable while becoming objectively labour-intensive, and it becomes fragile when task pressure rises enough to expose the hidden provider burden.

### 8. Recommended Next Model Iteration

If the next research round is intended to answer the unresolved parts of the earlier reflection more directly, the highest-value model extensions would be:

1. Endogenous service pricing and provider scarcity.
2. An explicit delay-tolerance or expected-response-time variable.
3. Skill retention or skill decay under repeated delegation.
4. Heterogeneous agent classes rather than a single generic resident population.

Without those additions, the current model is best used to analyse labour transfer, overload thresholds, norm sensitivity, and inequality in time allocation.

### 9. Parameter Reference

This section summarises the parameters that were active in the current campaign. The definitions below follow the implemented model in `model/params.py`, `model/agents.py`, and `model/model.py`.

#### 9.1 Core model parameters

| Parameter | Meaning | Range / type | Default run value | Type A preset | Type B preset |
| --- | --- | --- | --- | --- | --- |
| `num_agents` | Number of residents in the simulation | integer | 100 | 100 | 100 |
| `delegation_preference_mean` | Mean initial tendency to delegate rather than self-serve | `[0,1]` | 0.50 | 0.25 | 0.72 |
| `delegation_preference_std` | Heterogeneity of initial delegation preference | float | 0.10 | 0.10 | 0.10 |
| `service_cost_factor` | External service-price multiplier applied to task base time | float | 0.40 | 0.65 | 0.20 |
| `social_conformity_pressure` | Strength of peer influence on behavioural drift | `[0,1]` | 0.30 | 0.15 | 0.65 |
| `tasks_per_step_mean` | Mean number of daily tasks per agent | tasks/day | 2.5 | 2.2 | 2.8 |
| `tasks_per_step_std` | Day-to-day variability in task count | tasks/day | 0.75 | 0.70 | 0.80 |
| `initial_available_time` | Daily discretionary time budget before tasks begin | hours/day | 8.0 | 8.0 | 8.0 |
| `stress_threshold` | Remaining time below which stress starts to increase | hours | 2.5 | 2.5 | 2.5 |
| `stress_recovery_rate` | Stress decrease when end-of-day time stays above threshold | stress units/step | 0.10 | 0.10 | 0.10 |
| `adaptation_rate` | Speed of delegation-preference updating | preference units/step | 0.03 | 0.02 | 0.05 |
| `network_type` | Social topology for peer influence | `small_world` / `random` | `small_world` | `small_world` | `small_world` |
| `seed` | Random seed for reproducibility | integer | 42 | 42 | 42 |

#### 9.2 Task menu parameters

| Task type | Base time | Skill requirement | Interpretation |
| --- | --- | --- | --- |
| `domestic` | 0.8 hours | 0.30 | Routine domestic work |
| `administrative` | 1.2 hours | 0.50 | Paperwork, banking, scheduling |
| `errand` | 0.5 hours | 0.20 | Shopping, parcel pickup, quick errands |
| `maintenance` | 1.5 hours | 0.65 | Repairs and maintenance tasks |

#### 9.3 Structural constants used in the behavioural rules

These values are not exposed as campaign-level sweep parameters, but they materially affect behaviour:

| Constant | Value | Role |
| --- | --- | --- |
| Provider proficiency | 0.60 | Fixed efficiency of agents acting as service providers |
| Forced-delegation threshold | `available_time < 0.5 x task_time` | Delegation becomes mandatory when the day is too full |
| Stress boost coefficient | 0.30 | Adds delegation pressure when an agent is already stressed |
| Skill-gap weight | 0.25 | Converts task mismatch into more or less delegation pressure |
| Cost-penalty weight | 0.25 | Converts service price into delegation disincentive |
| Stress amplification of conformity | `1 + 0.5 x stress_level` | Makes stressed agents more susceptible to peer norms |
| Stress accumulation coefficient | 0.10 | Governs how quickly stress rises under time deficit |
| Small-world network parameters | `k=4`, `p=0.1` | Default local clustering plus short paths |
| Random-network edge probability | `4 / (num_agents - 1)` | Used for topology robustness comparisons |

### 10. Mathematical Mechanics and Parameter Interactions

This section states the simulation rules in mathematical form, following the current code implementation rather than the simplified narrative description in the design document.

#### 10.1 Daily task generation

For agent `i` on day `t`, the number of tasks is sampled as:

`n_{i,t} = max(1, round(N(mu_tasks, sigma_tasks)))`

where:

- `mu_tasks = tasks_per_step_mean`
- `sigma_tasks = tasks_per_step_std`

This means `tasks_per_step_mean` shifts the whole workload level, while `tasks_per_step_std` changes the volatility of daily workload.

#### 10.2 Task time cost

For a task `j` with base time `b_j`, skill requirement `r_j`, and agent proficiency `s_{i,j}`, the model first clamps proficiency:

`s* = clip(s_{i,j}, 0.1, 1.0)`

Base execution time is:

`c_base = b_j / s*`

If the agent is below the task's skill requirement, an extra mismatch penalty is applied:

- if `s* < r_j`, then `c_{i,j} = c_base x (1 + 2 x (r_j - s*))`
- otherwise `c_{i,j} = c_base`

This creates a nonlinear cost of being under-skilled, especially for maintenance and administrative tasks.

#### 10.3 Delegation decision

If the agent has too little time left, delegation is forced:

`if available_time < 0.5 x c_{i,j}, then delegate = 1`

Otherwise, the model constructs an effective delegation probability:

`p_eff = clip(p_i + 0.30 x stress_i + 0.25 x (r_j - s_{i,j}) - 0.25 x cost, 0, 1)`

where:

- `p_i = delegation_preference`
- `stress_i = stress_level`
- `cost = service_cost_factor`

Delegation is then sampled as:

`delegate_{i,j} ~ Bernoulli(p_eff)`

This is the key interaction equation in the model:

- higher `delegation_preference_mean` raises baseline delegation pressure
- higher `stress_level` pushes more tasks into delegation
- lower skill relative to task requirement pushes more tasks into delegation
- higher `service_cost_factor` suppresses delegation

#### 10.4 Service provision and payment

If a task is matched to a provider, the provider executes it at fixed provider proficiency `0.60`:

`c_provider,j = c_j(s = 0.60)`

The requester pays:

`fee_j = b_j x service_cost_factor`

The requester loses that amount from income, and the provider gains the same amount. Because provider proficiency is fixed and not personalised, delegation often introduces time overhead even when it feels convenient to the requester.

#### 10.5 Service matching

For each delegated task, provider candidates satisfy:

- `provider_id != requester_id`
- `provider.available_time >= 0.5 x base_time`

Among those candidates, the model chooses:

`provider* = argmax_k available_time_k`

This is a greedy capacity-allocation rule. It is not a market-clearing model and does not endogenise wages, queues, or provider specialisation.

#### 10.6 Stress dynamics

At the end of the day, if remaining time is below threshold:

`deficit_ratio = (stress_threshold - available_time) / stress_threshold`

`stress_{t+1} = min(1, stress_t + 0.10 x deficit_ratio)`

Otherwise, stress recovers as:

`stress_{t+1} = max(0, stress_t - stress_recovery_rate)`

This means `stress_threshold` determines when pressure starts, while `stress_recovery_rate` controls how quickly agents calm down after having enough time.

#### 10.7 Preference adaptation and norm diffusion

Let `N(i)` be the neighbours of agent `i`. The local norm is:

`m_i = mean_{k in N(i)}(delegation_preference_k)`

Conformity weight is:

`w_i = social_conformity_pressure x (1 + 0.5 x stress_i)`

The preference update is:

`delta_i = w_i x (m_i - p_i)`

`p_{i,t+1} = clip(p_{i,t} + adaptation_rate x delta_i, 0, 1)`

This formula explains why `social_conformity_pressure` and `adaptation_rate` interact multiplicatively. High conformity with low adaptation still produces slow drift. High conformity with high adaptation produces faster norm convergence.

#### 10.8 Model-level metrics

The main reported metrics are computed as follows:

- `avg_stress = mean_i(stress_i)`
- `avg_delegation_rate = mean_i(delegation_preference_i)`
- `total_labor_hours = sum_i(initial_available_time_i - available_time_i)`
- `tasks_delegated_frac = step_tasks_delegated / step_tasks_total`
- `unmatched_tasks = step_tasks_delegated - step_tasks_matched`

Social efficiency is:

`social_efficiency = (tasks_self_served + tasks_matched) / total_labor_hours`

where:

- `tasks_self_served = step_tasks_total - step_tasks_delegated`
- `tasks_matched = successfully matched delegated tasks`

The Gini coefficient is used for income and available time:

`G = sum_i sum_j |x_i - x_j| / (2 x n x sum_i x_i)`

#### 10.9 Parameter relationships in plain terms

The most important interactions are:

1. `delegation_preference_mean` x `service_cost_factor`
   Lower cost and higher baseline preference jointly raise realised delegation.
2. `delegation_preference_mean` x `tasks_per_step_mean`
   High delegation is only dangerous when total workload is also high enough to strain provider capacity.
3. `social_conformity_pressure` x `adaptation_rate`
   These jointly determine how quickly local norms propagate through the network.
4. `stress_threshold` x `initial_available_time` x task-time costs
   These determine how easily agents enter the stress-accumulation regime.
5. `task skill requirements` x `agent skill draws`
   These determine which tasks are naturally self-served and which are more likely to be delegated.

### 11. Experiment Configuration Details

#### 11.1 Campaign-level settings

The full campaign used:

- `scale = full`
- `workers = 8`
- `num_agents = 100`
- `network_type = small_world` by default
- `delegation_threshold_band = [0.15, 0.20, 0.25, 0.30, 0.35]` for threshold refinement

#### 11.2 Package A: Everyday Friction

Package A used the two society presets directly:

| Scenario | delegation mean | delegation std | service cost | conformity | tasks mean | tasks std | available time | stress threshold | recovery | adaptation | steps | seeds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Type A preset | 0.25 | 0.10 | 0.65 | 0.15 | 2.2 | 0.7 | 8.0 | 2.5 | 0.10 | 0.02 | 60, 120, 200, 300 | 12 |
| Type B preset | 0.72 | 0.10 | 0.20 | 0.65 | 2.8 | 0.8 | 8.0 | 2.5 | 0.10 | 0.05 | 60, 120, 200, 300 | 12 |

The purpose of this package was to compare the preset system configurations as bundles rather than as isolated parameters.

#### 11.3 Package B: Convenience Transfer

The main atlas used the default parameter set as the anchor:

| Fixed parameters | Value |
| --- | --- |
| delegation std | 0.10 |
| service cost | 0.40 |
| conformity | 0.30 |
| tasks std | 0.75 |
| available time | 8.0 |
| stress threshold | 2.5 |
| recovery | 0.10 |
| adaptation | 0.03 |
| network | `small_world` |

Swept parameters:

| Sweep | Values | Steps | Seeds |
| --- | --- | --- | --- |
| `delegation_preference_mean` | 0.10 to 0.90 in 0.10 increments | 150 | 8 |
| `tasks_per_step_mean` | 1.5, 2.0, 2.5, 3.0, 3.5 | 150 | 8 |

Threshold refinement then kept the same default anchor and used:

| Sweep | Values | Steps | Seeds |
| --- | --- | --- | --- |
| `delegation_preference_mean` | 0.15, 0.20, 0.25, 0.30, 0.35 | 250 | 20 |
| `tasks_per_step_mean` | 1.5, 2.0, 2.5, 3.0, 3.5 | 250 | 20 |

Selected story cases in Package B used:

| Story case | delegation mean | service cost | conformity | tasks mean | tasks std | steps | seeds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Threshold Pressure | 0.55 | 0.40 | 0.40 | 3.0 | 0.75 | 300 | 10 |
| Overloaded Convenience | 0.72 | 0.20 | 0.80 | 3.5 | 0.80 | 300 | 10 |

#### 11.4 Package C: Cheap Service Trap

Package C also used the default parameter set as anchor, then swept:

| Sweep | Values | Steps | Seeds |
| --- | --- | --- | --- |
| `delegation_preference_mean` | 0.10 to 0.90 in 0.10 increments | 120 | 8 |
| `service_cost_factor` | 0.10 to 0.90 in 0.10 increments | 120 | 8 |

Preset decomposition used 200 steps and 10 seeds for each scenario. The scenario construction was:

| Scenario | Base anchor | Replaced parameters |
| --- | --- | --- |
| `type_a_baseline` | Type A | none |
| `type_a_with_economic_friction` | Type A | `service_cost_factor <- 0.20` |
| `type_a_with_norm_lock_in` | Type A | `social_conformity_pressure <- 0.65`, `adaptation_rate <- 0.05` |
| `type_a_with_task_pressure` | Type A | `tasks_per_step_mean <- 2.8`, `tasks_per_step_std <- 0.8` |
| `type_b_baseline` | Type B | none |
| `type_b_with_economic_friction` | Type B | `service_cost_factor <- 0.65` |
| `type_b_with_norm_lock_in` | Type B | `social_conformity_pressure <- 0.15`, `adaptation_rate <- 0.02` |
| `type_b_with_task_pressure` | Type B | `tasks_per_step_mean <- 2.2`, `tasks_per_step_std <- 0.7` |

The Package C story case used:

| Story case | delegation mean | service cost | conformity | tasks mean | tasks std | steps | seeds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cheap but Low-Conformity | 0.55 | 0.20 | 0.15 | 2.5 | 0.75 | 300 | 10 |

#### 11.5 Package D: Norm Lock-in

Package D again used the default parameter set as anchor, then swept:

| Sweep | Values | Steps | Seeds |
| --- | --- | --- | --- |
| `delegation_preference_mean` | 0.10 to 0.90 in 0.10 increments | 150 | 8 |
| `social_conformity_pressure` | 0.0, 0.2, 0.4, 0.6, 0.8 | 150 | 8 |

The mixed-system deep dive used:

| Sweep | Values | Steps | Seeds |
| --- | --- | --- | --- |
| `delegation_preference_mean` | 0.45, 0.50, 0.55 | 250 | 20 |
| `social_conformity_pressure` | 0.2, 0.4, 0.6 | 250 | 20 |

The Package D story case used:

| Story case | delegation mean | service cost | conformity | tasks mean | tasks std | steps | seeds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Mixed and Unstable | 0.50 | 0.40 | 0.40 | 2.5 | 0.75 | 300 | 10 |

These package-level settings matter for interpretation. For example, the reason Package D isolates norm lock-in is that price and task-load are held at the default anchor while conformity is varied; the reason Package B isolates overload is that service cost and conformity remain fixed while workload and delegation move.

---

## 中文版

### 1. 目的

本报告基于 *The Convenience Paradox* 当前 full campaign 的仿真实验结果进行分析，并将结果与此前反思备忘录中提出的问题进行对照。需要强调的是，先前备忘录在这里被当作“研究问题来源”，而不是“等待被验证的前提”。以下所有推论都以当前仿真结果为依据。

本报告保持抽象表达，只使用项目中的中性标签 `Type A` 与 `Type B`，不把模型结果当作对任何现实中被命名社会的直接证据。

### 2. 实验基础

本次 full campaign 使用 narrative-first 分析管线，执行了四个实验包：

| Package | 主要设计 | 规模 |
| --- | --- | --- |
| Package A: Everyday Friction | Type A / Type B 不同 horizon 对照 | 2 个 preset x 4 个 horizon x 12 个 seeds |
| Package B: Convenience Transfer | delegation x task-load atlas + threshold refinement | 9 x 5 atlas x 8 个 seeds；5 x 5 refinement x 20 个 seeds |
| Package C: Cheap Service Trap | delegation x service-cost atlas + preset decomposition | 9 x 9 atlas x 8 个 seeds；8 个 decomposition 场景 x 10 个 seeds |
| Package D: Norm Lock-in | delegation x conformity atlas + mixed-system deep dive | 9 x 5 atlas x 8 个 seeds；3 x 3 deep dive x 20 个 seeds |

核心定量分析共使用 2,224 次 summary runs，另加 60 次 story-case runs 用于代表性轨迹与博客图表素材。所有运行都基于当前 Mesa 模型，固定 100 个 agents、小世界网络、显式规则驱动行为，以及外生服务价格。

### 3. 模型范围与边界

解释这些结果时，有三条边界必须明确：

1. `service_cost_factor` 是外生变量。模型可以测试外部价格摩擦如何改变行为，但不能内生地产生价格。
2. 模型没有直接表示 delay tolerance、耐心程度或文化期待的变量。这类问题只能通过 delegation convergence 和 realised delegation behaviour 间接近似。
3. 模型当前衡量的是 labour、stress、efficiency 与 inequality 的代理指标；并不衡量创造力、基础科研、政策质量或现实中的制度安排。

### 4. 结果

#### 4.1 基线对比：便利会重新分配劳动，但不会自动恶化平均福祉

在 60 到 300 steps 的 horizon scan 中，`Type B` 基线在所有 horizon 上都稳定地产生了比 `Type A` 更高的总劳动量，但平均压力更低、可支配时间不平等程度也更低。

| Horizon | Type B 相比 Type A 的总劳动 | Type B 相比 Type A 的平均压力 | Type B 相比 Type A 的时间不平等 | Type B 比 Type A 更高的 delegated task share |
| --- | --- | --- | --- | --- |
| 60 steps | +17.8% | -69.0% | -38.4% | +54.0 个百分点 |
| 120 steps | +18.8% | -69.3% | -36.7% | +54.1 个百分点 |
| 200 steps | +17.3% | -66.6% | -38.1% | +54.2 个百分点 |
| 300 steps | +17.4% | -69.7% | -38.6% | +54.4 个百分点 |

这是本轮实验最关键的结果之一。当前模型支持“高便利系统会让整体总劳动量上升”这一命题。但在当前 preset 假设下，这种额外劳动并没有转化为更高的平均压力。恰恰相反：在观测到的时间范围内，`Type B` 的平均压力更低，社会效率也略高于 `Type A`。

这意味着，当前模型**不支持**“便利导向基线必然在平均福祉上更差”这样的笼统结论。当前模型支持的是一个更窄、更精确的结论：便利会把系统的劳动结构整体抬高，但如果 task pressure 与 service capacity 仍处在可管理范围内，平均压力未必会上升。

#### 4.2 与其说便利消除了劳动，不如说便利转移了劳动

story-case 输出把这种转移机制展示得更具体。代表性 case 的结果如下：

| Story case | Tail 总劳动时长 | Tail 平均压力 | 最终 provider 平均工作时间 | 最终平均 delegated tasks |
| --- | --- | --- | --- | --- |
| Autonomy Baseline | 421.8 | 0.0330 | 121.8 | 59.6 |
| Convenience Baseline | 502.3 | 0.0110 | 953.8 | 536.4 |
| Threshold Pressure | 550.0 | 0.0442 | 696.8 | 385.6 |
| Overloaded Convenience | 611.1 | 0.5486 | 1454.8 | 822.5 |

相对于 autonomy baseline，convenience baseline 产生了：

- 19.1% 更高的总劳动量
- 7.83 倍的 provider 平均工作时间
- 66.7% 更低的平均压力

相对于 autonomy baseline，overloaded convenience case 产生了：

- 11.95 倍的 provider 平均工作时间
- 在更高 task pressure 下显著升高的压力

这强力支持了“劳动转移”这一论点。在当前模型中，便利并不主要表现为工作消失，而是工作被重新分配到提供者时间、匹配容量和服务吞吐之中。便利基线之所以在消费侧看起来更轻松，是因为提供者侧吸收了系统成本。

#### 4.3 当前模型里的主导过载机制是 task pressure，而不是 delegation 本身

Package B 表明，导致系统进入过载的主要驱动力是 task pressure，而不是 delegation 单独作用。

按 task-load 分组的平均结果如下：

| Task load | 平均压力 | 平均总劳动 | 平均时间不平等 | 平均 delegated-task share |
| --- | --- | --- | --- | --- |
| 1.5 | 0.0074 | 303.1 | 0.1580 | 0.2844 |
| 2.0 | 0.0154 | 381.3 | 0.1909 | 0.2902 |
| 2.5 | 0.0340 | 469.0 | 0.2245 | 0.3008 |
| 3.0 | 0.1073 | 554.1 | 0.2581 | 0.3266 |
| 3.5 | 0.7913 | 632.3 | 0.2801 | 0.5199 |

threshold refinement 进一步确认了同样的模式。在被重点追踪的 delegation band 内，平均压力从 task load `3.0` 时的 `0.1511` 跃升至 task load `3.5` 时的 `0.9134`，同时平均总劳动从 `563.2` 增长到 `643.0`。

最高压力的参数格点并不是最高 delegation 的格点，而是集中在极高 task load (`3.5`) 与低到中等 delegation (`0.15` 到 `0.35`) 区间。这一点纠正了一个过于简单的叙事。当前模型并没有告诉我们“更高 delegation 总会带来更严重过载”。它告诉我们的是：当系统进入高吞吐、高负荷状态时，过载会急剧出现，而 delegation 是在这种压力背景下与之相互作用，而不是单独制造过载。

#### 4.4 低价服务确实重要，但它不是全部解释

Package C 单独隔离了外部价格摩擦的影响。当 `service_cost_factor` 较低时，realised delegation 明显更高：

| Service cost factor | 平均 delegated-task share | 平均总劳动 | 平均压力 |
| --- | --- | --- | --- |
| 0.10 | 0.4504 | 462.3 | 0.0199 |
| 0.20 | 0.4566 | 459.9 | 0.0186 |
| 0.50 | 0.3643 | 467.5 | 0.0295 |
| 0.65 | 0.2078 | 475.5 | 0.0497 |
| 0.90 | 0.2870 | 471.3 | 0.0447 |

因此，较低的价格确实会推动系统走向更高 delegation，并且在平均意义上伴随更低压力。但和 task pressure 的变化相比，这一效应仍然相对温和。preset decomposition 尤其说明问题：

| 场景 | Tail 压力 | Tail 总劳动 | Tail delegated fraction |
| --- | --- | --- | --- |
| Type A baseline | 0.034 | 429.1 | 0.091 |
| Type A with economic-friction swap | 0.023 | 420.3 | 0.182 |
| Type A with task-pressure swap | 0.114 | 531.4 | 0.125 |
| Type B baseline | 0.012 | 503.6 | 0.635 |
| Type B with economic-friction swap | 0.018 | 512.2 | 0.529 |
| Type B with task-pressure swap | 0.003 | 398.9 | 0.632 |

这里有两个结论。

第一，低价服务在模型中确实是一个真实驱动器，因为它会提高实际 delegation。第二，低价服务并不是单独足够的解释。与 norm family 的替换相比，task-pressure 的变化对 labour 和 stress 的影响更强，很多时候也强于 price-friction 的变化。因此，当前证据支持“低价服务是更大反馈系统中的一个促成条件”，而不是“唯一主因”。

#### 4.5 混合系统确实更不稳定一些，但效应幅度是中等而非剧烈

Package D 对“中间态是否比极端态更不稳定”提供了部分支持。最终 delegation rate 的跨 seed 波动最大值，确实出现在中间初始条件附近：

| 初始 delegation preference | 最终 delegation 标准差均值 |
| --- | --- |
| 0.10 | 0.0073 |
| 0.40 | 0.0065 |
| 0.45 | 0.0113 |
| 0.50 | 0.0083 |
| 0.55 | 0.0113 |
| 0.80 | 0.0055 |
| 0.90 | 0.0039 |

按 conformity 分组后，最终 delegation 的平均标准差从 conformity `0.0` 时的 `0.0060`，上升到 conformity `0.2` 到 `0.6` 区间的约 `0.0075`。

最不稳定的 mixed-start cell 为：

- 初始 delegation preference `0.45`
- conformity `0.4`
- 最终 delegation 均值 `0.4540`
- 最终 delegation 标准差 `0.0113`
- 不同 seeds 间最终 delegation 范围 `0.4343` 到 `0.4769`

这说明当前模型中的中间区间确实比极端区间更容易出现波动。但这个扩散范围仍然比较窄。当前参数设定下，模型**没有**呈现出明显的、戏剧性的“两极分裂”。因此，更稳妥的结论是：

- `H4` 只能得到**部分支持**
- 中间区间比极端区间更不稳定
- 但这种不稳定是轻到中度，而不是强烈分裂成不同 basin

#### 4.6 关于“系统是否会训练出更快期待”的当前结论

此前反思提出了一个问题：系统是否会训练人去期待更快响应。当前模型无法直接回答，因为它没有显式的 delay-tolerance 变量。当前模型能显示的是更有限的内容：

- 更低价格与更高 conformity 会让 realised delegation 更容易持续
- 高便利状态下，实际上的非委托行为会变得更少
- 在 norm pressure 下，中间状态会变得更依赖路径

这些可以作为某种 lock-in 的代理证据，但它们不是对耐心、等待时的情绪反应、或即时性期待的直接测量。任何更强的表述都会超出当前模型边界。

### 5. 与先前反思问题的对照

此前反思文提出了若干更宽泛的问题。当前 campaign 对它们给出的回答如下：

| 将问题抽象化后的表述 | 当前结果判断 | 说明 |
| --- | --- | --- |
| 日常小摩擦是否是更深层系统结构的信号，而不是孤立烦恼？ | 支持 | preset horizon scan 显示不同 horizon 上劳动配置、delegation 与时间不平等存在稳定差异。 |
| 便利是在节省劳动，还是在转移劳动？ | 强支持“转移劳动” | convenience-heavy regime 中，总劳动与 provider time 都上升。 |
| 低价服务是否是便利依赖的主要原因？ | 部分支持 | 低价确实提升 delegation，但 task pressure 是更强的过载驱动因素。 |
| 系统是否会训练出更快期待，并让退出变难？ | 只能间接支持 | 模型显示了 norm convergence 和 convenience lock-in 的代理迹象，但没有直接测量 delay tolerance。 |
| 混合系统是否不稳定？ | 部分支持 | 中间起点的波动更大，但并没有强烈分裂。 |
| 这个模型能否解释更高层的产出，如创造力、科研或宏观发展轨迹？ | 不支持 | 这些结果变量并不在当前模型中。 |

### 6. 主要结论

对当前 full campaign 证据最严格的总结如下：

1. 当前模型更强地支持 **convenience transfer** 命题，而不是笼统的 **convenience harm** 命题。
2. 在当前 presets 下，便利导向基线需要更多总劳动，但并不会带来更高的平均压力；相反，它的平均压力更低。
3. 最清晰的过载机制是 **高 task pressure**，而不是 delegation 单独作用。
4. 低价服务确实重要，但在当前模型里它更像更大反馈系统中的促成因素，而不是唯一原因。
5. 混合系统确实比极端系统更不稳定一些，但当前证据表现为中等强度，而不是戏剧性的分裂。

### 7. 对先前反思的意义

此前反思之所以有分析价值，是因为它提出了正确类型的系统性问题。但当前仿真并不会同等力度地支持每一种直觉怀疑。

它支持“便利可能在总体劳动上很昂贵”这一点，也支持“消费侧的轻松可能建立在提供者侧的隐形劳动之上”这一点。但在当前假设下，它并不支持“便利导向基线必然让平均福祉更差”这一更强说法。它同样不支持关于创造力、科研或文明层面产出的推断。

因此，当前结果收窄了论证空间。最稳妥的表述不是“便利是坏的”，而是：

> 便利可以在主观体验上依然舒适，同时在客观上变得更加劳动密集；而当 task pressure 上升到足以暴露隐藏 provider burden 的程度时，这种便利会变得脆弱。

### 8. 建议的下一轮模型扩展

如果下一轮研究想更直接回答此前反思中仍未解决的部分，最值得优先扩展的机制是：

1. 内生服务定价与提供者稀缺。
2. 显式的 delay-tolerance 或 expected-response-time 变量。
3. 在重复 delegation 下的 skill retention 或 skill decay。
4. 异质化 agent classes，而不是单一的 generic resident population。

在没有这些扩展之前，当前模型最适合用来分析 labour transfer、overload threshold、norm sensitivity 与时间分配不平等。

### 9. 参数说明

本节总结当前 campaign 中实际使用到的参数。下面的定义以 `model/params.py`、`model/agents.py` 与 `model/model.py` 中的实现为准。

#### 9.1 核心模型参数

| 参数 | 含义 | 取值范围 / 类型 | 默认运行值 | Type A preset | Type B preset |
| --- | --- | --- | --- | --- | --- |
| `num_agents` | 仿真中的居民数量 | 整数 | 100 | 100 | 100 |
| `delegation_preference_mean` | 初始“委托而非自助处理”的平均倾向 | `[0,1]` | 0.50 | 0.25 | 0.72 |
| `delegation_preference_std` | 初始委托倾向的异质性 | float | 0.10 | 0.10 | 0.10 |
| `service_cost_factor` | 外生服务价格倍率，按任务基准时间计费 | float | 0.40 | 0.65 | 0.20 |
| `social_conformity_pressure` | 同伴影响行为漂移的强度 | `[0,1]` | 0.30 | 0.15 | 0.65 |
| `tasks_per_step_mean` | 每个 agent 每天收到的平均任务数 | tasks/day | 2.5 | 2.2 | 2.8 |
| `tasks_per_step_std` | 每日任务数波动 | tasks/day | 0.75 | 0.70 | 0.80 |
| `initial_available_time` | 每天开始时的可支配时间预算 | hours/day | 8.0 | 8.0 | 8.0 |
| `stress_threshold` | 低于该剩余时间后，压力开始累积 | hours | 2.5 | 2.5 | 2.5 |
| `stress_recovery_rate` | 当日剩余时间高于阈值时，压力恢复速度 | stress units/step | 0.10 | 0.10 | 0.10 |
| `adaptation_rate` | 委托偏好更新速度 | preference units/step | 0.03 | 0.02 | 0.05 |
| `network_type` | 同伴影响的社会网络拓扑 | `small_world` / `random` | `small_world` | `small_world` | `small_world` |
| `seed` | 复现实验的随机种子 | 整数 | 42 | 42 | 42 |

#### 9.2 任务菜单参数

| 任务类型 | 基准时间 | 技能要求 | 含义 |
| --- | --- | --- | --- |
| `domestic` | 0.8 小时 | 0.30 | 日常家务 |
| `administrative` | 1.2 小时 | 0.50 | 文书、银行、安排事务 |
| `errand` | 0.5 小时 | 0.20 | 购物、取件、短程跑腿 |
| `maintenance` | 1.5 小时 | 0.65 | 维修与维护类任务 |

#### 9.3 行为规则中的结构常数

这些值不是当前 campaign 直接 sweep 的参数，但它们会实质性影响行为：

| 常数 | 数值 | 作用 |
| --- | --- | --- |
| Provider proficiency | 0.60 | agent 作为服务提供者时的固定效率 |
| Forced-delegation threshold | `available_time < 0.5 x task_time` | 当一天过满时，委托变成“被迫”行为 |
| Stress boost coefficient | 0.30 | agent 已有压力时，会进一步推高委托倾向 |
| Skill-gap weight | 0.25 | 把任务技能不匹配转换成更高或更低的委托压力 |
| Cost-penalty weight | 0.25 | 把服务价格转换为委托抑制 |
| Stress amplification of conformity | `1 + 0.5 x stress_level` | 压力越大，越容易受同伴规范影响 |
| Stress accumulation coefficient | 0.10 | 时间赤字下压力上升速度 |
| 小世界网络参数 | `k=4`, `p=0.1` | 默认的局部聚类与短路径结构 |
| 随机网络连边概率 | `4 / (num_agents - 1)` | 用于拓扑稳健性比较 |

### 10. 数学机制与参数联动

本节用数学形式说明仿真规则，以当前代码实现为准，而不是设计文档中的简化叙述。

#### 10.1 每日任务生成

对于第 `t` 天的 agent `i`，任务数量为：

`n_{i,t} = max(1, round(N(mu_tasks, sigma_tasks)))`

其中：

- `mu_tasks = tasks_per_step_mean`
- `sigma_tasks = tasks_per_step_std`

因此，`tasks_per_step_mean` 改变的是整体工作负荷水平，而 `tasks_per_step_std` 改变的是工作负荷的波动性。

#### 10.2 任务时间成本

对于任务 `j`，其基准时间为 `b_j`，技能要求为 `r_j`，agent 熟练度为 `s_{i,j}`。模型先将熟练度截断为：

`s* = clip(s_{i,j}, 0.1, 1.0)`

基础执行时间为：

`c_base = b_j / s*`

如果该 agent 的技能低于任务要求，则额外施加不匹配惩罚：

- 若 `s* < r_j`，则 `c_{i,j} = c_base x (1 + 2 x (r_j - s*))`
- 否则 `c_{i,j} = c_base`

这会让“低技能处理高门槛任务”的代价呈非线性上升，尤其体现在 maintenance 与 administrative 任务上。

#### 10.3 委托决策

如果 agent 剩余时间过少，则直接被迫委托：

`if available_time < 0.5 x c_{i,j}, then delegate = 1`

否则，模型构造一个有效委托概率：

`p_eff = clip(p_i + 0.30 x stress_i + 0.25 x (r_j - s_{i,j}) - 0.25 x cost, 0, 1)`

其中：

- `p_i = delegation_preference`
- `stress_i = stress_level`
- `cost = service_cost_factor`

随后再采样：

`delegate_{i,j} ~ Bernoulli(p_eff)`

这是模型里最核心的联动公式：

- 更高的 `delegation_preference_mean` 会抬高基线委托倾向
- 更高的 `stress_level` 会把更多任务推向委托
- 当技能低于任务要求时，更容易委托
- 更高的 `service_cost_factor` 会压低委托概率

#### 10.4 服务提供与付费

如果任务被匹配到 provider，则 provider 使用固定熟练度 `0.60` 来执行：

`c_provider,j = c_j(s = 0.60)`

请求者支付费用：

`fee_j = b_j x service_cost_factor`

请求者收入减少该数值，provider 收入增加相同数值。由于 provider 的效率是固定的而且不具备个体化优势，所以 delegation 往往会在主观便利之外引入额外时间开销。

#### 10.5 服务匹配

每个被委托任务的 provider 候选必须满足：

- `provider_id != requester_id`
- `provider.available_time >= 0.5 x base_time`

在候选者中，模型选择：

`provider* = argmax_k available_time_k`

这是一种贪心式容量分配规则。它不是市场清算模型，也不内生化工资、排队或 provider 专业化。

#### 10.6 压力动态

每天结束时，如果剩余时间低于阈值：

`deficit_ratio = (stress_threshold - available_time) / stress_threshold`

`stress_{t+1} = min(1, stress_t + 0.10 x deficit_ratio)`

否则，压力恢复为：

`stress_{t+1} = max(0, stress_t - stress_recovery_rate)`

因此，`stress_threshold` 决定何时开始进入压力累积区，`stress_recovery_rate` 决定当 agent 拥有足够时间后，恢复得有多快。

#### 10.7 偏好更新与规范扩散

设 `N(i)` 为 agent `i` 的邻居集合，则局部规范为：

`m_i = mean_{k in N(i)}(delegation_preference_k)`

从众权重为：

`w_i = social_conformity_pressure x (1 + 0.5 x stress_i)`

偏好更新为：

`delta_i = w_i x (m_i - p_i)`

`p_{i,t+1} = clip(p_{i,t} + adaptation_rate x delta_i, 0, 1)`

这个公式解释了为什么 `social_conformity_pressure` 与 `adaptation_rate` 是乘法联动关系。高 conformity 但低 adaptation，行为漂移仍然较慢；高 conformity 且高 adaptation，则会产生更快的规范收敛。

#### 10.8 模型级指标

主要输出指标计算如下：

- `avg_stress = mean_i(stress_i)`
- `avg_delegation_rate = mean_i(delegation_preference_i)`
- `total_labor_hours = sum_i(initial_available_time_i - available_time_i)`
- `tasks_delegated_frac = step_tasks_delegated / step_tasks_total`
- `unmatched_tasks = step_tasks_delegated - step_tasks_matched`

社会效率定义为：

`social_efficiency = (tasks_self_served + tasks_matched) / total_labor_hours`

其中：

- `tasks_self_served = step_tasks_total - step_tasks_delegated`
- `tasks_matched = 成功匹配到 provider 的委托任务数`

收入和可支配时间不平等用 Gini 系数表示：

`G = sum_i sum_j |x_i - x_j| / (2 x n x sum_i x_i)`

#### 10.9 用通俗语言理解参数联动

最重要的参数联动关系有：

1. `delegation_preference_mean` x `service_cost_factor`
   更低价格与更高基线委托偏好，会共同提高实际 delegation。
2. `delegation_preference_mean` x `tasks_per_step_mean`
   只有当总工作负荷足够高、provider capacity 被压紧时，高 delegation 才会真正变危险。
3. `social_conformity_pressure` x `adaptation_rate`
   这两者共同决定局部规范在网络中扩散的速度。
4. `stress_threshold` x `initial_available_time` x 任务时间成本
   这三者共同决定 agent 多容易进入压力累积状态。
5. `任务技能要求` x `agent 技能抽样`
   这决定了哪些任务天然更容易自助完成，哪些更容易被委托出去。

### 11. 各实验参数设置

#### 11.1 Campaign 级设置

本次 full campaign 使用：

- `scale = full`
- `workers = 8`
- `num_agents = 100`
- 默认 `network_type = small_world`
- `delegation_threshold_band = [0.15, 0.20, 0.25, 0.30, 0.35]`，用于 threshold refinement

#### 11.2 Package A: Everyday Friction

Package A 直接使用两个 society presets：

| 场景 | delegation mean | delegation std | service cost | conformity | tasks mean | tasks std | available time | stress threshold | recovery | adaptation | steps | seeds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Type A preset | 0.25 | 0.10 | 0.65 | 0.15 | 2.2 | 0.7 | 8.0 | 2.5 | 0.10 | 0.02 | 60, 120, 200, 300 | 12 |
| Type B preset | 0.72 | 0.10 | 0.20 | 0.65 | 2.8 | 0.8 | 8.0 | 2.5 | 0.10 | 0.05 | 60, 120, 200, 300 | 12 |

这个 package 的目的，是把 preset 作为整套系统配置来比较，而不是拆解单一参数。

#### 11.3 Package B: Convenience Transfer

主 atlas 以默认参数集为锚点：

| 固定参数 | 数值 |
| --- | --- |
| delegation std | 0.10 |
| service cost | 0.40 |
| conformity | 0.30 |
| tasks std | 0.75 |
| available time | 8.0 |
| stress threshold | 2.5 |
| recovery | 0.10 |
| adaptation | 0.03 |
| network | `small_world` |

被 sweep 的参数为：

| Sweep | 取值 | Steps | Seeds |
| --- | --- | --- | --- |
| `delegation_preference_mean` | 0.10 到 0.90，每 0.10 一个点 | 150 | 8 |
| `tasks_per_step_mean` | 1.5, 2.0, 2.5, 3.0, 3.5 | 150 | 8 |

threshold refinement 仍保持默认锚点，只改为：

| Sweep | 取值 | Steps | Seeds |
| --- | --- | --- | --- |
| `delegation_preference_mean` | 0.15, 0.20, 0.25, 0.30, 0.35 | 250 | 20 |
| `tasks_per_step_mean` | 1.5, 2.0, 2.5, 3.0, 3.5 | 250 | 20 |

Package B 中选取的 story cases 为：

| Story case | delegation mean | service cost | conformity | tasks mean | tasks std | steps | seeds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Threshold Pressure | 0.55 | 0.40 | 0.40 | 3.0 | 0.75 | 300 | 10 |
| Overloaded Convenience | 0.72 | 0.20 | 0.80 | 3.5 | 0.80 | 300 | 10 |

#### 11.4 Package C: Cheap Service Trap

Package C 同样以默认参数集为锚点，然后 sweep：

| Sweep | 取值 | Steps | Seeds |
| --- | --- | --- | --- |
| `delegation_preference_mean` | 0.10 到 0.90，每 0.10 一个点 | 120 | 8 |
| `service_cost_factor` | 0.10 到 0.90，每 0.10 一个点 | 120 | 8 |

preset decomposition 对每个场景运行 200 steps、10 个 seeds。场景构造方式为：

| 场景 | 基础锚点 | 被替换的参数 |
| --- | --- | --- |
| `type_a_baseline` | Type A | 无 |
| `type_a_with_economic_friction` | Type A | `service_cost_factor <- 0.20` |
| `type_a_with_norm_lock_in` | Type A | `social_conformity_pressure <- 0.65`, `adaptation_rate <- 0.05` |
| `type_a_with_task_pressure` | Type A | `tasks_per_step_mean <- 2.8`, `tasks_per_step_std <- 0.8` |
| `type_b_baseline` | Type B | 无 |
| `type_b_with_economic_friction` | Type B | `service_cost_factor <- 0.65` |
| `type_b_with_norm_lock_in` | Type B | `social_conformity_pressure <- 0.15`, `adaptation_rate <- 0.02` |
| `type_b_with_task_pressure` | Type B | `tasks_per_step_mean <- 2.2`, `tasks_per_step_std <- 0.7` |

Package C 的 story case 为：

| Story case | delegation mean | service cost | conformity | tasks mean | tasks std | steps | seeds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cheap but Low-Conformity | 0.55 | 0.20 | 0.15 | 2.5 | 0.75 | 300 | 10 |

#### 11.5 Package D: Norm Lock-in

Package D 同样以默认参数集为锚点，然后 sweep：

| Sweep | 取值 | Steps | Seeds |
| --- | --- | --- | --- |
| `delegation_preference_mean` | 0.10 到 0.90，每 0.10 一个点 | 150 | 8 |
| `social_conformity_pressure` | 0.0, 0.2, 0.4, 0.6, 0.8 | 150 | 8 |

mixed-system deep dive 使用：

| Sweep | 取值 | Steps | Seeds |
| --- | --- | --- | --- |
| `delegation_preference_mean` | 0.45, 0.50, 0.55 | 250 | 20 |
| `social_conformity_pressure` | 0.2, 0.4, 0.6 | 250 | 20 |

Package D 的 story case 为：

| Story case | delegation mean | service cost | conformity | tasks mean | tasks std | steps | seeds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Mixed and Unstable | 0.50 | 0.40 | 0.40 | 2.5 | 0.75 | 300 | 10 |

这些 package 级设置会直接影响解释方式。例如，Package D 之所以能隔离 norm lock-in，是因为价格与 task-load 固定在默认锚点，只改变 conformity；Package B 之所以能更清楚地识别 overload，是因为 service cost 与 conformity 保持不变，而 workload 与 delegation 被同时移动。
