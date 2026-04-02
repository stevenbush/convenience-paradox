"""tests/test_llm_audit.py — Unit tests for the shared LLM audit recorder."""

import json

from api.llm_audit import LlmAuditRecorder


def test_recorder_writes_role_artifact_with_call(tmp_path):
    """A recorded call should be embedded into the persisted role artifact."""
    recorder = LlmAuditRecorder(run_id="probe-1", output_dir=tmp_path)
    recorder.record_call(
        role="role_1",
        call_kind="scenario_parser",
        model="qwen3.5:4b",
        think=False,
        system_prompt="system prompt",
        user_prompt="user prompt",
        raw_response='{"value": 1}',
        parsed_output={"value": 1},
        schema_validation={"schema": "ParsedScenarioParams", "valid": True, "error": None},
        elapsed_seconds=0.12,
    )

    artifact_path = recorder.write_role_artifact(
        role="role_1",
        filename="role1.json",
        payload={
            "role": "Role 1 — Scenario Parser",
            "status": "ok",
            "downstream_effect": {"final_metric": 0.5},
        },
    )

    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "probe-1"
    assert payload["status"] == "ok"
    assert payload["call"]["call_kind"] == "scenario_parser"
    assert payload["call"]["parsed_output"]["value"] == 1
    assert payload["downstream_effect"]["final_metric"] == 0.5
