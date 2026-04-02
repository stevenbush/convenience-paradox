# Service Cost 研究重跑报告

**日期**: 2026-04-01  
**稳定版对照 campaign**: `20260401_125557_full_campaign`  
**研究版重跑 campaign**: `20260401_223144_service_cost_research_v2_progress`  
**研究引擎**: `ConvenienceParadoxResearchModel`  
**总运行时长**: `34分47秒`  
**补充机制 probe**: `data/results/campaigns/20260401_223144_service_cost_research_v2_progress/summaries/research_metric_probe.csv`

## 1. `research_v2` 这次到底改了什么

这次重跑没有碰网页稳定模型，而是把所有机制修正都放进了研究引擎：

- requester 增加委托协调时间成本
- provider 接单资格改为按“完整预期服务时长”判断
- provider 侧加入服务摩擦
- 未匹配委托任务回流 backlog
- 新增 research-only 的 stress / capacity 指标

这些改动的核心目的，就是把稳定模型里原来表达不出来的“委托-供给-积压-过载”链路补出来。

## 2. 最核心的结论

这次重跑把结论改得更接近你的原始直觉，但不是简单地“全部翻转”。

1. 便利导向基线不再比自治导向基线更低压。
2. 在低负载情境下，便宜服务仍然可以降压。
3. 但当 task load 上升到大约 `3.0` 左右时，便宜服务会开始**抬高**压力，因为 backlog 和匹配失败终于进入了动力学。
4. 过载机制不再只是“task pressure 单独主导”，而变成了 **task pressure × delegation × capacity** 的交互问题。

也就是说，你原先的直觉是**部分正确**的，只是它成立的前提是系统进入容量约束区间。

## 3. 基线结果：旧结论和新结论的对比

看 200 steps：

| 场景 | 稳定版 stress | 研究版 stress | 稳定版 labor | 研究版 labor | 稳定版委托占比 | 研究版委托占比 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Type A baseline | 0.0346 | 0.0413 | 429.47 | 436.27 | 0.0899 | 0.0947 |
| Type B baseline | 0.0116 | 0.0492 | 503.61 | 565.18 | 0.6324 | 0.6465 |

这是本次重跑最重要的定性变化。

在旧稳定模型里，Type B 是“劳动更多但压力更低”。  
在 `research_v2` 里，Type B 仍然劳动更多，但**压力也更高**了。

这说明之前“便利导向基线平均压力更低”的结论并不稳健。它高度依赖于：

- requester 几乎不承担委托协调时间
- backlog 不回流
- scarcity 通道缺失

## 4. `service_cost_factor` 在新模型里具体怎么起作用

### 4.1 Default context

在固定 default context 下，低 cost 仍然会降压，但它已经**不会再降低总劳动**了。

| service_cost_factor | 稳定版 avg stress | 研究版 avg stress | 稳定版 labor | 研究版 labor | 稳定版委托占比 | 研究版委托占比 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.10 | 0.0199 | 0.0209 | 462.28 | 501.39 | 0.4504 | 0.4493 |
| 0.90 | 0.0447 | 0.0346 | 471.32 | 494.00 | 0.2870 | 0.2584 |

这其实很关键，因为它正好回应了你之前的直觉：

- 低 cost 仍然会提高 delegation
- 低 cost 仍然会在可承受情境下降低 stress
- 但现在低 cost 已经会让总劳动更高，而不是更低

这个结果比稳定版更符合“便利提升会扩大系统总劳动”这一直觉。

### 4.2 Type A / Type B / overloaded 三种锚定情境

- 在 Type A context 里，低 cost 会明显降压，并提高 delegation。
- 在 Type B context 里，低 cost 仍然降压，但幅度比 Type A context 小。
- 在 overloaded convenience context 里，所有 cost 水平的 stress 都已经饱和到 `1.0`；低 cost 的主要作用不再是继续抬高 stress，而是把 backlog 爆得更大。

所以 `service_cost_factor` 不是一个可以脱离上下文单独解读的参数。它的作用高度依赖当前 task-load 所在区间。

## 5. 阈值：便宜服务从“减压”变成“放大器”的位置

这次 `service_cost x task_load` atlas 给出了最直接的答案。

### 中等 delegation 切片（`delegation_preference_mean = 0.55`）

| Task load | cost=0.05 时 stress | cost=1.00 时 stress | 低价减高价 |
| --- | ---: | ---: | ---: |
| 2.50 | 0.0160 | 0.0314 | -0.0154 |
| 3.00 | 0.2826 | 0.2044 | +0.0782 |
| 3.50 | 1.0000 | 1.0000 | 0.0000 |

### 高 delegation 切片（`delegation_preference_mean = 0.72`）

| Task load | cost=0.05 时 stress | cost=1.00 时 stress | 低价减高价 |
| --- | ---: | ---: | ---: |
| 2.50 | 0.0135 | 0.0203 | -0.0068 |
| 3.00 | 0.4619 | 0.2130 | +0.2489 |
| 3.50 | 1.0000 | 1.0000 | 0.0000 |

这基本就把阈值说清楚了：

- 在 `2.75` 以下，低价服务仍然更像减压阀
- 到 `3.0` 左右，符号开始翻转
- 到 `3.5` 以上，系统整体进入饱和区，低价与高价都会崩，但低价通常更早、更重地触发 backlog

所以对“为什么旧模型没跑出恶性循环”的回答现在更准确了：

- 不是说恶性循环不存在
- 而是它本来就不是 everywhere 的
- 它是在达到 capacity threshold 之后才成为主导机制
- 稳定模型以前没有把这个 threshold 表达出来

## 6. 为什么低价服务会在过载区间抬高 stress

这次补做的 `research_metric_probe.csv` 把机制细节补出来了。

### 中等 delegation，task load = `3.0`

| Cost | Stress | Backlog | Match rate | Stress-breach share |
| --- | ---: | ---: | ---: | ---: |
| 0.05 | 0.2826 | 0.3500 | 0.9981 | 0.6551 |
| 1.00 | 0.2044 | 0.0000 | 1.0000 | 0.5821 |

### 高 delegation，task load = `3.0`

| Cost | Stress | Backlog | Match rate | Stress-breach share |
| --- | ---: | ---: | ---: | ---: |
| 0.05 | 0.4619 | 1.3250 | 0.9949 | 0.7146 |
| 1.00 | 0.2130 | 0.2250 | 0.9987 | 0.6191 |

### overloaded convenience context

| Cost | Stress | Backlog | Match rate | Delegated share |
| --- | ---: | ---: | ---: | ---: |
| 0.05 | 1.0000 | 47559.7083 | 0.0000 | 0.9975 |
| 1.00 | 1.0000 | 11693.8333 | 0.0007 | 0.9717 |

现在这个机制链条已经很清楚了：

1. 低价服务提高 realised delegation。
2. 更多任务进入 service pool。
3. provider capacity 一旦开始吃紧，就会出现匹配失败。
4. 失败任务现在会回流 backlog。
5. backlog 会占用后续时间预算，把更多 agent 推到 stress threshold 以下。

这就是稳定模型以前缺掉的那条闭环。

## 7. 对你最初 5 个问题的直接回答

### Q1. `service_cost_factor` 现在还值得重点关注吗？

值得，但不能脱离 task-load 单独看。

- 低负载：低 cost 降压、提高 delegation
- 中高负载：低 cost 可能因为 backlog 反而升压
- 极端过载：stress 无论高低价都会饱和，但低价会让崩溃更快、积压更大

### Q2. 为什么旧模型里低 cost 会同时降低 labor 和 stress？

因为旧模型把 delegation 写得太轻了：

- requester 几乎不花时间协调
- provider 匹配门槛过宽
- 委托失败不积压
- provider 执行平均仍然过高效

### Q3. 为什么旧模型里便利导向社会平均压力更低？

因为旧模型更多是在“重新分配时间压力”，而没有真正激活 scarcity。现在把协调成本和 backlog 回流加进去以后，这个结论已经不成立了。

### Q4. 为什么旧模型没跑出明显的 delegation 恶性循环？

因为它没有 durable backlog channel。  
新模型已经显示：恶性循环会在 task-load 越过阈值以后出现，但并不是所有 delegation 水平下都同样强。

### Q5. 旧结果更像参数问题还是公式问题？

更像是机制覆盖不足，而不是 preset 初衷本身错了。  
这次重跑说明，主要问题在于 capacity-friction 没被正确纳入。

## 8. 还剩下一个重要问题

有一个 research-only 指标还需要继续改：`delegation_labor_delta`。

它在很多低负载格子里仍然为负，而且在极端过载时会变成非常大的负值。这**不**表示过载是“高效的”，而是说明当前这个指标的定义还没有把 backlog 作为“待偿还未来劳动”完整资本化。

所以：

- 在低 backlog 格子里，它还可以做方向性参考
- 但一旦 backlog 爆炸，它就不再是一个可靠的 welfare summary metric

这意味着下一轮还需要补一个校准动作：

- 要么进一步提高 provider overhead
- 要么把 `delegation_labor_delta` 换成一个 backlog-adjusted outstanding-work 指标

## 9. 最终结论

这次重跑已经把最核心的概念问题解决了。

- 旧结论“便宜服务会降低压力”说得太宽泛
- 新结论更准确：

> 便宜服务只有在系统仍低于 provider-capacity threshold 时才会降压；一旦 task pressure 足够高，便宜服务会加速 delegation、制造 backlog，并抬高压力。

这是当前证据下最稳健、最可辩护的解释。
