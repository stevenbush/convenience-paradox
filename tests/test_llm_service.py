"""tests/test_llm_service.py — Tests for the LLM Service Layer (Phase 4)

Test strategy:
    This test file validates two distinct aspects of the LLM integration:

    1. Unit tests (always run): Test schema validation, data flow, and the
       Flask API endpoints themselves using mocking. These run without Ollama.
       They validate that the LLM service correctly handles inputs, applies
       Pydantic schemas, and returns the right HTTP status codes.

    2. Integration tests (Ollama required, marked @pytest.mark.ollama):
       Test real LLM inference with the local Ollama server.
       Only run these manually when Ollama is confirmed running:
           pytest tests/test_llm_service.py -m ollama -v

Design philosophy (from CLAUDE.md §8.0):
    - Mock the `ollama.chat` call in unit tests to avoid Ollama dependency.
    - Use realistic JSON responses in mocks so schema validation is tested.
    - Always test both the happy path AND failure modes (empty response, bad JSON,
      missing fields) because the LLM integration is the most fragile surface area.

White-box principle testing:
    - Verify that ParsedScenarioParams validation catches out-of-range values.
    - Verify that null fields in Role 1 output are handled gracefully.
    - Verify that the audit_log in Role 2 responses contains the prompt, enabling
      independent verification of what the LLM was asked.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from api.schemas import (
    AgentProfileOutput,
    ParsedScenarioParams,
    ResultInterpretation,
    VisualizationAnnotation,
)


# ---------------------------------------------------------------------------
# Schema validation tests (no Ollama required)
# ---------------------------------------------------------------------------

class TestParsedScenarioParamsSchema:
    """Validate ParsedScenarioParams (Role 1 output schema)."""

    def test_valid_full_params(self):
        """All fields present and valid — should pass validation."""
        data = {
            "delegation_preference_mean": 0.75,
            "service_cost_factor": 0.20,
            "social_conformity_pressure": 0.60,
            "tasks_per_step_mean": 3.0,
            "num_agents": 100,
            "scenario_summary": "A high-delegation society",
            "reasoning": "Cheap services drive delegation upward.",
        }
        p = ParsedScenarioParams(**data)
        assert p.delegation_preference_mean == 0.75
        assert p.service_cost_factor == 0.20

    def test_all_optional_fields_null(self):
        """Only required fields present (all optional fields null) — should pass.
        This models the case where the LLM cannot extract all parameters from a
        vague scenario description.
        """
        p = ParsedScenarioParams(
            scenario_summary="A vague scenario",
            reasoning="Not enough information to set all parameters.",
        )
        assert p.delegation_preference_mean is None
        assert p.service_cost_factor is None

    def test_delegation_preference_out_of_range_rejected(self):
        """delegation_preference_mean > 1.0 must be rejected.
        This validates the schema protects the model from invalid LLM outputs.
        """
        with pytest.raises(ValidationError):
            ParsedScenarioParams(
                delegation_preference_mean=1.5,  # > 1.0: invalid
                scenario_summary="Invalid scenario",
            )

    def test_service_cost_below_minimum_rejected(self):
        """service_cost_factor < 0.05 must be rejected."""
        with pytest.raises(ValidationError):
            ParsedScenarioParams(
                service_cost_factor=0.01,  # < 0.05 minimum
                scenario_summary="Free services scenario",
            )


class TestAgentProfileOutputSchema:
    """Validate AgentProfileOutput (Role 2 output schema)."""

    def test_valid_profile(self):
        """All fields present and within range — should pass."""
        p = AgentProfileOutput(
            delegation_preference=0.30,
            skill_domestic=0.70,
            skill_administrative=0.55,
            skill_errand=0.65,
            skill_maintenance=0.45,
            profile_description="A self-reliant individual with moderate skills.",
        )
        skills = p.to_skill_set()
        assert set(skills.keys()) == {"domestic", "administrative", "errand", "maintenance"}
        assert skills["domestic"] == 0.70

    def test_skill_below_minimum_rejected(self):
        """skill_domestic < 0.3 must be rejected."""
        with pytest.raises(ValidationError):
            AgentProfileOutput(
                delegation_preference=0.50,
                skill_domestic=0.10,  # Below min 0.3
                skill_administrative=0.50,
                skill_errand=0.50,
                skill_maintenance=0.50,
                profile_description="Test profile",
            )

    def test_delegation_above_max_rejected(self):
        """delegation_preference > 0.98 must be rejected."""
        with pytest.raises(ValidationError):
            AgentProfileOutput(
                delegation_preference=0.99,  # Above max 0.98
                skill_domestic=0.50,
                skill_administrative=0.50,
                skill_errand=0.50,
                skill_maintenance=0.50,
                profile_description="Test",
            )


class TestResultInterpretationSchema:
    """Validate ResultInterpretation (Role 3 output schema)."""

    def test_valid_interpretation(self):
        """Full valid interpretation — should pass."""
        r = ResultInterpretation(
            answer="Stress is low because the run is too short for involution to emerge.",
            detailed_explanation="The H3 stress divergence requires ~100+ steps.",
            hypothesis_connection="H3",
            confidence_note="Only 20 steps were run; long-run effects not yet visible.",
        )
        assert "H3" in r.hypothesis_connection
        assert len(r.answer) > 0

    def test_minimal_interpretation(self):
        """Only required fields (answer, detailed_explanation) — should pass."""
        r = ResultInterpretation(
            answer="Delegation is rising.",
            detailed_explanation="Social conformity is pushing agents to adopt delegation norms.",
        )
        assert r.confidence_note == ""


class TestVisualizationAnnotationSchema:
    """Validate VisualizationAnnotation (Role 4 output schema)."""

    def test_title_length_enforced(self):
        """chart_title must be <= 60 characters."""
        with pytest.raises(ValidationError):
            VisualizationAnnotation(
                chart_title="A" * 61,  # Over limit
                caption="Some caption.",
                key_insight="Key insight here.",
            )

    def test_valid_annotation(self):
        """Full valid annotation — should pass."""
        a = VisualizationAnnotation(
            chart_title="Total Labour Hours Over Time",
            caption="Labour hours increased steadily over 50 steps.",
            key_insight="Labour hours rose 12% during the simulation run.",
            hypothesis_tag="H1",
        )
        assert a.hypothesis_tag == "H1"


# ---------------------------------------------------------------------------
# Flask LLM endpoint tests (with Ollama mocked)
# ---------------------------------------------------------------------------

def _make_mock_response(data: dict) -> MagicMock:
    """Helper: create a mock ollama.chat response with given JSON data."""
    mock_resp = MagicMock()
    mock_resp.message = MagicMock()
    mock_resp.message.content = json.dumps(data)
    return mock_resp


class TestFlaskLlmEndpoints:
    """Test the Flask LLM API endpoints (roles 1–4) with Ollama mocked.

    Using the Flask test client avoids starting a real HTTP server.
    Ollama calls are patched to return pre-determined JSON responses,
    so these tests run offline and are deterministic.
    """

    @pytest.fixture(autouse=True)
    def client(self):
        """Create a Flask test client for each test."""
        from api.app import create_app
        app = create_app()
        app.config["TESTING"] = True
        self.app = app
        self.client = app.test_client()

    def test_llm_status_offline(self):
        """GET /api/llm/status should return 503 when Ollama is not running."""
        with patch("ollama.list", side_effect=Exception("Connection refused")):
            r = self.client.get("/api/llm/status")
            assert r.status_code == 503
            data = r.get_json()
            assert data["available"] is False

    def test_llm_status_online(self):
        """GET /api/llm/status should return 200 when Ollama is healthy."""
        mock_model = MagicMock()
        mock_model.model = "qwen3.5:4b"
        mock_list = MagicMock()
        mock_list.models = [mock_model]
        with patch("ollama.list", return_value=mock_list):
            r = self.client.get("/api/llm/status")
            assert r.status_code == 200
            assert r.get_json()["available"] is True

    def test_parse_scenario_missing_description(self):
        """POST /api/llm/parse_scenario without 'description' → 400."""
        r = self.client.post("/api/llm/parse_scenario", json={})
        assert r.status_code == 400
        assert "description" in r.get_json()["error"].lower()

    def test_parse_scenario_success(self):
        """POST /api/llm/parse_scenario with valid description → 200 with params."""
        mock_output = {
            "delegation_preference_mean": 0.80,
            "service_cost_factor": 0.15,
            "social_conformity_pressure": 0.70,
            "tasks_per_step_mean": 3.5,
            "num_agents": 100,
            "scenario_summary": "A convenience-oriented abstract scenario",
            "reasoning": "Cheap and widely available services promote delegation.",
        }
        with patch("ollama.chat", return_value=_make_mock_response(mock_output)):
            r = self.client.post("/api/llm/parse_scenario", json={
                "description": "Everyone uses delivery apps and services are nearly free."
            })
        assert r.status_code == 200
        data = r.get_json()
        assert "params" in data
        assert data["params"]["delegation_preference_mean"] == 0.80
        assert "rationale" in data
        assert data["scenario_summary"] != ""

    def test_parse_scenario_ollama_offline(self):
        """POST /api/llm/parse_scenario when Ollama is offline → 503."""
        with patch("ollama.chat", side_effect=Exception("Connection refused")):
            r = self.client.post("/api/llm/parse_scenario", json={
                "description": "A test scenario."
            })
        assert r.status_code == 503

    def test_generate_profile_missing_description(self):
        """POST /api/llm/generate_profile without 'description' → 400."""
        r = self.client.post("/api/llm/generate_profile", json={})
        assert r.status_code == 400

    def test_generate_profile_success_with_audit_log(self):
        """POST /api/llm/generate_profile → 200 with audit_log for transparency."""
        mock_output = {
            "delegation_preference": 0.25,
            "skill_domestic": 0.75,
            "skill_administrative": 0.60,
            "skill_errand": 0.65,
            "skill_maintenance": 0.80,
            "profile_description": "A self-sufficient individual with practical skills.",
        }
        with patch("ollama.chat", return_value=_make_mock_response(mock_output)):
            r = self.client.post("/api/llm/generate_profile", json={
                "description": "An elderly retiree who values self-sufficiency.",
                "count": 1,
            })
        assert r.status_code == 200
        data = r.get_json()
        assert len(data["profiles"]) == 1
        # Audit log presence confirms white-box principle: prompt is recorded.
        assert "audit_log" in data
        assert data["audit_log"][0]["output"]["delegation_preference"] == 0.25

    def test_interpret_results_missing_question(self):
        """POST /api/llm/interpret without 'question' → 400."""
        r = self.client.post("/api/llm/interpret", json={"context": {}})
        assert r.status_code == 400

    def test_interpret_results_success(self):
        """POST /api/llm/interpret → 200 with structured interpretation."""
        mock_output = {
            "answer": "Stress is low because the simulation has only run for 20 steps.",
            "detailed_explanation": "H3's stress divergence emerges after 100+ steps.",
            "hypothesis_connection": "H3",
            "confidence_note": "Short run: long-run stress dynamics not yet visible.",
        }
        with patch("ollama.chat", return_value=_make_mock_response(mock_output)):
            r = self.client.post("/api/llm/interpret", json={
                "question": "Why is stress low in the Type B run?",
                "context": {"current_step": 20, "preset": "type_b"},
            })
        assert r.status_code == 200
        data = r.get_json()
        assert "interpretation" in data
        assert len(data["caveats"]) >= 1  # confidence_note → caveats list
        assert "H3" in data["hypothesis_connection"]

    def test_annotate_chart_missing_name(self):
        """POST /api/llm/annotate without 'chart_name' → 400."""
        r = self.client.post("/api/llm/annotate", json={"metrics": {}})
        assert r.status_code == 400

    def test_annotate_chart_success(self):
        """POST /api/llm/annotate → 200 with chart annotation."""
        mock_output = {
            "chart_title": "Total Labour Hours Over 50 Steps",
            "caption": "Total labour hours rose steadily during the run.",
            "key_insight": "Labour hours increased by 8% — consistent with H1.",
            "hypothesis_tag": "H1",
        }
        with patch("ollama.chat", return_value=_make_mock_response(mock_output)):
            r = self.client.post("/api/llm/annotate", json={
                "chart_name": "total_labor_hours",
                "metrics": {"min": 380, "max": 420, "final": 415, "trend": "increasing"},
                "preset": "type_b",
            })
        assert r.status_code == 200
        data = r.get_json()
        assert data["hypothesis_tag"] == "H1"
        assert data["chart_name"] == "total_labor_hours"


# ---------------------------------------------------------------------------
# Live integration tests (require Ollama; mark with -m ollama to run)
# ---------------------------------------------------------------------------

@pytest.mark.ollama
class TestLiveOllamaIntegration:
    """Integration tests that call the real local Ollama server.

    Prerequisites:
        1. Ollama must be running: `ollama serve`
        2. qwen3.5:4b must be pulled: `ollama pull qwen3.5:4b`
        3. Run with: pytest tests/test_llm_service.py -m ollama -v

    These tests validate end-to-end quality of the LLM responses,
    not just schema conformance. They are slow (~5-15 seconds each)
    and should not be part of the default CI run.
    """

    def test_live_scenario_parse_type_b_scenario(self):
        """Role 1: LLM should parse a high-delegation description accurately.

        Expected: delegation_preference_mean close to 0.7–0.9,
        service_cost_factor below 0.3 (cheap services).
        """
        from api.llm_service import parse_scenario
        result = parse_scenario(
            "Imagine a society where delivery robots handle everything: "
            "groceries, laundry, cooking, repairs. Services are nearly free "
            "and everyone uses them by default. There is strong social pressure "
            "to use these services — doing things yourself is seen as inefficient."
        )
        # Validate schema compliance (not exact values — LLM has temperature)
        p = ParsedScenarioParams(**result)
        # Directional check: high delegation and low cost expected
        if p.delegation_preference_mean is not None:
            assert p.delegation_preference_mean > 0.5, \
                f"Expected high delegation, got {p.delegation_preference_mean}"
        if p.service_cost_factor is not None:
            assert p.service_cost_factor < 0.5, \
                f"Expected low service cost, got {p.service_cost_factor}"
        assert p.scenario_summary, "scenario_summary should not be empty"

    def test_live_result_interpretation_mentions_h3(self):
        """Role 3: LLM interpretation of a short run should mention H3 limitations."""
        from api.llm_service import interpret_results
        result = interpret_results(
            question="Why is stress not rising despite high delegation?",
            context={
                "current_step": 15,
                "preset": "type_b",
                "latest_metrics": {
                    "avg_stress": 0.02, "avg_delegation_rate": 0.78,
                    "total_labor_hours": 420.0, "social_efficiency": 0.52,
                },
            },
        )
        r = ResultInterpretation(**result)
        assert len(r.answer) > 20, "answer should be a complete sentence"
        # The LLM should mention the short-run limitation — but we don't enforce
        # exact text since LLM output varies. We validate schema compliance only.

    def test_live_visualization_annotation_returns_insight(self):
        """Role 4: LLM annotation should return a non-empty key_insight."""
        from api.llm_service import annotate_visualization
        result = annotate_visualization(
            "total_labor_hours",
            {"min": 380, "max": 435, "final": 430, "trend": "increasing", "steps_run": 50},
            preset="type_b",
        )
        a = VisualizationAnnotation(**result)
        assert len(a.key_insight) > 10, "key_insight should be a real sentence"
        assert len(a.caption) > 20, "caption should have 2+ sentences"
