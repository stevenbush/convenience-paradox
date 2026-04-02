# Service-Cost Research Rerun Report

**Date**: 2026-04-01  
**Stable comparison campaign**: `20260401_125557_full_campaign`  
**Research rerun campaign**: `20260401_223144_service_cost_research_v2_progress`  
**Research engine**: `ConvenienceParadoxResearchModel`  
**Elapsed runtime**: `34m 47s`  
**Supplemental metric probe**: `data/results/campaigns/20260401_223144_service_cost_research_v2_progress/summaries/research_metric_probe.csv`

## 1. What changed in `research_v2`

The rerun kept the dashboard-facing stable model untouched and moved all mechanism changes into the research engine:

- requester coordination time cost
- stricter provider eligibility based on expected service time
- provider-side service overhead
- unmatched delegated tasks returned as backlog
- research-only stress/capacity reporters

This matters because the old stable model could explain why cheap service lowered stress, but it could not express a real delegation-capacity crisis. `research_v2` was designed to test exactly that missing channel.

## 2. Headline result

The rerun changed the interpretation in an important but not absolute way:

1. The convenience-heavy baseline is no longer lower-stress than the autonomy baseline.
2. Cheap service still lowers stress in low-load contexts.
3. But once task pressure reaches about `3.0` tasks/step, cheap service starts to **raise** stress because backlog and match failure finally enter the dynamics.
4. The overload mechanism is now a **task-pressure x delegation x capacity** interaction rather than task pressure alone.

So the original intuition was partly right, but only after the missing scarcity channel was restored.

## 3. Baseline comparison: old result vs new result

At 200 steps:

| Scenario | Stable stress | Research stress | Stable labor | Research labor | Stable delegated share | Research delegated share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Type A baseline | 0.0346 | 0.0413 | 429.47 | 436.27 | 0.0899 | 0.0947 |
| Type B baseline | 0.0116 | 0.0492 | 503.61 | 565.18 | 0.6324 | 0.6465 |

This is the single biggest qualitative reversal in the rerun.

Under the stable engine, Type B used more labor but looked less stressful. Under `research_v2`, Type B still uses more labor, but it is now also more stressful than Type A.

That means the earlier “convenience baseline lowers average stress” result was not robust. It depended on missing requester-side coordination costs and missing backlog mechanics.

## 4. What `service_cost_factor` now does

### 4.1 Default context

In the fixed default context, low cost still lowers stress, but it no longer lowers total labor.

| service_cost_factor | Stable avg stress | Research avg stress | Stable labor | Research labor | Stable delegated share | Research delegated share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.10 | 0.0199 | 0.0209 | 462.28 | 501.39 | 0.4504 | 0.4493 |
| 0.90 | 0.0447 | 0.0346 | 471.32 | 494.00 | 0.2870 | 0.2584 |

So the rerun produced a cleaner answer to your earlier concern:

- low cost still encourages delegation
- low cost still reduces stress in manageable contexts
- but low cost now increases total labor rather than decreasing it

This is much closer to the intuition that convenience expands system work even when it remains locally comfortable.

### 4.2 Type A and Type B anchored contexts

- In the Type A context, low cost strongly lowers stress and raises delegation.
- In the Type B context, low cost still lowers stress, but only modestly.
- In the overloaded convenience context, stress is already saturated at `1.0` for all costs; cheaper service mainly makes the backlog explosion worse.

That means `service_cost_factor` is not a universal monotone “bad/good” parameter. Its effect depends strongly on the surrounding task-load regime.

## 5. The threshold: where cheap service flips from relief to overload

The new `service_cost x task_load` atlas gives the clearest answer.

### Mid-delegation slice (`delegation_preference_mean = 0.55`)

| Task load | Stress at cost 0.05 | Stress at cost 1.00 | Low-cost minus high-cost |
| --- | ---: | ---: | ---: |
| 2.50 | 0.0160 | 0.0314 | -0.0154 |
| 3.00 | 0.2826 | 0.2044 | +0.0782 |
| 3.50 | 1.0000 | 1.0000 | 0.0000 |

### High-delegation slice (`delegation_preference_mean = 0.72`)

| Task load | Stress at cost 0.05 | Stress at cost 1.00 | Low-cost minus high-cost |
| --- | ---: | ---: | ---: |
| 2.50 | 0.0135 | 0.0203 | -0.0068 |
| 3.00 | 0.4619 | 0.2130 | +0.2489 |
| 3.50 | 1.0000 | 1.0000 | 0.0000 |

This is the main threshold result:

- below about `2.75`, cheap service still behaves as a relief valve
- around `3.0`, the sign flips
- above `3.5`, both low-cost and high-cost cells are saturated, but cheap service typically reaches collapse sooner and with more backlog

So the answer to “why didn’t the old model show the vicious cycle?” is now much clearer:

- the vicious cycle does not dominate everywhere
- it emerges after a capacity threshold
- the stable model failed to represent that threshold properly

## 6. Why stress rises under cheap service in the overloaded regime

The supplemental research probe gives the missing mechanism detail.

### Mid-delegation, task load `3.0`

| Cost | Stress | Backlog | Match rate | Stress-breach share |
| --- | ---: | ---: | ---: | ---: |
| 0.05 | 0.2826 | 0.3500 | 0.9981 | 0.6551 |
| 1.00 | 0.2044 | 0.0000 | 1.0000 | 0.5821 |

### High-delegation, task load `3.0`

| Cost | Stress | Backlog | Match rate | Stress-breach share |
| --- | ---: | ---: | ---: | ---: |
| 0.05 | 0.4619 | 1.3250 | 0.9949 | 0.7146 |
| 1.00 | 0.2130 | 0.2250 | 0.9987 | 0.6191 |

### Overloaded convenience context

| Cost | Stress | Backlog | Match rate | Delegated share |
| --- | ---: | ---: | ---: | ---: |
| 0.05 | 1.0000 | 47559.7083 | 0.0000 | 0.9975 |
| 1.00 | 1.0000 | 11693.8333 | 0.0007 | 0.9717 |

So the mechanism is now transparent:

1. Cheap service raises realised delegation.
2. Higher delegation pushes more tasks into the service pool.
3. Once provider capacity becomes tight, some tasks fail to match.
4. Those tasks now return as backlog.
5. Backlog consumes future time and pushes more agents below the stress threshold.

This is the missing loop that the stable model could not generate.

## 7. Direct answers to the original five questions

### Q1. Should we focus on `service_cost_factor`?

Yes, but not in isolation. The rerun shows that `service_cost_factor` is strongly context-dependent:

- low-load context: lower cost reduces stress and raises delegation
- medium/high-load context: lower cost can raise stress by triggering backlog
- extreme overload: stress saturates regardless of cost, but lower cost worsens collapse speed and backlog size

### Q2. Why did low cost previously lower labor and stress?

Because the stable model made delegation too easy and too frictionless:

- requester coordination had almost no time cost
- provider matching was too permissive
- failed delegation did not carry over
- provider execution remained too efficient on average

### Q3. Why did a more convenience-oriented society previously look less stressed?

Because the stable model mainly redistributed time burden without activating scarcity. Once coordination cost and backlog return were introduced, the convenience baseline stopped looking lower-stress.

### Q4. Why didn’t the old model show a strong delegation spiral?

Because there was no durable backlog channel. The rerun now shows that the spiral appears after the task-load threshold, not at every delegation level.

### Q5. Were the old results caused by bad presets or bad formulas?

Mostly by incomplete mechanism coverage rather than by preset intent. The rerun indicates that the central issue was missing capacity-friction dynamics.

## 8. Important remaining issue

One research-only metric still needs redesign: `delegation_labor_delta`.

It remains negative in many low-load cells, and in severe overload it becomes extremely negative. That does **not** mean overload is “efficient”. It means the current metric compares delegated-task execution against self-service counterfactuals without fully capitalising deferred backlog as outstanding future work.

So the metric is still useful directionally in low-backlog cells, but it is not yet a reliable welfare summary once backlog explodes.

This suggests one more calibration step is needed:

- either raise provider overhead further
- or replace `delegation_labor_delta` with a backlog-adjusted outstanding-work measure

## 9. Bottom line

The rerun resolved the main conceptual problem.

- The old result “cheap service lowers stress” was too broad.
- The new result is more precise:

> Cheap service lowers stress only while the system remains below a provider-capacity threshold. Once task pressure is high enough, cheap service accelerates delegation, creates backlog, and raises stress.

That is the strongest defensible interpretation of the current evidence.
