"""tests/test_llm_role_probe.py — End-to-end artifact tests for the probe CLI."""

import json
from argparse import Namespace
from unittest.mock import MagicMock, patch

from analysis.llm_role_probe import run_probe


def _ollama_response(content: str) -> MagicMock:
    """Create a minimal Ollama chat response."""
    response = MagicMock()
    response.message = MagicMock()
    response.message.content = content
    return response


def test_run_probe_writes_manifest_report_and_role_artifacts(tmp_path):
    """The harness should generate manifest, report, and one artifact per role."""
    config_path = tmp_path / "probe_config.json"
    config_path.write_text(json.dumps({
        "shared_mini_simulation": {
            "steps": 3,
            "params": {
                "num_agents": 20,
                "delegation_preference_mean": 0.55,
                "delegation_preference_std": 0.08,
                "service_cost_factor": 0.3,
                "social_conformity_pressure": 0.4,
                "tasks_per_step_mean": 2.5,
                "tasks_per_step_std": 0.5,
                "stress_threshold": 2.5,
                "stress_recovery_rate": 0.1,
                "adaptation_rate": 0.04,
                "initial_available_time": 8.0,
                "network_type": "small_world"
            },
            "preset_label": "Test Probe"
        },
        "role_1": {
            "description": "A moderate delegation test case.",
            "base_params": {
                "num_agents": 20,
                "delegation_preference_mean": 0.5,
                "delegation_preference_std": 0.1,
                "service_cost_factor": 0.4,
                "social_conformity_pressure": 0.3,
                "tasks_per_step_mean": 2.5,
                "tasks_per_step_std": 0.75,
                "stress_threshold": 2.5,
                "stress_recovery_rate": 0.1,
                "adaptation_rate": 0.03,
                "initial_available_time": 8.0,
                "network_type": "small_world"
            },
            "mini_run_steps": 2
        },
        "role_2": {
            "description": "A profile probe case.",
            "decision_probe": {
                "available_time": 3.0,
                "stress_level": 0.3,
                "service_cost_factor": 0.3,
                "tasks": ["domestic", "maintenance"],
                "random_draws": [0.2, 0.8]
            }
        },
        "role_3": {
            "question": "What does this run suggest?",
            "history": []
        },
        "role_4": {
            "chart_name": "total_labor_hours",
            "preset": "custom"
        },
        "role_5": {
            "warmup_steps": 1,
            "forum_fraction": 0.2,
            "group_size": 2,
            "num_turns": 1,
            "model_params": {
                "num_agents": 10,
                "delegation_preference_mean": 0.56,
                "delegation_preference_std": 0.08,
                "service_cost_factor": 0.28,
                "social_conformity_pressure": 0.5,
                "tasks_per_step_mean": 2.4,
                "tasks_per_step_std": 0.5,
                "stress_threshold": 2.5,
                "stress_recovery_rate": 0.1,
                "adaptation_rate": 0.04,
                "initial_available_time": 8.0,
                "network_type": "small_world"
            }
        }
    }), encoding="utf-8")

    args = Namespace(
        roles="all",
        tag="testprobe",
        seed=42,
        output_dir=str(tmp_path / "llm_logs"),
        report_dir=str(tmp_path / "reports"),
        config=str(config_path),
    )

    mock_models = MagicMock()
    mock_models.models = [MagicMock(model="qwen3.5:4b"), MagicMock(model="qwen3:1.7b")]
    responses = [
        _ollama_response(json.dumps({
            "delegation_preference_mean": 0.7,
            "service_cost_factor": 0.2,
            "social_conformity_pressure": 0.5,
            "tasks_per_step_mean": 3.0,
            "num_agents": 100,
            "scenario_summary": "A high-convenience abstract scenario",
            "reasoning": "Affordable services and visible norms raise delegation.",
        })),
        _ollama_response(json.dumps({
            "delegation_preference": 0.65,
            "skill_domestic": 0.45,
            "skill_administrative": 0.8,
            "skill_errand": 0.55,
            "skill_maintenance": 0.35,
            "profile_description": "A convenience-seeking resident with uneven skills.",
        })),
        _ollama_response(json.dumps({
            "answer": "The short run suggests rising delegation pressure without decisive long-run evidence.",
            "detailed_explanation": "Labour remains elevated while stress is still early-stage.",
            "hypothesis_connection": "H1",
            "confidence_note": "This probe is short and intended for inspection rather than inference.",
        })),
        _ollama_response(json.dumps({
            "chart_title": "Total Labour Hours",
            "caption": "Labour hours stay elevated across the short probe. This is consistent with a delegation-heavy setup.",
            "key_insight": "Labour remains elevated in the short run.",
            "hypothesis_tag": "H1",
        })),
        _ollama_response("I use services when time pressure is high."),
        _ollama_response("I would still compare cost before delegating everything."),
        _ollama_response(json.dumps({
            "norm_signal": 0.35,
            "confidence": 0.55,
            "summary": "The pair leans slightly toward delegation under time pressure.",
        })),
    ]

    with patch("ollama.list", return_value=mock_models), patch("ollama.chat", side_effect=responses):
        exit_code = run_probe(args)

    assert exit_code == 0

    run_dirs = list((tmp_path / "llm_logs").iterdir())
    assert len(run_dirs) == 1
    manifest_path = run_dirs[0] / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "completed"
    assert len(manifest["roles_completed"]) == 5

    report_files = list((tmp_path / "reports").glob("*.md"))
    assert len(report_files) == 1
    report_text = report_files[0].read_text(encoding="utf-8")
    assert "LLM Role Probe Report" in report_text
    assert "Role 1 — Scenario Parser" in report_text

    role1_path = run_dirs[0] / "role1_scenario_parser.json"
    role5_path = run_dirs[0] / "role5_agent_forums.json"
    role1_payload = json.loads(role1_path.read_text(encoding="utf-8"))
    role5_payload = json.loads(role5_path.read_text(encoding="utf-8"))
    assert role1_payload["call"]["call_kind"] == "scenario_parser"
    assert len(role5_payload["calls"]) == 3
