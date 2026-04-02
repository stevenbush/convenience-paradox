"""tests/test_llm_service_audit.py — Recorder integration tests for Roles 1–4."""

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from api.llm_audit import LlmAuditRecorder
from api.llm_service import generate_agent_profile, interpret_results, parse_scenario


def _mock_chat_response(data: dict) -> MagicMock:
    """Create an Ollama mock response with JSON content."""
    response = MagicMock()
    response.message = MagicMock()
    response.message.content = json.dumps(data)
    return response


def test_parse_scenario_records_successful_audit_call(tmp_path):
    """Role 1 should emit one successful recorder entry with schema metadata."""
    recorder = LlmAuditRecorder(run_id="probe-role1", output_dir=tmp_path)
    payload = {
        "delegation_preference_mean": 0.72,
        "service_cost_factor": 0.22,
        "social_conformity_pressure": 0.51,
        "tasks_per_step_mean": 2.8,
        "num_agents": 100,
        "scenario_summary": "A moderately high-delegation abstract scenario",
        "reasoning": "Affordable services and visible peer behaviour raise delegation.",
    }

    with patch("ollama.chat", return_value=_mock_chat_response(payload)):
        result = parse_scenario("A test scenario.", recorder=recorder)

    calls = recorder.get_calls("role_1")
    assert result["delegation_preference_mean"] == 0.72
    assert len(calls) == 1
    assert calls[0]["call_kind"] == "scenario_parser"
    assert calls[0]["schema_validation"]["valid"] is True
    assert calls[0]["raw_response"] is not None


def test_generate_agent_profile_records_schema_failure(tmp_path):
    """Role 2 should record schema-invalid output before raising ValidationError."""
    recorder = LlmAuditRecorder(run_id="probe-role2", output_dir=tmp_path)
    invalid_payload = {
        "delegation_preference": 1.4,
        "skill_domestic": 0.75,
        "skill_administrative": 0.65,
        "skill_errand": 0.60,
        "skill_maintenance": 0.55,
        "profile_description": "Invalid profile for schema testing.",
    }

    with patch("ollama.chat", return_value=_mock_chat_response(invalid_payload)):
        with pytest.raises(ValidationError):
            generate_agent_profile("A test persona.", recorder=recorder)

    calls = recorder.get_calls("role_2")
    assert len(calls) == 1
    assert calls[0]["call_kind"] == "profile_generator"
    assert calls[0]["schema_validation"]["valid"] is False
    assert "delegation_preference" in calls[0]["schema_validation"]["error"]


def test_parse_scenario_records_connection_error(tmp_path):
    """Role 1 should capture connection failures in the recorder."""
    recorder = LlmAuditRecorder(run_id="probe-role1-error", output_dir=tmp_path)

    with patch("ollama.chat", side_effect=Exception("Connection refused")):
        with pytest.raises(RuntimeError):
            parse_scenario("A failing scenario.", recorder=recorder)

    calls = recorder.get_calls("role_1")
    assert len(calls) == 1
    assert calls[0]["error"]["message"] == "Connection refused"


def test_interpret_results_accepts_analysis_alias(tmp_path):
    """Role 3 should recover when the model returns `analysis` instead of `answer`."""
    recorder = LlmAuditRecorder(run_id="probe-role3-alias", output_dir=tmp_path)
    alias_payload = {
        "analysis": "This short run suggests mild delegation pressure without strong stress growth yet.",
        "details": "The system remains early-stage, so long-run claims would be premature.",
        "hypothesis": "H3",
        "caveat": "This is a short probe run.",
    }

    with patch("ollama.chat", return_value=_mock_chat_response(alias_payload)):
        result = interpret_results(
            "What does this run suggest?",
            {"current_step": 6, "preset": "custom"},
            recorder=recorder,
        )

    assert result["answer"].startswith("This short run suggests")
    assert result["detailed_explanation"].startswith("The system remains")
    assert result["hypothesis_connection"] == "H3"
    assert result["confidence_note"] == "This is a short probe run."
