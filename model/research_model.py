"""model/research_model.py — Research-only simulation engine.

Architecture role:
    This module defines `ConvenienceParadoxResearchModel`, a research-only
    extension of the stable `ConvenienceParadoxModel`. It exists to support
    mechanism audits and focused reruns without changing the dashboard-facing
    model contract used by the web application.

Why this file exists:
    The dashboard currently depends on the stable behaviour and public
    parameter contract of `ConvenienceParadoxModel`. The research questions
    raised after the full campaign require additional white-box mechanisms:

      - delegated-task backlog instead of silent disappearance
      - requester-side coordination costs
      - explicit provider-side service friction
      - stricter provider-capacity matching
      - extra labour-accounting metrics for diagnosis

    Those additions are useful for research, but they would change the
    semantics of the live dashboard if applied directly to the stable model.
    This module therefore implements a parallel engine with an interface that
    remains close to the stable model while keeping the web app untouched.

Used by:
    - analysis/narrative_campaign.py — research_v2 engine runs
    - tests/test_research_model.py   — research-engine verification

Design constraints:
    - White-box only: all behaviour remains explicit and rule-based.
    - Dashboard compatibility is protected by isolation, not by forcing the
      stable and research engines to be identical.
    - Public helper methods remain available:
        `step()`, `get_model_dataframe()`, `get_agent_dataframe()`,
        `get_agent_states()`, `get_params()`
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
from model.model import ConvenienceParadoxModel, _gini
from model.params import TASK_TYPES

logger = logging.getLogger(__name__)


class ResearchResident(Resident):
    """Resident variant with backlog and coordination-cost accounting.

    The stable `Resident` assumes that delegated tasks either get matched in
    the current step or disappear from the requester's lived experience. For
    the research engine that is too forgiving: unserved delegated work should
    remain in the system and show up as next-step backlog.
    """

    def __init__(
        self,
        model: "ConvenienceParadoxResearchModel",
        initial_available_time: float,
        delegation_preference: float,
        skill_set: dict[str, float],
        stress_threshold: float,
        conformity_sensitivity: float,
        adaptation_rate: float,
    ) -> None:
        super().__init__(
            model=model,
            initial_available_time=initial_available_time,
            delegation_preference=delegation_preference,
            skill_set=skill_set,
            stress_threshold=stress_threshold,
            conformity_sensitivity=conformity_sensitivity,
            adaptation_rate=adaptation_rate,
        )
        self.carryover_tasks: list[Task] = []
        self.coordination_time_spent: float = 0.0

    def _self_time_for_task(self, task: Task) -> float:
        """Return the time this requester would spend if self-serving."""
        proficiency = self.skill_set.get(task.task_type, 0.4)
        return task.time_cost_for(proficiency)

    def generate_and_decide(self) -> None:
        """Generate new tasks, prepend backlog, then decide self-serve vs delegate.

        Unlike the stable engine, backlog tasks survive across steps until they
        are either self-served or successfully matched to a provider.
        """
        self.available_time = self.initial_available_time

        carryover = list(self.carryover_tasks)
        self.carryover_tasks = []
        for task in carryover:
            task.delegated = False

        self.task_queue = carryover

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

        for task in self.task_queue:
            if self._should_delegate(task):
                task.delegated = True
                self.model.service_pool.append(task)
                self.tasks_delegated += 1

                fee = task.base_time * self.model.service_cost_factor
                self.income -= fee

                coordination_time = task.base_time * self.model.requester_coordination_cost_factor
                realised_coordination = min(self.available_time, coordination_time)
                self.available_time = max(0.0, self.available_time - coordination_time)
                self.coordination_time_spent += realised_coordination
                self.model._step_coordination_hours += realised_coordination

                self_time = self._self_time_for_task(task)
                self.model._step_delegated_counterfactual_self_hours += self_time
            else:
                self._execute_task_self(task)

    def _execute_task_self(self, task: Task) -> None:
        """Execute a task personally and book the labour explicitly."""
        time_cost = self._self_time_for_task(task)
        realised_time = min(self.available_time, time_cost)
        self.available_time = max(0.0, self.available_time - time_cost)
        self.tasks_completed_self += 1
        self.model._step_self_labor_hours += realised_time

    def provide_service(self, task: Task) -> float:
        """Provide service with explicit friction relative to stable matching."""
        provider_proficiency = 0.60
        base_time_cost = task.time_cost_for(provider_proficiency)
        time_cost = base_time_cost * self.model.provider_service_overhead_factor

        self.available_time = max(0.0, self.available_time - time_cost)
        self.time_spent_providing += time_cost

        fee = task.base_time * self.model.service_cost_factor
        self.income += fee

        self.model._step_service_labor_hours += time_cost
        self.model._step_delegated_actual_service_hours += time_cost

        return time_cost

    def get_state_dict(self) -> dict:
        """Return the observable state, extended with research-only fields."""
        state = super().get_state_dict()
        state["carryover_tasks_count"] = len(self.carryover_tasks)
        state["coordination_time_spent"] = round(self.coordination_time_spent, 3)
        return state


class ConvenienceParadoxResearchModel(ConvenienceParadoxModel):
    """Research-only model variant for post-campaign mechanism audits.

    This class intentionally does not replace the stable dashboard engine. It
    mirrors the stable constructor closely so that analysis code can swap in
    the research engine without changing its calling convention.
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
        requester_coordination_cost_factor: float = 0.15,
        provider_service_overhead_factor: float = 1.11,
    ) -> None:
        mesa.Model.__init__(self, rng=seed)

        self.engine_name: str = "research_v2"

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
        self.requester_coordination_cost_factor: float = requester_coordination_cost_factor
        self.provider_service_overhead_factor: float = provider_service_overhead_factor

        self.task_type_registry: dict[str, dict] = TASK_TYPES
        self.service_pool: list[Task] = []
        self.current_step: int = 0

        self._step_tasks_total: int = 0
        self._step_tasks_delegated: int = 0
        self._step_tasks_matched: int = 0
        self._step_time_in_service: float = 0.0
        self._step_self_labor_hours: float = 0.0
        self._step_service_labor_hours: float = 0.0
        self._step_coordination_hours: float = 0.0
        self._step_delegated_counterfactual_self_hours: float = 0.0
        self._step_delegated_actual_service_hours: float = 0.0

        rng_int = int(seed) if seed is not None else None
        if network_type == "small_world":
            if num_agents < 5:
                # Tiny research tests need a valid graph without changing the
                # stable dashboard model's default topology assumptions.
                G = nx.complete_graph(n=num_agents)
            else:
                G = nx.watts_strogatz_graph(n=num_agents, k=4, p=0.1, seed=rng_int)
        else:
            p_edge = 4.0 / max(num_agents - 1, 1)
            G = nx.erdos_renyi_graph(n=num_agents, p=p_edge, seed=rng_int)

        self.grid: mesa_space.NetworkGrid = mesa_space.NetworkGrid(G)

        task_type_names = list(TASK_TYPES.keys())
        for node_id in range(num_agents):
            raw_pref = float(self.rng.normal(
                delegation_preference_mean, delegation_preference_std
            ))
            pref = float(np.clip(raw_pref, 0.02, 0.98))
            skill_set = {
                t: float(self.rng.uniform(0.3, 0.9)) for t in task_type_names
            }

            agent = ResearchResident(
                model=self,
                initial_available_time=initial_available_time,
                delegation_preference=pref,
                skill_set=skill_set,
                stress_threshold=stress_threshold,
                conformity_sensitivity=social_conformity_pressure,
                adaptation_rate=adaptation_rate,
            )
            self.grid.place_agent(agent, node_id)

        self._agents_by_id: dict[int, ResearchResident] = {
            int(agent.unique_id): agent for agent in self.agents
        }

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "avg_stress": self._compute_avg_stress,
                "avg_delegation_rate": self._compute_avg_delegation_rate,
                "total_labor_hours": self._compute_total_labor_hours,
                "social_efficiency": self._compute_social_efficiency,
                "gini_income": self._compute_gini_income,
                "gini_available_time": self._compute_gini_available_time,
                "tasks_delegated_frac": self._compute_tasks_delegated_frac,
                "unmatched_tasks": self._compute_unmatched_tasks,
                "avg_income": self._compute_avg_income,
                "self_labor_hours": self._compute_self_labor_hours,
                "service_labor_hours": self._compute_service_labor_hours,
                "delegation_coordination_hours": self._compute_delegation_coordination_hours,
                "delegated_counterfactual_self_hours": self._compute_delegated_counterfactual_self_hours,
                "delegated_actual_service_hours": self._compute_delegated_actual_service_hours,
                "delegation_labor_delta": self._compute_delegation_labor_delta,
                "stress_breach_share": self._compute_stress_breach_share,
                "mean_time_deficit": self._compute_mean_time_deficit,
                "backlog_tasks": self._compute_backlog_tasks,
                "delegation_match_rate": self._compute_delegation_match_rate,
            },
            agent_reporters={
                "available_time": "available_time",
                "stress_level": "stress_level",
                "delegation_preference": "delegation_preference",
                "income": "income",
                "tasks_completed_self": "tasks_completed_self",
                "tasks_delegated": "tasks_delegated",
                "time_spent_providing": "time_spent_providing",
                "carryover_tasks_count": lambda a: len(a.carryover_tasks),
                "coordination_time_spent": "coordination_time_spent",
            },
        )
        self.datacollector.collect(self)

        logger.debug(
            "ConvenienceParadoxResearchModel initialised: %d agents, "
            "delegation_mean=%.2f, service_cost=%.2f, engine=%s, seed=%s",
            num_agents,
            delegation_preference_mean,
            service_cost_factor,
            self.engine_name,
            seed,
        )

    def _expected_provider_time(self, task: Task) -> float:
        """Return provider time used both for capacity checks and accounting."""
        provider_proficiency = 0.60
        base_time_cost = task.time_cost_for(provider_proficiency)
        return base_time_cost * self.provider_service_overhead_factor

    def step(self) -> None:
        """Advance one research step with explicit labour sub-accounting."""
        self.service_pool = []
        self._step_tasks_total = 0
        self._step_tasks_delegated = 0
        self._step_tasks_matched = 0
        self._step_time_in_service = 0.0
        self._step_self_labor_hours = 0.0
        self._step_service_labor_hours = 0.0
        self._step_coordination_hours = 0.0
        self._step_delegated_counterfactual_self_hours = 0.0
        self._step_delegated_actual_service_hours = 0.0

        self.agents.shuffle_do("generate_and_decide")

        for agent in self.agents:
            self._step_tasks_total += len(agent.task_queue)
            self._step_tasks_delegated += sum(1 for t in agent.task_queue if t.delegated)

        self._run_service_matching()
        self.agents.shuffle_do("update_state")
        self.datacollector.collect(self)
        self.current_step += 1

    def _run_service_matching(self) -> None:
        """Match delegated tasks with stricter provider-capacity checks.

        Unmatched tasks are not discarded. They are returned to the requester's
        backlog so the work survives into the next day.
        """
        if not self.service_pool:
            return

        self.random.shuffle(self.service_pool)
        all_agents = list(self.agents)

        for task in self.service_pool:
            expected_provider_time = self._expected_provider_time(task)
            candidates = [
                a for a in all_agents
                if a.unique_id != task.requester_id
                and a.available_time >= expected_provider_time
            ]

            if not candidates:
                requester = self._agents_by_id.get(int(task.requester_id))
                if requester is not None:
                    task.delegated = False
                    requester.carryover_tasks.append(task)
                continue

            provider = max(candidates, key=lambda a: a.available_time)
            time_spent = provider.provide_service(task)
            self._step_tasks_matched += 1
            self._step_time_in_service += time_spent

    def _compute_self_labor_hours(self) -> float:
        """Hours spent self-serving tasks in the current step."""
        return float(self._step_self_labor_hours)

    def _compute_service_labor_hours(self) -> float:
        """Hours spent providing services in the current step."""
        return float(self._step_service_labor_hours)

    def _compute_delegation_coordination_hours(self) -> float:
        """Hours spent arranging delegated tasks in the current step."""
        return float(self._step_coordination_hours)

    def _compute_delegated_counterfactual_self_hours(self) -> float:
        """Counterfactual requester self-labour for delegated tasks."""
        return float(self._step_delegated_counterfactual_self_hours)

    def _compute_delegated_actual_service_hours(self) -> float:
        """Actual provider labour spent on delegated tasks."""
        return float(self._step_delegated_actual_service_hours)

    def _compute_delegation_labor_delta(self) -> float:
        """Net labour added by delegation relative to requester self-service."""
        return float(
            self._step_delegated_actual_service_hours
            + self._step_coordination_hours
            - self._step_delegated_counterfactual_self_hours
        )

    def _compute_stress_breach_share(self) -> float:
        """Share of agents ending the step below the stress threshold."""
        values = [
            1.0 if agent.available_time < agent.stress_threshold else 0.0
            for agent in self.agents
        ]
        return float(np.mean(values)) if values else 0.0

    def _compute_mean_time_deficit(self) -> float:
        """Mean shortfall below the stress threshold across all agents."""
        deficits = [
            max(0.0, agent.stress_threshold - agent.available_time)
            for agent in self.agents
        ]
        return float(np.mean(deficits)) if deficits else 0.0

    def _compute_backlog_tasks(self) -> int:
        """Count tasks carried into the next step because they were not resolved."""
        return int(sum(len(agent.carryover_tasks) for agent in self.agents))

    def _compute_delegation_match_rate(self) -> float:
        """Fraction of delegated tasks matched this step."""
        if self._step_tasks_delegated == 0:
            return 1.0
        return float(self._step_tasks_matched / self._step_tasks_delegated)

    def get_params(self) -> dict[str, Any]:
        """Return model parameters plus research-only engine metadata."""
        params = super().get_params()
        params.update(
            {
                "engine": self.engine_name,
                "requester_coordination_cost_factor": self.requester_coordination_cost_factor,
                "provider_service_overhead_factor": self.provider_service_overhead_factor,
            }
        )
        return params
