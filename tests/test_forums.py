"""tests/test_forums.py — Recorder integration tests for the experimental forum role."""

import json
from unittest.mock import MagicMock, patch

from api.llm_audit import LlmAuditRecorder
from model.forums import run_forum_step
from model.model import ConvenienceParadoxModel


def _message_response(content: str) -> MagicMock:
    """Create a simple Ollama response object."""
    response = MagicMock()
    response.message = MagicMock()
    response.message.content = content
    return response


def test_run_forum_step_records_dialogue_and_updates(tmp_path):
    """Role 5 should log each dialogue turn and the extracted forum outcome."""
    recorder = LlmAuditRecorder(run_id="probe-role5", output_dir=tmp_path)
    model = ConvenienceParadoxModel(num_agents=10, seed=42)

    responses = [
        _message_response("I delegate routine chores when time gets tight."),
        _message_response("I still prefer doing some tasks myself if the cost is high."),
        _message_response(json.dumps({
            "norm_signal": 0.4,
            "confidence": 0.5,
            "summary": "The group leans mildly toward delegation when time pressure is high.",
        })),
    ]

    with patch("ollama.chat", side_effect=responses):
        session = run_forum_step(
            model,
            forum_fraction=0.2,
            group_size=2,
            num_turns=1,
            recorder=recorder,
            rng_seed=123,
        )

    calls = recorder.get_calls("role_5")
    assert len(session.groups) == 1
    assert len(calls) == 3
    assert calls[0]["call_kind"] == "forum_dialogue_turn"
    assert calls[-1]["call_kind"] == "forum_outcome_extraction"
    assert calls[-1]["schema_validation"]["valid"] is True
    assert len(session.groups[0].preference_updates) == 2
    assert session.groups[0].delta_applied > 0
