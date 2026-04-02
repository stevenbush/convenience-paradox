# 正式研究分析报告：`20260401_235956_research_v2_15k_parallel_20260401`

**日期**：2026-04-02  
**实验目录**：`data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401`  
**研究引擎**：`research_v2`  
**资产清单**：[正式报告清单](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/formal_report_manifest.json>)

## 摘要

本报告针对当前仓库中最完整的一组 `research_v2` campaign 输出，构建一份更接近正式研究分析文体的白盒报告。它的出发点是一些跨系统的日常生活观察：有的社会配置更强调便利与委托，有的配置保留更大的自治与时间边界。但这些观察在这里并不被当作结论，而是被转化为明确的机制问题，再交由抽象 agent-based model 检验。换言之，本报告回答的是“在当前模型里，哪些推论是站得住的”，而不是“现实世界一定如此”。

本次 campaign 覆盖 1146 个聚合情景、13346 条 seed 级汇总记录，以及 1088 条额外阈值细化记录，全部来自带有 backlog 回流、严格匹配与劳动增量核算的研究专用引擎。最稳健的三点结论是：第一，更高 delegation 与更高系统总劳动稳定同向，Type B 在 450 步时仍保留 30.01% 的劳动溢价；第二，过载并不是在所有参数区缓慢出现，而是在任务负载 3.0-3.25 的窄带附近明显跳变；第三，低服务价格并非普遍有利，它在低负载区减压，但在接近容量边界时会放大 backlog。

因此，这份报告最适合被理解为一项探索性白盒建模研究，也是一项关于“如何把 qualitative observation 转化为透明模型结构、并用数据治理方式约束分析结论”的能力展示。它在解释抽象的劳动转移、过载阈值和规范敏感性时最有说服力；而在价格内生性、等待耐受度或现实社会映射等问题上，则保持明确克制。

## 问题定义与研究动机

本报告要处理的正式问题是：高便利配置究竟是否真正减少了系统总劳动，还是主要改变了劳动在系统内部的分布方式，并由此改变了“谁感受到负担”以及“负担何时变得可见”。其核心直觉很简单：个体层面的便利体验，可能建立在系统其他位置更多的服务劳动、协调成本或时间压力之上。

因此，这个模型被当作一层结构化翻译器，用来把松散的社会观察转化为清晰的 feedback loop、white-box agent rule、可复现实验 campaign，以及可审计的输出资产。这里的重点不只是现象分析本身，也包括这种转译过程本身所体现的能力：把 qualitative input 转成 formal model specification，再把 model output 落成有出处、有边界的研究分析。

![图 1 因果回路](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/figures/figure_01_causal_loop.png>)

*图 1. 便利、委托、提供者负担、时间稀缺、backlog 与规范强化之间的概念性因果回路。*

## 研究问题与假设

本研究围绕四条相互关联的假设展开：

1. **H1**：更高 delegation 会提高系统总劳动小时数。
2. **H2**：存在从“便利”滑向“内卷/过载”的临界区间。
3. **H3**：更高自治会降低便利性，但改善更广义的福祉代理指标。
4. **H4**：混合系统不稳定，会向极端漂移。

表 1 给出研究问题、假设、实验包与核心指标之间的映射。

| 研究问题 | 对应假设 | 实验包 | 主要指标 | 分析角色 |
| --- | --- | --- | --- | --- |
| 稳定存在的日常摩擦，是否意味着更深层的时间分配结构？ | H3（部分支持） | Package A | tail_total_labor_hours, tail_avg_stress, final_available_time_mean, tail_tasks_delegated_frac | 长 horizon 基线对比 |
| 便利究竟是在消灭劳动，还是在系统内部转移劳动？ | H1（强支持），H2（强支持） | Package B | self_labor_hours, service_labor_hours, delegation_coordination_hours, tail_backlog_tasks, tail_delegation_labor_delta | 劳动转移拆解与阈值映射 |
| 低服务价格本身究竟能解释多少现象？ | H2（在上下文层面获得强支持） | Package C | tail_avg_stress, tail_backlog_tasks, tail_tasks_delegated_frac, tail_total_labor_hours | 上下文扫描与价格翻转分析 |
| 混合系统是否会在规范压力下向极端漂移？ | H4（部分支持，且包含重要负结果） | Package D | final_avg_delegation_rate, final_avg_delegation_rate_std, tail_backlog_tasks | 混合状态离散度与稳定性评估 |

源 CSV：[表 1 CSV](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/tables/table_01_question_hypothesis_mapping.csv>)

## 模型定义与白盒机制映射

本报告基于研究专用的 `ConvenienceParadoxResearchModel`，而不是网页稳定版引擎。这个区分非常重要，因为正式分析依赖的关键机制都位于 research line：carryover backlog、requester coordination cost、更严格的 provider matching，以及将 self/service/coordination/labor delta 拆开的劳动核算。

![图 2 白盒流程图](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/figures/figure_02_white_box_flow.png>)

*图 2. 本报告使用的研究版引擎生命周期。*

表 2 概括了稳定版与研究版模型之间最关键的解释边界。

| 机制维度 | 稳定版模型 | 研究版模型 | 研究意义 |
| --- | --- | --- | --- |
| 未匹配委托任务 | 只统计 unmatched，但不会作为下一步真实任务返回 | 返回请求者的 carryover backlog | 让过载从事后统计变成可累积的真实压力 |
| 提供者可接单条件 | 较宽松的匹配门槛 | 提供者必须有足够剩余时间完成整项服务 | 让供给紧张变得可观测 |
| 请求者侧委托摩擦 | 仅隐含存在 | 显式 coordination-time cost | 避免 delegation 在请求者视角下显得“零成本” |
| 提供者侧服务摩擦 | 较简化的 provider 服务耗时 | 显式 provider overhead factor | 刻画为他人提供服务所需的额外努力 |
| 劳动核算方式 | 以总劳动聚合为主 | 拆分 self labor、service labor、coordination labor 与 labor delta | 支持直接检验“劳动转移”命题 |
| 解释边界 | 面向 dashboard 的稳定契约 | 研究专用 `research_v2` 契约 | 在不破坏网页兼容性的前提下扩展解释能力 |

源 CSV：[表 2 CSV](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/tables/table_02_model_delta.csv>)

## 实验基础与数据治理

本报告严格只使用已有 campaign 输出，不执行任何新的 simulation run。因此，它的证据基础是有限、稳定且可审计的：

- `summaries/combo_summary.csv`：包级聚合输出
- `summaries/per_seed_summary.csv`：seed 级分布
- `summaries/threshold_refinement_per_seed.csv`：阈值细化扫描
- `summaries/preset_decomposition_per_seed.csv`：低价服务机制拆解
- `summaries/story_case_selection.csv` 及对应案例时间序列
- writing-support 目录中的证据映射与 claim boundary 文档

报告生成器会把所有衍生图表和表格写入同一 campaign 目录下的 `report_assets/formal_report/`，同时保存每张图与每张表对应的源 CSV 与 provenance manifest。这样做的意义有两层：一是保证本轮分析本身可追溯；二是为后续作品集展示或技术博客撰写保留可复用的下游资产。

## 结果

### 1. 基线差异并未随更长 horizon 消失

![图 3 基线 horizon 对比](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/figures/figure_03_baseline_horizon_panel.png>)

*图 3. Type A 与 Type B 在 120、200、300、450 步下仍保持不同的劳动、压力、可支配时间与委托比例结构。*

Package A 的 horizon comparison 表明，高 delegation 的 Type B 并不会随着时间延长而自动回归到 Type A。到 450 步时，Type B 仍然保持 30.01% 的总劳动溢价，平均压力比 Type A 高 0.0128，平均剩余时间则更低（2.458 对 3.653）。这说明在当前模型里，“便利型配置”不是短期扰动，而是一组更稳定的结构性差异。

### 2. 便利更像劳动转移，而不是劳动消失

表 3 汇总了四个代表性 story case。

| 案例 | 委托均值 | 任务负载均值 | 服务成本系数 | 规范压力 | 尾段压力 | 尾段总劳动小时 | 尾段 backlog | 尾段委托劳动增量 | 最终平均可支配时间 | 最终平均提供服务时间 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Autonomy Baseline | 0.250 | 2.200 | 0.650 | 0.150 | 0.034 | 428.312 | 0.000 | -15.646 | 3.665 | 182.235 |
| Convenience Baseline | 0.720 | 2.800 | 0.200 | 0.650 | 0.052 | 566.817 | 0.000 | -3.095 | 2.783 | 1420.281 |
| Threshold Pressure | 0.550 | 3.000 | 0.400 | 0.400 | 0.189 | 595.346 | 0.350 | -13.706 | 1.787 | 1099.966 |
| Overloaded Convenience | 0.720 | 5.500 | 0.200 | 0.800 | 1.000 | 800.000 | 133788.100 | -318853.257 | 0.000 | 26.854 |

源 CSV：[表 3 CSV](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/tables/table_03_key_scenario_comparison.csv>)

![图 4 代表性案例时间序列](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/figures/figure_04_story_case_panel.png>)

*图 4. 四个代表性案例的动态轨迹。*

![图 6 劳动拆解](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/figures/figure_06_labor_transfer_decomposition.png>)

*图 6. 代表性案例中的 self labor、service labor、coordination labor 与 delegation labor delta。*

这些案例把“劳动转移”机制变得非常具体。高便利基线在较长时期内可以维持较低压力，但它是通过把更多工作推向 provider 侧与协调成本来实现的。在 overloaded convenience 情景中，首先崩溃的并不是“表面的便利体验”，而是提供者一侧的隐性劳动与 backlog 指标。这正是 `delegation_labor_delta` 的价值所在：它能直接回答 delegation 究竟是节省了系统劳动，还是仅仅换了劳动承担者。

### 3. 过载阈值存在，但它是窄带而不是万能常数

![图 5 阈值相图](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/figures/figure_05_threshold_phase_map.png>)

*图 5. Package B 的相图与低 delegation 带的细化阈值证据。*

主 atlas 只告诉我们 backlog 在哪里第一次可见，而细化扫描才支撑更克制、更正式的阈值陈述。在低 delegation refinement band 中，任务负载 3.0 时，压力仍维持在 0.242-0.309，backlog 基本可忽略；到了 3.25，压力跃升到 0.629-0.730，backlog 变为 0.61-2.25；到 3.5，系统几乎进入饱和，压力达到 0.992-0.999，backlog 扩大到 11.40-21.47。因此，比较稳妥的说法不是“找到了普适阈值”，而是“在当前模型切片下，反复观察到了 3.0-3.25 的狭窄过渡带”。

### 4. 低服务价格只在低负载区是缓冲器

![图 7 服务价格上下文](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/figures/figure_07_service_cost_context.png>)

*图 7. Package C 中的上下文扫描与低价翻转点。*

Package C 显示，价格效应是强上下文依赖的。在 Edge context 中，低价把压力从 0.2172 推高到 0.4410，同时把 backlog 从 0.2292 放大到 1.1729。在 Overloaded context 中，两种价格情景的压力都已饱和，但低价仍把 backlog 扩大到 71926.00，而高价情景约为 20991.78。因此，最值得保留的结论并不是“低价服务好或不好”，而是“低价是否减压，取决于系统离容量边界还有多远”。

### 5. Mixed-system instability 存在，但更有价值的是其负结果

![图 8 mixed-system stability](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/figures/figure_08_mixed_stability.png>)

*图 8. Mixed-system 区间内的离散程度与 seed 级最终 delegation 分布。*

Package D 的 mixed-state 分析确实检测到中间区间比极端区间更容易波动，但波动幅度相当有限。当前 deep dive 中最大的最终 delegation 标准差也只有 0.0125，对应初始 delegation 0.50、conformity 0.30。这正是需要谦卑表达的地方：它给 H4 提供了部分支持，但同时也是一个有价值的负结果，因为当前参数带下并没有出现强烈的 bifurcation 或 lock-in 极化。

## 讨论、边界与谦卑表述

如果用一句话概括本轮实验，最稳健的结论并不是“便利一定更糟”，而是：便利型配置可以在主观体验上保持顺滑，同时在系统层面变得更劳动密集，并在接近容量边界时更脆弱。与此同时，本报告最有价值的地方也不只是具体结论，而是它如何把 qualitative observation 转译成可检验机制，并通过显式的数据落盘和证据边界控制分析强度。

这种克制并不是附加说明，而是研究质量本身的一部分。当前工作要展示的是：如何把社会观察 formalize 成模型结构，如何把模型结构映射为可追踪指标，以及如何在输出研究结论时持续提醒自己“哪些能说，哪些只能谨慎说，哪些当前根本不能说”。这也是本项目最直接体现 synthesis、conceptualization 与 data stewardship 能力的部分。

表 4 给出正式假设判断矩阵。

| 假设 | 判断 | 关键证据 | 解释 |
| --- | --- | --- | --- |
| H1 | 强支持 | Type B 在 450 步时仍保持约 30.0% 的劳动溢价。 | 更高 delegation 与更高系统总劳动稳定同向。 |
| H2 | 强支持 | 观测到的阈值带集中在任务负载 3.10 左右，并被细化到 3.0-3.25。 | 在高 backlog 区出现之前，存在一个狭窄的过载过渡带。 |
| H3 | 部分支持 | Type A 保持更高的最终可支配时间，而低价过载格点的 backlog 可达 71926.0。 | 自治与更高剩余时间、较低结构性压力同向，但模型并未直接度量 convenience 感知。 |
| H4 | 部分支持，并包含重要负结果 | 混合状态下最大的标准差也仅为 0.0125。 | 中间状态确实更易波动，但当前设定并未产生强烈的 lock-in 分裂。 |

源 CSV：[表 4 CSV](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/tables/table_04_hypothesis_verdict_matrix.csv>)

表 5 给出 claim boundary 与 limitation table。

| 主张边界 | 表述 |
| --- | --- |
| 可以较有把握地说 | 当前 ABM 可以识别出在抽象 Type A / Type B 系统中，高 delegation 与更高总劳动小时相关联的参数区间。 |
| 可以较有把握地说 | 当前 ABM 可以比较 stress、labor 与 inequality proxy 在不同任务压力、价格摩擦和 conformity 下的演化。 |
| 可以较有把握地说 | 当前 ABM 可以检验中等初始 delegation 状态在模型的 conformity 与 stress feedback 规则下是否稳定。 |
| 可以在保留条件下说 | 模型可以显示更低的外生服务价格会把行为推向更高 delegation，但这仅限于外生价格摩擦实验。 |
| 可以在保留条件下说 | 模型可以通过 delegation convergence proxy 近似刻画 norm lock-in 与速度预期，但并没有直接测量 delay tolerance。 |
| 可以在保留条件下说 | 模型可以可视化 convenience 如何把时间负担转移给 providers，但现实社会的具体劳动力市场结构不在当前范围内。 |
| 当前模型不能主张 | 由于价格不是内生变量，模型不能识别廉价服务与服务依赖之间完整的现实因果回路。 |
| 当前模型不能主张 | 模型不能测量真实人口、具体国家或明确政策结果。 |
| 当前模型不能主张 | 由于缺少相关机制，模型不能直接检验技能退化、人口结构不平等或显式的等待耐受度动态。 |

源 CSV：[表 5 CSV](<../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report/tables/table_05_claim_boundaries.csv>)

## 结论与下一步模型扩展

基于当前 campaign，可以给出四点阶段性结论：

1. H1 获得强支持：更高 delegation 与更高总劳动稳定同向。
2. H2 获得强支持，但应严格表述为“在当前机制设定下观察到 3.0-3.25 的过渡带”。
3. H3 获得部分支持，因为模型更擅长度量 available time 与 stress proxy，而不是直接度量 convenience perception。
4. H4 获得部分支持，同时包含一个重要负结果：mixed systems 的确略不稳定，但远没有强烈滑向两极。

下一轮最值得扩展的机制已经很清楚：内生价格形成、显式等待耐受度、provider/requester 类型分化，以及更丰富的技能保持或技能退化机制。在这些机制加入之前，当前报告最适合被视为一项透明、克制且可审计的机制探索研究。
