# 实验研究分析报告：`20260401_235956_research_v2_15k_parallel_20260401`

**日期**：2026-04-02  
**实验目录**：`data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401`  
**研究引擎**：`research_v2`  
**实验尺度**：`research_15k`  
**覆盖 package**：`Package A`、`Package B`、`Package C`、`Package D`

## 1. 数据基础与实验结构

这是当前仓库中覆盖最完整的一组研究型 campaign，目标不是单点验证，而是把四条机制链同时跑通：

1. 预设社会的长期差异是否稳定存在
2. 便利是否节省劳动，还是仅仅转移劳动
3. 低价服务在哪些区间会从减压阀变成过载放大器
4. 混合系统是否会因为规范压力而锁定到某一端

本组实验的可复核数据规模如下：

- `summaries/combo_summary.csv`：1146 个聚合场景
- `summaries/per_seed_summary.csv`：13346 条 seed 级记录
- `summaries/threshold_refinement_per_seed.csv`：1088 条 seed 级记录
- 可直接复核的 seed 级总记录数：`14434`

按模块拆分：

- `Package A / preset_horizon_scan`：8 个场景，20 seeds，覆盖 120/200/300/450 步
- `Package B / delegation_task_load_atlas`：170 个场景，12 seeds；`threshold_refinement`：68 个场景，16 seeds
- `Package C / service_cost_context_scan`：55 个场景，20 seeds；`service_cost_task_load_atlas`：748 个场景，12 seeds；`preset_decomposition_v2`：12 个聚合场景
- `Package D / delegation_conformity_atlas`：60 个场景，12 seeds；`mixed_stability_deep_dive`：25 个场景，14 seeds

因此，这一组实验最适合拿来做阶段性研究结论，而不是只做一次图像展示。

## 2. 总结性判断

1. Type B 与 Type A 的结构差异在更长 horizon 下没有消失，反而稳定收敛为一组非常清晰的“高委托、高劳动、低剩余时间”特征。
2. 便利更像“劳动转移机制”而不是“劳动消除机制”。低负载时它会降低 requesters 的压力，但不会减少系统总劳动；负载一旦上升，它会更早触发积压。
3. `service_cost_factor` 不能脱离 `tasks_per_step_mean` 和 `delegation_preference_mean` 单独解读。低价服务在低负载时减压，在边缘负载和过载时则明显放大 backlog。
4. 本次实验强力支持 H1 与 H2；对 H3 给出部分支持；对 H4 则给出了一个重要的负结果：在当前 moderate-load 切片下，混合系统并没有表现出强烈的规范锁定。

## 3. Package A：Type A / Type B 差异在 450 步内保持稳定

`Package A` 的 horizon scan 给出了当前最稳的基线差异：


| 步数  | Type A 压力 | Type B 压力 | 压力差     | Type A 总劳动 | Type B 总劳动 | 劳动差异   | Type A 委托占比 | Type B 委托占比 | Type A 最终可支配时间 | Type B 最终可支配时间 | Type B backlog |
| --- | --------- | --------- | ------- | ---------- | ---------- | ------ | ----------- | ----------- | -------------- | -------------- | -------------- |
| 120 | 0.0378    | 0.0546    | +0.0168 | 434.01     | 568.93     | +31.1% | 0.0961      | 0.6475      | 3.7488         | 2.3237         | 0.0375         |
| 200 | 0.0400    | 0.0492    | +0.0092 | 435.65     | 565.02     | +29.7% | 0.0934      | 0.6456      | 3.6020         | 2.2761         | 0.0175         |
| 300 | 0.0380    | 0.0491    | +0.0112 | 433.96     | 564.07     | +30.0% | 0.0893      | 0.6434      | 3.6246         | 2.4443         | 0.0233         |
| 450 | 0.0392    | 0.0520    | +0.0128 | 435.18     | 565.78     | +30.0% | 0.0893      | 0.6451      | 3.6532         | 2.4581         | 0.0222         |


可以直接得出三点：

- Type B 的高委托状态不是短暂现象，450 步以后仍维持约 30% 的总劳动溢价。
- Type B 的压力虽然没有像过载区那样爆炸，但始终高于 Type A。
- Type B 的剩余可支配时间长期更低，说明所谓“便利”并没有把系统推向更宽裕的时间预算。

对应图像：

- `package_a_everyday_friction/figures/horizon_short.png`
- `package_a_everyday_friction/figures/horizon_long.png`

## 4. Package B：便利并没有消灭劳动，而是把劳动转移给系统别处

### 4.1 低负载时，更多委托会降压，但不会降总劳动

在 `tasks_per_step_mean = 2.5` 时，委托偏好从 `0.05` 升到 `0.95`：

- 压力从 `0.0983` 降到 `0.0122`
- 总劳动从 `488.81` 升到 `509.65`
- 自劳小时从 `455.55` 降到 `92.82`
- 服务劳动从 `31.46` 升到 `386.71`
- 协调劳动从 `1.80` 升到 `30.12`

这说明，在宽松负载下，便利确实能把 requester 端的体验变轻，但系统层面的劳动并没有消失，只是被重分配为服务劳动与协调劳动。

### 4.2 阈值不是固定常数，而是随委托水平左移

主 atlas 中，第一次出现 `tail_backlog_tasks_mean > 0.1` 的任务负载如下：


| 委托均值 | backlog 首次出现的负载 | 该点平均压力 |
| ---- | --------------- | ------ |
| 0.05 | 3.25            | 0.6407 |
| 0.15 | 3.25            | 0.6829 |
| 0.25 | 3.25            | 0.8366 |
| 0.35 | 3.25            | 0.9471 |
| 0.45 | 3.00            | 0.2092 |
| 0.55 | 3.00            | 0.2221 |
| 0.65 | 3.00            | 0.2807 |
| 0.75 | 3.00            | 0.3619 |
| 0.85 | 3.00            | 0.5836 |
| 0.95 | 3.00            | 0.8269 |


这说明一件非常关键的事：  
随着委托倾向上升，系统的容量边界会左移。也就是，同样的任务负载，在高委托体制下会更早进入积压区。

### 4.3 `threshold_refinement` 把拐点收缩到 `3.0-3.25`

低委托带（`0.05-0.20`）的 16-seed 精细化扫描显示：

- `load = 3.0` 时，压力在 `0.242-0.309`，几乎没有 backlog
- `load = 3.25` 时，压力跃迁到 `0.629-0.730`，backlog 开始变成 `0.61-2.25`
- `load = 3.5` 时，压力几乎全部饱和到 `0.992-0.999`，backlog 扩大到 `11.40-21.47`

所以，对 Package B 来说，最稳健的阈值描述是：

> 在当前参数设定下，`tasks_per_step_mean` 从 3.0 上升到 3.25 的窄带，是“便利开始转化为系统性负担转移”的关键区间。

### 4.4 高负载时，劳动上限趋于饱和，但积压规模继续分化

在 `load = 5.5` 时，总劳动几乎对所有 delegation 水平都收敛到 `799-800`，但系统状态并不相同：

- `delegation=0.05`：backlog `29693.76`
- `delegation=0.55`：backlog `44238.63`
- `delegation=0.95`：backlog `118768.75`

也就是说，极端过载时，平均劳动小时已经接近上限，真正区分系统状态的不是“又多干了多少”，而是“有多少工作被滚动推迟到了未来”。

对应图像：

- `package_b_convenience_transfer/figures/task_load_heatmap.png`
- `package_b_convenience_transfer/figures/threshold_strip.png`
- `package_b_convenience_transfer/figures/burden_transfer.png`

## 5. Package C：低价服务只在低负载区有效，越接近边缘负载越容易变成陷阱

### 5.1 上下文扫描：低价对低负载有效，对边缘负载有害

`service_cost_context_scan` 里，最低价与最高价情景对比如下：


| 上下文        | 低价压力   | 高价压力   | 低价总劳动  | 高价总劳动  | 低价委托占比 | 高价委托占比 | 低价 backlog | 高价 backlog |
| ---------- | ------ | ------ | ------ | ------ | ------ | ------ | ---------- | ---------- |
| Default    | 0.0191 | 0.0445 | 501.05 | 493.08 | 0.4640 | 0.1908 | 0.0000     | 0.0000     |
| Type A     | 0.0214 | 0.0666 | 439.54 | 437.41 | 0.2221 | 0.0403 | 0.0000     | 0.0000     |
| Type B     | 0.0510 | 0.0674 | 565.75 | 559.03 | 0.6879 | 0.4081 | 0.0333     | 0.0021     |
| Edge       | 0.4410 | 0.2172 | 604.90 | 594.68 | 0.8023 | 0.4502 | 1.1729     | 0.2292     |
| Overloaded | 1.0000 | 1.0000 | 800.00 | 798.73 | 0.9984 | 0.9832 | 71926.00   | 20991.78   |


这里最重要的不是“低价是否更受欢迎”，而是：

- 在 `Default` 与 `Type A` 区，低价明显减压
- 到 `Edge` 区，低价反而把压力从 `0.2172` 推到 `0.4410`
- 在 `Overloaded` 区，压力已经全部饱和，但低价把 backlog 放大到高价的约 `3.43` 倍

### 5.2 完整 atlas：价格翻转点随 delegation 提前出现

以最便宜 `service_cost_factor = 0.02` 和最昂贵 `1.20` 做对照，符号翻转位置如下：


| 委托均值 | 首个“低价压力 > 高价压力”的负载 | 压力差（低价-高价） | backlog 差（低价-高价） |
| ---- | ------------------ | ---------- | ---------------- |
| 0.35 | 3.25               | +0.3146    | +9.1563          |
| 0.55 | 3.00               | +0.0588    | +0.6632          |
| 0.72 | 3.00               | +0.2990    | +1.2014          |
| 0.90 | 3.00               | +0.6133    | +3.5660          |


这张表说明：

- delegation 越高，低价服务越早从“缓冲器”转为“放大器”
- 在高 delegation 条件下，价格翻转甚至在 `3.0` 就已发生
- delegation 越高，翻转点的压力惩罚越重

### 5.3 机制拆解：任务负载仍是主变量，价格决定放大倍数

`preset_decomposition_v2` 的结果与第一组实验一致：

- 对 Type A，提升任务负载均值带来最大压力增量：`+0.1015`
- 对 Type A，仅降低服务成本会把压力拉低 `-0.0138`，但同时提高委托占比 `+0.0899`
- 对 Type B，把任务负载均值从 `2.8` 降回 `2.2`，压力下降 `-0.0468`
- 对 Type B，仅把服务成本从 `0.20` 提到 `0.65`，压力只小幅上升 `+0.0070`

因此，这一 package 的最稳结论是：

> 价格不是第一因，容量压力才是；但价格会决定系统在接近阈值时是“轻微堆积”还是“快速积压”。

对应图像：

- `package_c_cheap_service_trap/figures/service_cost_taskload_backlog_heatmap.png`

## 6. Package D：在当前 moderate-load 切片下，没有观察到强烈的规范锁定

这是这组大实验里最有价值的负结果之一。

### 6.1 `delegation_conformity_atlas` 的整体结论

在 `tasks_per_step_mean = 2.5`、`service_cost_factor = 0.4` 的切片中：

- 各 conformity 水平下的平均 `delegation_shift` 仅在 `+0.0041` 到 `+0.0049` 之间
- `final_avg_delegation_rate_std` 基本稳定在 `0.0100` 左右
- `tail_backlog_tasks_mean` 在所有格点都为 `0.0`

代表性格点：

- 初始委托 `0.05` 最终稳定在约 `0.0797-0.0798`
- 初始委托 `0.55` 最终稳定在约 `0.5553-0.5554`
- 初始委托 `0.95` 最终稳定在约 `0.9270`

最大的 seed 间不稳定点也很温和：

- `delegation_preference_mean = 0.45`
- `social_conformity_pressure = 0.4`
- `final_avg_delegation_rate_std = 0.0111`

这个量级并不足以支持“系统会自发锁死到单侧极端”的强叙事。

### 6.2 `mixed_stability_deep_dive`：中间态基本保持中间态

针对 `0.35-0.65` 的混合起点做深挖后，结果更清楚：

- 平均 `delegation_shift` 仍只有 `+0.0054` 到 `+0.0056`
- `final_avg_delegation_rate_std` 约为 `0.0124`
- 所有情景的 backlog 都是 `0.0`

也就是说，在当前参数带中：

- mixed systems 会有轻微上浮
- 但它们没有显著分叉，也没有显著 path dependence
- conformity 主要影响叙事解释，不足以单独制造锁定

这部分结果的研究意义不在于“发现了 lock-in”，而在于明确了一个边界：

> 在没有明显过载、没有内生价格、没有更强适应增益的情况下，规范压力本身不足以让系统从中间态快速滑向极端。

对应图像：

- `package_d_norm_lock_in/figures/conformity_heatmap.png`
- `package_d_norm_lock_in/figures/mixed_stability_distribution.png`
- `package_d_norm_lock_in/figures/limits_figure.png`

## 7. 对研究假设的阶段性评估

### H1：更高委托率会提高系统总劳动小时数

强支持。  
`Package A` 的 Type B / Type A 比较，以及 `Package B` 的 delegation-task-load atlas，都反复显示更高 delegation 与更高总劳动同向变化。

### H2：存在触发 involution spiral 的阈值

强支持。  
`Package B` 的 16-seed threshold refinement 把阈值压缩到 `3.0-3.25`；`Package C` 则表明在高 delegation 与低价格同时存在时，这个阈值会更早出现。

### H3：更高自治会降低便利感，但提升总体福祉

部分支持。  
当前模型没有直接度量“主观便利感”，但更高自治确实对应：

- 更低总劳动
- 更低平均压力
- 更高剩余可支配时间

因此，就系统福利代理指标而言，证据偏向支持 H3。

### H4：混合系统不稳定，会向极端漂移

本组实验不支持 H4 的强版本。  
在 `Package D` 的 moderate-load 切片中，中间系统整体保持中间，仅有非常轻微的上浮，没有出现强锁定或大规模分叉。

## 8. 研究边界与下一步建议

这组实验已经能支撑一版严肃的研究叙述，但仍应保留以下边界：

- 服务价格是外生变量，因此不能把“低价服务陷阱”直接外推为现实中的完整因果闭环。
- `Package D` 只在 `task_load = 2.5` 的切片上检验规范压力，因此它更像是“在温和环境下没有观察到强锁定”，而不是“规范永远不重要”。
- backlog 爆炸时，`delegation_labor_delta` 不适合继续当作福利汇总指标，它更像“未偿还劳动”的残缺代理。

下一步最值得做的三件事是：

1. 把 `Package D` 放到更接近阈值的高负载带上重跑，检验“规范压力 + 容量紧张”是否会共同触发锁定。
2. 为 `Package B` 和 `Package C` 补一组 backlog-adjusted welfare 指标，把未来待偿还工作显式资本化。
3. 在论文式写法里把本组结果组织为一条更清晰的链：`高委托 -> 劳动转移 -> 容量阈值左移 -> 低价放大积压 -> mixed slice 并未单独锁定`。

