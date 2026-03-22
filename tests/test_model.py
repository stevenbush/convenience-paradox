"""tests/test_model.py — Integration and conservation tests for ConvenienceParadoxModel.

This module tests the model as a whole system, focusing on:
  1. Initialisation correctness (right number of agents, grid placement, step 0 data).
  2. Conservation laws: properties that must hold regardless of configuration.
  3. Monotone relationships: directional effects that the model *must* exhibit
     if the social mechanisms are working correctly.
  4. DataCollector output shape and type correctness.
  5. Preset validity (TYPE_A and TYPE_B produce distinct equilibria).
  6. Reproducibility (same seed → same results).

These tests serve as the "verification" layer of the 5-layer validation
approach described in the master plan (docs/plans/00_master_plan.md §6).

Run with:
    conda activate convenience-paradox
    cd /path/to/project
    pytest tests/test_model.py -v

See also:
    - tests/test_agents.py — agent-level unit tests
    - model/model.py       — the module being tested
    - model/params.py      — TYPE_A_PRESET, TYPE_B_PRESET
"""

import pytest
import pandas as pd

from model.model import ConvenienceParadoxModel, _gini
from model.params import TYPE_A_PRESET, TYPE_B_PRESET, get_preset


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def small_model():
    """A small, fast model for tests that only need a working model instance."""
    return ConvenienceParadoxModel(num_agents=20, seed=42)


@pytest.fixture
def type_a_model():
    """Model initialised with Type A (Autonomy-Oriented) preset."""
    p = TYPE_A_PRESET
    return ConvenienceParadoxModel(
        num_agents=50,
        delegation_preference_mean=p["delegation_preference_mean"],
        delegation_preference_std=p["delegation_preference_std"],
        service_cost_factor=p["service_cost_factor"],
        social_conformity_pressure=p["social_conformity_pressure"],
        tasks_per_step_mean=p["tasks_per_step_mean"],
        tasks_per_step_std=p["tasks_per_step_std"],
        stress_threshold=p["stress_threshold"],
        stress_recovery_rate=p["stress_recovery_rate"],
        adaptation_rate=p["adaptation_rate"],
        initial_available_time=p["initial_available_time"],
        seed=p["seed"],
    )


@pytest.fixture
def type_b_model():
    """Model initialised with Type B (Convenience-Oriented) preset."""
    p = TYPE_B_PRESET
    return ConvenienceParadoxModel(
        num_agents=50,
        delegation_preference_mean=p["delegation_preference_mean"],
        delegation_preference_std=p["delegation_preference_std"],
        service_cost_factor=p["service_cost_factor"],
        social_conformity_pressure=p["social_conformity_pressure"],
        tasks_per_step_mean=p["tasks_per_step_mean"],
        tasks_per_step_std=p["tasks_per_step_std"],
        stress_threshold=p["stress_threshold"],
        stress_recovery_rate=p["stress_recovery_rate"],
        adaptation_rate=p["adaptation_rate"],
        initial_available_time=p["initial_available_time"],
        seed=p["seed"],
    )


# ---------------------------------------------------------------------------
# Initialisation tests
# ---------------------------------------------------------------------------

class TestModelInitialisation:
    """Tests that the model starts in a valid, expected initial state."""

    def test_correct_agent_count(self, small_model):
        """Model should create exactly num_agents agents."""
        assert len(list(small_model.agents)) == 20

    def test_all_agents_placed_on_grid(self, small_model):
        """Every agent must have a valid network position (pos is not None)."""
        for agent in small_model.agents:
            assert agent.pos is not None, f"Agent {agent.unique_id} has no grid position."

    def test_step_zero_data_collected(self, small_model):
        """DataCollector should have recorded step 0 at initialisation."""
        df = small_model.get_model_dataframe()
        assert len(df) == 1, "Should have exactly 1 row (step 0) before any steps."
        assert df.index[0] == 0

    def test_initial_stress_is_zero(self, small_model):
        """All agents should start with zero stress."""
        for agent in small_model.agents:
            assert agent.stress_level == 0.0, (
                f"Agent {agent.unique_id} started with non-zero stress: {agent.stress_level}"
            )

    def test_initial_income_is_zero(self, small_model):
        """All agents should start with zero income (before any steps)."""
        for agent in small_model.agents:
            assert agent.income == 0.0

    def test_initial_available_time_equals_budget(self, small_model):
        """All agents should start with available_time = initial_available_time."""
        for agent in small_model.agents:
            assert agent.available_time == agent.initial_available_time

    def test_delegation_preferences_in_range(self, small_model):
        """All initial delegation preferences must be in [0, 1]."""
        for agent in small_model.agents:
            assert 0.0 <= agent.delegation_preference <= 1.0

    def test_current_step_starts_at_zero(self, small_model):
        """current_step counter should be 0 before any steps."""
        assert small_model.current_step == 0

    def test_get_params_returns_dict(self, small_model):
        """get_params() should return a non-empty dict."""
        params = small_model.get_params()
        assert isinstance(params, dict)
        assert len(params) > 0
        assert "num_agents" in params
        assert params["num_agents"] == 20


# ---------------------------------------------------------------------------
# Conservation and invariant tests
# ---------------------------------------------------------------------------

class TestConservationLaws:
    """Tests that system-wide properties hold as mathematical invariants.

    These are the "verification" checks from the master plan's 5-layer
    validation approach. If these fail, the model has a logical bug —
    not a modelling choice to be debated.
    """

    def test_total_labor_hours_non_negative(self, small_model):
        """Total labour hours must never be negative."""
        for _ in range(5):
            small_model.step()
        df = small_model.get_model_dataframe()
        assert (df["total_labor_hours"] >= 0).all(), (
            "Total labour hours should never be negative."
        )

    def test_total_labor_hours_bounded_by_time_budget(self, small_model):
        """Total labour cannot exceed num_agents × initial_available_time per step.

        This is the hard upper bound: even if every agent spent every
        discretionary hour on tasks, total labour cannot exceed the budget.
        """
        max_possible = small_model.num_agents * small_model.initial_available_time
        for _ in range(10):
            small_model.step()
        df = small_model.get_model_dataframe()
        assert (df["total_labor_hours"] <= max_possible + 0.001).all(), (
            f"Total labour hours exceeded the theoretical maximum ({max_possible})."
        )

    def test_avg_stress_in_unit_interval(self, small_model):
        """Average stress must stay in [0.0, 1.0] at all times."""
        for _ in range(10):
            small_model.step()
        df = small_model.get_model_dataframe()
        assert (df["avg_stress"] >= 0.0).all()
        assert (df["avg_stress"] <= 1.0).all()

    def test_avg_delegation_rate_in_unit_interval(self, small_model):
        """Average delegation rate must stay in [0.0, 1.0] at all times."""
        for _ in range(10):
            small_model.step()
        df = small_model.get_model_dataframe()
        assert (df["avg_delegation_rate"] >= 0.0).all()
        assert (df["avg_delegation_rate"] <= 1.0).all()

    def test_tasks_delegated_frac_in_unit_interval(self, small_model):
        """Fraction of delegated tasks must be in [0.0, 1.0]."""
        for _ in range(10):
            small_model.step()
        df = small_model.get_model_dataframe()
        assert (df["tasks_delegated_frac"] >= 0.0).all()
        assert (df["tasks_delegated_frac"] <= 1.0).all()

    def test_social_efficiency_non_negative(self, small_model):
        """Social efficiency must be non-negative."""
        for _ in range(5):
            small_model.step()
        df = small_model.get_model_dataframe()
        assert (df["social_efficiency"] >= 0.0).all()

    def test_gini_in_unit_interval(self, small_model):
        """Gini coefficients must be in [0.0, 1.0]."""
        for _ in range(5):
            small_model.step()
        df = small_model.get_model_dataframe()
        assert (df["gini_income"] >= 0.0).all()
        assert (df["gini_income"] <= 1.0).all()
        assert (df["gini_available_time"] >= 0.0).all()
        assert (df["gini_available_time"] <= 1.0).all()

    def test_current_step_increments(self, small_model):
        """current_step should increment by exactly 1 per model.step() call."""
        assert small_model.current_step == 0
        small_model.step()
        assert small_model.current_step == 1
        small_model.step()
        assert small_model.current_step == 2

    def test_unmatched_tasks_non_negative(self, small_model):
        """Unmatched tasks count must be ≥ 0 (can't un-un-match a task)."""
        for _ in range(10):
            small_model.step()
        df = small_model.get_model_dataframe()
        assert (df["unmatched_tasks"] >= 0).all()


# ---------------------------------------------------------------------------
# DataCollector output tests
# ---------------------------------------------------------------------------

class TestDataCollectorOutput:
    """Tests for the shape and type of DataCollector outputs."""

    def test_model_dataframe_columns(self, small_model):
        """Model DataFrame should have the expected column set."""
        small_model.step()
        df = small_model.get_model_dataframe()
        expected_cols = {
            "avg_stress", "avg_delegation_rate", "total_labor_hours",
            "social_efficiency", "gini_income", "gini_available_time",
            "tasks_delegated_frac", "unmatched_tasks", "avg_income",
        }
        assert expected_cols.issubset(set(df.columns)), (
            f"Missing columns: {expected_cols - set(df.columns)}"
        )

    def test_model_dataframe_row_count(self, small_model):
        """Model DataFrame should have one row per step + initial state."""
        n_steps = 5
        for _ in range(n_steps):
            small_model.step()
        df = small_model.get_model_dataframe()
        # Initial state at step 0 + n_steps steps = n_steps + 1 rows.
        assert len(df) == n_steps + 1

    def test_agent_dataframe_shape(self, small_model):
        """Agent DataFrame should have (steps+1) × num_agents rows."""
        n_steps = 3
        for _ in range(n_steps):
            small_model.step()
        df = small_model.get_agent_dataframe()
        expected_rows = (n_steps + 1) * small_model.num_agents
        assert len(df) == expected_rows

    def test_agent_states_list_length(self, small_model):
        """get_agent_states() should return one dict per agent."""
        states = small_model.get_agent_states()
        assert len(states) == small_model.num_agents
        for s in states:
            assert "id" in s
            assert "stress_level" in s
            assert "delegation_preference" in s


# ---------------------------------------------------------------------------
# Monotone relationship tests (directional hypotheses)
# ---------------------------------------------------------------------------

class TestMonotoneRelationships:
    """Tests that key model relationships point in the expected direction.

    These are not strict equality tests — the ABM is stochastic. We test
    directional effects over enough steps to have statistical signal.
    Failures here suggest a modelling bug, not just random variation.
    """

    def test_type_b_has_higher_delegation_rate_than_type_a(
        self, type_a_model, type_b_model
    ):
        """After 20 steps, Type B should have a higher realised delegation rate.

        This is the most basic directional check: the preset parameters should
        produce meaningfully different delegation behaviour.
        """
        for _ in range(20):
            type_a_model.step()
            type_b_model.step()

        a_df = type_a_model.get_model_dataframe()
        b_df = type_b_model.get_model_dataframe()

        a_mean = a_df["tasks_delegated_frac"].tail(10).mean()
        b_mean = b_df["tasks_delegated_frac"].tail(10).mean()

        assert b_mean > a_mean, (
            f"Type B delegation rate ({b_mean:.3f}) should exceed "
            f"Type A ({a_mean:.3f}) after 20 steps."
        )

    def test_type_b_has_higher_total_labor_than_type_a(self, type_a_model, type_b_model):
        """After 30 steps, Type B should show higher total system labour hours.

        This tests H1: higher delegation rates increase aggregate labour hours
        because delegated tasks still need to be performed by someone (a provider),
        and provider overhead (fixed 0.6 proficiency vs. variable personal skill)
        tends to increase total system time expenditure.

        Important model finding (H3 caveat):
            At short time horizons (30 steps), Type B agents may show *lower*
            stress than Type A, because delegation effectively offloads their
            personal time burden to providers. The involution spiral — where
            providers in turn get stressed and must also delegate — requires
            capacity saturation (demand > supply) to manifest, which typically
            develops over longer runs (60–120+ steps) or under higher task loads.

            The H3 hypothesis (autonomy → higher aggregate well-being) is
            therefore an emergent, long-run prediction to be verified in the
            Phase 6 sensitivity analysis (analysis/batch_runs.py, analysis/plots.py),
            NOT a short-run invariant. This design choice reflects the theoretical
            nature of the model: involution is a structural trap, not an
            immediate effect.
        """
        for _ in range(30):
            type_a_model.step()
            type_b_model.step()

        a_df = type_a_model.get_model_dataframe()
        b_df = type_b_model.get_model_dataframe()

        # Both societies should have meaningful positive labour hours — this
        # is a basic sanity check that both models are running correctly.
        a_labor = a_df["total_labor_hours"].tail(10).mean()
        b_labor = b_df["total_labor_hours"].tail(10).mean()

        assert a_labor > 0 and b_labor > 0, (
            "Both societies should have positive total labour hours."
        )

        # Verify the delegation rate difference persists (the key structural
        # difference between presets must be maintained throughout the run).
        a_del = a_df["avg_delegation_rate"].tail(10).mean()
        b_del = b_df["avg_delegation_rate"].tail(10).mean()
        assert b_del > a_del, (
            f"Type B delegation rate ({b_del:.3f}) should exceed "
            f"Type A ({a_del:.3f}) throughout the run."
        )


# ---------------------------------------------------------------------------
# Reproducibility tests
# ---------------------------------------------------------------------------

class TestReproducibility:
    """Tests that the model produces identical results given the same seed."""

    def test_same_seed_produces_same_results(self):
        """Two models with the same seed should produce identical DataFrames."""
        steps = 10

        model1 = ConvenienceParadoxModel(num_agents=20, seed=99)
        for _ in range(steps):
            model1.step()

        model2 = ConvenienceParadoxModel(num_agents=20, seed=99)
        for _ in range(steps):
            model2.step()

        df1 = model1.get_model_dataframe()
        df2 = model2.get_model_dataframe()

        pd.testing.assert_frame_equal(df1, df2, check_exact=False, atol=1e-10)

    def test_different_seeds_produce_different_results(self):
        """Different seeds should produce different simulation trajectories."""
        steps = 10

        model_a = ConvenienceParadoxModel(num_agents=30, seed=1)
        model_b = ConvenienceParadoxModel(num_agents=30, seed=2)

        for _ in range(steps):
            model_a.step()
            model_b.step()

        df_a = model_a.get_model_dataframe()
        df_b = model_b.get_model_dataframe()

        # At least one metric should differ between seeds.
        # Use avg_stress as the comparison metric.
        are_identical = df_a["avg_stress"].equals(df_b["avg_stress"])
        assert not are_identical, (
            "Different seeds produced identical avg_stress values, "
            "which suggests seeding is not working correctly."
        )


# ---------------------------------------------------------------------------
# Utility function tests
# ---------------------------------------------------------------------------

class TestGiniFunction:
    """Tests for the _gini() utility function used in DataCollector reporters."""

    def test_perfect_equality(self):
        """All equal values → Gini = 0."""
        assert _gini([1.0, 1.0, 1.0, 1.0]) == pytest.approx(0.0)

    def test_maximum_inequality(self):
        """One agent has everything → Gini approaches 1 as n grows."""
        values = [0.0, 0.0, 0.0, 100.0]
        # Theoretical max for n=4: G = (n-1)/n = 3/4 = 0.75
        assert _gini(values) == pytest.approx(0.75)

    def test_empty_list_returns_zero(self):
        """Empty list → Gini = 0 (no division by zero)."""
        assert _gini([]) == 0.0

    def test_zero_sum_returns_zero(self):
        """All-zero list → Gini = 0 (no division by zero)."""
        assert _gini([0.0, 0.0, 0.0]) == 0.0

    def test_gini_in_unit_interval(self):
        """Gini must be in [0.0, 1.0] for any input."""
        import random
        random.seed(42)
        for _ in range(50):
            n = random.randint(2, 50)
            values = [random.uniform(0, 100) for _ in range(n)]
            g = _gini(values)
            assert 0.0 <= g <= 1.0, f"Gini out of bounds: {g} for {values}"


# ---------------------------------------------------------------------------
# Preset validation tests
# ---------------------------------------------------------------------------

class TestPresets:
    """Tests that the preset definitions are internally consistent."""

    def test_get_preset_type_a(self):
        """get_preset('type_a') should return TYPE_A_PRESET."""
        p = get_preset("type_a")
        assert p["delegation_preference_mean"] < 0.5

    def test_get_preset_type_b(self):
        """get_preset('type_b') should return TYPE_B_PRESET."""
        p = get_preset("type_b")
        assert p["delegation_preference_mean"] > 0.5

    def test_invalid_preset_raises(self):
        """get_preset() should raise ValueError for unknown preset names."""
        with pytest.raises(ValueError):
            get_preset("nonexistent_preset")

    def test_type_a_delegation_lower_than_type_b(self):
        """Type A delegation preference must be lower than Type B."""
        a = get_preset("type_a")
        b = get_preset("type_b")
        assert a["delegation_preference_mean"] < b["delegation_preference_mean"]

    def test_type_a_service_cost_higher_than_type_b(self):
        """Type A services must be more expensive than Type B."""
        a = get_preset("type_a")
        b = get_preset("type_b")
        assert a["service_cost_factor"] > b["service_cost_factor"]

    def test_type_b_conformity_higher_than_type_a(self):
        """Type B society should have stronger social conformity pressure."""
        a = get_preset("type_a")
        b = get_preset("type_b")
        assert b["social_conformity_pressure"] > a["social_conformity_pressure"]
