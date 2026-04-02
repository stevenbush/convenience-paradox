"""tests/test_research_model.py — Verification for the research-only engine.

This module validates the additional mechanisms introduced by
`ConvenienceParadoxResearchModel` while protecting the dashboard-facing stable
model from accidental behavioural drift.

Coverage goals:
  - delegated tasks become backlog when they cannot be matched
  - backlog survives into the next step instead of disappearing
  - requester coordination time is explicitly booked
  - provider-side service friction is applied
  - research labour sub-accounts remain internally consistent
"""

from __future__ import annotations

import pytest

from model.agents import Task
from model.research_model import ConvenienceParadoxResearchModel


@pytest.fixture
def backlog_model() -> ConvenienceParadoxResearchModel:
    """Tiny model configured so that delegated work cannot be matched."""
    model = ConvenienceParadoxResearchModel(
        num_agents=2,
        delegation_preference_mean=0.95,
        delegation_preference_std=0.0,
        service_cost_factor=0.10,
        social_conformity_pressure=0.0,
        tasks_per_step_mean=1.0,
        tasks_per_step_std=0.0,
        stress_threshold=0.2,
        stress_recovery_rate=0.10,
        adaptation_rate=0.01,
        initial_available_time=0.4,
        seed=42,
    )
    for agent in model.agents:
        agent.delegation_preference = 1.0
    return model


def test_unmatched_tasks_become_backlog(backlog_model: ConvenienceParadoxResearchModel) -> None:
    """Delegated tasks should survive as backlog when no provider can accept them."""
    backlog_model.step()
    latest = backlog_model.get_model_dataframe().iloc[-1]

    assert latest["unmatched_tasks"] > 0
    assert latest["backlog_tasks"] > 0
    assert latest["delegation_match_rate"] < 1.0
    assert sum(len(agent.carryover_tasks) for agent in backlog_model.agents) == int(latest["backlog_tasks"])


def test_backlog_is_carried_into_next_step(backlog_model: ConvenienceParadoxResearchModel) -> None:
    """Carryover tasks should increase the next step's task total."""
    backlog_model.step()
    carried = sum(len(agent.carryover_tasks) for agent in backlog_model.agents)
    assert carried > 0

    for agent in backlog_model.agents:
        agent.initial_available_time = 8.0
        agent.delegation_preference = 0.0

    backlog_model.step()
    assert backlog_model._step_tasks_total >= backlog_model.num_agents + carried


def test_requester_coordination_hours_are_recorded() -> None:
    """Delegation should add explicit requester-side coordination time."""
    model = ConvenienceParadoxResearchModel(
        num_agents=8,
        delegation_preference_mean=0.95,
        delegation_preference_std=0.0,
        service_cost_factor=0.10,
        tasks_per_step_mean=1.0,
        tasks_per_step_std=0.0,
        seed=7,
    )
    for agent in model.agents:
        agent.delegation_preference = 1.0

    model.step()
    latest = model.get_model_dataframe().iloc[-1]
    assert latest["delegation_coordination_hours"] > 0.0


def test_provider_service_friction_applies() -> None:
    """Provider time should include the research-engine overhead multiplier."""
    model = ConvenienceParadoxResearchModel(num_agents=4, seed=11)
    provider = list(model.agents)[0]
    provider.available_time = 8.0
    task = Task(
        task_type="administrative",
        base_time=1.2,
        skill_requirement=0.5,
        requester_id=999,
    )

    time_spent = provider.provide_service(task)
    expected = task.time_cost_for(0.60) * model.provider_service_overhead_factor
    assert time_spent == pytest.approx(expected)


def test_labour_subaccounts_sum_to_total_labor() -> None:
    """Self, service, and coordination labour should reconcile to total labor."""
    model = ConvenienceParadoxResearchModel(
        num_agents=12,
        delegation_preference_mean=0.80,
        delegation_preference_std=0.0,
        service_cost_factor=0.20,
        tasks_per_step_mean=1.0,
        tasks_per_step_std=0.0,
        seed=21,
    )
    for agent in model.agents:
        agent.delegation_preference = 1.0

    model.step()
    latest = model.get_model_dataframe().iloc[-1]
    explicit_total = (
        latest["self_labor_hours"]
        + latest["service_labor_hours"]
        + latest["delegation_coordination_hours"]
    )
    assert latest["total_labor_hours"] == pytest.approx(explicit_total)
    assert latest["delegation_labor_delta"] == pytest.approx(
        latest["delegated_actual_service_hours"]
        + latest["delegation_coordination_hours"]
        - latest["delegated_counterfactual_self_hours"]
    )

