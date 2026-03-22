"""model/model.py — ConvenienceParadoxModel (Mesa Model)

Architecture role:
    This module is the simulation engine. It is a headless Mesa Model that:
      - Creates and manages all Resident agents on a social network.
      - Coordinates the three-phase daily step (generate→match→update).
      - Maintains the central service pool (delegated tasks awaiting providers).
      - Collects time-series data via Mesa's DataCollector.
      - Exposes data-export helpers consumed by the Flask API (api/routes.py).

    No visualisation or web code lives here. The model runs identically
    whether called from the Flask server, a Jupyter notebook, batch_run
    scripts (analysis/batch_runs.py), or unit tests (tests/test_model.py).

Simulation mechanics overview:
    Each call to model.step() advances the simulation by one day:

      Phase 1 — Task generation & delegation:
        Each agent (in random order) generates their day's tasks and decides
        whether to handle each task personally or place it in the service pool.
        Self-served tasks are executed immediately (time deducted from agent).

      Phase 2 — Service matching:
        The model distributes tasks from the service pool to agents with
        spare time capacity. This is the involution mechanism: agents who
        delegated their tasks free up time, but then accept service tasks —
        potentially ending the day no better off than if they had self-served.

      Phase 3 — State update:
        Each agent updates their stress level (based on remaining time) and
        adapts their delegation preference toward their network neighbours'
        norm (social conformity). These feedback loops can drive the system
        toward convergence or bifurcation (H4).

    The DataCollector records model-level and agent-level metrics after each
    step, producing time-series DataFrames for analysis and visualisation.

Research context:
    Hypotheses being tested (see docs/plans/00_master_plan.md §6):
      H1: Higher delegation rates → higher total systemic labour hours.
      H2: A critical delegation threshold triggers an involution spiral.
      H3: Higher autonomy → lower perceived convenience, higher well-being.
      H4: Mixed-delegation systems drift toward extremes (instability).

See also:
    - model/agents.py    — Resident agent class
    - model/params.py    — TYPE_A_PRESET, TYPE_B_PRESET, PARAMETER_DEFINITIONS
    - analysis/batch_runs.py — Mesa batch_run for parameter sweeps
    - api/routes.py      — Flask endpoints that call model methods
"""

from __future__ import annotations

import logging
from typing import Any

import mesa
import mesa.space as mesa_space
import networkx as nx
import numpy as np
import pandas as pd

from model.agents import Resident, Task
from model.params import TASK_TYPES

logger = logging.getLogger(__name__)


class ConvenienceParadoxModel(mesa.Model):
    """Agent-Based Model of service delegation and social involution.

    This model investigates whether rational individual choices about
    delegating daily tasks can collectively produce a system-level "involution
    spiral" — a state where everyone is busier serving each other than they
    would be under simple self-service.

    The model is deliberately transparent and rule-based (white-box):
    every agent decision is governed by explicit, parameterised formulas.
    LLM components operate only at the input/output periphery (see api/llm_service.py).

    Social network:
        Agents are embedded in a Watts-Strogatz small-world network by default.
        This topology provides both local clustering (community norm pockets)
        and short average path lengths (global norm diffusion). Edges are the
        channels through which delegation norms spread via social conformity.

    Service pool:
        A list of delegated Task objects, cleared and repopulated each step.
        It acts as a simple labour market: requesters post tasks; the model
        assigns them to available providers. The pool size at end of matching
        indicates unmet service demand.

    Attributes:
        num_agents: Total number of Resident agents.
        delegation_preference_mean: Mean starting delegation preference [0, 1].
        delegation_preference_std: Std dev of initial preference distribution.
        service_cost_factor: Service price as a multiplier of task base_time.
        social_conformity_pressure: Peer influence strength [0, 1].
        tasks_per_step_mean: Mean daily tasks per agent.
        tasks_per_step_std: Std dev of daily task count.
        stress_threshold: Hours below which stress accumulates.
        stress_recovery_rate: Per-step stress reduction when time is surplus.
        adaptation_rate: Step size for preference updates.
        initial_available_time: Daily discretionary hours per agent.
        network_type: Network topology ("small_world" or "random").
        task_type_registry: Dict of task type definitions (from params.py).
        service_pool: Current step's delegated tasks awaiting providers.
        grid: NetworkGrid placing agents on the social network.
        current_step: Number of completed steps.
        datacollector: Mesa DataCollector for time-series metrics.
    """

    def __init__(
        self,
        num_agents: int = 100,
        delegation_preference_mean: float = 0.50,
        delegation_preference_std: float = 0.10,
        service_cost_factor: float = 0.40,
        social_conformity_pressure: float = 0.30,
        tasks_per_step_mean: float = 2.5,
        tasks_per_step_std: float = 0.75,
        stress_threshold: float = 2.5,
        stress_recovery_rate: float = 0.10,
        adaptation_rate: float = 0.03,
        initial_available_time: float = 8.0,
        network_type: str = "small_world",
        seed: int | None = 42,
    ) -> None:
        """Initialise the model with given parameters.

        Args:
            num_agents: Number of Resident agents.
            delegation_preference_mean: Mean starting delegation preference.
            delegation_preference_std: Std dev of starting preference.
            service_cost_factor: Service price multiplier [0, 1].
            social_conformity_pressure: Peer influence strength [0, 1].
            tasks_per_step_mean: Mean daily tasks per agent.
            tasks_per_step_std: Std dev of daily task count.
            stress_threshold: Hours of remaining time below which stress grows.
            stress_recovery_rate: Per-step stress recovery when surplus time.
            adaptation_rate: Learning rate for preference updates.
            initial_available_time: Discretionary hours available each day.
            network_type: Social network topology ("small_world" or "random").
            seed: Random seed for reproducibility. Passed to both the Mesa
                RNG (numpy) and the Python random module.

        Note:
            A Watts-Strogatz small-world network (k=4, p=0.1) is used as the
            default social topology. This choice reflects the empirical finding
            that real social networks exhibit both local clustering (tightly
            knit community groups with shared norms) and short global path
            lengths (ideas and norms can spread across the whole society
            quickly). An Erdős-Rényi random graph is available as an
            alternative for sensitivity analysis.
        """
        # Mesa 3.x uses `rng` kwarg (seed is deprecated but still works;
        # we pass it explicitly to avoid the FutureWarning).
        super().__init__(rng=seed)

        # --- Store parameters (needed by agents and DataCollector reporters) ---
        self.num_agents: int = num_agents
        self.delegation_preference_mean: float = delegation_preference_mean
        self.delegation_preference_std: float = delegation_preference_std
        self.service_cost_factor: float = service_cost_factor
        self.social_conformity_pressure: float = social_conformity_pressure
        self.tasks_per_step_mean: float = tasks_per_step_mean
        self.tasks_per_step_std: float = tasks_per_step_std
        self.stress_threshold: float = stress_threshold
        self.stress_recovery_rate: float = stress_recovery_rate
        self.adaptation_rate: float = adaptation_rate
        self.initial_available_time: float = initial_available_time
        self.network_type: str = network_type

        # The task type registry is shared with agents so we don't duplicate
        # the TASK_TYPES dict in every agent instance.
        self.task_type_registry: dict[str, dict] = TASK_TYPES

        # --- Simulation state ---
        # service_pool is cleared and repopulated on every step.
        # Agents append to it during generate_and_decide(); the model
        # reads and empties it during _run_service_matching().
        self.service_pool: list[Task] = []
        self.current_step: int = 0

        # Step-level accumulators: reset each step, used by DataCollector.
        # These provide efficient step-local stats without querying all agents.
        self._step_tasks_total: int = 0
        self._step_tasks_delegated: int = 0
        self._step_tasks_matched: int = 0  # delegated tasks successfully matched
        self._step_time_in_service: float = 0.0

        # --- Build social network ---
        # The network defines who each agent's "neighbours" are for the
        # social conformity mechanism. We build it with networkx then
        # wrap it in Mesa's NetworkGrid for spatial queries.
        rng_int = int(seed) if seed is not None else None
        if network_type == "small_world":
            # Watts-Strogatz: k=4 (each node starts with 4 neighbours),
            # p=0.1 (10% rewiring probability introduces long-range ties).
            G = nx.watts_strogatz_graph(n=num_agents, k=4, p=0.1, seed=rng_int)
        else:
            # Erdős-Rényi random graph: edge probability gives ~4 expected
            # neighbours per node (k/n = 4/100), matching the small-world baseline.
            p_edge = 4.0 / max(num_agents - 1, 1)
            G = nx.erdos_renyi_graph(n=num_agents, p=p_edge, seed=rng_int)

        self.grid: mesa_space.NetworkGrid = mesa_space.NetworkGrid(G)

        # --- Create agents and place on network ---
        task_type_names = list(TASK_TYPES.keys())
        for node_id in range(num_agents):
            # Sample delegation preference from a truncated normal distribution.
            # Using numpy's rng for reproducibility under Mesa's seeding.
            raw_pref = float(self.rng.normal(
                delegation_preference_mean, delegation_preference_std
            ))
            # Clamp to (0.02, 0.98) — no agent is a perfect delegator or
            # self-server; this preserves behavioural heterogeneity at extremes.
            pref = float(np.clip(raw_pref, 0.02, 0.98))

            # Skill set: each agent has a random proficiency for each task type.
            # Drawn uniformly from [0.3, 0.9] — all agents have at least basic
            # capability, none are perfect experts on every task type.
            skill_set = {
                t: float(self.rng.uniform(0.3, 0.9)) for t in task_type_names
            }

            agent = Resident(
                model=self,
                initial_available_time=initial_available_time,
                delegation_preference=pref,
                skill_set=skill_set,
                stress_threshold=stress_threshold,
                conformity_sensitivity=social_conformity_pressure,
                adaptation_rate=adaptation_rate,
            )
            self.grid.place_agent(agent, node_id)

        # --- DataCollector configuration ---
        # Model-level reporters produce one value per step (time-series).
        # Agent-level reporters produce one value per agent per step.
        # All values are consumed by the Flask API → Plotly.js dashboard.
        self.datacollector = mesa.DataCollector(
            model_reporters={
                # Primary well-being indicator (H3 test variable).
                # Rising avg_stress signals time pressure in the system.
                "avg_stress":           self._compute_avg_stress,
                # Primary delegation-rate tracker.
                # Tracks whether society is converging to delegation norm (H4).
                "avg_delegation_rate":  self._compute_avg_delegation_rate,
                # Primary H1 test variable: total collective labour expended.
                # We expect this to RISE with delegation in the involution regime.
                "total_labor_hours":    self._compute_total_labor_hours,
                # System efficiency (H1/H2 proxy): tasks done per labour hour.
                # Involution manifests as FALLING efficiency.
                "social_efficiency":    self._compute_social_efficiency,
                # Income inequality across agents.
                "gini_income":          self._compute_gini_income,
                # Time-wealth inequality (leisure distribution).
                "gini_available_time":  self._compute_gini_available_time,
                # Realised delegation fraction (actual behaviour, not preference).
                "tasks_delegated_frac": self._compute_tasks_delegated_frac,
                # Service pool residual: unmet demand indicator.
                "unmatched_tasks":      self._compute_unmatched_tasks,
                # Mean cumulative income (tracks service economy growth).
                "avg_income":           self._compute_avg_income,
            },
            agent_reporters={
                # Individual-level data for distribution plots and agent traces.
                "available_time":        "available_time",
                "stress_level":          "stress_level",
                "delegation_preference": "delegation_preference",
                "income":                "income",
                "tasks_completed_self":  "tasks_completed_self",
                "tasks_delegated":       "tasks_delegated",
                "time_spent_providing":  "time_spent_providing",
            },
        )

        # Collect step-0 baseline (before any simulation runs) so the
        # dashboard shows the initial state as soon as the model is created.
        self.datacollector.collect(self)

        logger.info(
            "ConvenienceParadoxModel initialised: %d agents, "
            "delegation_mean=%.2f, service_cost=%.2f, conformity=%.2f, seed=%s",
            num_agents, delegation_preference_mean,
            service_cost_factor, social_conformity_pressure, seed,
        )

    # -----------------------------------------------------------------------
    # Main simulation step
    # -----------------------------------------------------------------------

    def step(self) -> None:
        """Advance the simulation by one day (one step).

        Orchestrates the three-phase daily cycle:
          Phase 1: Agents generate tasks and make delegation decisions.
          Phase 2: Model matches delegated tasks to service providers.
          Phase 3: Agents update stress and adapt delegation preferences.

        Following CLAUDE.md §8.2, this method is kept thin. Substantive
        logic lives in agent methods; the model's role is coordination.
        """
        # --- Reset step-level state ---
        # The service_pool accumulates during Phase 1 and is consumed in Phase 2.
        self.service_pool = []
        self._step_tasks_total = 0
        self._step_tasks_delegated = 0
        self._step_tasks_matched = 0
        self._step_time_in_service = 0.0

        # --- Phase 1: Task generation and delegation decisions ---
        # shuffle_do ensures random agent ordering each step —
        # prevents any systematic first-mover advantage.
        self.agents.shuffle_do("generate_and_decide")

        # Tally totals from all agents' task queues for the DataCollector.
        for agent in self.agents:
            self._step_tasks_total += len(agent.task_queue)
            self._step_tasks_delegated += sum(1 for t in agent.task_queue if t.delegated)

        # --- Phase 2: Service pool matching ---
        # The model distributes delegated tasks to available providers.
        # This is the involution mechanism: providers spend time serving others,
        # reducing collective leisure even as individual agents sought convenience.
        self._run_service_matching()

        # --- Phase 3: State update ---
        # Each agent updates stress (time-pressure check) and preference
        # (social conformity drift toward network neighbours).
        self.agents.shuffle_do("update_state")

        # --- Data collection ---
        self.datacollector.collect(self)
        self.current_step += 1

    # -----------------------------------------------------------------------
    # Service matching (Phase 2 coordination)
    # -----------------------------------------------------------------------

    def _run_service_matching(self) -> None:
        """Distribute delegated tasks from the service pool to willing providers.

        This method acts as a simple labour market: tasks in the pool are
        assigned to agents who have available time. The matching algorithm
        is deliberately simple — it prioritises transparent mechanics over
        market realism, consistent with this model's theoretical purpose.

        Algorithm:
          1. Shuffle the service pool (random order removes position bias).
          2. For each task, find candidate providers: agents with enough
             remaining time who are not the original requester.
          3. Assign the task to the candidate with the most spare time
             (greedy: maximises the chance that subsequent tasks also get matched).
          4. Tasks with no available provider remain unmatched (service shortfall).

        Side effects:
            - Updates provider agents' available_time and income.
            - Increments _step_tasks_matched and _step_time_in_service.

        Note:
            This greedy matching over-simplifies real markets (no price signals,
            no specialisation matching, no transport costs). This is intentional:
            the model explores norm-level dynamics, not market microstructure.
            A more sophisticated market model would obscure the involution mechanism
            with confounding factors.
        """
        if not self.service_pool:
            return

        # Randomise pool order to ensure fairness across task types and positions.
        self.random.shuffle(self.service_pool)

        # Build a mutable list of all agents for provider selection.
        # Any agent can be a provider — the model does not pre-assign roles.
        # This captures the real dynamic where people take on service work
        # opportunistically based on current time availability and income need.
        all_agents = list(self.agents)

        for task in self.service_pool:
            # Minimum time needed to accept this task: 50% of base_time.
            # Providers must have at least this much spare time to take the task.
            min_time_needed = task.base_time * 0.5

            # Candidate providers: have spare time AND are not the requester
            # (agents don't serve themselves through the pool — that would be
            # economically circular and unrealistic).
            candidates = [
                a for a in all_agents
                if a.unique_id != task.requester_id
                and a.available_time >= min_time_needed
            ]

            if not candidates:
                # No provider available this step → unmatched task (service shortfall).
                # This signals system overload: more delegation demand than capacity.
                # In real markets this would drive up prices; in this model it
                # creates stress for requesters whose tasks go unserved.
                continue

            # Greedy selection: provider with the most remaining available_time.
            # This heuristic is efficient (more tasks get matched) and simple
            # to reason about for model validation.
            provider = max(candidates, key=lambda a: a.available_time)
            time_spent = provider.provide_service(task)

            self._step_tasks_matched += 1
            self._step_time_in_service += time_spent

    # -----------------------------------------------------------------------
    # DataCollector reporter functions
    # -----------------------------------------------------------------------
    # Each function computes one model-level metric per step.
    # They are called by Mesa's DataCollector automatically after each step.

    def _compute_avg_stress(self) -> float:
        """Mean stress level across all agents.

        The primary well-being metric. Rising avg_stress signals that agents
        collectively feel time-pressured — the hallmark of involution dynamics.
        Used to test H3: autonomy-oriented societies should show lower stress.
        """
        values = [a.stress_level for a in self.agents]
        return float(np.mean(values)) if values else 0.0

    def _compute_avg_delegation_rate(self) -> float:
        """Mean delegation preference across all agents.

        Tracks whether the society is converging toward delegation or autonomy.
        A rising trend suggests norm diffusion toward Type B behaviour (H4).
        """
        values = [a.delegation_preference for a in self.agents]
        return float(np.mean(values)) if values else 0.0

    def _compute_total_labor_hours(self) -> float:
        """Total hours spent on tasks by all agents this step.

        Computed as (initial_available_time − remaining available_time) summed
        across all agents. This is the primary H1 test variable:
        we hypothesise that higher delegation rates produce MORE total labour
        hours (not fewer), because service provision adds overhead to the system.

        Note:
            Includes both time spent self-serving own tasks AND time spent
            providing services to others. This captures the full collective
            cost of the delegation economy in one metric.
        """
        total = sum(
            a.initial_available_time - a.available_time for a in self.agents
        )
        return float(total)

    def _compute_social_efficiency(self) -> float:
        """Tasks completed per collective labour-hour this step.

        social_efficiency = tasks_served / total_labour_hours.

        Higher is better: the society produces more useful output per unit of
        collective time. Involution manifests as *falling* efficiency: more
        time is spent but the useful task-completion rate does not keep pace.

        How tasks_served is computed:
          - Self-served tasks: (total − delegated)
          - Successfully matched delegated tasks: _step_tasks_matched
          - Unmatched delegated tasks: not served (subtracted)

        Returns:
            Efficiency ratio, or 0.0 if no labour was expended.
        """
        total_labor = self._compute_total_labor_hours()
        if total_labor < 0.001:
            return 0.0
        tasks_self_served = self._step_tasks_total - self._step_tasks_delegated
        tasks_done = tasks_self_served + self._step_tasks_matched
        return float(max(0.0, tasks_done) / total_labor)

    def _compute_gini_income(self) -> float:
        """Gini coefficient of cumulative income across agents.

        Gini = 0: perfect equality; Gini = 1: maximum inequality.
        In Type B societies, income should concentrate among dedicated
        service providers over time, increasing the Gini coefficient.
        """
        return float(_gini([a.income for a in self.agents]))

    def _compute_gini_available_time(self) -> float:
        """Gini coefficient of remaining available_time across agents.

        Measures inequality in daily leisure at end of day.
        High Gini here: some agents have ample free time while others are
        completely overloaded — a structural imbalance characteristic of
        involution dynamics.
        """
        return float(_gini([a.available_time for a in self.agents]))

    def _compute_tasks_delegated_frac(self) -> float:
        """Fraction of all tasks this step that were delegated.

        This is the *realised* delegation rate — actual behaviour rather than
        the preference-based mean. The gap between preference and behaviour
        can reveal interesting dynamics (e.g., high preference but low
        realised delegation when service cost is prohibitive).
        """
        if self._step_tasks_total == 0:
            return 0.0
        return float(self._step_tasks_delegated / self._step_tasks_total)

    def _compute_unmatched_tasks(self) -> int:
        """Number of delegated tasks that found no provider this step.

        Unmatched tasks indicate service-sector capacity shortfall:
        demand for delegation exceeds the time-availability of potential
        providers. This is a leading indicator of involution stress —
        when tasks go unserved, requesters experience compounding stress.
        """
        return self._step_tasks_delegated - self._step_tasks_matched

    def _compute_avg_income(self) -> float:
        """Mean cumulative net income across all agents.

        Tracks the flow of economic value through the service economy.
        In high-delegation societies, income variance increases as some agents
        specialise in provision and earn positive net income while heavy
        delegators accumulate negative net income (fees outpace earnings).
        """
        values = [a.income for a in self.agents]
        return float(np.mean(values)) if values else 0.0

    # -----------------------------------------------------------------------
    # Data export helpers (used by Flask API and analysis scripts)
    # -----------------------------------------------------------------------

    def get_model_dataframe(self) -> pd.DataFrame:
        """Return model-level time-series data as a Pandas DataFrame.

        Returns:
            DataFrame indexed by step number (0 = initial state).
            Columns: avg_stress, avg_delegation_rate, total_labor_hours,
                     social_efficiency, gini_income, gini_available_time,
                     tasks_delegated_frac, unmatched_tasks, avg_income.
        """
        return self.datacollector.get_model_vars_dataframe()

    def get_agent_dataframe(self) -> pd.DataFrame:
        """Return agent-level time-series data as a Pandas DataFrame.

        Returns:
            DataFrame with MultiIndex (Step, AgentID).
            Columns: available_time, stress_level, delegation_preference,
                     income, tasks_completed_self, tasks_delegated,
                     time_spent_providing.
        """
        return self.datacollector.get_agent_vars_dataframe()

    def get_agent_states(self) -> list[dict]:
        """Return current state of all agents as a list of plain dicts.

        Used by the Flask API to push live agent state to the dashboard
        for distribution plots and per-agent inspection.

        Returns:
            List of agent state dicts (one per agent), serialisation-safe.
        """
        return [a.get_state_dict() for a in self.agents]

    def get_params(self) -> dict[str, Any]:
        """Return the model's current parameter values as a dict.

        Used by the Flask API, analysis scripts, and report generators to
        log the exact configuration of each simulation run alongside results.

        Returns:
            Dict of parameter name → value, including current_step.
        """
        return {
            "num_agents": self.num_agents,
            "delegation_preference_mean": self.delegation_preference_mean,
            "delegation_preference_std": self.delegation_preference_std,
            "service_cost_factor": self.service_cost_factor,
            "social_conformity_pressure": self.social_conformity_pressure,
            "tasks_per_step_mean": self.tasks_per_step_mean,
            "tasks_per_step_std": self.tasks_per_step_std,
            "stress_threshold": self.stress_threshold,
            "stress_recovery_rate": self.stress_recovery_rate,
            "adaptation_rate": self.adaptation_rate,
            "initial_available_time": self.initial_available_time,
            "network_type": self.network_type,
            "current_step": self.current_step,
        }


# ---------------------------------------------------------------------------
# Utility functions (module-level, used by DataCollector reporters)
# ---------------------------------------------------------------------------

def _gini(values: list[float]) -> float:
    """Compute the Gini coefficient for a list of non-negative values.

    The Gini coefficient measures distributional inequality:
      - 0.0 = perfect equality (all values identical).
      - 1.0 = maximum inequality (one agent has everything).

    Formula used: G = Σᵢ Σⱼ |xᵢ - xⱼ| / (2 · n · Σxᵢ)
    Equivalently computed in O(n log n) via sorted cumulative sums.

    Args:
        values: List of non-negative numerical values (e.g., incomes, times).

    Returns:
        Gini coefficient in [0.0, 1.0].

    Note:
        Returns 0.0 for empty lists or zero-sum distributions.
        Zero-sum is common at step 0 when cumulative income is all zero.
        Values are shifted to non-negative before computation when any
        value is negative (e.g., agents who spent more on fees than they earned).
    """
    if not values:
        return 0.0

    # Shift values to non-negative domain if any are negative.
    # This occurs for income when delegation fees exceed service earnings.
    min_val = min(values)
    if min_val < 0:
        values = [v - min_val for v in values]

    total = sum(values)
    if total < 1e-9:
        return 0.0

    n = len(values)
    sorted_vals = sorted(values)
    cumsum = 0.0
    for i, v in enumerate(sorted_vals):
        # Standard sorted-array Gini computation: O(n log n)
        cumsum += v * (2 * (i + 1) - n - 1)
    return cumsum / (n * total)
