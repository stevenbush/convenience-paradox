"""tests/test_narrative_campaign.py — Smoke tests for the narrative campaign runner.

This module validates the new analysis/narrative_campaign.py workflow:
  1. Per-seed aggregation keeps parameter columns as grouping keys.
  2. Threshold-band inference returns a refined delegation band.
  3. A smoke-scale package-A campaign writes the expected artefact structure.

The goal is not to exhaustively test every figure, but to verify that the
campaign pipeline is structurally sound and safe to run from a real script
entry point on the local machine.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from analysis.narrative_campaign import (
    PACKAGE_A,
    PACKAGE_DEFINITIONS,
    RESEARCH_15K_SCALE,
    SMOKE_SCALE,
    _build_threshold_tasks,
    _build_decomposition_tasks,
    _build_experiment_tasks,
    _expand_horizon_experiments,
    _aggregate_per_seed,
    _story_case_replay_rows,
    _story_case_seed_rows,
    _threshold_band_from_atlas,
    build_campaign_plan,
    run_campaign,
)


def test_aggregate_per_seed_keeps_grouping_columns() -> None:
    """Numeric parameter columns should remain grouping keys, not be averaged away."""
    per_seed = pd.DataFrame(
        [
            {
                "package_slug": PACKAGE_A,
                "package_title": "Package A",
                "experiment_slug": "demo",
                "experiment_title": "Demo",
                "scenario_id": "type_a",
                "scenario_label": "Type A",
                "narrative_question": "Question",
                "steps": 60,
                "seed": 0,
                "delegation_preference_mean": 0.25,
                "tail_avg_stress": 0.10,
                "tail_total_labor_hours": 100.0,
                "final_avg_delegation_rate": 0.20,
            },
            {
                "package_slug": PACKAGE_A,
                "package_title": "Package A",
                "experiment_slug": "demo",
                "experiment_title": "Demo",
                "scenario_id": "type_a",
                "scenario_label": "Type A",
                "narrative_question": "Question",
                "steps": 60,
                "seed": 1,
                "delegation_preference_mean": 0.25,
                "tail_avg_stress": 0.30,
                "tail_total_labor_hours": 140.0,
                "final_avg_delegation_rate": 0.40,
            },
        ]
    )

    aggregated = _aggregate_per_seed(per_seed)

    assert len(aggregated) == 1
    assert aggregated.loc[0, "steps"] == 60
    assert aggregated.loc[0, "delegation_preference_mean"] == 0.25
    assert aggregated.loc[0, "tail_avg_stress_mean"] == 0.20
    assert aggregated.loc[0, "tail_total_labor_hours_mean"] == 120.0


def test_threshold_band_from_atlas_returns_refined_values() -> None:
    """Threshold inference should return a compact band centred on sharp changes."""
    atlas = pd.DataFrame(
        [
            {"tasks_per_step_mean": 2.0, "delegation_preference_mean": 0.30, "tail_avg_stress_mean": 0.05},
            {"tasks_per_step_mean": 2.0, "delegation_preference_mean": 0.50, "tail_avg_stress_mean": 0.07},
            {"tasks_per_step_mean": 2.0, "delegation_preference_mean": 0.70, "tail_avg_stress_mean": 0.40},
            {"tasks_per_step_mean": 3.0, "delegation_preference_mean": 0.30, "tail_avg_stress_mean": 0.08},
            {"tasks_per_step_mean": 3.0, "delegation_preference_mean": 0.50, "tail_avg_stress_mean": 0.10},
            {"tasks_per_step_mean": 3.0, "delegation_preference_mean": 0.70, "tail_avg_stress_mean": 0.55},
        ]
    )

    band = _threshold_band_from_atlas(atlas)

    assert len(band) >= 3
    assert min(band) >= 0.05
    assert max(band) <= 0.95
    assert any(abs(value - 0.50) <= 0.10 for value in band)


def test_build_threshold_tasks_preserves_engine_for_research_runs() -> None:
    """Threshold refinement tasks must carry the engine field for worker execution."""
    tasks = _build_threshold_tasks(
        scale=SMOKE_SCALE,
        delegation_band=[0.45, 0.50],
        engine="research_v2",
    )

    assert tasks
    assert {task["engine"] for task in tasks} == {"research_v2"}


def test_research_15k_scale_stays_near_requested_task_budget() -> None:
    """The dedicated 15k scale should stay close to the requested total workload."""
    experiments, story_cases = build_campaign_plan(
        scale=RESEARCH_15K_SCALE,
        packages=list(PACKAGE_DEFINITIONS.keys()),
        engine="research_v2",
    )
    experiments = _expand_horizon_experiments(experiments, RESEARCH_15K_SCALE)

    main_tasks = 0
    decomposition_tasks = 0
    for experiment in experiments:
        if experiment.slug in {"preset_decomposition", "preset_decomposition_v2"}:
            decomposition_tasks += len(
                _build_decomposition_tasks(
                    scale=RESEARCH_15K_SCALE,
                    experiment_slug=experiment.slug,
                    package_slug=experiment.package_slug,
                    engine="research_v2",
                )
            )
            continue
        if experiment.slug.startswith("preset_horizon_scan_"):
            main_tasks += len(experiment.seeds)
            continue
        main_tasks += len(_build_experiment_tasks(experiment, "research_v2"))

    story_seed_tasks = len(_story_case_seed_rows(story_cases, "research_v2"))
    story_replay_tasks = len(_story_case_replay_rows(story_cases, "research_v2"))
    threshold_tasks_est = (
        len(RESEARCH_15K_SCALE.atlas_task_load_values) * 5 * RESEARCH_15K_SCALE.threshold_seeds
    )
    total_est = (
        main_tasks
        + decomposition_tasks
        + story_seed_tasks
        + story_replay_tasks
        + threshold_tasks_est
    )

    assert 14500 <= total_est <= 15500


def test_run_campaign_smoke_package_a_writes_expected_outputs(tmp_path: Path) -> None:
    """A smoke campaign should produce manifests, summaries, figures, and writing support."""
    result = run_campaign(
        scale=SMOKE_SCALE,
        packages=[PACKAGE_A],
        workers=1,
        output_root=tmp_path,
        write_report=False,
    )

    campaign_dir = Path(result["campaign_dir"])
    assert campaign_dir.exists()
    assert (campaign_dir / "manifest.json").exists()
    assert (campaign_dir / "progress.json").exists()
    assert (campaign_dir / "progress.log").exists()
    assert (campaign_dir / "summaries" / "per_seed_summary.csv").exists()
    assert (campaign_dir / "summaries" / "per_seed_summary.partial.csv").exists()
    assert (campaign_dir / PACKAGE_A / "research_summary.csv").exists()
    assert (campaign_dir / PACKAGE_A / "blog_numbers.json").exists()
    assert (campaign_dir / PACKAGE_A / "figure_manifest.json").exists()
    assert (campaign_dir / "writing_support" / "question_to_evidence_crosswalk.md").exists()
    assert (campaign_dir / "writing_support" / "claim_safety_table.md").exists()
    assert (campaign_dir / "writing_support" / "scene_bank.md").exists()

    figures_dir = campaign_dir / PACKAGE_A / "figures"
    assert (figures_dir / "horizon_short.png").exists()
    assert (figures_dir / "horizon_long.png").exists()

    progress = json.loads((campaign_dir / "progress.json").read_text(encoding="utf-8"))
    assert progress["status"] == "completed"
    assert progress["percent_complete"] == 100.0
    assert progress["completed_runs"] == progress["total_runs"]


def test_run_campaign_smoke_package_a_supports_research_engine(tmp_path: Path) -> None:
    """The campaign runner should swap in the research engine without touching dashboard code."""
    result = run_campaign(
        scale=SMOKE_SCALE,
        packages=[PACKAGE_A],
        workers=1,
        output_root=tmp_path,
        write_report=False,
        engine="research_v2",
    )

    campaign_dir = Path(result["campaign_dir"])
    assert campaign_dir.exists()
    assert (campaign_dir / "manifest.json").exists()
    assert Path(result["progress_path"]).exists()
    assert Path(result["progress_log_path"]).exists()

    summary = pd.read_csv(campaign_dir / PACKAGE_A / "research_summary.csv")
    assert "engine" in summary.columns
    assert set(summary["engine"]) == {"research_v2"}
    assert "tail_backlog_tasks_mean" in summary.columns
    assert "tail_delegation_match_rate_mean" in summary.columns
    assert "tail_delegation_labor_delta_mean" in summary.columns
