# Social Modeling and Model Design Introduction

*The Convenience Paradox: Agent-Based Modeling of Service Delegation and Social Involution*

> **Disclaimer**: This model explores abstract social dynamics and is not intended
> to characterise or evaluate any specific society, culture, or nation. All
> references use abstract system labels ("Type A", "Type B"). Empirical data
> is cited by dataset name only.

---

## Table of Contents

1. [The Motivating Observation](#1-the-motivating-observation)
2. [Theoretical Framing: What Is the "Convenience Paradox"?](#2-theoretical-framing-what-is-the-convenience-paradox)
3. [Why Agent-Based Modeling?](#3-why-agent-based-modeling)
4. [From Observation to Abstraction: The Two Society Archetypes](#4-from-observation-to-abstraction-the-two-society-archetypes)
5. [The Agent: A Resident Navigating Daily Life](#5-the-agent-a-resident-navigating-daily-life)
6. [The Decision Engine: Self-Serve or Delegate?](#6-the-decision-engine-self-serve-or-delegate)
7. [The Involution Mechanism: How Convenience Becomes a Trap](#7-the-involution-mechanism-how-convenience-becomes-a-trap)
8. [Social Conformity and Norm Diffusion](#8-social-conformity-and-norm-diffusion)
9. [Parameter Design and Theoretical Mapping](#9-parameter-design-and-theoretical-mapping)
10. [Metrics as Social Indicators](#10-metrics-as-social-indicators)
11. [Research Hypotheses](#11-research-hypotheses)
12. [Empirical Grounding Strategy](#12-empirical-grounding-strategy)
13. [Methodological Boundaries and Limitations](#13-methodological-boundaries-and-limitations)

---

## 1. The Motivating Observation

Across different societies, people organise the routine business of daily
life — cooking, cleaning, running errands, processing paperwork, getting
repairs done — in strikingly different ways. Two broad patterns can be
observed:

**Pattern A — The Autonomy-Oriented System.** Individuals tend to handle most
matters personally. Filing taxes, cooking dinner, assembling furniture —
these are considered part of ordinary adult competence. This requires more
upfront effort and personal time investment, but it grants each person a
sense of independent control. When a task *does* require reliance on
someone else — say, a government office or a tradesperson — there is a
culturally ingrained tolerance for waiting. The expectation of immediate
responsiveness is low. The boundary between "my responsibility" and
"someone else's job" is drawn conservatively: most things fall on the
individual's side.

**Pattern B — The Convenience-Oriented System.** Many daily tasks are
routinely outsourced to a vast, inexpensive service economy. Food arrives
at your door within minutes. Shops stay open late and on weekends.
Government paperwork can be handled by intermediaries. This *feels*
remarkably efficient from any single individual's perspective — there is
always someone ready to do it for you, quickly and cheaply. But zoom out,
and a structural paradox emerges: *someone else* is expending working hours
to provide that convenience. And that someone is simultaneously delegating
*their* tasks to yet another someone. The result is a society where everyone
is perpetually busy — rushing around to provide convenience for one
another — yet no one seems to have more free time than before. In fact,
many people have *less*.

This observation, born from lived experience across different social
systems, raises a set of questions that lie at the intersection of
sociology, economics, and complexity science:

- Does a high-delegation society actually produce more aggregate well-being,
  or does it simply redistribute the labour of daily life while adding
  transactional overhead?
- Is there a tipping point — a critical level of service delegation — beyond
  which the system enters a self-reinforcing spiral of escalating mutual
  service provision?
- In the long run, which pattern leaves residents with more genuine leisure
  time and lower chronic stress?
- Are moderate, mixed systems stable, or do they inevitably drift toward one
  extreme or the other?

These are the questions this project was designed to investigate.

---

## 2. Theoretical Framing: What Is the "Convenience Paradox"?

The "convenience paradox" is the core theoretical proposition of this
project. It can be stated concisely:

> **When individuals delegate tasks to gain personal convenience, they
> collectively create a system that requires *more* total labour than if
> everyone had self-served — because someone must perform every delegated
> task, and the delegation process itself introduces overhead.**

This proposition draws on several streams of social and economic theory:

### 2.1 The Division of Labour and Its Discontents

Adam Smith's foundational insight in *The Wealth of Nations* (1776) was
that specialisation increases productivity. A pin factory with ten
specialised workers produces more pins per person than ten generalists.
This logic extends to service economies: a professional house cleaner
is faster than an amateur. But Smith also noted a crucial qualifier —
the efficiency gains of specialisation apply to *production*, not
necessarily to the full cycle of daily life. When every routine personal
activity is outsourced to a specialist, the overhead of coordination,
transportation, and market friction can overwhelm the efficiency gain.

The model captures this through the **provider proficiency parameter**
(fixed at 0.6 in `model/agents.py`): service providers are competent
generalists, but they are systematically *less efficient* at your specific
task than you would be with moderate skill. A professional cleaner is
faster at cleaning in general — but *your* particular kitchen layout,
your preferences, and your definition of "done" introduce friction that
self-service avoids.

### 2.2 Involution (Neijuan / 内卷)

The concept of "involution" — originally coined by anthropologist Clifford
Geertz in *Agricultural Involution* (1963) to describe Javanese rice
farming, and later adopted in broader sociological discourse — describes
a process of intensification without development. More and more effort
is invested, but the output per unit of effort does not increase. The
system grows denser and busier without anyone becoming meaningfully
better off.

In contemporary usage, the term has been applied to describe social
dynamics where competitive pressures compel individuals to invest ever
more effort simply to maintain their relative position — a zero-sum
escalation. This project extends the concept to service delegation:
when everyone delegates to save time, the collective demand for service
labour rises, pulling more people into service provision and ultimately
consuming the time that delegation was supposed to free up.

The model operationalises this through the **total_labor_hours** metric
and the **involution feedback loop** (§7 below): agents who delegate
their tasks to save time then accept service tasks from the pool to earn
income — ending the day no better off than if they had simply done their
own work.

### 2.3 Social Conformity and Norm Cascades

Solomon Asch's conformity experiments (1951) and subsequent work in
social psychology demonstrate that individuals adjust their behaviour to
match perceived group norms, even when those norms are suboptimal.
Everett Rogers' *Diffusion of Innovations* (1962) describes how
behaviours spread through social networks via local adoption cascades.

In the context of service delegation, conformity operates as a powerful
amplifier: if your neighbours all use food delivery, you feel social
pressure to do the same — and the infrastructure shifts to *assume*
delivery is the norm (fewer nearby grocery stores, shorter cooking
equipment shelf space, reduced cooking skill transmission). The cost
of non-conformity rises, making delegation increasingly unavoidable
even for those who would prefer self-service.

The model captures this through the **social_conformity_pressure**
parameter and the **preference drift mechanism** in the agent's
`update_state()` method: each agent nudges their delegation preference
toward the average of their network neighbours, weighted by conformity
pressure and amplified by personal stress.

### 2.4 Time Poverty and the Service Economy

Sociologist Jonathan Gershuny's work on time-use surveys reveals a
counterintuitive pattern: residents of high-service economies do not
necessarily report more leisure. Instead, the time "freed" by delegation
is often consumed by the employment needed to *pay* for those services,
or by participation in the service economy itself. Economist Juliet
Schor's *The Overworked American* (1991) documents how rising
consumption standards create a work-spend cycle that erodes leisure
even as productivity grows.

The model's **income** and **available_time** tracking at the agent
level makes this dynamic visible: agents can simultaneously be net
delegators (spending money) and net providers (spending time), ending
each day with both negative income *and* depleted time.

---

## 3. Why Agent-Based Modeling?

The convenience paradox is fundamentally an **emergent phenomenon**: no
individual intends to create a system-level involution spiral. Each
person is making locally rational decisions ("this task is cheaper to
delegate than to do myself"). The macro-level outcome — everyone being
busier — emerges from the interaction of many such micro-level decisions,
amplified by social network effects.

This is precisely the class of problems for which Agent-Based Modeling
(ABM) was designed. ABM allows us to:

1. **Specify individual behaviour rules** (micro-level) and observe what
   collective patterns emerge (macro-level), without imposing top-down
   assumptions about system equilibria.

2. **Embed agents in a social network** so that peer influence,
   information diffusion, and local norm formation arise naturally from
   the network topology.

3. **Explore parameter spaces** systematically: we can vary delegation
   preference, service cost, and conformity pressure independently to
   identify thresholds, bifurcation points, and sensitivity.

4. **Run counterfactual experiments** that are impossible in the real
   world: what happens if we take a society at equilibrium and suddenly
   halve the cost of services? Does a moderate society stay moderate,
   or does it cascade toward one extreme?

The modeling framework used is **Mesa** (version 3.5.x), a Python-based
ABM library. The simulation is designed as a "white-box" model: every
agent decision is governed by explicit, parameterised rules — no opaque
machine learning or hidden logic. This transparency is essential for
a model intended to build theoretical understanding rather than to
predict specific outcomes.

---

## 4. From Observation to Abstraction: The Two Society Archetypes

To investigate the convenience paradox without attributing behaviours to
any specific real-world society, the model defines two **abstract
archetypes** — idealised poles of a spectrum:

### Type A Society (Autonomy-Oriented)

| Characteristic | Description |
|---|---|
| Cultural norm | Self-reliance; handling one's own affairs is a mark of competence |
| Delegation attitude | Deliberate and selective; reserved for genuinely specialised tasks |
| Service economy | Exists but moderately priced; not the default for routine tasks |
| Social pressure | Low; individuals choose their own strategies without strong norm enforcement |
| Time orientation | Higher tolerance for personal time investment; lower expectation of instant service |

### Type B Society (Convenience-Oriented)

| Characteristic | Description |
|---|---|
| Cultural norm | Service utilisation; using available services is practical and expected |
| Delegation attitude | Pervasive and routine; extends to tasks most individuals could handle themselves |
| Service economy | Large, cheap, and competitive; infrastructure assumes delegation as default |
| Social pressure | High; deviation from delegation norms incurs social cost and practical friction |
| Time orientation | Low tolerance for personal task investment; high expectation of immediate availability |

These archetypes are not value judgments. Each has structural strengths
and weaknesses that the model is designed to reveal under controlled
conditions.

---

## 5. The Agent: A Resident Navigating Daily Life

Each agent in the simulation represents a **Resident** — a person living
in the abstract society, facing the universal challenge of managing daily
tasks within a finite time budget.

### 5.1 The Daily Time Budget

Every agent begins each simulated day with `initial_available_time` hours
of discretionary time (default: 8.0 hours). This represents the hours
remaining after fixed commitments — sleep, baseline employment, commuting.
As the agent handles tasks (either personally or as a service provider),
this budget is consumed. The amount remaining at end of day determines
whether the agent experiences stress.

The choice to give both Type A and Type B societies the *same* initial
time budget (8.0 hours) is deliberate: both societies have 24-hour days.
The difference in outcomes must emerge from *how agents use their time*,
not from an unfair structural advantage.

### 5.2 Daily Tasks

Each day, every agent receives a random number of tasks drawn from a
Gaussian distribution (mean and standard deviation set by
`tasks_per_step_mean` and `tasks_per_step_std`). Tasks are drawn from
four categories, each representing a class of daily life activity:

| Task Type | Base Time (hours) | Skill Requirement | Social Mapping |
|---|---|---|---|
| **domestic** | 0.8 | 0.3 (low) | Cooking, cleaning, laundry — routine tasks most adults can do adequately |
| **administrative** | 1.2 | 0.5 (moderate) | Paperwork, banking, scheduling — requires literacy and organisational skill |
| **errand** | 0.5 | 0.2 (very low) | Shopping, parcel collection — frequently delegated in convenience societies |
| **maintenance** | 1.5 | 0.65 (high) | Household repairs, DIY — highest skill barrier, most time-intensive |

The **base_time** is the duration at average proficiency (skill = 1.0).
An agent with lower skill takes proportionally longer (the formula is
`base_time / proficiency`). This creates a natural economic logic:
unskilled agents gain more from delegation because self-service is slow
for them, while skilled agents gain less because they can do it quickly
themselves.

The **skill_requirement** represents a threshold below which self-service
becomes notably inefficient. It is used conceptually to define task
difficulty but does not create a hard barrier — agents can always attempt
any task; the cost is simply higher if their skill is low.

### 5.3 Skills and Heterogeneity

Each agent has a `skill_set` — a dictionary mapping each task type to a
proficiency value between 0.3 and 0.9, drawn uniformly at random during
model initialisation. No agent is perfectly skilled at everything, and no
agent is completely incompetent. This heterogeneity ensures that
delegation decisions are not trivially identical across agents:

- An agent with high domestic skill (0.85) and low maintenance skill (0.35)
  will rationally self-serve domestic tasks but be tempted to delegate
  maintenance.
- This per-task variation interacts with the delegation preference to
  create a rich landscape of individual strategies.

### 5.4 The Dual Role: Delegator and Provider

A critical design choice — and one that directly models the social
phenomenon under investigation — is that **every agent can be both a
delegator and a service provider**. There is no separate "worker class"
in the simulation. An agent may delegate all three of their daily tasks
to save time, then turn around and accept two tasks from the service
pool to earn income.

This captures the real-world dynamic where the same person might order
takeout for dinner (delegating cooking) and then spend their evening
driving for a ride-hailing service (providing transport for others). The
time "saved" by delegating is consumed by providing — and the net effect
on leisure is zero or negative.

---

## 6. The Decision Engine: Self-Serve or Delegate?

The heart of the model is the delegation decision. For each task, each
agent runs a probabilistic decision function that integrates four factors:

### 6.1 Base Delegation Preference (Cultural Disposition)

The agent's `delegation_preference` is a value between 0 and 1,
representing their inherent tendency to delegate. This is the primary
variable of interest across the model. It is initialised from a normal
distribution with mean `delegation_preference_mean` (set by the society
preset) and evolves over time through social influence.

**Social interpretation**: This parameter encodes the cultural norm of
the society. In a Type A society (mean ≈ 0.25), most agents default to
self-service. In a Type B society (mean ≈ 0.72), most agents default
to delegation. The standard deviation (0.10 in both presets) ensures
that every society has some variation — contrarians who buck the norm.

### 6.2 Stress Boost

Stressed agents are more likely to delegate. The formula adds
`stress_level × 0.30` to the delegation probability, making delegation
a coping mechanism for time pressure.

**Social interpretation**: When people are overwhelmed, they reach for
convenience — ordering delivery instead of cooking, hiring someone
instead of DIY. This is individually rational but collectively
dangerous: if *everyone* does it, demand for services rises, pulling
more people into service provision, creating more time pressure, and
feeding a positive feedback loop (the involution spiral).

### 6.3 Skill Discount

High proficiency in the relevant task type *reduces* delegation
probability by `proficiency × 0.20`. Skilled agents gain less from
delegating because they can do the task quickly themselves.

**Social interpretation**: A competent cook has little reason to order
takeout — it costs money and the food may not be as good. A skilled
handyman has little reason to hire a repair service. Skill acts as a
natural buffer against the delegation cascade: societies that maintain
broad practical skills in the population are more resistant to
involution.

### 6.4 Cost Penalty

Higher service costs reduce delegation probability by
`service_cost_factor × 0.25`. When services are expensive, delegation
carries a meaningful economic cost that agents weigh against the time
benefit.

**Social interpretation**: This is the price mechanism. In a Type A
society, services are moderately expensive (cost factor 0.65), creating
a significant disincentive. In a Type B society, services are cheap
(cost factor 0.20), removing the economic brake on delegation.
The cheapness of services in a high-delegation society is both a symptom
and a cause: cheap services encourage delegation, and high demand for
services (fuelled by delegation norms) creates competitive downward
pressure on prices through an abundance of providers.

### 6.5 Forced Delegation

If an agent's remaining time is less than half the task's time cost,
they *must* delegate regardless of preference — they simply cannot fit
the task into their day. This models the real constraint that time is
finite: when you are out of hours, convenience is no longer a choice but
a necessity.

### 6.6 The Combined Formula

The effective delegation probability is:

$$p_{effective} = \text{clamp}\bigl(p_{base} + 0.30 \times stress - 0.20 \times skill - 0.25 \times cost,\ 0,\ 1\bigr)$$

The agent then draws a uniform random number; if it falls below
$p_{effective}$, the task is delegated. Otherwise, the agent self-serves.

This formula is deliberately simple, transparent, and auditable. Every
coefficient is visible in the source code. There are no hidden weights
or opaque learned parameters. This is essential for a model whose purpose
is theoretical exploration rather than prediction.

---

## 7. The Involution Mechanism: How Convenience Becomes a Trap

The central theoretical contribution of this model is the **involution
feedback loop** — a self-reinforcing cycle that can emerge in
high-delegation societies. The loop operates across three phases of each
simulated day:

### Phase 1 — Task Generation and Delegation Decisions

Each agent generates tasks and decides how to handle them. In a
high-delegation society, many agents place their tasks into the
communal **service pool**.

### Phase 2 — Service Matching

The model distributes tasks from the service pool to agents with
available time. The matching algorithm is deliberately simple: tasks
are assigned to whichever agent currently has the most spare time
(a greedy heuristic). Critically, any agent can be a provider —
including agents who just delegated their own tasks.

This is where the paradox materialises:

1. Agent Alice delegates her cooking task to save 0.8 hours.
2. Agent Bob delegated his errand task to save 0.5 hours.
3. The service pool now contains both tasks.
4. Alice, who now has "free" time because she delegated, is matched as
   a provider for Bob's errand task. She spends 0.83 hours on it
   (at provider proficiency 0.6, the 0.5-hour errand takes
   0.5/0.6 ≈ 0.83 hours).
5. Bob is matched as a provider for Alice's cooking task. He spends
   0.8/0.6 ≈ 1.33 hours on it.
6. **Net result**: Alice "saved" 0.8 hours by delegating, then spent
   0.83 hours providing. Net time saved: -0.03 hours. Bob "saved" 0.5
   hours, then spent 1.33 hours. Net time saved: -0.83 hours.

**The system as a whole spent more total labour hours than if both had
self-served.** This is because provider proficiency (0.6) is below the
average self-service proficiency (0.3–0.9 range, mean ≈ 0.6), and
crucially, providers are *not as efficient at your specific task as you
are* — the overhead of serving a stranger's needs adds friction that
self-service avoids.

### Phase 3 — Stress and Preference Update

Agents who ended the day with insufficient remaining time accumulate
stress. Stressed agents are more likely to delegate the next day
(§6.2), which feeds more tasks into the pool, requiring more providers,
consuming more collective time, generating more stress — completing the
feedback loop.

Meanwhile, social conformity pulls agents' delegation preferences
toward their neighbours' average. In a society where most neighbours
delegate heavily, even reluctant agents are gradually drawn into the
delegation norm.

### The Spiral

The full loop is:

```
High delegation → Large service pool → Agents provide services to fill time
→ Less leisure time → More stress → Higher delegation preference
→ Even more delegation → Even larger pool → ...
```

This is "involution" in the precise Geertzian sense: intensification
without development. The system becomes busier and busier, but no one
gains more leisure. The model is designed to detect and measure this
spiral through its metrics (§10).

---

## 8. Social Conformity and Norm Diffusion

Agents do not exist in isolation. They are embedded in a **social
network** — a Watts-Strogatz small-world graph by default — that
determines who influences whom.

### 8.1 Network Topology

The Watts-Strogatz model produces networks with two key properties:

- **High clustering**: agents form tight local communities where most
  of your friends also know each other. This creates "norm pockets"
  where local consensus can develop.
- **Short path lengths**: a few long-range connections ensure that norms
  can diffuse across the entire society relatively quickly, not just
  within isolated clusters.

These properties are well-established in the social network literature
as characteristic of real-world social networks (Watts & Strogatz, 1998).

The default configuration uses k=4 (each agent starts with 4 neighbours)
and p=0.1 (10% of edges are randomly rewired), producing a network that
balances local cohesion with global connectivity.

### 8.2 The Conformity Mechanism

At the end of each day, every agent observes the mean delegation
preference of their network neighbours and nudges their own preference
toward that mean:

$$\Delta p = \alpha \times w_{conformity} \times (1 + 0.5 \times stress) \times (\bar{p}_{neighbours} - p_{self})$$

Where:
- $\alpha$ = `adaptation_rate` (step size, controlling how fast preferences change)
- $w_{conformity}$ = `social_conformity_pressure` (how much agents care about fitting in)
- $stress$ amplifies conformity (stressed agents are more susceptible to social influence)
- $\bar{p}_{neighbours}$ = mean delegation preference of neighbours
- $p_{self}$ = agent's current preference

**Social interpretation**: In a Type A society (conformity = 0.15),
agents are weakly influenced by peers — individual strategies persist.
In a Type B society (conformity = 0.65), peer pressure is strong —
agents who start with low delegation preference are rapidly pulled
toward the group norm. This captures the observation that in high-service
societies, the infrastructure and social expectations make non-delegation
increasingly difficult: if every restaurant assumes delivery is the
norm, the sit-down option erodes.

### 8.3 Stress as Conformity Amplifier

The `(1 + 0.5 × stress)` term means that stressed agents are *more*
susceptible to peer influence. This draws on behavioural science
findings (Cialdini, 2001) that uncertainty and cognitive load increase
reliance on social cues. A stressed, time-poor agent is more likely to
look at what their neighbours are doing and follow suit — even if that
behaviour is part of the problem.

---

## 9. Parameter Design and Theoretical Mapping

Every tuneable parameter in the model corresponds to a sociologically
meaningful dimension. This section provides the full mapping between
model parameters and the social phenomena they represent.

### 9.1 Core Behavioural Parameters

| Parameter | Type A Value | Type B Value | Social Meaning |
|---|---|---|---|
| `delegation_preference_mean` | 0.25 | 0.72 | **Cultural disposition toward self-reliance vs. service use.** The single most important parameter. It encodes the society's default answer to the question: "Should I do this myself or have someone do it for me?" Low values reflect cultures that value independence and personal competence; high values reflect cultures that value efficiency and specialised service. |
| `delegation_preference_std` | 0.10 | 0.10 | **Intra-society heterogeneity.** Both societies contain individuals who deviate from the norm. This prevents the model from being a trivial comparison of two homogeneous populations and allows emergent role differentiation (some agents become persistent providers, others persistent delegators). |
| `social_conformity_pressure` | 0.15 | 0.65 | **Strength of social norm enforcement.** Low conformity allows diverse strategies to coexist; high conformity drives the population toward a single behavioural equilibrium. This is the mechanism through which a "convenience culture" self-perpetuates: once enough people delegate, the social pressure to conform pulls the remaining self-servers into the delegation norm. |
| `adaptation_rate` | 0.02 | 0.05 | **Cultural inertia vs. dynamism.** Low adaptation rate means social norms change slowly — agents are set in their ways. High adaptation rate means the society is behaviourally fluid — agents quickly adjust to new circumstances and peer behaviour. Type B's faster adaptation enables the rapid norm cascades that can trigger involution spirals. |

### 9.2 Economic Parameters

| Parameter | Type A Value | Type B Value | Social Meaning |
|---|---|---|---|
| `service_cost_factor` | 0.65 | 0.20 | **Price of convenience.** In Type A, services are moderately expensive — delegation is a considered investment. In Type B, services are cheap — delegation is the path of least resistance. Low service cost removes the economic friction that would otherwise discourage excessive delegation. This parameter is grounded in World Bank WDI data on service sector employment: in economies with very high service sector participation, competition drives prices down. |

### 9.3 Task Environment Parameters

| Parameter | Type A Value | Type B Value | Social Meaning |
|---|---|---|---|
| `tasks_per_step_mean` | 2.2 | 2.8 | **Daily task burden.** Type B's slightly higher task load reflects the busier pace of convenience-oriented societies (more deliveries to receive, more app-based interactions, more micro-transactions). This is grounded in ILO data showing higher average weekly hours in high-delegation regions. |
| `tasks_per_step_std` | 0.7 | 0.8 | **Day-to-day variability.** Type B has slightly more variable daily demands, reflecting the less predictable rhythm of life in a high-service economy where external dependencies introduce scheduling variability. |
| `initial_available_time` | 8.0 | 8.0 | **The 24-hour constraint.** Deliberately identical across both presets. Both societies have the same number of hours in a day. Any difference in outcomes — leisure, stress, total labour — must emerge from behavioural choices, not from an unfair structural endowment. This is a crucial design decision for the model's theoretical integrity. |

### 9.4 Psychological Parameters

| Parameter | Type A Value | Type B Value | Social Meaning |
|---|---|---|---|
| `stress_threshold` | 2.5 | 2.5 | **Well-being boundary.** The number of remaining hours below which an agent feels time-pressured. Identical across presets to ensure comparability: any difference in stress outcomes reflects behavioural dynamics, not different thresholds for feeling stressed. |
| `stress_recovery_rate` | 0.10 | 0.10 | **Psychological resilience.** How quickly stress dissipates when an agent does have surplus time. Again identical, ensuring the model isolates the effect of the delegation system rather than confounding it with differences in individual resilience. |

### 9.5 Network Parameters

| Parameter | Default Value | Social Meaning |
|---|---|---|
| `network_type` | `small_world` | **Community structure.** The Watts-Strogatz small-world topology balances local clustering (tight-knit neighbourhoods with shared norms) and global connectivity (ideas spreading across the whole society). An Erdős-Rényi random graph alternative is available for sensitivity analysis, testing whether the clustering structure of social ties matters for norm diffusion dynamics. |

---

## 10. Metrics as Social Indicators

The model collects nine model-level metrics at each simulation step.
Each metric is designed to measure a specific dimension of the
convenience paradox:

### 10.1 Well-Being Metrics

| Metric | Formula | What It Reveals |
|---|---|---|
| `avg_stress` | Mean of all agents' stress levels [0, 1] | **Collective well-being.** The primary indicator of whether the society is "working well." Rising average stress signals that the system is extracting more from agents than it returns in genuine convenience. This is the core test variable for H3. |
| `avg_income` | Mean of all agents' cumulative net income | **Economic health of agents.** In a zero-sum service economy, mean income trends toward zero (fees paid = fees earned). Divergence from zero signals structural imbalances. |
| `gini_available_time` | Gini coefficient of remaining daily hours | **Leisure inequality.** High inequality means some agents have ample free time while others are completely depleted — a hallmark of involution where service providers sacrifice their leisure to supply others' convenience. |
| `gini_income` | Gini coefficient of cumulative income | **Economic inequality.** In high-delegation societies, income concentrates among dedicated providers, creating a stratified service economy. |

### 10.2 System Efficiency Metrics

| Metric | Formula | What It Reveals |
|---|---|---|
| `total_labor_hours` | Sum of (initial_time − remaining_time) across all agents | **Collective effort.** The primary test variable for H1. If this is higher under delegation than under autonomy (holding task count constant), it demonstrates that delegation *adds* overhead to the system rather than saving labour. |
| `social_efficiency` | Tasks completed / total labour hours | **Productivity ratio.** Involution manifests as falling efficiency: more hours are worked, but the useful task completion rate does not keep pace. The gap between self-service efficiency and delegation efficiency is the "involution tax." |

### 10.3 Behavioural Dynamics Metrics

| Metric | Formula | What It Reveals |
|---|---|---|
| `avg_delegation_rate` | Mean delegation preference across all agents | **Norm convergence.** Tracks whether the society is drifting toward delegation or autonomy over time. A monotonically rising trend under high conformity pressure would support H4 (unstable middle ground). |
| `tasks_delegated_frac` | Delegated tasks / total tasks this step | **Realised vs. preferred behaviour.** The gap between this metric and `avg_delegation_rate` reveals whether preferences are being constrained by economic or capacity factors (wanting to delegate but unable to afford it, or willing to self-serve but forced to delegate due to time pressure). |
| `unmatched_tasks` | Delegated tasks − matched tasks | **Service capacity shortfall.** When demand for delegation exceeds the available provider pool, tasks go unserved. This is a leading indicator: a rising trend signals that the service economy is overloaded and stress is about to spike. |

---

## 11. Research Hypotheses

The model was designed to test four specific hypotheses about the
relationship between service delegation and social outcomes:

### H1: Higher delegation rates lead to higher total systemic labour hours

**Mechanism tested**: When tasks are delegated, they are executed by
providers at slightly below-average efficiency (proficiency 0.6). The
friction of outsourcing — a provider who doesn't know your kitchen, your
filing system, your preferences — means every delegated task takes
slightly longer than self-service by a competent individual.
Additionally, each delegation transaction involves economic overhead
(fee payment) that creates pressure for agents to earn income by
providing more services, further increasing total hours worked.

**How the model tests it**: Compare `total_labor_hours` between a Type A
run and a Type B run over the same number of steps, with the same
`initial_available_time`. If H1 holds, Type B should consistently
show higher total labour hours despite comparable task counts.

### H2: A critical delegation threshold triggers an involution spiral

**Mechanism tested**: Below a certain delegation level, the service pool
is small and easily absorbed by agents with spare capacity — the system
remains in a stable, low-stress equilibrium. Above that threshold, the
feedback loop (stress → delegate → more demand → providers busier →
more stress) becomes self-reinforcing and the system "tips" into a
high-labour, high-stress state.

**How the model tests it**: Parameter sweeps across `delegation_preference_mean`
from 0.1 to 0.9, holding other parameters constant. If H2 holds, there
should be a non-linear jump in `avg_stress` and `total_labor_hours` at
some critical delegation level — a bifurcation point rather than a
smooth linear increase.

### H3: Higher autonomy achieves lower perceived convenience but higher aggregate well-being

**Mechanism tested**: Type A agents handle more tasks personally, which
may feel less "convenient" (more personal effort per task). But because
they avoid the involution overhead, they retain more leisure time at end
of day and experience lower chronic stress.

**How the model tests it**: Compare `avg_stress` and mean
`available_time` at equilibrium between Type A and Type B runs. If H3
holds, Type A should show lower stress and more remaining leisure time,
despite agents spending more time on self-service.

### H4: Mixed systems are unstable, tending to drift toward extremes

**Mechanism tested**: A society starting with moderate delegation
(preference mean ≈ 0.50) contains both self-servers and delegators.
Social conformity creates local norm pockets. Over time, the conformity
mechanism should amplify small differences: clusters of delegators pull
their neighbours toward delegation, while self-server clusters pull
toward autonomy. If one side gains a slight advantage (e.g., through
random stress fluctuations), the conformity cascade accelerates until
the entire society has converged to one extreme.

**How the model tests it**: Run with `delegation_preference_mean = 0.50`
and moderate conformity. Track the distribution of delegation preferences
over time. If H4 holds, the initially unimodal distribution should
become bimodal (two camps) and eventually collapse to a single peak at
one extreme.

---

## 12. Empirical Grounding Strategy

This project follows an **"empirically informed theoretical modeling"**
approach. Real-world data does not calibrate the model to reproduce
specific empirical outcomes. Instead, it serves two bounded roles:

### 12.1 Parameter Range Bounding

Empirical data from four international datasets tells us what parameter
values produce plausible outcomes:

| Dataset | What It Informs | How It Enters the Model |
|---|---|---|
| **ILO ILOSTAT 2022-2024** (weekly working hours) | Plausible range for `tasks_per_step_mean` and the expected gap in `total_labor_hours` between Type A and Type B outcomes | High-autonomy regions average ~36.8h/week; high-delegation regions average ~49.8h/week. The 35% gap provides a validation target for the model's labour output difference. |
| **WVS Wave 7 (2017-2022)** (autonomy/obedience dimension) | Starting `delegation_preference_mean` for each preset | Autonomy scores of 0.65-0.72 in high-autonomy regions map to delegation preferences of ~0.25; scores of 0.30-0.40 in high-delegation regions map to ~0.72. |
| **OECD Better Life Index 2023** (work-life balance) | Validation targets for simulated stress and available time | High-autonomy regions score 8.0-9.0 on work-life balance; the model should show correspondingly low stress. High-delegation regions score 4.5-6.0; the model should show elevated stress. |
| **World Bank WDI 2022** (service sector employment) | `service_cost_factor` values | Service employment at 72% in high-delegation economies (downward price pressure → low cost factor 0.20) vs. 68% in high-autonomy economies (professional services → higher cost factor 0.65). |

### 12.2 Pattern-Oriented Validation

After simulation runs, the model's outputs are checked against
empirically observed qualitative patterns:

- Type A outcomes should qualitatively resemble high-autonomy region
  data: lower total hours, higher leisure, lower stress.
- Type B outcomes should qualitatively resemble high-delegation region
  data: higher total hours, lower leisure, higher stress.

This is *plausibility checking*, not quantitative calibration. The model
is not expected to reproduce exact numerical values from real-world data.
It is expected to reproduce the *direction* and *relative magnitude* of
differences between the two societal archetypes.

### 12.3 Why Not Full Calibration?

Full calibration to real-world data would require:
- Individual-level time-use diary data (not available at needed granularity)
- Longitudinal tracking of delegation behaviour changes (no existing dataset)
- Causal identification of delegation → stress pathways (observational data
  cannot establish this)

The model is a *theoretical exploration tool*, not a predictive engine.
Its value lies in making the mechanisms of the convenience paradox
explicit and explorable, not in forecasting the stress level of any
real population.

---

## 13. Methodological Boundaries and Limitations

Transparency about limitations is essential for responsible modeling.
This model makes several simplifying assumptions that bound the scope of
its conclusions:

### 13.1 Simplifications

1. **Homogeneous provider proficiency.** All service providers have
   proficiency 0.6, regardless of the task type or their personal skills.
   In reality, professional service providers are often *more* skilled
   than the requester at specialised tasks (plumbing, tax preparation).
   The model's uniform provider proficiency captures the friction of
   outsourcing *routine* tasks (cooking, errands) but understates the
   efficiency gains of delegating *specialised* tasks.

2. **No explicit labour market.** The service pool uses a simple greedy
   matching algorithm. There are no prices set by supply and demand, no
   specialisation, no transport costs, and no quality differentiation.
   This is intentional — the model focuses on norm-level dynamics rather
   than market microstructure — but it means the model cannot capture
   market equilibrium effects that might moderate the involution spiral.

3. **Static task types.** The menu of four task types does not change
   over the simulation. In reality, technological change continuously
   creates new task categories and renders old ones obsolete.

4. **No learning.** Agents' `skill_set` values are fixed at
   initialisation. In reality, repeated self-service improves skill
   (learning by doing), while persistent delegation may cause skill
   atrophy. Incorporating skill dynamics would likely *strengthen* the
   involution effect (delegation → skill loss → delegation becomes
   even more necessary).

5. **No geographic or demographic structure.** All agents are identical
   in their structural position (same initial time budget, same stress
   threshold). The only heterogeneity is in skill levels and starting
   delegation preference. Real societies have significant demographic
   variation (age, income, education) that interacts with delegation
   behaviour.

### 13.2 What the Model Can and Cannot Claim

**The model CAN**:
- Demonstrate that plausible micro-level decision rules *can* produce
  macro-level involution dynamics under identifiable parameter conditions.
- Identify which parameters most strongly influence the emergence of
  involution (sensitivity analysis).
- Show whether moderate systems are dynamically stable or unstable under
  conformity pressure.
- Generate testable predictions about the relationship between delegation
  rate and total systemic labour.

**The model CANNOT**:
- Prove that real-world involution *is* caused by these mechanisms.
- Predict the stress level, working hours, or well-being of any specific
  real population.
- Prescribe optimal policy interventions for real societies.
- Claim that one societal archetype is universally "better" than the other.

The purpose of this model is to make the convenience paradox *thinkable*
— to provide a formal framework for reasoning about dynamics that are
difficult to observe directly in the complexity of real social systems.

---

*Document generated for The Convenience Paradox project. For technical
implementation details, see the source files in `model/` and the
execution log in `docs/execution_log.md`.*
