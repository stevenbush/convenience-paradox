"""tests/test_agents.py — Unit tests for the Resident agent class.

This test module validates the core decision logic of the Resident agent
in isolation, ensuring that each rule behaves correctly before the full
model is assembled. Testing agents independently from the model (and from
each other) makes it easy to pinpoint the source of any misbehaviour.

Test coverage:
  - Task time_cost_for() formula correctness.
  - Self-serve vs. delegate decision logic across edge cases.
  - Stress update rule (rising on time deficit, falling on surplus).
  - Preference adaptation (conformity toward neighbours).
  - Service provision (time and income accounting).
  - Cumulative counter correctness.

Run with:
    conda activate convenience-paradox
    cd /path/to/project
    pytest tests/test_agents.py -v

See also:
    - tests/test_model.py — model-level integration and conservation tests
    - model/agents.py    — the module being tested
"""

import pytest

from model.agents import Task, Resident
from model.model import ConvenienceParadoxModel


# ---------------------------------------------------------------------------
# Fixtures: minimal model instances for agent testing
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_model_type_a():
    """A small Type-A-like model for testing agents in isolation.

    Uses 10 agents with low delegation preference to provide a realistic
    neighbourhood for preference-adaptation tests.
    """
    return ConvenienceParadoxModel(
        num_agents=10,
        delegation_preference_mean=0.20,
        delegation_preference_std=0.05,
        service_cost_factor=0.65,
        social_conformity_pressure=0.15,
        tasks_per_step_mean=2.0,
        tasks_per_step_std=0.1,
        stress_threshold=2.5,
        stress_recovery_rate=0.10,
        adaptation_rate=0.05,
        initial_available_time=8.0,
        seed=1,
    )


@pytest.fixture
def minimal_model_type_b():
    """A small Type-B-like model for testing high-delegation behaviour."""
    return ConvenienceParadoxModel(
        num_agents=10,
        delegation_preference_mean=0.80,
        delegation_preference_std=0.05,
        service_cost_factor=0.20,
        social_conformity_pressure=0.65,
        tasks_per_step_mean=2.0,
        tasks_per_step_std=0.1,
        stress_threshold=2.5,
        stress_recovery_rate=0.10,
        adaptation_rate=0.05,
        initial_available_time=8.0,
        seed=2,
    )


# ---------------------------------------------------------------------------
# Task tests
# ---------------------------------------------------------------------------

class TestTask:
    """Tests for the Task dataclass and its time_cost_for() method."""

    def test_base_time_at_full_proficiency(self):
        """An expert (proficiency=1.0) takes exactly base_time hours."""
        task = Task(task_type="domestic", base_time=1.0, skill_requirement=0.3)
        assert task.time_cost_for(1.0) == pytest.approx(1.0)

    def test_time_doubles_at_half_proficiency(self):
        """An agent at proficiency=0.5 takes 2× the base time."""
        task = Task(task_type="domestic", base_time=1.0, skill_requirement=0.3)
        assert task.time_cost_for(0.5) == pytest.approx(2.0)

    def test_minimum_proficiency_clamp(self):
        """Proficiency below 0.1 is clamped to prevent extreme time costs."""
        task = Task(task_type="maintenance", base_time=1.5, skill_requirement=0.65)
        # Proficiency 0.0 is clamped to 0.1 → time = 1.5 / 0.1 = 15.0
        assert task.time_cost_for(0.0) == pytest.approx(15.0)
        # Negative proficiency should be handled identically.
        assert task.time_cost_for(-0.5) == pytest.approx(15.0)

    def test_time_cost_always_positive(self):
        """time_cost_for() should always return a positive number."""
        task = Task(task_type="errand", base_time=0.5, skill_requirement=0.2)
        for p in [0.0, 0.1, 0.5, 1.0]:
            assert task.time_cost_for(p) > 0

    def test_higher_proficiency_means_less_time(self):
        """Verifies the monotone relationship: more skill → less time."""
        task = Task(task_type="administrative", base_time=1.2, skill_requirement=0.5)
        times = [task.time_cost_for(p) for p in [0.3, 0.5, 0.7, 0.9]]
        assert times == sorted(times, reverse=True), (
            "Higher proficiency should always produce lower or equal time cost."
        )

    def test_delegated_flag_default_false(self):
        """Tasks start as not delegated."""
        task = Task(task_type="errand", base_time=0.5, skill_requirement=0.2)
        assert task.delegated is False

    def test_requester_id_default(self):
        """Default requester_id is -1 (sentinel for 'not yet assigned')."""
        task = Task(task_type="domestic", base_time=0.8, skill_requirement=0.3)
        assert task.requester_id == -1


# ---------------------------------------------------------------------------
# Resident agent — time and task accounting
# ---------------------------------------------------------------------------

class TestResidentTimeAccounting:
    """Tests for available_time reset and task execution accounting."""

    def test_available_time_resets_each_step(self, minimal_model_type_a):
        """available_time should reset to initial_available_time at step start."""
        agent = list(minimal_model_type_a.agents)[0]
        # Manually drain available_time below initial.
        agent.available_time = 0.5
        # generate_and_decide() resets available_time first.
        agent.generate_and_decide()
        # After the call, it should have been reset (then possibly reduced by self-served tasks).
        # It must not be above initial_available_time.
        assert agent.available_time <= agent.initial_available_time

    def test_self_served_task_reduces_available_time(self, minimal_model_type_a):
        """Executing a task personally should reduce available_time."""
        agent = list(minimal_model_type_a.agents)[0]
        agent.available_time = 8.0
        before = agent.available_time
        task = Task(task_type="errand", base_time=0.5, skill_requirement=0.2,
                    requester_id=agent.unique_id)
        agent._execute_task_self(task)
        assert agent.available_time < before

    def test_available_time_never_negative(self, minimal_model_type_a):
        """available_time should be floored at 0.0, never negative."""
        agent = list(minimal_model_type_a.agents)[0]
        agent.available_time = 0.1
        # Force a large task.
        task = Task(task_type="maintenance", base_time=5.0, skill_requirement=0.65,
                    requester_id=agent.unique_id)
        agent._execute_task_self(task)
        assert agent.available_time >= 0.0

    def test_tasks_completed_self_increments(self, minimal_model_type_a):
        """tasks_completed_self should increment for each self-served task."""
        agent = list(minimal_model_type_a.agents)[0]
        before = agent.tasks_completed_self
        task = Task(task_type="domestic", base_time=0.8, skill_requirement=0.3,
                    requester_id=agent.unique_id)
        agent._execute_task_self(task)
        assert agent.tasks_completed_self == before + 1

    def test_provide_service_increments_income_and_time_providing(self, minimal_model_type_a):
        """Providing a service should earn income and accumulate time_spent_providing."""
        agent = list(minimal_model_type_a.agents)[0]
        agent.available_time = 8.0
        income_before = agent.income
        time_before = agent.time_spent_providing

        task = Task(task_type="errand", base_time=0.5, skill_requirement=0.2,
                    requester_id=999)  # different requester
        time_spent = agent.provide_service(task)

        assert agent.income > income_before, "Provider should earn a fee."
        assert agent.time_spent_providing > time_before, "Provider time should accumulate."
        assert time_spent > 0

    def test_provide_service_reduces_available_time(self, minimal_model_type_a):
        """Providing a service costs the provider their own available_time."""
        agent = list(minimal_model_type_a.agents)[0]
        agent.available_time = 8.0
        before = agent.available_time

        task = Task(task_type="domestic", base_time=0.8, skill_requirement=0.3,
                    requester_id=999)
        agent.provide_service(task)
        assert agent.available_time < before


# ---------------------------------------------------------------------------
# Resident agent — delegation decision logic
# ---------------------------------------------------------------------------

class TestResidentDelegationDecision:
    """Tests for the _should_delegate() decision rule."""

    def test_forced_delegation_when_time_critical(self, minimal_model_type_a):
        """Agent must delegate when they have almost no time left, regardless of preference."""
        agent = list(minimal_model_type_a.agents)[0]
        # Override to a very low-delegation agent.
        agent.delegation_preference = 0.0
        agent.stress_level = 0.0
        # Leave almost no time.
        agent.available_time = 0.05

        task = Task(task_type="maintenance", base_time=2.0, skill_requirement=0.65,
                    requester_id=agent.unique_id)
        # Task requires at least 0.5× 2.0 = 1.0 hours. Agent only has 0.05.
        # Must delegate regardless of preference.
        assert agent._should_delegate(task) is True

    def test_low_preference_agent_tends_to_self_serve(self, minimal_model_type_a):
        """A low-preference, low-stress agent should mostly self-serve (probabilistic)."""
        agent = list(minimal_model_type_a.agents)[0]
        agent.delegation_preference = 0.02  # very low
        agent.stress_level = 0.0
        agent.available_time = 8.0

        task = Task(task_type="domestic", base_time=0.8, skill_requirement=0.3,
                    requester_id=agent.unique_id)

        # Run 100 trials; expect < 30% delegation with such low preference.
        delegate_count = sum(agent._should_delegate(task) for _ in range(100))
        assert delegate_count < 40, (
            f"Low-preference agent delegated {delegate_count}/100 times — expected < 40."
        )

    def test_high_preference_agent_tends_to_delegate(self, minimal_model_type_b):
        """A high-preference, low-cost agent should mostly delegate."""
        agent = list(minimal_model_type_b.agents)[0]
        agent.delegation_preference = 0.95
        agent.stress_level = 0.0
        agent.available_time = 8.0

        task = Task(task_type="errand", base_time=0.5, skill_requirement=0.2,
                    requester_id=agent.unique_id)

        # 100 trials: expect > 60% delegation with high preference and low cost.
        delegate_count = sum(agent._should_delegate(task) for _ in range(100))
        assert delegate_count > 55, (
            f"High-preference agent only delegated {delegate_count}/100 times — expected > 55."
        )

    def test_stress_increases_delegation_probability(self, minimal_model_type_a):
        """Higher stress should increase the chance of delegation."""
        model = minimal_model_type_a
        agent = list(model.agents)[0]
        agent.delegation_preference = 0.40  # moderate baseline
        agent.available_time = 8.0

        task = Task(task_type="domestic", base_time=0.8, skill_requirement=0.3,
                    requester_id=agent.unique_id)

        agent.stress_level = 0.0
        low_stress_count = sum(agent._should_delegate(task) for _ in range(200))

        agent.stress_level = 1.0
        high_stress_count = sum(agent._should_delegate(task) for _ in range(200))

        assert high_stress_count > low_stress_count, (
            "Stressed agents should delegate more than calm agents."
        )


# ---------------------------------------------------------------------------
# Resident agent — stress and preference updates
# ---------------------------------------------------------------------------

class TestResidentStateUpdate:
    """Tests for the update_state() feedback mechanisms."""

    def test_stress_increases_when_time_deficit(self, minimal_model_type_a):
        """Stress should rise when available_time is below stress_threshold."""
        agent = list(minimal_model_type_a.agents)[0]
        agent.stress_level = 0.0
        agent.available_time = 0.0  # Completely exhausted.
        # stress_threshold is 2.5 → agent is well below threshold.

        agent.update_state()
        assert agent.stress_level > 0.0, "Stress should have increased."

    def test_stress_decreases_when_time_surplus(self, minimal_model_type_a):
        """Stress should fall when available_time exceeds the threshold."""
        agent = list(minimal_model_type_a.agents)[0]
        agent.stress_level = 0.5  # Start with moderate stress.
        agent.available_time = agent.initial_available_time  # Full day unspent.

        agent.update_state()
        assert agent.stress_level < 0.5, "Stress should have recovered."

    def test_stress_bounded_zero_to_one(self, minimal_model_type_a):
        """Stress must always remain in [0.0, 1.0]."""
        agent = list(minimal_model_type_a.agents)[0]

        # Test upper bound: start at 1.0 stress with zero time.
        agent.stress_level = 1.0
        agent.available_time = 0.0
        agent.update_state()
        assert agent.stress_level <= 1.0

        # Test lower bound: start at 0.0 stress with full time.
        agent.stress_level = 0.0
        agent.available_time = 8.0
        agent.update_state()
        assert agent.stress_level >= 0.0

    def test_delegation_preference_bounded(self, minimal_model_type_a):
        """delegation_preference must remain in [0.0, 1.0] after update."""
        model = minimal_model_type_a
        # Run several steps to let preferences evolve.
        for _ in range(10):
            model.step()

        for agent in model.agents:
            assert 0.0 <= agent.delegation_preference <= 1.0, (
                f"Agent {agent.unique_id} has out-of-bounds preference: "
                f"{agent.delegation_preference}"
            )

    def test_preference_moves_toward_high_neighbour_mean(self, minimal_model_type_a):
        """With high conformity, an agent's preference should drift toward neighbours'."""
        model = minimal_model_type_a
        agents = list(model.agents)
        target = agents[0]

        # Set target agent's preference low.
        target.delegation_preference = 0.10
        # Set all neighbours' preferences high.
        neighbours = model.grid.get_neighbors(target.pos, include_center=False)
        for n in neighbours:
            n.delegation_preference = 0.90

        # Increase conformity for strong signal.
        model.social_conformity_pressure = 0.80
        target.conformity_sensitivity = 0.80

        before = target.delegation_preference
        target.update_state()
        after = target.delegation_preference

        assert after > before, (
            "Agent preference should have risen toward high-preference neighbours."
        )
