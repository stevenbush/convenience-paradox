# 便利悖论：基于代理的服务委托、劳动转移与社会内卷探索性研究

**作者：** 施际原 | 计算社会科学作品集研究
**日期：** 2026-04-02
**实验规模：** 14,656 次仿真运行，4 个研究包（research_v2 引擎）

---

> *在海外生活几年后，某个周日下午，我站在一家关门的超市前。在另一个大陆的城市里，我几乎可以
> 在任何时间走进街角的便利店。这个小小的不便让我思考了很久——不是因为它是什么困难，而是因为
> 它像一根线头，我越拉越发现它连接着更大的东西：一张由相互依赖的社会机制编织而成的网。*
>
> *到底是廉价服务在先，还是对服务的依赖在先？低价是原因还是结果？一旦反馈循环启动，
> 提高价格还能改变什么吗？*

---

## 1. 摘要

本报告采用**代理基模型 (Agent-Based Model, ABM)** 研究**便利-自主权张力**——即不同社会在个人
自力更生与服务委托之间呈现出显著不同的均衡状态，且这些均衡似乎具有自我强化特性。

使用基于 Mesa 框架的仿真系统（100 个代理，Watts-Strogatz 小世界网络），我们探索了关于委托率、
服务成本、社会从众压力和任务负荷如何交互产生系统总劳动、个体压力和不平等涌现模式的四个假设。
**14,656 次运行**构成了证据基础。

模型内的主要发现：(1) 便利导向配置（B 类）持续产生约 **30.0%** 的
额外系统劳动；(2) 窄任务负荷阈值带（3.0--3.25 任务/步）标志着从可管理委托到累积过载的转变；
(3) 自主导向代理保留更多可用时间（3.65h vs 2.46h）。

**重要说明：** 本研究是一项方法论演示，旨在展示将定性社会观察转化为正式代理基模型的过程，
体现结构化信息综合与计算数据管理能力。作者是计算领域专业人员，而非社会学或经济学领域专家。
模型设计、理论框架和由此得出的结论均具探索性质，不应被视为权威性社会科学发现。读者应评估
方法论的严谨性和分析过程的透明度，而非将实质性结论视为定论。

---

## 2. 问题定义与理论框架

### 2.1 便利-自主权张力

不同社会的日常生活节奏呈现出截然不同的模式。在某些环境中，个人自行管理大部分日常事务——做饭、
跑腿、小修理——接受更高的时间成本和较慢的服务时效。在其他环境中，价格低廉的第三方服务鼓励
广泛委托，形成节奏更快、联系更紧密的服务生态系统。

从**复杂适应系统**的视角来看，这些模式可以被理解为个体决策、服务可用性、价格结构、社会规范
和时间约束之间交互反馈循环的涌现属性。

### 2.2 概念因果环路

<figure style="margin:1.6rem auto 1.25rem auto; width:100%; max-width:920px;"><div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:14px 14px 10px 14px; box-shadow:0 1px 2px rgba(15,23,42,0.06);"><img src="../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report_v2/figures/figure_01_causal_loop.svg" alt="figure_01_causal_loop" width="920" loading="lazy" style="display:block; width:100%; max-width:920px; height:auto; margin:0 auto;" /></div><figcaption style="margin-top:0.55rem; text-align:center; font-size:0.92rem; line-height:1.45; color:#6b7280;">图 1. 概念因果环路。</figcaption></figure>

图 1 展示了模型中嵌入的概念反馈结构。两个增强回路占主导：**R1**（压力驱动的委托螺旋）和
**R2**（规范驱动的便利锁定）。

### 2.3 从观察到正式模型

从定性观察到计算模型的翻译经过三个阶段：识别反馈机制、形式化为代理规则、设计隔离实验。
这种结构化翻译本身就是本工作的核心贡献。

---

## 3. 研究问题与假设

| research_question | hypothesis | package | primary_metrics | analysis_role |
| --- | --- | --- | --- | --- |
| Do stable everyday frictions signal a deeper time-allocation architecture? | H3 (partial) | Package A | labor hours, stress, available time, delegation fraction | Long-horizon baseline comparison |
| Does convenience eliminate labor or relocate it inside the system? | H1, H2 | Package B | self/service/coordination labor, backlog, labor delta | Labor-transfer decomposition and threshold mapping |
| How much can low service price explain by itself? | H2 (contextual) | Package C | stress, backlog, delegation fraction, labor hours | Service-cost sensitivity and cost-flip analysis |
| Do mixed systems drift toward extremes under norm pressure? | H4 (partial negative) | Package D | final delegation rate, delegation rate std | Mixed-state dispersion assessment |

四个假设：

- **H1**：更高的委托率导致更高的系统总劳动时间。
- **H2**：临界委托阈值触发内卷螺旋。
- **H3**：更高的自主权与较低的便利感知但更高的总体福祉相关。
- **H4**：混合系统（适度委托）不稳定，会向极端漂移。

---

## 4. 模型规范

### 4.1 代理架构

每个 **Resident** 代理拥有 8.0 小时的日时间预算，每步接收 1-5 个任务。委托决策公式：

*p_eff = clamp( p_base + 0.30 * stress + 0.25 * skill_gap - 0.25 * cost, 0, 1 )*

### 4.2 模型生命周期

<figure style="margin:1.6rem auto 1.25rem auto; width:100%; max-width:1040px;"><div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:14px 14px 10px 14px; box-shadow:0 1px 2px rgba(15,23,42,0.06);"><img src="../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report_v2/figures/figure_02_model_lifecycle.svg" alt="figure_02_model_lifecycle" width="1040" loading="lazy" style="display:block; width:100%; max-width:1040px; height:auto; margin:0 auto;" /></div><figcaption style="margin-top:0.55rem; text-align:center; font-size:0.92rem; line-height:1.45; color:#6b7280;">图 2. 白盒模型生命周期。</figcaption></figure>

### 4.3 参数配置

<figure style="margin:1.6rem auto 1.25rem auto; width:100%; max-width:760px;"><div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:14px 14px 10px 14px; box-shadow:0 1px 2px rgba(15,23,42,0.06);"><img src="../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report_v2/figures/figure_03_radar_profile.svg" alt="figure_03_radar_profile" width="760" loading="lazy" style="display:block; width:100%; max-width:760px; height:auto; margin:0 auto;" /></div><figcaption style="margin-top:0.55rem; text-align:center; font-size:0.92rem; line-height:1.45; color:#6b7280;">图 3. A 类与 B 类参数画像。</figcaption></figure>

### 4.4 研究引擎增强（research_v2）

| mechanism | stable | research_v2 | significance |
| --- | --- | --- | --- |
| Unmatched tasks | Discarded each step | Carried over as backlog | Makes overload cumulative |
| Provider eligibility | Loose threshold | Must cover full service time | Tighter supply constraint |
| Delegation friction | Implicit | 15% coordination cost | Delegation is not free |
| Provider overhead | Simple timing | 11% service overhead | Serving others costs extra |
| Labor accounting | Aggregate only | Self / service / coordination split | Tests labor-transfer claim |

---

## 5. 实验设计与数据管理

实验包含 **14,656 次完成的运行**，组织为四个研究包。所有运行使用 research_v2 引擎，
采用尾窗聚合（最后 20% 步数），每个场景单元跨多个随机种子复制。

---

## 6. 结果

### 6.1 H1：委托增加系统总劳动（强支持）

<figure style="margin:1.6rem auto 1.25rem auto; width:100%; max-width:1040px;"><div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:14px 14px 10px 14px; box-shadow:0 1px 2px rgba(15,23,42,0.06);"><img src="../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report_v2/figures/figure_04_horizon_panel.svg" alt="figure_04_horizon_panel" width="1040" loading="lazy" style="display:block; width:100%; max-width:1040px; height:auto; margin:0 auto;" /></div><figcaption style="margin-top:0.55rem; text-align:center; font-size:0.92rem; line-height:1.45; color:#6b7280;">图 4. 关键指标的时长对比。</figcaption></figure>

图 4 在四个仿真时长（120、200、300、450 步）下比较 A 类（自主导向）与 B 类（便利导向）。
六项关键指标揭示了持续的结构性差异——这些差异既不随时长收敛也不发散，表明这是真正的均衡分离
而非瞬态动力学。

**总劳动时间**差距最为显著：450 步时 B 类产生 565.8 小时，A 类为
435.2 小时——**30.0% 的溢价**。
该差距在 120 步时即已可见（约 31.1% 差异），
并在所有后续时长中保持稳定，证实劳动开销是高委托配置的*结构性*特征而非初始化假象。

**压力水平**反映了相同模式：450 步时 B 类代理平均压力为 0.052，
A 类为 0.039。虽然两者均低于饱和值（1.0），但持续差距反映了便利配置中
协调开销和服务提供职责对时间预算的压缩。

**可用时间**从代理层面最直接地呈现影响：A 类代理平均保留 3.65 小时
自由时间，B 类仅有 2.46 小时——约
1.20 小时的差距。在 8 小时日预算中，A 类代理保留
约 45.7% 的时间作为可支配时间，B 类仅为
30.7%。

**委托率**确认了配置差异：B 类委托 64.5% 的任务，
A 类为 8.9%。**收入基尼系数** B 类略高
（0.231 vs 0.191），
反映了服务经济结构中的收入分化。

<figure style="margin:1.6rem auto 1.25rem auto; width:100%; max-width:1040px;"><div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:14px 14px 10px 14px; box-shadow:0 1px 2px rgba(15,23,42,0.06);"><img src="../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report_v2/figures/figure_05_agent_distributions.svg" alt="figure_05_agent_distributions" width="1040" loading="lazy" style="display:block; width:100%; max-width:1040px; height:auto; margin:0 auto;" /></div><figcaption style="margin-top:0.55rem; text-align:center; font-size:0.92rem; line-height:1.45; color:#6b7280;">图 5. 代理层结果分布。</figcaption></figure>

图 5 揭示了代理层面的分布特征。A 类可用时间以 3.7 小时为中心呈宽分布，
反映了任务负荷和技能水平的个体差异。B 类可用时间更低且分布更紧——从众压力使委托行为趋同，
也使其后果趋同。B 类收入分布呈现更长的右尾，是服务经济中部分代理从服务提供中获得显著更多
收入的标志。

**本结果未能说明的：** 模型使用外生固定服务成本。在真实经济中，30.0%
的劳动溢价可能被内生价格调整、专业化带来的生产率提升或服务质量改善部分抵消。该溢价反映的是
模型核算框架内的*协调和提供者开销的结构性成本*。

### 6.2 H2：阈值触发内卷（强支持）

<figure style="margin:1.6rem auto 1.25rem auto; width:100%; max-width:920px;"><div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:14px 14px 10px 14px; box-shadow:0 1px 2px rgba(15,23,42,0.06);"><img src="../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report_v2/figures/figure_06_phase_atlas.svg" alt="figure_06_phase_atlas" width="920" loading="lazy" style="display:block; width:100%; max-width:920px; height:auto; margin:0 auto;" /></div><figcaption style="margin-top:0.55rem; text-align:center; font-size:0.92rem; line-height:1.45; color:#6b7280;">图 6. 委托-任务负荷相位图谱。</figcaption></figure>

图 6 展示委托-任务负荷相位图谱，映射两个最重要控制参数空间中的系统级积压。
颜色梯度（对数标度）揭示三个截然不同的状态域：

1. **安全区**（左下，深色）：低任务负荷和/或低委托。系统吸收全部任务，无残余积压。
2. **过渡带**（对角走廊，黄-橙色）：积压首次出现的窄带区域。微小参数变化导致不成比例的
   巨大结果差异——复杂系统中相变行为的特征。
3. **过载区**（右上，深红色）：高任务负荷结合中高委托率。积压每步累积增长，所有代理
   趋向最大压力和劳动饱和。

白色起始线追踪积压首次超过零的边界，该边界持续位于**任务负荷 3.0--3.25** 范围内。

<figure style="margin:1.6rem auto 1.25rem auto; width:100%; max-width:1040px;"><div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:14px 14px 10px 14px; box-shadow:0 1px 2px rgba(15,23,42,0.06);"><img src="../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report_v2/figures/figure_07_threshold_detail.svg" alt="figure_07_threshold_detail" width="1040" loading="lazy" style="display:block; width:100%; max-width:1040px; height:auto; margin:0 auto;" /></div><figcaption style="margin-top:0.55rem; text-align:center; font-size:0.92rem; line-height:1.45; color:#6b7280;">图 7. 阈值转变细节。</figcaption></figure>

图 7 通过三个互补面板分离阈值机制：

**(a) 阈值处的压力**：积压首次出现时，代理已经历升高的压力，表明系统在可见过载之前就已
达到容量极限。更高的委托水平使起始点对应更低的压力值——委托更多的代理更早触及容量壁垒。

**(b) 首次积压的任务负荷**：阈值任务负荷在各委托水平间高度一致，徘徊在 3.0-3.25 任务/步。
这一仅 0.25 单位的窄带代表临界窗口：低于此值系统找到均衡，高于此值累积过载开始。

**(c) 精细过渡带**：最小和最大委托水平之间的压力包络在阈值之上呈现紧密收敛。一旦积压
开始累积，系统轨迹主要由任务负荷决定，委托水平成为次要因素。

<figure style="margin:1.6rem auto 1.25rem auto; width:100%; max-width:1040px;"><div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:14px 14px 10px 14px; box-shadow:0 1px 2px rgba(15,23,42,0.06);"><img src="../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report_v2/figures/figure_08_story_timeseries.svg" alt="figure_08_story_timeseries" width="1040" loading="lazy" style="display:block; width:100%; max-width:1040px; height:auto; margin:0 auto;" /></div><figcaption style="margin-top:0.55rem; text-align:center; font-size:0.92rem; line-height:1.45; color:#6b7280;">图 8. 四类故事案例动态轨迹。</figcaption></figure>

图 8 通过四个故事案例追踪六项指标的动态轨迹：

- **自主基线**：稳定均衡，压力低（0.034），
  总劳动适中（428.3h），积压为零。
- **便利基线**：较高但仍稳定的均衡，压力 0.052，
  总劳动 566.8h。服务劳动占总劳动的
  主要比例。
- **阈值压力**：近临界运行，压力 0.189，
  总劳动 595.3h。积压可能间歇出现但
  不会螺旋失控。
- **过载便利**：灾难性崩溃。压力在约 50 步内饱和至 1.0。积压指数增长至
  133788 个任务。总劳动达到上限
  （800.0h）。这是内卷螺旋的
  纯粹形态。

**本结果未能说明的：** 3.0--3.25 阈值带是该模型特定配置（100 代理、8 小时预算、15% 协调
开销、11% 提供者开销、贪心匹配）的属性。阈值*概念*——分隔可管理与灾难性动力学的窄带——
是可迁移的洞见；具体数值是该特定模型的属性。

### 6.3 H3：自主权保留福祉（部分支持）

<figure style="margin:1.6rem auto 1.25rem auto; width:100%; max-width:920px;"><div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:14px 14px 10px 14px; box-shadow:0 1px 2px rgba(15,23,42,0.06);"><img src="../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report_v2/figures/figure_09_labor_decomposition.svg" alt="figure_09_labor_decomposition" width="920" loading="lazy" style="display:block; width:100%; max-width:920px; height:auto; margin:0 auto;" /></div><figcaption style="margin-top:0.55rem; text-align:center; font-size:0.92rem; line-height:1.45; color:#6b7280;">图 9. 各案例劳动结构分解。</figcaption></figure>

图 9 将劳动预算分解为三个组成部分：自劳动（代理自行完成的任务）、服务劳动（提供者代为完成
的任务）和协调成本（匹配和委托交易的开销）。

分解揭示了便利如何在*过载*系统之前先*重塑*劳动结构：

- **自主基线**：自劳动占主导（380.2h），
  服务劳动最低（45.0h），
  协调可忽略（3.1h）。
  总计：428.3h。
- **便利基线**：自劳动降至 177.3h，但服务劳动
  升至 361.4h，协调成本增加
  28.1h。总计：
  566.8h——尽管自劳动大幅减少，总量反而
  *更高*。这是 H1 在组件层面的具体表现。

委托劳动增量线（橙色，右轴）量化了委托的*净*劳动效应：在便利配置中始终为正，证实在本模型中
委托是*净劳动创造者*而非劳动节省者。每个委托任务因协调开销（15%）和提供者时间惩罚（11%）
而产生比自行完成更多的总系统工时。

<figure style="margin:1.6rem auto 1.25rem auto; width:100%; max-width:760px;"><div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:14px 14px 10px 14px; box-shadow:0 1px 2px rgba(15,23,42,0.06);"><img src="../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report_v2/figures/figure_10_available_time_density.svg" alt="figure_10_available_time_density" width="760" loading="lazy" style="display:block; width:100%; max-width:760px; height:auto; margin:0 auto;" /></div><figcaption style="margin-top:0.55rem; text-align:center; font-size:0.92rem; line-height:1.45; color:#6b7280;">图 10. 可用时间分布。</figcaption></figure>

图 10 比较最终步的可用时间分布。A 类代理以 3.7 小时为中心呈现宽分布。
B 类代理聚集在更低的 2.5 小时处且分布更紧——从众压力使委托行为
趋同，也使其后果趋同。

1.20 小时的可用时间差距代表了模型抽象框架内
有意义的生活方式差异：A 类代理保留约 45.7% 的日预算
作为自由时间，B 类仅 30.7%。在模型中，这是
"便利的代价"——尽管模型无法评估代理是否会主观偏好这一权衡。

**本结果未能说明的：** "福祉"仅通过可用时间和压力指标近似。模型无法衡量主观满意度、
感知便利、委托服务质量或自由时间的心理价值。B 类代理可能尽管可用时间较少但体验到更高的
感知生活质量——这完全超出模型的测量能力。"部分支持"的判定反映了我们能测量的（时间、压力）
与完整福祉评估所需测量的之间的重要差距。

### 6.4 H4：混合系统与规范锁定（部分支持，重要阴性结果）

<figure style="margin:1.6rem auto 1.25rem auto; width:100%; max-width:760px;"><div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:14px 14px 10px 14px; box-shadow:0 1px 2px rgba(15,23,42,0.06);"><img src="../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report_v2/figures/figure_11_mixed_heatmap.svg" alt="figure_11_mixed_heatmap" width="760" loading="lazy" style="display:block; width:100%; max-width:760px; height:auto; margin:0 auto;" /></div><figcaption style="margin-top:0.55rem; text-align:center; font-size:0.92rem; line-height:1.45; color:#6b7280;">图 11. 混合系统稳定性热力图。</figcaption></figure>

图 11 映射混合系统参数空间中最终委托率的标准差，测试中等委托水平的群体是否在从众压力下
向极端漂移。实验在初始委托偏好（0.35--0.65）和社会从众压力（0.1--0.9）之间进行网格扫描。

结果清晰且值得注意：最大观察标准差仅为 **0.0125**。在所有 30 个
参数组合中，系统保持惊人的稳定。更高的从众压力不会产生可测量的更大分散度——热图中的
单元格标注显示整个网格中数值几乎一致。

<figure style="margin:1.6rem auto 1.25rem auto; width:100%; max-width:760px;"><div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:14px 14px 10px 14px; box-shadow:0 1px 2px rgba(15,23,42,0.06);"><img src="../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report_v2/figures/figure_12_mixed_scatter.svg" alt="figure_12_mixed_scatter" width="760" loading="lazy" style="display:block; width:100%; max-width:760px; height:auto; margin:0 auto;" /></div><figcaption style="margin-top:0.55rem; text-align:center; font-size:0.92rem; line-height:1.45; color:#6b7280;">图 12. 混合系统逐种子结果。</figcaption></figure>

图 12 从逐种子视角强化了这一发现。每个点代表一次仿真运行的最终委托率与其初始委托偏好均值
的关系，颜色编码从众压力。点紧密聚集在恒等线（初始 = 最终）附近，对从众压力无可见依赖。
即使在最高从众压力（0.9）下，最终委托率也在初始值的 0.0125 范围内。

这是一个**重要的阴性结果**，其科学价值恰恰在于约束了模型的解释力。可能的解释包括：

1. **弱适应率**：偏好适应率（每步 0.02--0.05）相对于仿真长度可能太慢。
2. **对称从众**：当前从众机制将代理向邻域均值对称推动，而非不对称放大偏差。
3. **缺少阈值反馈**：模型缺少使委托在临界采用水平之上自我强化的机制（如使自我服务
   逐渐变难的技能衰退）。

该阴性结果为未来工作指明了具体方向：需要更强的反馈机制（内生定价、技能退化、显式规范
级联）才能重现假设中的锁定动力学。当前模型建立了一个*基线*，用以衡量附加机制是否产生
质性不同的行为。

### 6.5 服务成本敏感性（交叉分析）

<figure style="margin:1.6rem auto 1.25rem auto; width:100%; max-width:1040px;"><div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:14px 14px 10px 14px; box-shadow:0 1px 2px rgba(15,23,42,0.06);"><img src="../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report_v2/figures/figure_13_cost_sensitivity.svg" alt="figure_13_cost_sensitivity" width="1040" loading="lazy" style="display:block; width:100%; max-width:1040px; height:auto; margin:0 auto;" /></div><figcaption style="margin-top:0.55rem; text-align:center; font-size:0.92rem; line-height:1.45; color:#6b7280;">图 13. 服务成本敏感性。</figcaption></figure>

图 13 检验服务成本作为情境调节因子的角色。左面板比较五种参数环境下低与高服务成本的压力水平；
右面板识别低成本从有益转变为有害的任务负荷转折点。

核心发现是**低服务成本是有条件有益的**：

- 在**默认**环境中，较低的服务成本适度降低压力（0.019
  vs 0.044）——更便宜的服务使偶尔委托真正减轻了
  时间压力。
- 在**A 类**环境（低委托、高自给）中，成本差异影响极小，因为无论价格如何，很少有代理选择委托。
- 在**过载**环境中，低成本和高成本均产生接近最大压力
  （1.000 vs
  1.000）——系统已超越价格信号能影响结果的范围。
- 在**阈值带**附近（任务负荷 3.0--3.25），低服务成本反而*放大*压力——更便宜的服务吸引更多委托
  请求，超出提供者容量，产生比高成本场景（代理更多自我服务）更多的积压。

右面板映射"翻转点"——低成本从减压转变为增压的任务负荷。该翻转点一致落在 3.0--3.5 范围，
强化了 H2 中识别的阈值动力学。服务成本与任务负荷之间的交互作用是典型的非线性现象：
同一干预（降价）因系统是否处于容量边界以下或附近而产生相反效果。

---

## 7. 假设判定矩阵

| hypothesis | judgment | evidence | interpretation |
| --- | --- | --- | --- |
| H1 | Strong support | Type B maintains a 30.0% labor premium at 450 steps. | Higher delegation is consistently linked to more total system labor. |
| H2 | Strong support | Threshold band at task load 3.10, refined to 3.0–3.25. | A narrow overload band precedes the high-backlog regime. |
| H3 | Partial support | Type A retains 3.65h vs 2.46h for Type B. | Autonomy preserves more personal time; convenience is not directly measured. |
| H4 | Partial (important negative) | Max mixed-state std = 0.0125. | Moderate instability, but no dramatic bifurcation under current parameters. |

---

## 8. 讨论

### 8.1 声明边界

本分析采用三层声明框架以维持透明度：

**可以自信地说：**
- ABM 可以识别更高委托与更高系统总劳动相关联的参数区域。
- ABM 可以比较不同配置下压力、劳动和不平等的演化轨迹。
- ABM 可以测试中等委托状态在其反馈规则下是否保持稳定。

**需附加说明：**
- 较低的服务价格推动更多委托行为，但仅作为外生实验处理。
- 规范锁定通过委托收敛近似代理，而非直接测量延迟容忍度。
- 便利将负担转移向提供者，但确切的劳动市场结构超出模型范围。

**无法声称：**
- 模型无法识别完整的因果循环，因为价格不是内生的。
- 模型无法衡量真实人口、具名社会或具体政策结果。
- 模型无法测试技能衰退、人口不平等或显式延迟容忍度动力学。

### 8.2 翻译过程作为贡献

本工作的首要贡献不在于关于委托动力学的具体发现，而在于展示的**结构化翻译过程**——从模糊
的社会观察（"便利在这里感觉不同"）出发，将其形式化为反馈环路结构，实现为白盒代理决策规则，
运行系统化实验，并诚实报告发现。

这一过程展示了两项具体能力：

1. **信息综合与概念化**：将定性观察转化为因果环路图、代理决策函数、参数预设等结构化输出，
   适用于模型规范。
2. **数据管理**：使用经验风格化事实指导模型参数、设计可重复实验、维护每个图表和表格的
   源级可审计性，并应用透明的三层声明框架。

### 8.3 与复杂性科学的关联

便利-自主权张力映射到复杂适应系统中已确立的概念：驱动路径依赖的正反馈循环、标志状态
转变的阈值效应、以及从同质代理规则中涌现的不平等。模型结果与这些理论预期一致，尽管具体
定量发现取决于模型的参数化。

---

## 9. 本研究的范围与局限性

### 9.1 方法论演示，非领域贡献

作者是计算与 IT 专业人员，**不是受过训练的社会科学家或经济学家**。本报告展示的是将定性观察
转化为正式计算模型的*过程*，具体展示以下能力：

- 将定性和定量输入综合为结构化、可测试的计算框架
- 设计和执行系统化仿真实验
- 维护具有透明溯源的严格数据管理

**模型设计、理论推导及所得结论从领域专家角度来看可能并不准确。** ABM 是对极其复杂的社会现象
的刻意简化的风格化表示。读者应评估*方法论和过程质量*，而非将实质性结论视为权威性社会科学发现。

### 9.2 技术局限

- **外生价格**：服务成本为固定参数，而非由市场决定。这阻止了测试廉价服务与服务依赖
  之间的完整循环因果关系。
- **无延迟容忍度**：模型未捕捉原始观察中识别的"延迟容忍度"变量。这需要显式的时间
  偏好机制。
- **规模**：小世界网络上的 100 个代理。更大的群体可能揭示不同的动力学。
- **缺失机制**：技能衰退、人口异质性、制度缓冲和显式服务质量变化未被建模。
- **风格化事实而非校准**：参数由 ILO/WVS/OECD 数据范围启发，但未拟合到具体经验分布。

### 9.3 未来扩展

- **内生价格形成**：响应供需的服务成本。
- **延迟容忍度动力学**：发展服务速度期望的代理。
- **技能衰退与学习**：随实践或委托频率变化的能力。
- **更大的社区结构网络**：聚集的规范和异质邻域。
- **经验校准**：与领域专家合作，将模型扎根于具体数据。

---

## 10. 结论

本代理基建模研究通过 14,656 次仿真运行探索了**便利-自主权张力**，测试了关于服务委托、
劳动转移、阈值效应和规范锁定的四个假设。模型内的关键发现：

1. **委托增加系统劳动**（H1，强支持）：B 类产生约 30.0%
   的额外总劳动，这一差距在所有仿真时长中持续存在。
2. **窄阈值触发内卷**（H2，强支持）：从可管理委托到累积过载的转变发生在任务负荷
   3.0--3.25 的窄带中——仅 0.25 单位的参数窗口分隔了均衡与崩溃。
3. **自主权保留可用时间**（H3，部分支持）：A 类代理保留更多个人时间
  （3.65h vs 2.46h），尽管"福祉"
   仅通过时间和压力代理指标近似。
4. **混合系统不稳定性较弱**（H4，部分支持，重要阴性结果）：在当前参数下，混合系统不会
   剧烈分叉——对未来建模的约束条件。

**本工作的贡献在于展示了从定性社会观察到正式计算模型再到透明实验分析的严谨方法论，
而非特定的实质性结论。** 模型是一个概念验证，展示了如何将关于社会系统的日常观察
形式化、测试并诚实报告，同时保持对分析能做和不能做的声明的清晰边界。

---

## 附录

### A.1 参数敏感性

<figure style="margin:1.6rem auto 1.25rem auto; width:100%; max-width:1040px;"><div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:14px 14px 10px 14px; box-shadow:0 1px 2px rgba(15,23,42,0.06);"><img src="../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report_v2/figures/figure_14_param_sensitivity.svg" alt="figure_14_param_sensitivity" width="1040" loading="lazy" style="display:block; width:100%; max-width:1040px; height:auto; margin:0 auto;" /></div><figcaption style="margin-top:0.55rem; text-align:center; font-size:0.92rem; line-height:1.45; color:#6b7280;">图 14. 参数敏感性面板。</figcaption></figure>

图 14 展示三项关键结果指标（平均压力、总劳动时间、积压任务）如何随任务负荷在五个不同
委托水平（0.05、0.25、0.45、0.65、0.85）下变化：

- **压力**：低任务负荷（< 2.5）下，无论委托水平如何，压力均匀低。阈值带（3.0--3.25）
  以上压力快速饱和。任务负荷是主导因素。
- **总劳动时间**：委托水平之间的分离在阈值以下最为可见。更高委托即使在系统舒适时也
  产生更多总劳动——证实 H1 的发现不依赖于过载。
- **积压任务**（对数标度）：阈值最戏剧性的可视化。3.0 以下积压为零，3.25 以上积压增长
  数个数量级。0.25 单位窗口内从零到数千的陡峭转变说明了为何阈值是相变而非渐进退化。

### A.2 实验覆盖

<figure style="margin:1.6rem auto 1.25rem auto; width:100%; max-width:920px;"><div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:14px 14px 10px 14px; box-shadow:0 1px 2px rgba(15,23,42,0.06);"><img src="../../data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401/report_assets/formal_report_v2/figures/figure_15_campaign_coverage.svg" alt="figure_15_campaign_coverage" width="920" loading="lazy" style="display:block; width:100%; max-width:920px; height:auto; margin:0 auto;" /></div><figcaption style="margin-top:0.55rem; text-align:center; font-size:0.92rem; line-height:1.45; color:#6b7280;">图 15. 实验覆盖范围图。</figcaption></figure>

图 15 映射所有 14,656 次运行在四个研究包中的参数空间覆盖。B 包（便利转移）在委托-任务
负荷平面提供最密集覆盖。A 包（日常摩擦）覆盖两种特定配置的四个时长。C 包（廉价服务陷阱）
探索服务成本维度。D 包（规范锁定）探查从众-委托交互空间。综合覆盖确保与所有四个假设相关
的关键参数交互以足够密度采样。

---

*本模型使用抽象的 A 类 / B 类配置探索社会动力学。不旨在刻画或评价任何特定社会、文化或国家。*

*报告由 `formal_campaign_report_v2.py` 从实验数据生成。所有图表均有对应的源 CSV 文件供独立验证。*
