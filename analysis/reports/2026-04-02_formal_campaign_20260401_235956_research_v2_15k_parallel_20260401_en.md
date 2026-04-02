# Formal Research Report: `20260401_235956_research_v2_15k_parallel_20260401`

**Date**: 2026-04-02  
**Campaign directory**: `data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401`  
**Engine**: `research_v2`  
**Asset manifest**: [formal report manifest](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/formal_report_manifest.json>)

## Abstract

This report examines the most complete `research_v2` campaign currently available for *The Convenience Paradox* and reworks it into a paper-style, white-box analysis package. The study is motivated by repeated everyday observations that some social settings feel more convenience-heavy while others preserve wider autonomy and time boundaries. The report does **not** treat those observations as conclusions. Instead, it translates them into explicit mechanism questions, tests them in an abstract agent-based model, and evaluates only what the model and campaign outputs can honestly support.

The campaign covers 1146 aggregated scenario cells, 13346 seed-level summary rows, and 1088 additional refinement rows, all generated from the research-only engine with backlog carryover, stricter matching, and explicit labor-delta accounting. Three findings are especially robust. First, higher delegation is consistently associated with higher total system labor, with the Type B baseline retaining a 30.01% labor premium at 450 steps. Second, overload does not emerge gradually across all settings; it appears within a narrow observed transition band around task load 3.0-3.25. Third, low service price is conditional rather than universally beneficial: it reduces pressure in low-load contexts but amplifies backlog once the system moves close to capacity.

This should be read as an exploratory modeling study and as an example of disciplined synthesis, model specification, and data stewardship. The current report is strongest when it speaks about abstract labor transfer, overload thresholds, and norm-sensitive stability. It is deliberately cautious about broader claims because prices remain exogenous, delay tolerance is not directly modeled, and the outputs are not evidence about any named real-world population.

## Problem Definition and Motivation

The formal problem addressed here is whether a high-convenience social configuration truly reduces total work, or whether it mainly redistributes work across agents while changing who feels the burden and when that burden becomes visible. The motivating intuition is straightforward: everyday convenience can feel individually efficient even when it requires someone else, somewhere in the system, to absorb additional coordination, service labor, or time pressure.

The model is therefore used as a structured translation layer between qualitative observation and quantitative mechanism analysis. That translation is itself part of the contribution. The point of the exercise is not to claim final truth about a social phenomenon, but to show how loosely framed observations can be turned into explicit feedback loops, white-box agent rules, reproducible campaigns, and auditable outputs. In that sense, the report is both a substantive analysis and a demonstration of computational social science workflow discipline.

![Figure 1 causal loop](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/figures/figure_01_causal_loop.png>)

*Figure 1. Conceptual causal loop linking convenience, delegation, provider burden, time scarcity, backlog, and norm reinforcement.*

## Research Questions and Hypotheses

The study follows four linked hypothesis families derived from the broader convenience-versus-autonomy observation:

1. **H1**: Higher delegation rates increase total system labor hours.
2. **H2**: A critical threshold triggers a convenience-to-involution transition.
3. **H3**: Higher autonomy lowers convenience but improves broader well-being proxies.
4. **H4**: Mixed systems are unstable and drift toward extremes.

Table 1 maps the core research questions and hypotheses onto the campaign packages and their primary metrics.

| research_question | hypothesis | package | primary_metrics | analysis_role |
| --- | --- | --- | --- | --- |
| Do stable everyday frictions signal a deeper time-allocation architecture? | H3 (partial) | Package A | tail_total_labor_hours, tail_avg_stress, final_available_time_mean, tail_tasks_delegated_frac | Long-horizon baseline comparison |
| Does convenience eliminate labor or relocate it inside the system? | H1 (strong), H2 (strong) | Package B | self_labor_hours, service_labor_hours, delegation_coordination_hours, tail_backlog_tasks, tail_delegation_labor_delta | Labor-transfer decomposition and threshold mapping |
| How much can low service price explain by itself? | H2 (strong contextual support) | Package C | tail_avg_stress, tail_backlog_tasks, tail_tasks_delegated_frac, tail_total_labor_hours | Context scan and cost-flip analysis |
| Do mixed systems drift toward extremes under norm pressure? | H4 (partial, important negative result) | Package D | final_avg_delegation_rate, final_avg_delegation_rate_std, tail_backlog_tasks | Mixed-state dispersion and stability assessment |

Source CSV: [Table 1 CSV](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/tables/table_01_question_hypothesis_mapping.csv>)

## Model Specification and White-Box Mechanism Mapping

The report is based on the research-only `ConvenienceParadoxResearchModel`, not the stable dashboard engine. This distinction matters because the formal analysis relies on mechanisms that the dashboard line intentionally does not expose yet: carryover backlog, explicit requester coordination cost, stricter provider matching, and labor accounting that separates self labor, service labor, coordination labor, and delegation labor delta.

![Figure 2 white-box flow](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/figures/figure_02_white_box_flow.png>)

*Figure 2. White-box lifecycle of the research engine used for this report.*

Table 2 summarizes the practical model delta that matters for interpretation.

| mechanism | stable_model | research_model | why_it_matters |
| --- | --- | --- | --- |
| Unmatched delegated work | Counted as unmatched but does not return as next-step work | Returns to requester carryover backlog | Makes overload cumulative instead of purely retrospective |
| Provider eligibility | Loose matching threshold | Provider must have enough remaining time for the full service | Makes supply tightness observable |
| Requester-side delegation friction | Implicit only | Explicit coordination-time cost | Prevents delegation from looking costless to the requester |
| Provider-side service friction | Simpler provider service timing | Explicit provider overhead factor | Captures extra effort needed to serve others |
| Labor accounting | Primarily total labor aggregate | Separates self labor, service labor, coordination labor, and labor delta | Supports direct testing of the labor-transfer claim |
| Interpretation boundary | Dashboard-facing baseline contract | Research-only `research_v2` contract | Preserves web compatibility while expanding explanation capacity |

Source CSV: [Table 2 CSV](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/tables/table_02_model_delta.csv>)

## Experimental Basis and Data Stewardship

This report uses only persisted outputs from the existing campaign directory. No new simulations are run during report generation. The input basis is therefore auditable and finite:

- `summaries/combo_summary.csv` for package-level aggregates
- `summaries/per_seed_summary.csv` for seed-level distributions
- `summaries/threshold_refinement_per_seed.csv` for the refined threshold band
- `summaries/preset_decomposition_per_seed.csv` for the cheap-service mechanism decomposition
- `summaries/story_case_selection.csv` plus saved case traces for representative trajectories
- writing-support notes for claim boundaries and evidence crosswalks

The report builder writes every derived figure and table into `report_assets/formal_report/` under the same campaign, including compact source CSVs and a provenance manifest. This matters for two reasons. First, it keeps the analysis reproducible and inspectable. Second, it preserves downstream reuse value for later portfolio or blog-oriented writing without requiring another round of manual extraction.

## Results

### 1. Baseline divergence remains stable rather than fading away

![Figure 3 baseline horizons](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/figures/figure_03_baseline_horizon_panel.png>)

*Figure 3. Type A and Type B maintain distinct labor, stress, available-time, and delegation profiles across 120, 200, 300, and 450 steps.*

The baseline horizon comparison shows that the high-delegation Type B configuration does not converge back toward the Type A baseline as the horizon extends. At 450 steps, Type B still carries a 30.01% labor premium, a stress level that is 0.0128 higher, and a lower mean remaining-time level (2.458 vs. 3.653). This is analytically important because it indicates that the convenience-heavy configuration is not merely a short-run transition artifact within the current model.

### 2. Convenience behaves more like labor transfer than labor elimination

Table 3 compares the four representative cases selected for narrative and diagnostic value.

| case | delegation_mean | task_load_mean | service_cost_factor | conformity | tail_stress | tail_total_labor_hours | tail_backlog_tasks | tail_delegation_labor_delta | final_available_time_mean | final_provider_time_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Autonomy Baseline | 0.250 | 2.200 | 0.650 | 0.150 | 0.034 | 428.312 | 0.000 | -15.646 | 3.665 | 182.235 |
| Convenience Baseline | 0.720 | 2.800 | 0.200 | 0.650 | 0.052 | 566.817 | 0.000 | -3.095 | 2.783 | 1420.281 |
| Threshold Pressure | 0.550 | 3.000 | 0.400 | 0.400 | 0.189 | 595.346 | 0.350 | -13.706 | 1.787 | 1099.966 |
| Overloaded Convenience | 0.720 | 5.500 | 0.200 | 0.800 | 1.000 | 800.000 | 133788.100 | -318853.257 | 0.000 | 26.854 |

Source CSV: [Table 3 CSV](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/tables/table_03_key_scenario_comparison.csv>)

![Figure 4 story cases](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/figures/figure_04_story_case_panel.png>)

*Figure 4. Dynamic trajectories for the four representative cases used throughout the report.*

![Figure 6 labor transfer decomposition](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/figures/figure_06_labor_transfer_decomposition.png>)

*Figure 6. Self labor, service labor, coordination labor, and delegation labor delta across representative cases.*

The story-case evidence makes the transfer mechanism concrete. The convenience-heavy baseline maintains relatively low stress for long stretches, but it does so by moving more work into provider time and coordination overhead. In the overloaded convenience case, the average user-facing convenience does not disappear first; instead, the provider side absorbs escalating hidden effort until backlog dominates the system state. This is exactly where the `delegation_labor_delta` metric becomes useful: it reveals whether delegation is reducing labor in aggregate or merely relocating it.

### 3. The overload threshold is narrow and should not be overstated

![Figure 5 threshold phase map](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/figures/figure_05_threshold_phase_map.png>)

*Figure 5. Package B phase map and refined transition evidence around task load 3.0-3.25.*

The main atlas shows where visible backlog first appears, but the refined scan is what supports a disciplined threshold claim. In the low-delegation refinement band, stress remains within 0.242-0.309 at task load 3.0 and backlog stays negligible. By 3.25, stress jumps to 0.629-0.730 and backlog becomes visible at 0.61-2.25. At 3.5, the system is effectively saturated: stress reaches 0.992-0.999 while backlog grows to 11.40-21.47. The correct interpretation is therefore not that there is a universal threshold constant, but that the current model repeatedly exposes a narrow transition band around 3.0-3.25 under the audited parameter slice.

### 4. Low service price is a conditional buffer that can turn into an amplifier

![Figure 7 service cost context](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/figures/figure_07_service_cost_context.png>)

*Figure 7. Context scan and low-price flip onset in Package C.*

The context scan makes the conditional nature of price effects explicit. In the Edge context, low price raises stress from 0.2172 to 0.4410 and increases backlog from 0.2292 to 1.1729. In the Overloaded context, both cost regimes are saturated on stress, but the low-cost regime expands backlog to 71926.00 versus 20991.78 under the high-cost comparison. This supports a sharper claim than "cheap service matters": price only looks like a relief valve while the system is comfortably below capacity.

### 5. Mixed-system instability exists, but the strongest result is still a restrained one

![Figure 8 mixed stability](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/figures/figure_08_mixed_stability.png>)

*Figure 8. Dispersion and per-seed final delegation outcomes in the mixed-system slice.*

The mixed-state analysis does detect some extra variability in the middle zone, but the effect is modest. The largest final-delegation standard deviation in the deep-dive slice is only 0.0125, observed at initial delegation 0.50 and conformity 0.30. This is exactly the sort of result that should be reported carefully: it gives partial support to the intuition that mixed systems are harder to stabilize, yet it also functions as a negative result because the current settings do **not** produce a dramatic bifurcation.

## Discussion, Boundaries, and Humble Claims

The strongest defensible interpretation of the campaign is not "convenience is bad." It is narrower and more useful: convenience-heavy configurations can remain subjectively smooth while becoming objectively more labor-intensive and more fragile near capacity. The report is also strongest when it treats the model as a mechanism probe rather than a stand-in for real societies.

This caution is not an afterthought. It is part of the quality standard of the exercise. The present work is meant to demonstrate the ability to transform qualitative observations into explicit model structure, map that structure onto measurable outputs, and maintain data provenance throughout the analysis. It is **not** a claim that the current model exhausts the social phenomenon or that it can adjudicate real institutional histories.

Table 4 states the formal hypothesis judgments used throughout the report.

| hypothesis | judgment | evidence | interpretation |
| --- | --- | --- | --- |
| H1 | Strong support | Type B keeps a 30.0% labor premium at 450 steps. | Higher delegation is consistently associated with more total system labor. |
| H2 | Strong support | Observed threshold band centers on task load 3.10 and is refined to 3.0-3.25. | A narrow overload band appears before the high-backlog regime. |
| H3 | Partial support | Type A keeps higher final available time while low-cost overload cells reach backlog 71926.0. | Autonomy aligns with more remaining time and lower structural pressure, but convenience is not measured directly. |
| H4 | Partial support with an important negative result | The largest mixed-state standard deviation remains only 0.0125. | Middle states are somewhat noisier, but the current settings do not produce a dramatic lock-in split. |

Source CSV: [Table 4 CSV](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/tables/table_04_hypothesis_verdict_matrix.csv>)

Table 5 makes the claim boundaries explicit.

| claim_status | statement |
| --- | --- |
| Can Say Confidently | The current ABM can identify parameter regions where higher delegation is associated with higher total labour hours in abstract Type A / Type B systems. |
| Can Say Confidently | The current ABM can compare how stress, labour, and inequality proxies evolve under different levels of task pressure, price friction, and conformity. |
| Can Say Confidently | The current ABM can test whether moderate initial delegation states remain stable under the model's conformity and stress feedback rules. |
| Can Say With Caveat | The model can show that lower external service prices push behaviour toward more delegation, but only as an exogenous price-friction experiment. |
| Can Say With Caveat | The model can approximate norm lock-in and speed expectations through delegation convergence proxies, not through a direct measure of delay tolerance. |
| Can Say With Caveat | The model can visualise how convenience shifts time burdens toward providers, but the exact labour market structure of real societies is outside scope. |
| Cannot Claim From Current Model | The model cannot identify the full real-world causal loop between cheap services and service dependence because prices are not endogenous. |
| Cannot Claim From Current Model | The model cannot measure real populations, named countries, or concrete policy outcomes. |
| Cannot Claim From Current Model | The model cannot directly test skill decay, demographic inequality, or explicit tolerance-for-delay dynamics because those mechanisms are absent. |

Source CSV: [Table 5 CSV](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/tables/table_05_claim_boundaries.csv>)

## Conclusion and Next-Step Model Extensions

Four conclusions follow from the current campaign.

1. The evidence strongly supports H1: higher delegation is associated with higher total labor.
2. The evidence strongly supports H2, but only in the disciplined form of an observed transition band around task load 3.0-3.25 under the current mechanism set.
3. H3 receives partial support because the model is stronger on available-time and stress proxies than on direct convenience perception.
4. H4 receives partial support together with an important negative result: mixed systems are somewhat more variable, but they do not collapse into a dramatic lock-in story under the present slice.

The clearest next extensions are already visible from the report's boundaries: endogenous price formation, explicit delay-tolerance dynamics, differentiated provider/requester roles, and richer skill-retention mechanisms. Until then, the current report is most credible when it is read as a transparent, exploratory, and well-audited mechanism study.
