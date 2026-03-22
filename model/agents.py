"""model/agents.py — Resident Agent for The Convenience Paradox

Architecture role:
    This module defines `Resident`, the fundamental actor in the simulation.
    Every agent is a resident of an abstract society who must manage a set of
    daily tasks, deciding each day whether to handle tasks personally
    (self-service) or hire someone from the community (delegation).

    The `Task` dataclass is also defined here because tasks are closely tied
    to agent behaviour — they describe the "what" of the agent's daily life.

Conceptual design (social science rationale):
    The central tension modelled is the "convenience paradox":
    - Delegating feels convenient for the individual (saves personal time).
    - But *someone* in the system must still perform that task.
    - If many agents delegate, demand for service providers rises. Providers
      spend their time fulfilling others' tasks — often at the cost of their
      own leisure. Over time this can produce an "involution spiral": rising
      demand pulls more agents into service provision, reducing collective
      leisure even though everyone sought convenience.

    The agent's decision logic is fully explicit and rule-based. No LLM
    logic lives here. This preserves the "white-box" principle described in
    CLAUDE.md §6.1 and the interpretability philosophy discussed in
    Vanhée et al. (2507.05723).

Used by:
    - model/model.py  — creates Resident instances and calls their methods
    - tests/test_agents.py — tests decision rules in isolation

See also:
    - model/params.py  — TASK_TYPES registry and society presets
    - docs/plans/02_phase2_simulation.md — Phase 2 specification
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import mesa

if TYPE_CHECKING:
    # Avoid circular import: only needed for type hints, not at runtime.
    from model.model import ConvenienceParadoxModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Task data structure
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A single daily task that an agent must resolve each simulation step.

    Tasks are generated fresh each step (= each day) and represent the
    routine demands of daily life: cooking, errands, paperwork, repairs.
    Each task has a time cost that depends on the performing agent's skill
    level — expert agents handle tasks faster, making self-service cheaper.

    Attributes:
        task_type: Category label (key into TASK_TYPES in params.py).
        base_time: Hours the task takes for an agent of average skill (1.0).
        skill_requirement: Proficiency level below which self-service is
            noticeably slow. Agents below this threshold lose more time.
        delegated: Whether this task was placed in the community service pool.
        requester_id: unique_id of the agent who generated this task.
            Prevents an agent from serving as their own provider.
    """

    task_type: str
    base_time: float
    skill_requirement: float
    delegated: bool = False
    requester_id: int = -1

    def time_cost_for(self, proficiency: float) -> float:
        """Calculate actual hours needed to complete this task at given skill.

        The formula `base_time / effective_proficiency` means:
          - Proficiency 1.0 (expert) → exactly base_time hours.
          - Proficiency 0.5 (novice) → 2× base_time hours.
          - Proficiency 0.1 (minimum) → 10× base_time (capped to prevent extreme values).

        This creates a natural incentive for skilled agents to self-serve:
        they are efficient, so delegation offers little time saving. Unskilled
        agents gain more from delegating because self-service is very slow.

        Args:
            proficiency: Agent's skill level for this task type [0.0, 1.0].

        Returns:
            Hours required to complete the task (always positive).

        Note:
            Proficiency is clamped to [0.1, 1.0]. The lower bound prevents
            near-zero proficiency from producing unrealistically long durations
            that would distort model-level time aggregates.
        """
        effective = max(0.1, min(1.0, proficiency))
        return self.base_time / effective


# ---------------------------------------------------------------------------
# Resident Agent
# ---------------------------------------------------------------------------

class Resident(mesa.Agent):
    """A resident agent navigating service delegation in an abstract society.

    Each Resident represents one individual in a network-embedded community.
    Their core behavioural loop each simulation step (= one day) is:

      1. Reset the daily time budget (available_time ← initial_available_time).
      2. Receive a random set of daily tasks (drawn from the model's task menu).
      3. For each task: decide to self-serve (execute immediately, spend time)
         or delegate (add to the model's service pool, pay a fee).
      4. After all agents decide (coordinated by the model), potentially accept
         delegated tasks from the pool as a service provider — earning income
         but spending time.
      5. At end of day: update stress based on remaining time, then nudge
         delegation preference toward the local neighbourhood norm (conformity).

    Why agents can be both delegators AND providers:
        An agent may delegate their own tasks to save time, then accept others'
        tasks from the pool to earn income — ending up working the same or more
        hours. This is the "involution trap": rational individual choices
        (save time by delegating; earn money by providing) collectively produce
        a system where nobody gains leisure. This is the core mechanism being
        studied in H1 and H2.

    Attributes:
        available_time: Remaining discretionary hours today. Decremented as
            tasks are executed. Resets to initial_available_time each step.
        initial_available_time: Daily time budget (hours) at start of each day.
        skill_set: Dict mapping task_type → proficiency [0.0, 1.0]. Determines
            the time cost of self-serving each task type.
        delegation_preference: Probability [0.0, 1.0] of choosing to delegate
            when given a genuine choice. Evolves over time via social influence.
        stress_level: Current stress level [0.0, 1.0]. Rises when the agent
            ends the day with very little remaining time; falls when they have
            surplus. Feeds back into delegation decisions.
        stress_threshold: Hours of remaining time below which stress accrues.
        conformity_sensitivity: Weight of peer influence on preference updates.
        adaptation_rate: Step size for preference nudges each day.
        task_queue: This day's tasks (populated in generate_and_decide).
        income: Cumulative net income (earnings from providing − fees paid).
        tasks_completed_self: Cumulative count of self-served tasks.
        tasks_delegated: Cumulative count of delegated tasks.
        time_spent_providing: Cumulative hours spent providing services to others.
            Tracked separately to analyse the involution dynamic.
    """

    def __init__(
        self,
        model: "ConvenienceParadoxModel",
        initial_available_time: float,
        delegation_preference: float,
        skill_set: dict[str, float],
        stress_threshold: float,
        conformity_sensitivity: float,
        adaptation_rate: float,
    ) -> None:
        """Initialise a Resident agent with given traits.

        Args:
            model: Parent ConvenienceParadoxModel instance.
            initial_available_time: Discretionary hours available each day.
            delegation_preference: Starting delegation probability [0, 1].
            skill_set: Dict of {task_type: proficiency [0, 1]}.
            stress_threshold: Hours below which stress accumulates each step.
            conformity_sensitivity: Strength of peer influence on preference.
            adaptation_rate: Learning rate for preference updates per step.
        """
        super().__init__(model)

        # --- Time budget ---
        self.initial_available_time: float = initial_available_time
        self.available_time: float = initial_available_time

        # --- Behavioural traits ---
        # delegation_preference is the primary variable of interest.
        # It starts at the value sampled from the model's normal distribution
        # (reflecting society-wide norms) and evolves via social influence.
        self.delegation_preference: float = max(0.0, min(1.0, delegation_preference))
        self.skill_set: dict[str, float] = skill_set
        self.conformity_sensitivity: float = conformity_sensitivity
        self.adaptation_rate: float = adaptation_rate

        # --- Stress ---
        self.stress_level: float = 0.0
        self.stress_threshold: float = stress_threshold

        # --- Per-step state (reset at the start of each day) ---
        self.task_queue: list[Task] = []

        # --- Cumulative lifetime tracking (never reset after init) ---
        # income can go negative if an agent delegates more than they earn.
        self.income: float = 0.0
        self.tasks_completed_self: int = 0
        self.tasks_delegated: int = 0
        # time_spent_providing is the involution indicator at agent level:
        # the more time an agent spends serving others, the less leisure they have,
        # even if they also delegated all their own tasks.
        self.time_spent_providing: float = 0.0

    # -----------------------------------------------------------------------
    # Phase 1 of the daily step: task generation and delegation decision
    # -----------------------------------------------------------------------

    def generate_and_decide(self) -> None:
        """Generate today's tasks and decide how to handle each one.

        Called by the model at the start of each step via
        `self.agents.shuffle_do("generate_and_decide")`. Shuffling ensures no
        agent has a systematic first-mover advantage in task generation.

        This method:
          1. Resets the daily available_time budget.
          2. Samples a random number of tasks for the day.
          3. For each task: decides to self-serve (execute now) or delegate
             (place in model.service_pool for later matching).

        Self-served tasks are executed immediately within this method because
        the agent handles them directly and independently. Delegated tasks are
        handled in Phase 2 (model._run_service_matching).
        """
        # --- Reset daily budget ---
        self.available_time = self.initial_available_time
        self.task_queue = []

        # --- Generate today's tasks ---
        # Task count is drawn from a Gaussian distribution clamped to [1, ∞).
        # This models the stochastic nature of daily demands (some days busier).
        # Using Gaussian (not Poisson) to allow the model user to set std dev
        # explicitly via the tasks_per_step_std parameter.
        num_tasks = max(1, round(self.random.gauss(
            self.model.tasks_per_step_mean,
            self.model.tasks_per_step_std,
        )))

        task_type_names = list(self.model.task_type_registry.keys())
        for _ in range(num_tasks):
            t_type = self.random.choice(task_type_names)
            spec = self.model.task_type_registry[t_type]
            task = Task(
                task_type=t_type,
                base_time=spec["base_time"],
                skill_requirement=spec["skill_requirement"],
                requester_id=self.unique_id,
            )
            self.task_queue.append(task)

        # --- Delegation decision for each task ---
        for task in self.task_queue:
            if self._should_delegate(task):
                task.delegated = True
                self.model.service_pool.append(task)
                self.tasks_delegated += 1
                # The agent pays a service fee upon requesting delegation.
                # Fee = task's base_time × model's service_cost_factor.
                # This is deducted from income (net income can go negative).
                fee = task.base_time * self.model.service_cost_factor
                self.income -= fee
            else:
                self._execute_task_self(task)

    def _should_delegate(self, task: Task) -> bool:
        """Decide probabilistically whether to delegate a task.

        The delegation decision integrates four factors:
          1. Base preference (cultural disposition): the primary driver,
             set by the society preset and adapted over time.
          2. Stress boost: stressed agents are more likely to delegate to
             relieve time pressure. This is the main feedback loop driving
             involution — stress → delegate more → more demand → providers
             busier → more stress.
          3. Skill discount: agents skilled at this task type gain less
             from delegating (they are already fast at it), so skilled agents
             are slightly less likely to delegate this specific task.
          4. Cost penalty: expensive services reduce delegation incentive —
             rational agents weigh convenience against cost.

        Additionally, if the agent cannot possibly fit the task into their
        remaining day (forced delegation), they delegate regardless of preference.

        Args:
            task: The task being evaluated.

        Returns:
            True if the agent will delegate this task; False to self-serve.

        Note:
            All coefficients (0.3, 0.2, 0.25) are calibrated to keep the
            effective delegation probability within (0, 1) for the full range
            of input values. They are exposed indirectly via the presets but
            are intentionally not individually tunable sliders — adjusting
            delegation_preference_mean and social_conformity_pressure is the
            intended way to explore the model's parameter space.
        """
        proficiency = self.skill_set.get(task.task_type, 0.4)
        task_time = task.time_cost_for(proficiency)

        # --- Forced delegation: agent has almost no time left ---
        # If the agent can't comfortably fit this task, they must delegate.
        # Threshold is 50% of the task's time cost to allow some flexibility.
        if self.available_time < task_time * 0.5:
            return True

        # --- Compute effective delegation probability ---
        # Start from the agent's base preference (society-level disposition).
        p = self.delegation_preference

        # Stressed agents delegate more to relieve time pressure.
        # The "convenience trap" feedback: stress → delegate → cost → less income
        # → need to provide services to earn back → more time spent → more stress.
        stress_boost = self.stress_level * 0.30

        # High skill = fast self-service = less incentive to pay for delegation.
        # This keeps skilled agents as self-servers even in high-delegation societies.
        skill_discount = proficiency * 0.20

        # High service cost = economic disincentive to delegate.
        # service_cost_factor ranges 0→1; at 0.25 weight, high cost (1.0)
        # reduces delegation probability by 0.25.
        cost_penalty = self.model.service_cost_factor * 0.25

        effective_p = max(0.0, min(1.0, p + stress_boost - skill_discount - cost_penalty))
        return self.random.random() < effective_p

    def _execute_task_self(self, task: Task) -> None:
        """Execute a task personally, consuming time from the daily budget.

        Args:
            task: The task to perform.

        Note:
            Time cost is moderated by the agent's skill in this task type.
            The higher the proficiency, the less time spent — creating a
            direct incentive for skilled agents to self-serve.
        """
        proficiency = self.skill_set.get(task.task_type, 0.4)
        time_cost = task.time_cost_for(proficiency)
        # Floor at 0: can't have negative available time.
        self.available_time = max(0.0, self.available_time - time_cost)
        self.tasks_completed_self += 1

    # -----------------------------------------------------------------------
    # Phase 2 of the daily step: service provision (called from model)
    # -----------------------------------------------------------------------

    def provide_service(self, task: Task) -> float:
        """Accept and execute a task from the community service pool.

        This is the "other side" of the delegation economy. When this agent
        acts as a provider, they:
          - Spend their own available_time executing the task.
          - Earn a service fee (credited to income).

        The involution dynamic is visible here: an agent who delegated their
        own tasks to free up time may then fill that freed time by providing
        services for others — ending up with no net leisure gain. In the
        aggregate, this means the society as a whole may work MORE total hours
        in a high-delegation equilibrium (H1).

        Args:
            task: The task from the service pool to execute.

        Returns:
            Hours spent providing this service (for model-level accounting).

        Note:
            Provider proficiency is fixed at 0.6 (competent generalist).
            This is intentionally below the task requester's own skill level
            on domestic tasks (agents are typically ~0.5–0.9 in their own
            tasks). This slight efficiency penalty represents the real-world
            friction of outsourcing: providers are capable but not as
            personalised/efficient as the person doing their own tasks.
        """
        # Generalised service competency — providers are good but not
        # specialised in the requester's specific household or context.
        provider_proficiency = 0.60
        time_cost = task.time_cost_for(provider_proficiency)

        self.available_time = max(0.0, self.available_time - time_cost)
        self.time_spent_providing += time_cost

        # Income earned equals the fee the requester paid.
        fee = task.base_time * self.model.service_cost_factor
        self.income += fee

        return time_cost

    # -----------------------------------------------------------------------
    # Phase 3 of the daily step: state update (stress and preference)
    # -----------------------------------------------------------------------

    def update_state(self) -> None:
        """Update stress level and delegation preference at end of the day.

        Called by the model after service matching via
        `self.agents.shuffle_do("update_state")`.

        Two feedback mechanisms are implemented here:

        (A) Stress feedback:
            If remaining available_time < stress_threshold → stress rises.
            If remaining available_time > stress_threshold → stress recovers.
            Stress feeds back into _should_delegate() in the next step,
            creating a dynamic where time-pressured agents delegate more,
            which can increase provider demand and perpetuate the pressure.

        (B) Social conformity (preference drift):
            The agent observes the mean delegation_preference of their network
            neighbours. Their own preference nudges toward that local mean,
            weighted by the model's social_conformity_pressure and amplified
            by current stress (stressed agents are more susceptible to peer
            influence — a behavioural science observation).

            This mechanism enables norm diffusion: in a high-conformity society
            (Type B), even agents who start with low delegation preference will
            gradually shift toward the community norm. This is the pathway
            through which H4 (mixed-system instability) can emerge.

        Note:
            Preferences are bounded [0, 1]. The adaptation_rate controls the
            step size of each update, preventing abrupt behavioural flips that
            would be unrealistic in a social context.
        """
        # --- (A) Stress update ---
        if self.available_time < self.stress_threshold:
            # Agent ended the day with insufficient free time.
            # Stress increase is proportional to the time deficit:
            # a severe deficit (available_time ≈ 0) causes rapid stress rise;
            # a mild deficit causes gradual accumulation.
            deficit_ratio = (self.stress_threshold - self.available_time) / self.stress_threshold
            self.stress_level = min(1.0, self.stress_level + 0.10 * deficit_ratio)
        else:
            # Agent had surplus time; stress recovers at a fixed rate.
            self.stress_level = max(0.0, self.stress_level - self.model.stress_recovery_rate)

        # --- (B) Social conformity: preference drift ---
        # Query network neighbours via the model's NetworkGrid.
        # self.pos is the node_id assigned when the agent was placed on the grid.
        neighbours: list[Resident] = self.model.grid.get_neighbors(
            self.pos, include_center=False
        )

        if not neighbours:
            # Isolated node (rare in small-world graphs but theoretically possible).
            # No peer influence without neighbours; no preference update.
            return

        # Compute the local norm: mean delegation preference of neighbours.
        neighbour_mean = sum(n.delegation_preference for n in neighbours) / len(neighbours)

        # Stressed agents look to peers for behavioural guidance (conformity amplified).
        # This is consistent with behavioural literature: uncertainty and stress
        # increase susceptibility to social influence.
        conformity_weight = self.model.social_conformity_pressure * (1.0 + self.stress_level * 0.5)

        # Nudge preference toward the local norm by adaptation_rate × conformity_weight.
        delta = conformity_weight * (neighbour_mean - self.delegation_preference)
        self.delegation_preference = max(0.0, min(1.0,
            self.delegation_preference + self.adaptation_rate * delta
        ))

    # -----------------------------------------------------------------------
    # Utility / reporting
    # -----------------------------------------------------------------------

    def get_state_dict(self) -> dict:
        """Return a snapshot of the agent's current state as a plain dict.

        Used by the Flask API (/api/simulation/agents) to serialise live
        agent state for dashboard distribution plots and agent inspection.

        Returns:
            Dict with all observable agent attributes (serialisation-safe types).
        """
        return {
            "id": self.unique_id,
            "available_time": round(self.available_time, 3),
            "delegation_preference": round(self.delegation_preference, 3),
            "stress_level": round(self.stress_level, 3),
            "income": round(self.income, 3),
            "tasks_completed_self": self.tasks_completed_self,
            "tasks_delegated": self.tasks_delegated,
            "time_spent_providing": round(self.time_spent_providing, 3),
            "pos": self.pos,
        }
