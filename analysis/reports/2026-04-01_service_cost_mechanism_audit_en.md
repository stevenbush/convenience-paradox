# Service-Cost Mechanism Audit

**Date**: 2026-04-01  
**Stable campaign**: `20260401_125557_full_campaign`  
**Engine**: `stable` (`ConvenienceParadoxModel`)  
**Purpose**: Explain the current counter-intuitive findings before any research-only mechanism changes are interpreted.

## Scope

This audit answers five questions raised from the current full-campaign report:

1. How does `service_cost_factor` affect delegation, labor, and stress?
2. Why does lower `service_cost_factor` coincide with lower average total labor in the current model?
3. Why can a more convenience-oriented baseline show lower average stress?
4. Why is overload currently dominated by task pressure rather than delegation itself?
5. Do the present results suggest a parameter problem, a formula problem, or a scan-range problem?

This document only interprets the **current stable model**. It does not use any `research_v2` results.

## Short Answer

The current result is structurally consistent with the stable model. It is not mainly a noise issue.

Three stable-model facts explain most of the pattern:

1. Lower `service_cost_factor` reliably raises realised delegation.
2. In the stable model, delegation usually reduces requester time burden more than it increases provider-side burden.
3. Capacity scarcity almost never activates, because unmatched delegated tasks are near zero across the current atlases.

Under those conditions, cheap service acts like a pressure-release valve rather than a trap amplifier.

## Evidence 1: What `service_cost_factor` does in the stable model

From Package C (`delegation_service_cost_atlas`), averaging across the delegation grid:

| service_cost_factor | delegated-task share | total labor hours | avg stress | unmatched tasks |
| --- | ---: | ---: | ---: | ---: |
| 0.10 | 0.4504 | 462.2840 | 0.0199 | 0.0 |
| 0.20 | 0.4282 | 461.4940 | 0.0214 | 0.0 |
| 0.30 | 0.4054 | 463.8227 | 0.0233 | 0.0 |
| 0.40 | 0.3844 | 465.2832 | 0.0276 | 0.0 |
| 0.50 | 0.3643 | 467.4845 | 0.0295 | 0.0 |
| 0.60 | 0.3426 | 466.5026 | 0.0316 | 0.0 |
| 0.70 | 0.3246 | 469.0505 | 0.0365 | 0.0 |
| 0.80 | 0.3050 | 469.9562 | 0.0402 | 0.0 |
| 0.90 | 0.2870 | 471.3211 | 0.0447 | 0.0 |

Within every fixed `delegation_preference_mean` slice in that atlas:

- higher cost strongly reduces realised delegation
- higher cost raises total labor
- higher cost raises stress

So the current stable result is not just a coarse averaging artifact. Even within fixed delegation-preference slices, cheaper service is associated with lower labor and lower stress.

## Evidence 2: Why lower service cost can lower labor in the stable model

This is the key mechanism issue.

In the stable model, provider execution is often faster than average self-service.

Using the implemented task-time formula and the stable assumptions:

- agents’ self-service skill is drawn uniformly from `0.3` to `0.9`
- provider skill is fixed at `0.6`
- task time rises sharply when skill is below the task requirement

Expected task times:

| task type | mean self time | provider time at skill 0.6 | provider vs mean self |
| --- | ---: | ---: | ---: |
| domestic | 1.4653 | 1.3333 | -9.0% |
| administrative | 2.4206 | 2.0000 | -17.4% |
| errand | 0.9158 | 0.8333 | -9.0% |
| maintenance | 3.5120 | 2.7500 | -21.7% |
| overall mean | 2.0785 | 1.7292 | -16.8% |

So in the current model, delegation is not labor-neutral. It is usually labor-saving in pure time accounting.

That means:

- when service gets cheaper, more tasks move into a mode that is often faster than average self-service
- requester time is relieved
- provider time rises, but not enough to offset the requester-side time saving
- total labor can therefore fall instead of rise

This is the main reason the stable model can produce “cheap service -> more delegation -> lower labor”.

## Evidence 3: Why lower service cost can also lower stress

In the stable model, stress is driven by end-of-day remaining time, not by delegation itself.

The stress update only depends on whether `available_time` falls below `stress_threshold`. There is:

- no direct stress penalty for delegating
- no direct stress penalty for relying on services
- no explicit waiting-cost variable
- no patience or expectation variable

Given the time-accounting structure above, cheap service lowers stress through the simplest available channel:

- cheaper service -> more delegation
- more delegation -> less requester-side time spent on own tasks
- less time depletion -> more agents stay above the stress threshold
- more agents above threshold -> lower average stress

This is why “cheap service accompanies lower stress” is not actually inconsistent with the current formula set.

## Evidence 4: Why scarcity is not biting in the stable model

The current overload story does **not** become a self-reinforcing delegation crisis because provider scarcity is too weakly expressed.

Two stable-model details matter:

1. Provider eligibility is permissive. A provider only needs `0.5 * base_time` in spare time to accept a task.
2. Unmatched delegated tasks are counted in `unmatched_tasks`, but they are not carried into the next step as backlog.

Empirically, this matters a lot:

- in the stable Package C cost atlas, mean `unmatched_tasks = 0.0` at every cost level
- in the stable Package B delegation x task-load atlas, maximum `tail_unmatched_tasks_mean = 0.0` in every cell, even at task load `3.5`

So the current model almost never enters a “delegation demand overwhelms supply, then backlog compounds tomorrow’s pressure” regime.

That is why the intuitive vicious cycle does not fully appear:

- more delegation does increase provider work
- but unmet demand is not carried forward
- and matching almost always succeeds
- so the system does not accumulate a persistent service backlog

## Evidence 5: Why the convenience baseline can show lower average stress

At 200 steps, the stable Package A baseline comparison is:

| scenario | tail avg stress | tail total labor | tail delegated share | final mean available time | final p10 available time | final p90 available time | time Gini |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Type A baseline | 0.0346 | 429.4746 | 0.0899 | 3.6915 | 0.9868 | 5.5850 | 0.2578 |
| Type B baseline | 0.0116 | 503.6110 | 0.6324 | 2.9793 | 1.8181 | 3.9169 | 0.1596 |

The stable Type B baseline uses more total labor, but its remaining-time distribution is tighter:

- lower mean free time than Type A
- much higher bottom-decile free time than Type A
- much lower time inequality than Type A

That combination is enough to lower mean stress, because stress is threshold-based.

In other words, the stable model is currently saying:

- convenience raises aggregate labor
- but it redistributes daily time pressure in a way that leaves fewer people deep below the stress threshold

This is why average stress can be lower even when total labor is higher.

## Evidence 6: Why task pressure dominates overload in the stable model

From stable Package B, mean outcomes by task load:

| task load | avg stress | total labor | time inequality | delegated share | unmatched tasks |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1.5 | 0.0058 | 298.8235 | 0.1422 | 0.3719 | 0.0 |
| 2.0 | 0.0120 | 376.5141 | 0.1716 | 0.3756 | 0.0 |
| 2.5 | 0.0269 | 464.2865 | 0.2021 | 0.3839 | 0.0 |
| 3.0 | 0.0829 | 549.0548 | 0.2352 | 0.4039 | 0.0 |
| 3.5 | 0.7235 | 626.3568 | 0.2638 | 0.5858 | 0.0 |

Within each fixed task-load slice:

- correlation(`delegation_preference_mean`, `total_labor`) is strongly negative
- correlation(`delegation_preference_mean`, `avg_stress`) is also negative

So under the stable mechanics, delegation behaves more like a shock absorber inside a fixed task-load slice, while task-load increases are what actually push the system across the stress threshold.

That is why the current model supports the statement:

> the dominant overload mechanism is task pressure, not delegation itself.

This is not because delegation is unimportant. It is because the stable model currently lacks a strong enough backlog-and-scarcity channel for delegation to become a durable overload amplifier.

## Diagnosis: is there a model problem?

Yes, but it is a **mechanism-coverage problem**, not simply “wrong numbers”.

The main stable-model gaps are:

1. **No backlog carryover**  
   Unmatched delegated tasks do not return as tomorrow’s burden.

2. **No requester coordination cost**  
   Delegating consumes money, but almost no time.

3. **Provider-side service is too efficient on average**  
   Fixed provider skill `0.6` is faster than mean self-service for the current skill distribution.

4. **Matching capacity is too permissive**  
   Candidate providers need only `0.5 * base_time` spare time, not the full expected service time.

5. **Stress is threshold-only**  
   There is no explicit penalty for waiting, uncertainty, failed handoff, or dependence on services.

These are exactly the kinds of omissions that can suppress the vicious cycle you expected to see.

## Is the scan range too narrow?

Partly, yes.

The stable scan already shows that high task load can create a sharp overload jump. But it still does not expose a genuine delegation-capacity crisis because the model almost never produces persistent shortage.

So the issue is not only the scan range. It is:

- scan range plus
- missing backlog dynamics plus
- overly forgiving provider matching plus
- overly efficient service execution

## Stable-model interpretation of the five user questions

1. **How should we understand `service_cost_factor`?**  
   In the stable model it mainly changes delegation uptake, not service capacity. Lower cost raises realised delegation and, under current mechanics, lowers both labor and stress.

2. **Why does low cost reduce average labor?**  
   Because delegated execution is often faster than mean self-service, and requesters pay almost no time cost to hand tasks off.

3. **Why can a more delegation-friendly society have lower average stress?**  
   Because stress is driven by remaining time below a threshold, and delegation currently helps keep more agents above that threshold.

4. **Why doesn’t the model show a strong self-reinforcing delegation spiral?**  
   Because backlog does not accumulate and matching nearly always succeeds, so service scarcity does not propagate.

5. **Does this imply preset or formula problems?**  
   It points to missing mechanism coverage and permissive formulas, not necessarily bad preset intent.

## Next Step

The correct next step is **not** to rewrite the dashboard model. It is to run a separate research engine that:

- keeps the stable dashboard contract untouched
- adds backlog carryover
- adds requester coordination time
- adds provider service friction
- makes provider eligibility depend on expected service time
- records explicit labor sub-accounts and match-rate metrics

That is exactly what `ConvenienceParadoxResearchModel` is designed to do.
