# ConvenienceParadoxResearchModel 设计说明

> 英文版：[ConvenienceParadoxResearchModel_design.en.md](ConvenienceParadoxResearchModel_design.en.md)

## 1. 设计目标

`ConvenienceParadoxResearchModel` 是一个**研究专用引擎**，用于回答当前稳定版网页模型尚不能充分解释的机制问题，尤其是：

- 为什么低 `service_cost_factor` 会伴随更低压力
- 为什么高 delegation 在当前模型中更像缓冲器而不是放大器
- 为什么既有实验里几乎看不到供给紧张与 backlog
- 在什么条件下 delegation 会从“减压”转为“放大负担”

该引擎的目标不是替代网页当前使用的 `ConvenienceParadoxModel`，而是为后续机制审计、定向重跑、研究报告提供一个更适合解释这些问题的白盒实验版本。

## 2. 为什么不能直接修改网页模型

当前 Dash 页面与其背后的稳定模型之间存在明确契约：

- 页面控件依赖 `model/params.py` 中固定的 `PARAMETER_DEFINITIONS`
- API 入参依赖 `api/schemas.py` 中固定的 `SimulationParams`
- KPI 与图表依赖稳定模型已有的旧指标列
- Analysis 页还有部分静态写死的研究结论文案

如果直接把 backlog、协调成本、provider 摩擦和更严格的匹配约束写进 `ConvenienceParadoxModel`，虽然研究上更合理，但会导致：

- 页面展示语义变化
- Analysis 静态说明可能与新结果失配
- 页面 sensitivity 下拉和 preset 对应的解释边界被动改变

因此本轮采用**双模型并行**策略：

- `ConvenienceParadoxModel`：网页稳定契约
- `ConvenienceParadoxResearchModel`：研究实验契约

## 3. 与稳定版模型的边界关系

### 3.1 稳定版模型负责什么

- 网页仿真控制
- 页面图表渲染
- 现有 preset 交互
- 现有 API / Dash 回调契约

### 3.2 研究版模型负责什么

- 机制审计
- `research_v2` campaign
- 针对 `service_cost_factor` 的定向重跑
- backlog / capacity / labor-delta 解释
- 独立的英文与中文研究报告

### 3.3 两者如何保持兼容

研究版模型保留以下接口，以便分析脚本可最小代价切换引擎：

- `step()`
- `get_model_dataframe()`
- `get_agent_dataframe()`
- `get_agent_states()`
- `get_params()`

这意味着分析脚本可以通过“选择模型类”来切换机制，而无需重写整个汇总与报告流水线。

## 4. 类结构与生命周期

## 4.1 类结构

- `ConvenienceParadoxResearchModel`
  - 继承稳定版 `ConvenienceParadoxModel`
  - 研究引擎名固定为 `research_v2`
  - 重建 research-only 的 `DataCollector`
  - 覆盖 `step()` 与 `_run_service_matching()`
- `ResearchResident`
  - 继承稳定版 `Resident`
  - 新增 backlog 与 coordination bookkeeping
  - 覆盖 `generate_and_decide()`、`_execute_task_self()`、`provide_service()`

## 4.2 生命周期

每一步的生命周期如下：

1. 重置 step 级别统计量
2. 每个 agent 先把 `carryover_tasks` 带入当天任务集
3. 再生成当天新任务
4. 对每个任务做 self-serve / delegate 决策
5. delegated task 进入 `service_pool`
6. `_run_service_matching()` 只允许“时间足够完成完整服务”的 provider 接单
7. 未匹配任务回流 requester 的 `carryover_tasks`
8. agent 依据日末剩余时间更新 stress 与 delegation preference
9. `DataCollector` 记录旧指标与新增研究指标

## 5. backlog / matching / stress / labor accounting 数据流

## 5.1 Backlog

稳定版问题：

- `unmatched_tasks` 只被统计，不会回到 requester 身上
- 所以“未被满足的委托需求”不会成为次日真实压力

研究版修正：

- 未匹配任务不消失
- 它们被放回 requester 的 `carryover_tasks`
- 下一步任务决策时，agent 需要重新面对这些任务

这保证了 backlog 是**真实任务残留**，而不是纯粹的后验统计信号。

## 5.2 Matching

稳定版问题：

- provider 候选门槛仅为 `0.5 * base_time`
- 这会让系统在很多情况下“看起来总有人能接单”

研究版修正：

- provider 候选门槛改为“剩余时间必须覆盖预期 provider 服务耗时”
- 预期 provider 耗时 = `task.time_cost_for(0.60) * provider_service_overhead_factor`

这让供给紧张更容易以可解释的方式显现出来。

## 5.3 Stress

研究版没有引入拍脑袋式的额外 stress 罚分。

压力仍然主要来自：

- 日末剩余时间是否跌破 `stress_threshold`
- backlog 通过“任务残留 -> 次日继续占用时间”间接提高压力
- requester 协调成本通过真实时间支出提高压力

这保证 stress 仍然是白盒、时间约束驱动，而不是为了得到想要结论额外加罚。

## 5.4 Labor Accounting

研究版把总劳动拆为三个显式部分：

- `self_labor_hours`
- `service_labor_hours`
- `delegation_coordination_hours`

此外还记录 delegated task 的两种对照口径：

- `delegated_counterfactual_self_hours`
  - 如果这些 delegated task 由 requester 自己做，本该花多少时间
- `delegated_actual_service_hours`
  - 这些 delegated task 实际由 provider 花了多少时间

于是可以定义：

- `delegation_labor_delta`
  - `delegated_actual_service_hours + delegation_coordination_hours - delegated_counterfactual_self_hours`

这个指标直接回答“委托到底是节省总工时，还是增加总工时”。

## 6. 新增指标定义与解释

研究版新增的模型级指标如下：

- `self_labor_hours`
  - 本步由 requester 自己完成任务的总工时
- `service_labor_hours`
  - 本步由 provider 完成委托任务的总工时
- `delegation_coordination_hours`
  - 本步由于委托而发生的沟通、安排、交接工时
- `delegated_counterfactual_self_hours`
  - 被委托任务若改为 self-serve 时的反事实工时
- `delegated_actual_service_hours`
  - 被委托任务在 provider 侧的实际工时
- `delegation_labor_delta`
  - 委托相对于 self-serve 是增加还是减少系统劳动
- `stress_breach_share`
  - 日末剩余时间低于 stress 阈值的 agent 占比
- `mean_time_deficit`
  - 所有 agent 距离 stress 阈值的平均缺口
- `backlog_tasks`
  - 本步结束后仍未解决、将进入下一步的任务数
- `delegation_match_rate`
  - 本步 delegated task 中成功匹配的比例

## 7. 与网页兼容的原则

本轮明确遵循以下兼容原则：

- 不修改 `dash_app/`
- 不修改 `api/schemas.py` 的页面入参契约
- 不修改 `model/params.py` 的页面参数定义与 preset
- 不把 research-only 参数写入 dashboard 控件
- 不要求网页图表消费新增指标
- 不要求网页 Analysis 静态结论立即同步到研究版结果

换句话说，网页继续使用稳定模型；研究模型只在分析脚本里显式调用。

## 8. 已知限制

- 研究版仍然没有内生价格形成，`service_cost_factor` 依旧是外生变量
- 研究版仍未引入“等待耐受度”“速度预期”“技能退化”等更深层机制
- agent 仍是单一居民类型，尚未区分职业 provider 与普通 requester
- stable 与 research 两条结果线短期并行，读报告时必须区分引擎版本

## 9. 未来何时考虑合并回主模型

只有满足以下条件，才考虑把研究机制逐步并回稳定模型：

1. 研究版在多轮 rerun 中表现稳定，解释力明显优于稳定版
2. 页面 Analysis 静态结论已重写，不再依赖旧机制结论
3. 页面 KPI 与图表设计已评估并确认能承载 backlog / match-rate 等新语义
4. API 与 dashboard 控件是否暴露 research-only 参数已有明确决策

在此之前，`ConvenienceParadoxResearchModel` 将继续作为独立研究引擎存在。
