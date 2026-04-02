"""analysis/llm_role_probe.py — CLI Harness for Inspecting All Five LLM Roles

Architecture role:
    This script runs one compact, reproducible probe for each LLM role used in
    the project and writes role-level JSON artifacts plus a human-readable
    Markdown report. The focus is manual inspection of prompts, raw outputs,
    parsed outputs, and visible downstream effects.

How to run:
    eval "$(conda shell.zsh hook)" && conda activate convenience-paradox
    python analysis/llm_role_probe.py --roles all --tag baseline --seed 42

Artifacts:
    data/results/llm_logs/<run_id>/         — structured JSON role artifacts
    analysis/reports/YYYY-MM-DD_<tag>.md    — human-readable summary report
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure project root is importable when run directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.llm_audit import LlmAuditRecorder, make_json_safe
from api.llm_service import (
    annotate_visualization,
    generate_agent_profile,
    get_llm_status,
    interpret_results,
    parse_scenario,
)
from api.schemas import SimulationParams
from model.agents import Task
from model.forums import format_session_for_api, run_forum_step
from model.model import ConvenienceParadoxModel
from model.params import TASK_TYPES


ROLE_DEFINITIONS = {
    "role_1": {
        "label": "Role 1 — Scenario Parser",
        "slug": "role1_scenario_parser",
    },
    "role_2": {
        "label": "Role 2 — Agent Profile Generator",
        "slug": "role2_agent_profile",
    },
    "role_3": {
        "label": "Role 3 — Result Interpreter",
        "slug": "role3_result_interpreter",
    },
    "role_4": {
        "label": "Role 4 — Visualization Annotator",
        "slug": "role4_visualization_annotator",
    },
    "role_5": {
        "label": "Role 5 — Agent Forums",
        "slug": "role5_agent_forums",
    },
}


@dataclass
class RoleRunResult:
    """One role's outcome within the probe harness."""

    role: str
    label: str
    status: str
    artifact_path: str | None
    error: str | None = None


class _FixedRandom:
    """Minimal deterministic RNG for the controlled decision probe."""

    def __init__(self, values: list[float]) -> None:
        self._values = list(values)
        self._index = 0

    def random(self) -> float:
        if self._index >= len(self._values):
            return self._values[-1]
        value = self._values[self._index]
        self._index += 1
        return value


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the LLM role probe harness."""
    default_config = PROJECT_ROOT / "analysis" / "configs" / "llm_role_probe_baseline.json"
    default_output_root = PROJECT_ROOT / "data" / "results" / "llm_logs"
    default_report_root = PROJECT_ROOT / "analysis" / "reports"

    parser = argparse.ArgumentParser(description="Run a small probe across all five LLM roles.")
    parser.add_argument("--roles", default="all", help="all or comma-separated role numbers, e.g. 1,3,5")
    parser.add_argument("--tag", default="baseline", help="Short run tag used in filenames.")
    parser.add_argument("--seed", type=int, default=42, help="Seed for deterministic probe setup.")
    parser.add_argument("--output-dir", default=str(default_output_root), help="Root dir for JSON artifacts.")
    parser.add_argument("--report-dir", default=str(default_report_root), help="Dir for Markdown reports.")
    parser.add_argument("--config", default=str(default_config), help="Probe config JSON path.")
    return parser.parse_args()


def parse_roles(value: str) -> list[str]:
    """Expand a role selector into canonical role keys."""
    if value.strip().lower() == "all":
        return list(ROLE_DEFINITIONS.keys())

    role_keys = []
    for item in value.split(","):
        item = item.strip()
        role_key = f"role_{item}"
        if role_key not in ROLE_DEFINITIONS:
            raise ValueError(f"Unsupported role selector: '{item}'")
        role_keys.append(role_key)
    return role_keys


def load_config(path: str | Path) -> dict[str, Any]:
    """Load the JSON probe configuration."""
    config_path = Path(path)
    return json.loads(config_path.read_text(encoding="utf-8"))


def build_run_id(tag: str, seed: int, started_at: datetime) -> str:
    """Create a deterministic, readable run identifier."""
    return f"{started_at.strftime('%Y%m%d_%H%M%S')}_{tag}_seed{seed}"


def run_model_steps(params: dict[str, Any], steps: int, seed: int) -> ConvenienceParadoxModel:
    """Initialise a model and advance it for a fixed number of steps."""
    model_params = dict(params)
    model_params.setdefault("seed", seed)
    model = ConvenienceParadoxModel(**model_params)
    for _ in range(steps):
        model.step()
    return model


def summarise_model(model: ConvenienceParadoxModel) -> dict[str, Any]:
    """Extract a compact, JSON-friendly simulation summary."""
    model_df = model.get_model_dataframe()
    last_row = model_df.iloc[-1].to_dict()
    return {
        "current_step": model.current_step,
        "params": model.get_params(),
        "latest_metrics": {k: round(float(v), 6) for k, v in last_row.items()},
        "recent_time_series": _recent_time_series(model_df, n=3),
    }


def _recent_time_series(model_df: Any, n: int = 3) -> list[dict[str, Any]]:
    """Return the last few time-series rows for interpretive context."""
    rows = []
    df_reset = model_df.reset_index()
    step_column = "Step" if "Step" in df_reset.columns else df_reset.columns[0]
    for _, row in df_reset.tail(n).iterrows():
        item = {"step": int(row[step_column])}
        for key, value in row.items():
            if key == step_column:
                continue
            item[key] = round(float(value), 6)
        rows.append(item)
    return rows


def compute_chart_metrics(model: ConvenienceParadoxModel, chart_name: str) -> dict[str, Any]:
    """Derive chart summary statistics used by Role 4."""
    df = model.get_model_dataframe()
    if chart_name not in df.columns:
        raise ValueError(f"Chart metric '{chart_name}' not found in model dataframe.")

    values = [float(v) for v in df[chart_name].tolist()]
    trend = "increasing" if values[-1] > values[0] + 0.01 else (
        "decreasing" if values[-1] < values[0] - 0.01 else "stable"
    )
    return {
        "min": round(min(values), 6),
        "max": round(max(values), 6),
        "final": round(values[-1], 6),
        "trend": trend,
        "steps_run": len(values) - 1,
    }


def role_review_checklist(status: str, calls: list[dict[str, Any]], downstream_effect: Any) -> dict[str, Any]:
    """Build a lightweight manual-review checklist for one role."""
    response_present = any(bool(call.get("raw_response")) for call in calls)
    schema_checks = [call.get("schema_validation", {}).get("valid") for call in calls if call.get("schema_validation")]
    schema_valid = all(schema_checks) if schema_checks else None
    effect_visible = status == "ok" and downstream_effect is not None
    return {
        "response_present": response_present,
        "schema_valid": schema_valid,
        "effect_visible": effect_visible,
        "appears_meaningful": "manual_review",
    }


def run_role_1(config: dict[str, Any], seed: int, recorder: LlmAuditRecorder) -> dict[str, Any]:
    """Probe Role 1 and show the parsed parameters' impact on a short run."""
    role_config = config["role_1"]
    parsed = parse_scenario(role_config["description"], recorder=recorder)

    base_params = dict(role_config["base_params"])
    applied_overrides = {
        key: value
        for key, value in parsed.items()
        if key in base_params and value is not None
    }
    validated = SimulationParams(**{**base_params, **applied_overrides})
    model = run_model_steps(validated.to_model_kwargs(), role_config["mini_run_steps"], seed)
    downstream_effect = {
        "base_params": base_params,
        "applied_overrides": applied_overrides,
        "final_params": validated.model_dump(),
        "simulation_summary": summarise_model(model),
    }
    return {
        "input": {"description": role_config["description"]},
        "parsed_output": parsed,
        "downstream_effect": downstream_effect,
    }


def _role2_effective_probability(agent: Any, task: Task) -> dict[str, Any]:
    """Mirror the explicit decision-rule components for reporting."""
    proficiency = agent.skill_set.get(task.task_type, 0.4)
    task_time = task.time_cost_for(proficiency)
    forced_delegation = agent.available_time < task_time * 0.5
    stress_boost = agent.stress_level * 0.30
    skill_gap = task.skill_requirement - proficiency
    skill_factor = skill_gap * 0.25
    cost_penalty = agent.model.service_cost_factor * 0.25
    effective_probability = max(
        0.0,
        min(1.0, agent.delegation_preference + stress_boost + skill_factor - cost_penalty),
    )
    return {
        "proficiency": round(proficiency, 6),
        "task_time": round(task_time, 6),
        "forced_delegation": forced_delegation,
        "effective_probability": round(effective_probability, 6),
    }


def run_role_2(config: dict[str, Any], seed: int, recorder: LlmAuditRecorder) -> dict[str, Any]:
    """Probe Role 2 with a fixed task bundle and deterministic draws."""
    role_config = config["role_2"]
    probe_config = role_config["decision_probe"]
    profile = generate_agent_profile(role_config["description"], recorder=recorder)

    model = ConvenienceParadoxModel(num_agents=20, seed=seed)
    model.service_cost_factor = float(probe_config["service_cost_factor"])
    agent = list(model.agents)[0]
    agent.delegation_preference = float(profile["delegation_preference"])
    agent.skill_set = {
        "domestic": float(profile["skill_domestic"]),
        "administrative": float(profile["skill_administrative"]),
        "errand": float(profile["skill_errand"]),
        "maintenance": float(profile["skill_maintenance"]),
    }
    agent.available_time = float(probe_config["available_time"])
    agent.stress_level = float(probe_config["stress_level"])

    decision_rows = []
    draws = list(probe_config["random_draws"])
    original_random = agent.model.random
    probe_random = _FixedRandom(draws)
    agent.model.random = probe_random
    try:
        for idx, task_type in enumerate(probe_config["tasks"]):
            task = Task(
                task_type=task_type,
                base_time=TASK_TYPES[task_type]["base_time"],
                skill_requirement=TASK_TYPES[task_type]["skill_requirement"],
                requester_id=agent.unique_id,
            )
            components = _role2_effective_probability(agent, task)
            random_draw = draws[idx]
            delegated = agent._should_delegate(task)
            decision_rows.append({
                "task_type": task_type,
                "random_draw": random_draw,
                "delegated": delegated,
                **components,
            })
    finally:
        agent.model.random = original_random

    downstream_effect = {
        "probe_state": {
            "available_time": agent.available_time,
            "stress_level": agent.stress_level,
            "service_cost_factor": model.service_cost_factor,
        },
        "decision_probe_results": decision_rows,
    }
    return {
        "input": {
            "description": role_config["description"],
            "decision_probe": probe_config,
        },
        "parsed_output": profile,
        "downstream_effect": downstream_effect,
    }


def build_shared_role3_context(config: dict[str, Any], seed: int) -> tuple[ConvenienceParadoxModel, dict[str, Any]]:
    """Run the shared mini-simulation used by Roles 3 and 4."""
    shared_config = config["shared_mini_simulation"]
    model = run_model_steps(shared_config["params"], shared_config["steps"], seed)
    summary = summarise_model(model)
    context = {
        "current_step": summary["current_step"],
        "preset": shared_config.get("preset_label", "custom"),
        "params_summary": summary["params"],
        "latest_metrics": summary["latest_metrics"],
        "recent_time_series": summary["recent_time_series"],
    }
    return model, context


def run_role_3(
    config: dict[str, Any],
    shared_context: dict[str, Any],
    recorder: LlmAuditRecorder,
) -> dict[str, Any]:
    """Probe Role 3 against the shared short-run simulation context."""
    role_config = config["role_3"]
    interpretation = interpret_results(
        role_config["question"],
        shared_context,
        role_config.get("history", []),
        recorder=recorder,
    )
    return {
        "input": {
            "question": role_config["question"],
            "context": shared_context,
            "history": role_config.get("history", []),
        },
        "parsed_output": interpretation,
        "downstream_effect": {
            "context_used": shared_context,
            "interpretation_fields": list(interpretation.keys()),
        },
    }


def run_role_4(
    config: dict[str, Any],
    shared_model: ConvenienceParadoxModel,
    recorder: LlmAuditRecorder,
) -> dict[str, Any]:
    """Probe Role 4 against a chart derived from the shared simulation."""
    role_config = config["role_4"]
    metrics = compute_chart_metrics(shared_model, role_config["chart_name"])
    annotation = annotate_visualization(
        role_config["chart_name"],
        metrics,
        preset=role_config.get("preset"),
        recorder=recorder,
    )
    return {
        "input": {
            "chart_name": role_config["chart_name"],
            "chart_metrics": metrics,
            "preset": role_config.get("preset"),
        },
        "parsed_output": annotation,
        "downstream_effect": {
            "chart_metrics_used": metrics,
            "annotation_targets_chart": role_config["chart_name"],
        },
    }


def run_role_5(config: dict[str, Any], seed: int, recorder: LlmAuditRecorder) -> dict[str, Any]:
    """Probe Role 5 with one tiny reproducible forum session."""
    role_config = config["role_5"]
    forum_model = ConvenienceParadoxModel(**role_config["model_params"], seed=seed)
    for _ in range(int(role_config["warmup_steps"])):
        forum_model.step()

    session = run_forum_step(
        forum_model,
        forum_fraction=float(role_config["forum_fraction"]),
        group_size=int(role_config["group_size"]),
        num_turns=int(role_config["num_turns"]),
        recorder=recorder,
        rng_seed=seed,
    )
    formatted = format_session_for_api(session)
    return {
        "input": {
            "warmup_steps": role_config["warmup_steps"],
            "forum_fraction": role_config["forum_fraction"],
            "group_size": role_config["group_size"],
            "num_turns": role_config["num_turns"],
            "model_params": forum_model.get_params(),
        },
        "parsed_output": {
            "forum_session_summary": {
                "step": formatted["step"],
                "n_agents_participating": formatted["n_agents_participating"],
                "total_norm_updates": formatted["total_norm_updates"],
            }
        },
        "downstream_effect": {
            "forum_session": formatted,
        },
    }


def write_role_artifact(
    recorder: LlmAuditRecorder,
    role_key: str,
    role_payload: dict[str, Any],
    status: str,
    error: str | None = None,
) -> Path:
    """Write one role artifact file, including the captured LLM calls."""
    role_meta = ROLE_DEFINITIONS[role_key]
    calls = recorder.get_calls(role_key)
    payload = {
        "role": role_meta["label"],
        "status": status,
        "input": role_payload.get("input"),
        "parsed_output": role_payload.get("parsed_output"),
        "downstream_effect": role_payload.get("downstream_effect"),
        "review_checklist": role_review_checklist(
            status,
            calls,
            role_payload.get("downstream_effect"),
        ),
        "error": error,
    }
    return recorder.write_role_artifact(
        role=role_key,
        filename=f"{role_meta['slug']}.json",
        payload=payload,
    )


def generate_report(
    *,
    run_id: str,
    tag: str,
    seed: int,
    config_path: Path,
    output_dir: Path,
    report_path: Path,
    roles: list[RoleRunResult],
) -> None:
    """Render a concise Markdown report for manual review."""
    lines = [
        "# LLM Role Probe Report",
        "",
        f"**Date**: {datetime.now().strftime('%Y-%m-%d')}  ",
        f"**Run ID**: `{run_id}`  ",
        f"**Tag**: `{tag}`  ",
        f"**Seed**: `{seed}`  ",
        f"**Config**: `{config_path}`  ",
        f"**JSON Artifacts**: `{output_dir}`  ",
        "",
        "## Role Status",
        "",
        "| Role | Status | Artifact |",
        "|---|---|---|",
    ]

    for item in roles:
        artifact = item.artifact_path or "-"
        lines.append(f"| {item.label} | {item.status} | `{artifact}` |")

    for item in roles:
        artifact_payload = {}
        if item.artifact_path:
            artifact_payload = json.loads(Path(item.artifact_path).read_text(encoding="utf-8"))
        lines.extend([
            "",
            f"## {item.label}",
            "",
            f"- Status: `{item.status}`",
            f"- Artifact: `{item.artifact_path or '-'}`",
        ])
        if item.error:
            lines.append(f"- Error: `{item.error}`")
        lines.extend([
            "",
            "### Input",
            "",
            "```json",
            _render_json_snippet(artifact_payload.get("input")),
            "```",
            "",
            "### Parsed Output",
            "",
            "```json",
            _render_json_snippet(artifact_payload.get("parsed_output")),
            "```",
            "",
            "### Downstream Effect",
            "",
            "```json",
            _render_json_snippet(artifact_payload.get("downstream_effect")),
            "```",
            "",
            "### Manual Review Checklist",
            "",
            "- [ ] response present",
            "- [ ] schema-valid",
            "- [ ] effect visible",
            "- [ ] appears meaningful",
        ])

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _render_json_snippet(payload: Any, max_chars: int = 1600) -> str:
    """Render a compact JSON snippet for the Markdown report."""
    text = json.dumps(make_json_safe(payload), indent=2, ensure_ascii=False)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n... [truncated]"


def run_probe(args: argparse.Namespace) -> int:
    """Run the selected role probes and write artifacts."""
    config_path = Path(args.config)
    config = load_config(config_path)
    selected_roles = parse_roles(args.roles)

    started_at = datetime.now()
    run_id = build_run_id(args.tag, args.seed, started_at)
    output_root = Path(args.output_dir)
    output_dir = output_root / run_id
    report_dir = Path(args.report_dir)
    report_path = report_dir / f"{started_at.strftime('%Y-%m-%d')}_llm_role_probe_{args.tag}.md"
    recorder = LlmAuditRecorder(run_id=run_id, output_dir=output_dir)

    llm_status = get_llm_status()
    manifest = {
        "run_id": run_id,
        "tag": args.tag,
        "seed": args.seed,
        "config_path": str(config_path),
        "started_at": started_at.isoformat(timespec="seconds"),
        "output_dir": str(output_dir),
        "report_path": str(report_path),
        "roles_requested": selected_roles,
        "llm_status": llm_status,
    }

    if not llm_status.get("available"):
        manifest["status"] = "aborted_ollama_unavailable"
        recorder.write_json("manifest.json", manifest)
        generate_report(
            run_id=run_id,
            tag=args.tag,
            seed=args.seed,
            config_path=config_path,
            output_dir=output_dir,
            report_path=report_path,
            roles=[],
        )
        print(f"LLM role probe aborted. Ollama unavailable. Manifest: {output_dir / 'manifest.json'}")
        print(f"Report: {report_path}")
        return 1

    shared_model = None
    shared_context = None
    if any(role in selected_roles for role in ("role_3", "role_4")):
        shared_model, shared_context = build_shared_role3_context(config, args.seed)

    role_results: list[RoleRunResult] = []

    for role_key in selected_roles:
        role_meta = ROLE_DEFINITIONS[role_key]
        try:
            if role_key == "role_1":
                payload = run_role_1(config, args.seed, recorder)
            elif role_key == "role_2":
                payload = run_role_2(config, args.seed, recorder)
            elif role_key == "role_3":
                payload = run_role_3(config, shared_context, recorder)
            elif role_key == "role_4":
                payload = run_role_4(config, shared_model, recorder)
            else:
                payload = run_role_5(config, args.seed, recorder)

            artifact_path = write_role_artifact(recorder, role_key, payload, status="ok")
            role_results.append(RoleRunResult(
                role=role_key,
                label=role_meta["label"],
                status="ok",
                artifact_path=str(artifact_path),
            ))
        except Exception as e:
            artifact_path = write_role_artifact(
                recorder,
                role_key,
                {"input": config.get(role_key), "parsed_output": None, "downstream_effect": None},
                status="error",
                error=str(e),
            )
            role_results.append(RoleRunResult(
                role=role_key,
                label=role_meta["label"],
                status="error",
                artifact_path=str(artifact_path),
                error=str(e),
            ))

    manifest["status"] = "completed"
    manifest["roles_completed"] = [
        {
            "role": result.role,
            "label": result.label,
            "status": result.status,
            "artifact_path": result.artifact_path,
            "error": result.error,
        }
        for result in role_results
    ]
    recorder.write_json("manifest.json", manifest)

    generate_report(
        run_id=run_id,
        tag=args.tag,
        seed=args.seed,
        config_path=config_path,
        output_dir=output_dir,
        report_path=report_path,
        roles=role_results,
    )

    print(f"LLM role probe complete. Run ID: {run_id}")
    print(f"Manifest: {output_dir / 'manifest.json'}")
    print(f"Report: {report_path}")
    for result in role_results:
        detail = f" | error: {result.error}" if result.error else ""
        print(f"- {result.label}: {result.status} | artifact: {result.artifact_path}{detail}")
    return 0


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()
    return run_probe(args)


if __name__ == "__main__":
    raise SystemExit(main())
