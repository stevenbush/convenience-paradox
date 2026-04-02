"""analysis/formal_campaign_report.py — Formal research report builder.

Architecture role:
    This module turns an existing narrative-campaign output directory into a
    paper-style research report package. It does not run new simulations.
    Instead, it reads the persisted campaign summaries, selected story-case
    traces, and writing-support notes, then writes:

      - report-specific figures (PNG + SVG)
      - compact source CSV files for each figure and table
      - a manifest describing provenance
      - one English Markdown report
      - one Chinese Markdown translation

Why this file exists:
    The repository already contains campaign runners and compact narrative
    summaries. What is missing is a reproducible, more formal analysis layer
    that packages the same evidence into a white-box research report that is
    suitable for portfolio review and later downstream writing.

Design constraints:
    - The script must remain post hoc only: it reads campaign outputs and
      never reruns the model.
    - Committed wording must stay abstract (`Type A` / `Type B` only).
    - Every figure and table must have a saved source CSV so the report can be
      audited and selectively reused later.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import textwrap
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / "data" / "results" / ".mplconfig"))

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Use a headless backend so the script is safe in CLI and CI contexts.
matplotlib.use("Agg")
REPORTS_DIR = PROJECT_ROOT / "analysis" / "reports"

logger = logging.getLogger(__name__)

PACKAGE_A = "package_a_everyday_friction"
PACKAGE_B = "package_b_convenience_transfer"
PACKAGE_C = "package_c_cheap_service_trap"
PACKAGE_D = "package_d_norm_lock_in"

COLORS = {
    "type_a": "#2166AC",
    "type_b": "#D6604D",
    "threshold": "#B2182B",
    "neutral": "#666666",
    "provider": "#1B9E77",
    "coordination": "#E6AB02",
    "backlog": "#762A83",
    "grid": "#DDDDDD",
    "soft_fill": "#F6F6F6",
}


@dataclass(frozen=True)
class ReportOutputs:
    """Paths returned by the formal report pipeline."""

    campaign_dir: Path
    asset_root: Path
    manifest_path: Path
    english_report_path: Path
    chinese_report_path: Path


def _ensure_dir(path: Path) -> Path:
    """Create a directory if needed and return it."""

    path.mkdir(parents=True, exist_ok=True)
    return path


def _read_text(path: Path) -> str:
    """Read UTF-8 text from disk."""

    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    """Write UTF-8 text with a trailing newline."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")


def _save_csv(df: pd.DataFrame, path: Path) -> Path:
    """Persist a compact CSV source table for later audit."""

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def _save_figure(fig: plt.Figure, png_path: Path, svg_path: Path) -> None:
    """Save one figure in both PNG and SVG formats."""

    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    plt.close(fig)


def _markdown_table(df: pd.DataFrame) -> str:
    """Render a compact GitHub-flavored Markdown table without extra deps."""

    string_df = df.fillna("").astype(str)
    headers = list(string_df.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in string_df.iterrows():
        lines.append("| " + " | ".join(row.tolist()) + " |")
    return "\n".join(lines)


def _fmt_num(value: float, digits: int = 3) -> str:
    """Format a float for report tables and prose."""

    if pd.isna(value):
        return "NA"
    return f"{value:.{digits}f}"


def _fmt_pct(value: float, digits: int = 1) -> str:
    """Format a percentage value."""

    if pd.isna(value):
        return "NA"
    return f"{value:.{digits}f}%"


def _link_relative(from_path: Path, target_path: Path, label: str) -> str:
    """Create a Markdown link with a filesystem-relative path."""

    rel_str = os.path.relpath(
        target_path.resolve(),
        start=from_path.resolve().parent,
    ).replace(os.sep, "/")
    return f"[{label}](<{rel_str}>)"


def _markdown_image(from_path: Path, target_path: Path, alt_text: str) -> str:
    """Create a Markdown image reference."""

    rel_str = os.path.relpath(
        target_path.resolve(),
        start=from_path.resolve().parent,
    ).replace(os.sep, "/")
    return f"![{alt_text}](<{rel_str}>)"


def _load_inputs(campaign_dir: Path) -> dict[str, object]:
    """Load all persisted campaign inputs required by the report builder.

    Args:
        campaign_dir: Existing narrative-campaign output directory.

    Returns:
        Dictionary of DataFrames and support texts.
    """

    summaries_dir = campaign_dir / "summaries"
    inputs = {
        "manifest": json.loads(_read_text(campaign_dir / "manifest.json")),
        "combo_summary": pd.read_csv(summaries_dir / "combo_summary.csv"),
        "per_seed_summary": pd.read_csv(summaries_dir / "per_seed_summary.csv"),
        "threshold_refinement": pd.read_csv(summaries_dir / "threshold_refinement_per_seed.csv"),
        "preset_decomposition": pd.read_csv(summaries_dir / "preset_decomposition_per_seed.csv"),
        "story_case_selection": pd.read_csv(summaries_dir / "story_case_selection.csv"),
        "claim_safety_text": _read_text(campaign_dir / "writing_support" / "claim_safety_table.md"),
        "crosswalk_text": _read_text(campaign_dir / "writing_support" / "question_to_evidence_crosswalk.md"),
        "scene_bank_text": _read_text(campaign_dir / "writing_support" / "scene_bank.md"),
        "research_design_text": _read_text(PROJECT_ROOT / "docs" / "ConvenienceParadoxResearchModel_design.en.md"),
    }
    return inputs


def _parse_claim_safety_table(text: str) -> pd.DataFrame:
    """Parse the simple heading-plus-bullets safety note into a table."""

    rows: list[dict[str, str]] = []
    section = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if line.startswith("- "):
            rows.append({
                "claim_status": section,
                "statement": line[2:].strip(),
            })
    return pd.DataFrame(rows)


def _question_hypothesis_mapping() -> pd.DataFrame:
    """Build the report's central question/hypothesis mapping table."""

    return pd.DataFrame(
        [
            {
                "research_question": "Do stable everyday frictions signal a deeper time-allocation architecture?",
                "hypothesis": "H3 (partial)",
                "package": "Package A",
                "primary_metrics": "tail_total_labor_hours, tail_avg_stress, final_available_time_mean, tail_tasks_delegated_frac",
                "analysis_role": "Long-horizon baseline comparison",
            },
            {
                "research_question": "Does convenience eliminate labor or relocate it inside the system?",
                "hypothesis": "H1 (strong), H2 (strong)",
                "package": "Package B",
                "primary_metrics": "self_labor_hours, service_labor_hours, delegation_coordination_hours, tail_backlog_tasks, tail_delegation_labor_delta",
                "analysis_role": "Labor-transfer decomposition and threshold mapping",
            },
            {
                "research_question": "How much can low service price explain by itself?",
                "hypothesis": "H2 (strong contextual support)",
                "package": "Package C",
                "primary_metrics": "tail_avg_stress, tail_backlog_tasks, tail_tasks_delegated_frac, tail_total_labor_hours",
                "analysis_role": "Context scan and cost-flip analysis",
            },
            {
                "research_question": "Do mixed systems drift toward extremes under norm pressure?",
                "hypothesis": "H4 (partial, important negative result)",
                "package": "Package D",
                "primary_metrics": "final_avg_delegation_rate, final_avg_delegation_rate_std, tail_backlog_tasks",
                "analysis_role": "Mixed-state dispersion and stability assessment",
            },
        ]
    )


def _stable_vs_research_delta_table() -> pd.DataFrame:
    """Summarize what changed between the stable and research engines."""

    return pd.DataFrame(
        [
            {
                "mechanism": "Unmatched delegated work",
                "stable_model": "Counted as unmatched but does not return as next-step work",
                "research_model": "Returns to requester carryover backlog",
                "why_it_matters": "Makes overload cumulative instead of purely retrospective",
            },
            {
                "mechanism": "Provider eligibility",
                "stable_model": "Loose matching threshold",
                "research_model": "Provider must have enough remaining time for the full service",
                "why_it_matters": "Makes supply tightness observable",
            },
            {
                "mechanism": "Requester-side delegation friction",
                "stable_model": "Implicit only",
                "research_model": "Explicit coordination-time cost",
                "why_it_matters": "Prevents delegation from looking costless to the requester",
            },
            {
                "mechanism": "Provider-side service friction",
                "stable_model": "Simpler provider service timing",
                "research_model": "Explicit provider overhead factor",
                "why_it_matters": "Captures extra effort needed to serve others",
            },
            {
                "mechanism": "Labor accounting",
                "stable_model": "Primarily total labor aggregate",
                "research_model": "Separates self labor, service labor, coordination labor, and labor delta",
                "why_it_matters": "Supports direct testing of the labor-transfer claim",
            },
            {
                "mechanism": "Interpretation boundary",
                "stable_model": "Dashboard-facing baseline contract",
                "research_model": "Research-only `research_v2` contract",
                "why_it_matters": "Preserves web compatibility while expanding explanation capacity",
            },
        ]
    )


def _context_label(raw_label: str) -> str:
    """Translate internal scenario prefixes into report labels."""

    mapping = {
        "default_context": "Default",
        "type_a_context": "Type A",
        "type_b_context": "Type B",
        "edge_context": "Edge",
        "overloaded_context": "Overloaded",
    }
    return mapping.get(raw_label, raw_label.replace("_", " ").title())


def _baseline_horizon_source(combo_summary: pd.DataFrame) -> pd.DataFrame:
    """Collect the horizon-comparison source table for Package A."""

    package_a = combo_summary[
        (combo_summary["package_slug"] == PACKAGE_A)
        & (combo_summary["experiment_slug"] == "preset_horizon_scan")
    ].copy()
    package_a["society"] = np.where(
        package_a["scenario_id"].str.startswith("type_a"), "Type A", "Type B"
    )
    cols = [
        "society",
        "steps",
        "tail_total_labor_hours_mean",
        "tail_avg_stress_mean",
        "tail_tasks_delegated_frac_mean",
        "final_available_time_mean_mean",
        "tail_backlog_tasks_mean",
    ]
    return package_a[cols].sort_values(["steps", "society"]).reset_index(drop=True)


def _story_case_key_table(story_case_selection: pd.DataFrame) -> pd.DataFrame:
    """Create a scenario-comparison table from the selected story cases."""

    selected_ids = [
        "autonomy_baseline",
        "convenience_baseline",
        "threshold_pressure",
        "overloaded_convenience",
    ]
    table = story_case_selection[
        story_case_selection["scenario_id"].isin(selected_ids)
    ].copy()
    table = table[
        [
            "title",
            "delegation_preference_mean",
            "tasks_per_step_mean",
            "service_cost_factor",
            "social_conformity_pressure",
            "tail_avg_stress",
            "tail_total_labor_hours",
            "tail_backlog_tasks",
            "tail_delegation_labor_delta",
            "tail_self_labor_hours",
            "tail_service_labor_hours",
            "tail_delegation_coordination_hours",
            "final_available_time_mean",
            "final_time_spent_providing_mean",
        ]
    ].rename(
        columns={
            "title": "case",
            "delegation_preference_mean": "delegation_mean",
            "tasks_per_step_mean": "task_load_mean",
            "service_cost_factor": "service_cost_factor",
            "social_conformity_pressure": "conformity",
            "tail_avg_stress": "tail_stress",
            "tail_total_labor_hours": "tail_total_labor_hours",
            "tail_backlog_tasks": "tail_backlog_tasks",
            "tail_delegation_labor_delta": "tail_delegation_labor_delta",
            "tail_self_labor_hours": "tail_self_labor_hours",
            "tail_service_labor_hours": "tail_service_labor_hours",
            "tail_delegation_coordination_hours": "tail_coordination_hours",
            "final_available_time_mean": "final_available_time_mean",
            "final_time_spent_providing_mean": "final_provider_time_mean",
        }
    )
    return table.reset_index(drop=True)


def _combined_story_timeseries(story_case_selection: pd.DataFrame) -> pd.DataFrame:
    """Load and combine the saved case time series for the main dynamic panel."""

    rows: list[pd.DataFrame] = []
    selected_ids = [
        "autonomy_baseline",
        "convenience_baseline",
        "threshold_pressure",
        "overloaded_convenience",
    ]
    for _, record in story_case_selection.iterrows():
        if record["scenario_id"] not in selected_ids:
            continue
        frame = pd.read_csv(record["model_timeseries"], compression="gzip")
        frame["scenario_id"] = record["scenario_id"]
        frame["case_title"] = record["title"]
        rows.append(frame)
    return pd.concat(rows, ignore_index=True)


def _threshold_atlas_source(combo_summary: pd.DataFrame) -> pd.DataFrame:
    """Collect the Package B delegation x task-load atlas."""

    atlas = combo_summary[
        (combo_summary["package_slug"] == PACKAGE_B)
        & (combo_summary["experiment_slug"] == "delegation_task_load_atlas")
    ].copy()
    return atlas[
        [
            "delegation_preference_mean",
            "tasks_per_step_mean",
            "tail_backlog_tasks_mean",
            "tail_avg_stress_mean",
            "tail_total_labor_hours_mean",
            "tail_delegation_labor_delta_mean",
        ]
    ].sort_values(["delegation_preference_mean", "tasks_per_step_mean"]).reset_index(drop=True)


def _threshold_onset_table(atlas_source: pd.DataFrame) -> pd.DataFrame:
    """Find the first task-load cell where backlog becomes meaningfully visible."""

    onset_rows: list[dict[str, float]] = []
    for delegation, subset in atlas_source.groupby("delegation_preference_mean"):
        subset = subset.sort_values("tasks_per_step_mean")
        visible = subset[subset["tail_backlog_tasks_mean"] > 0.1]
        if visible.empty:
            continue
        first = visible.iloc[0]
        onset_rows.append(
            {
                "delegation_preference_mean": delegation,
                "first_backlog_task_load": first["tasks_per_step_mean"],
                "avg_stress_at_onset": first["tail_avg_stress_mean"],
                "backlog_at_onset": first["tail_backlog_tasks_mean"],
            }
        )
    return pd.DataFrame(onset_rows).sort_values("delegation_preference_mean").reset_index(drop=True)


def _threshold_refinement_summary(threshold_refinement: pd.DataFrame) -> pd.DataFrame:
    """Summarize the refined low-delegation threshold band."""

    focus = threshold_refinement[
        threshold_refinement["delegation_preference_mean"].isin([0.05, 0.10, 0.15, 0.20])
    ].copy()
    cell_means = (
        focus.groupby(["delegation_preference_mean", "tasks_per_step_mean"])
        .agg(
            tail_avg_stress_mean=("tail_avg_stress", "mean"),
            tail_backlog_tasks_mean=("tail_backlog_tasks", "mean"),
        )
        .reset_index()
    )
    summary = (
        cell_means.groupby("tasks_per_step_mean")
        .agg(
            stress_min=("tail_avg_stress_mean", "min"),
            stress_max=("tail_avg_stress_mean", "max"),
            backlog_min=("tail_backlog_tasks_mean", "min"),
            backlog_max=("tail_backlog_tasks_mean", "max"),
        )
        .reset_index()
        .sort_values("tasks_per_step_mean")
    )
    return summary


def _service_cost_context_source(combo_summary: pd.DataFrame) -> pd.DataFrame:
    """Build a compact low-vs-high context comparison for Package C."""

    context_scan = combo_summary[
        (combo_summary["package_slug"] == PACKAGE_C)
        & (combo_summary["experiment_slug"] == "service_cost_context_scan")
    ].copy()
    context_scan["context"] = context_scan["scenario_id"].str.extract(r"^(.*)_serv")
    context_scan["context"] = context_scan["context"].map(_context_label)
    grouped_rows: list[dict[str, float | str]] = []
    for context, subset in context_scan.groupby("context"):
        subset = subset.sort_values("service_cost_factor")
        low = subset.iloc[0]
        high = subset.iloc[-1]
        grouped_rows.append(
            {
                "context": context,
                "low_cost_factor": low["service_cost_factor"],
                "high_cost_factor": high["service_cost_factor"],
                "low_cost_stress": low["tail_avg_stress_mean"],
                "high_cost_stress": high["tail_avg_stress_mean"],
                "low_cost_labor": low["tail_total_labor_hours_mean"],
                "high_cost_labor": high["tail_total_labor_hours_mean"],
                "low_cost_delegated_frac": low["tail_tasks_delegated_frac_mean"],
                "high_cost_delegated_frac": high["tail_tasks_delegated_frac_mean"],
                "low_cost_backlog": low["tail_backlog_tasks_mean"],
                "high_cost_backlog": high["tail_backlog_tasks_mean"],
            }
        )
    return pd.DataFrame(grouped_rows)


def _service_cost_flip_source(combo_summary: pd.DataFrame) -> pd.DataFrame:
    """Find where low price stops relieving stress and starts amplifying it."""

    atlas = combo_summary[
        (combo_summary["package_slug"] == PACKAGE_C)
        & (combo_summary["experiment_slug"] == "service_cost_task_load_atlas")
    ].copy()
    low_cost = atlas["service_cost_factor"].min()
    high_cost = atlas["service_cost_factor"].max()
    rows: list[dict[str, float]] = []
    for delegation, subset in atlas.groupby("delegation_preference_mean"):
        if delegation < 0.35:
            continue
        low = subset[subset["service_cost_factor"] == low_cost].sort_values("tasks_per_step_mean")
        high = subset[subset["service_cost_factor"] == high_cost].sort_values("tasks_per_step_mean")
        merged = low.merge(
            high,
            on=["delegation_preference_mean", "tasks_per_step_mean"],
            suffixes=("_low", "_high"),
        )
        flipped = merged[
            merged["tail_avg_stress_mean_low"] > merged["tail_avg_stress_mean_high"]
        ]
        if flipped.empty:
            continue
        first = flipped.iloc[0]
        rows.append(
            {
                "delegation_preference_mean": delegation,
                "flip_task_load": first["tasks_per_step_mean"],
                "stress_delta_low_minus_high": (
                    first["tail_avg_stress_mean_low"] - first["tail_avg_stress_mean_high"]
                ),
                "backlog_delta_low_minus_high": (
                    first["tail_backlog_tasks_mean_low"] - first["tail_backlog_tasks_mean_high"]
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("delegation_preference_mean").reset_index(drop=True)


def _mixed_stability_sources(
    combo_summary: pd.DataFrame,
    per_seed_summary: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Collect heatmap and distribution sources for the mixed-system analysis."""

    heatmap_df = combo_summary[
        (combo_summary["package_slug"] == PACKAGE_D)
        & (combo_summary["experiment_slug"] == "mixed_stability_deep_dive")
    ][
        [
            "delegation_preference_mean",
            "social_conformity_pressure",
            "final_avg_delegation_rate_mean",
            "final_avg_delegation_rate_std",
            "tail_backlog_tasks_mean",
        ]
    ].copy()
    point_df = per_seed_summary[
        (per_seed_summary["package_slug"] == PACKAGE_D)
        & (per_seed_summary["experiment_slug"] == "mixed_stability_deep_dive")
    ][
        [
            "scenario_id",
            "seed",
            "delegation_preference_mean",
            "social_conformity_pressure",
            "final_avg_delegation_rate",
            "tail_backlog_tasks",
        ]
    ].copy()
    return heatmap_df, point_df


def _hypothesis_verdict_table(
    baseline_source: pd.DataFrame,
    threshold_onset: pd.DataFrame,
    service_cost_context: pd.DataFrame,
    mixed_heatmap: pd.DataFrame,
) -> pd.DataFrame:
    """Construct the report's hypothesis matrix with fixed judgment language."""

    horizon_450 = baseline_source[baseline_source["steps"] == 450].set_index("society")
    labor_delta_pct = (
        (
            horizon_450.loc["Type B", "tail_total_labor_hours_mean"]
            / horizon_450.loc["Type A", "tail_total_labor_hours_mean"]
        )
        - 1.0
    ) * 100.0
    avg_flip = threshold_onset["first_backlog_task_load"].mean()
    overloaded_row = service_cost_context[service_cost_context["context"] == "Overloaded"].iloc[0]
    max_mixed_std = mixed_heatmap["final_avg_delegation_rate_std"].max()
    return pd.DataFrame(
        [
            {
                "hypothesis": "H1",
                "judgment": "Strong support",
                "evidence": f"Type B keeps a {_fmt_pct(labor_delta_pct, 1)} labor premium at 450 steps.",
                "interpretation": "Higher delegation is consistently associated with more total system labor.",
            },
            {
                "hypothesis": "H2",
                "judgment": "Strong support",
                "evidence": f"Observed threshold band centers on task load {_fmt_num(avg_flip, 2)} and is refined to 3.0-3.25.",
                "interpretation": "A narrow overload band appears before the high-backlog regime.",
            },
            {
                "hypothesis": "H3",
                "judgment": "Partial support",
                "evidence": (
                    f"Type A keeps higher final available time while low-cost overload cells reach backlog "
                    f"{_fmt_num(overloaded_row['low_cost_backlog'], 1)}."
                ),
                "interpretation": "Autonomy aligns with more remaining time and lower structural pressure, but convenience is not measured directly.",
            },
            {
                "hypothesis": "H4",
                "judgment": "Partial support with an important negative result",
                "evidence": f"The largest mixed-state standard deviation remains only {_fmt_num(max_mixed_std, 4)}.",
                "interpretation": "Middle states are somewhat noisier, but the current settings do not produce a dramatic lock-in split.",
            },
        ]
    )


def _narrative_stats(
    combo_summary: pd.DataFrame,
    per_seed_summary: pd.DataFrame,
    threshold_refinement: pd.DataFrame,
    service_cost_context: pd.DataFrame,
    service_cost_flip: pd.DataFrame,
    mixed_heatmap: pd.DataFrame,
) -> dict[str, object]:
    """Compute the headline values reused across prose, tables, and tests."""

    baseline_source = _baseline_horizon_source(combo_summary)
    horizon_450 = baseline_source[baseline_source["steps"] == 450].set_index("society")
    type_a_450 = horizon_450.loc["Type A"]
    type_b_450 = horizon_450.loc["Type B"]

    threshold_summary = _threshold_refinement_summary(threshold_refinement)
    threshold_30 = threshold_summary[threshold_summary["tasks_per_step_mean"] == 3.0].iloc[0]
    threshold_325 = threshold_summary[threshold_summary["tasks_per_step_mean"] == 3.25].iloc[0]
    threshold_35 = threshold_summary[threshold_summary["tasks_per_step_mean"] == 3.5].iloc[0]

    mixed_max_row = mixed_heatmap.sort_values("final_avg_delegation_rate_std", ascending=False).iloc[0]
    overloaded_row = service_cost_context[service_cost_context["context"] == "Overloaded"].iloc[0]
    edge_row = service_cost_context[service_cost_context["context"] == "Edge"].iloc[0]

    return {
        "campaign_rows": {
            "combo_summary": int(len(combo_summary)),
            "per_seed_summary": int(len(per_seed_summary)),
            "threshold_refinement": int(len(threshold_refinement)),
        },
        "type_b_labor_delta_450_pct": (
            (type_b_450["tail_total_labor_hours_mean"] / type_a_450["tail_total_labor_hours_mean"]) - 1.0
        ) * 100.0,
        "type_b_stress_delta_450": type_b_450["tail_avg_stress_mean"] - type_a_450["tail_avg_stress_mean"],
        "type_a_available_time_450": type_a_450["final_available_time_mean_mean"],
        "type_b_available_time_450": type_b_450["final_available_time_mean_mean"],
        "threshold_30": threshold_30.to_dict(),
        "threshold_325": threshold_325.to_dict(),
        "threshold_35": threshold_35.to_dict(),
        "edge_row": edge_row.to_dict(),
        "overloaded_row": overloaded_row.to_dict(),
        "service_cost_flip": service_cost_flip.to_dict(orient="records"),
        "mixed_max_row": mixed_max_row.to_dict(),
    }


def _table_display_frames(
    question_map: pd.DataFrame,
    model_delta: pd.DataFrame,
    key_cases: pd.DataFrame,
    hypothesis_matrix: pd.DataFrame,
    claim_boundaries: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Create human-readable table views for the Markdown reports."""

    key_case_display = key_cases[
        [
            "case",
            "delegation_mean",
            "task_load_mean",
            "service_cost_factor",
            "conformity",
            "tail_stress",
            "tail_total_labor_hours",
            "tail_backlog_tasks",
            "tail_delegation_labor_delta",
            "final_available_time_mean",
            "final_provider_time_mean",
        ]
    ].copy()
    for column in [
        "delegation_mean",
        "task_load_mean",
        "service_cost_factor",
        "conformity",
        "tail_stress",
        "tail_total_labor_hours",
        "tail_backlog_tasks",
        "tail_delegation_labor_delta",
        "final_available_time_mean",
        "final_provider_time_mean",
    ]:
        key_case_display[column] = key_case_display[column].map(
            lambda value, digits=3: _fmt_num(float(value), 3)
        )

    claim_display = claim_boundaries.copy()
    return {
        "question_map": question_map,
        "model_delta": model_delta,
        "key_cases": key_case_display,
        "hypothesis_matrix": hypothesis_matrix,
        "claim_boundaries": claim_display,
    }


def _add_manifest_entry(
    manifest: list[dict[str, object]],
    *,
    kind: str,
    slug: str,
    path: Path,
    source_files: list[Path],
    alternate_paths: list[Path] | None = None,
) -> None:
    """Append one figure/table/report item to the output manifest."""

    manifest.append(
        {
            "kind": kind,
            "slug": slug,
            "path": str(path),
            "alternate_paths": [str(p) for p in (alternate_paths or [])],
            "source_files": [str(p) for p in source_files],
        }
    )


def _draw_causal_loop(
    figures_dir: Path,
    sources_dir: Path,
    manifest: list[dict[str, object]],
) -> tuple[Path, Path]:
    """Create the conceptual causal-loop figure and source CSVs."""

    nodes = pd.DataFrame(
        [
            {"node": "Delegation convenience", "x": 0.18, "y": 0.78},
            {"node": "Delegation intensity", "x": 0.50, "y": 0.90},
            {"node": "Provider burden", "x": 0.82, "y": 0.78},
            {"node": "Available personal time", "x": 0.84, "y": 0.45},
            {"node": "Backlog carryover", "x": 0.50, "y": 0.12},
            {"node": "Stress and adaptation", "x": 0.18, "y": 0.30},
            {"node": "Norm reinforcement", "x": 0.50, "y": 0.52},
        ]
    )
    edges = pd.DataFrame(
        [
            {"source": "Delegation convenience", "target": "Delegation intensity", "sign": "+", "meaning": "Lower friction encourages delegation"},
            {"source": "Delegation intensity", "target": "Provider burden", "sign": "+", "meaning": "More requests increase provider labor"},
            {"source": "Provider burden", "target": "Available personal time", "sign": "-", "meaning": "Provider labor narrows time slack"},
            {"source": "Available personal time", "target": "Backlog carryover", "sign": "-", "meaning": "Less slack raises unresolved work"},
            {"source": "Backlog carryover", "target": "Stress and adaptation", "sign": "+", "meaning": "Residual work raises pressure"},
            {"source": "Stress and adaptation", "target": "Delegation intensity", "sign": "+", "meaning": "Pressure shifts decisions toward delegation"},
            {"source": "Delegation intensity", "target": "Norm reinforcement", "sign": "+", "meaning": "High delegation normalizes itself"},
            {"source": "Norm reinforcement", "target": "Delegation convenience", "sign": "+", "meaning": "Social expectations make delegation feel safer"},
            {"source": "Norm reinforcement", "target": "Stress and adaptation", "sign": "+", "meaning": "Copied behavior affects adaptation"},
        ]
    )

    nodes_path = _save_csv(nodes, sources_dir / "figure_01_causal_loop_nodes.csv")
    edges_path = _save_csv(edges, sources_dir / "figure_01_causal_loop_edges.csv")

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_facecolor("#FBFBFB")
    ax.axis("off")

    node_lookup = {row["node"]: (row["x"], row["y"]) for _, row in nodes.iterrows()}
    for _, edge in edges.iterrows():
        x0, y0 = node_lookup[edge["source"]]
        x1, y1 = node_lookup[edge["target"]]
        color = COLORS["threshold"] if edge["sign"] == "+" else COLORS["type_a"]
        ax.annotate(
            "",
            xy=(x1, y1),
            xytext=(x0, y0),
            arrowprops={
                "arrowstyle": "->",
                "color": color,
                "lw": 2.0,
                "connectionstyle": "arc3,rad=0.12",
            },
        )
        mx = (x0 + x1) / 2.0
        my = (y0 + y1) / 2.0
        ax.text(
            mx,
            my,
            edge["sign"],
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
            color=color,
            bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": color, "lw": 1.0},
        )

    for _, node in nodes.iterrows():
        ax.text(
            node["x"],
            node["y"],
            node["node"],
            ha="center",
            va="center",
            fontsize=11,
            bbox={"boxstyle": "round,pad=0.45", "fc": "white", "ec": "#444444", "lw": 1.2},
        )

    ax.set_title(
        "Figure 1. Conceptual causal loop behind convenience, backlog, and norm reinforcement",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )
    ax.text(
        0.02,
        0.02,
        "All links are conceptual and remain within the model's abstract Type A / Type B framing.",
        transform=ax.transAxes,
        fontsize=9,
        color=COLORS["neutral"],
    )

    png_path = figures_dir / "figure_01_causal_loop.png"
    svg_path = figures_dir / "figure_01_causal_loop.svg"
    _save_figure(fig, png_path, svg_path)
    _add_manifest_entry(
        manifest,
        kind="figure",
        slug="figure_01_causal_loop",
        path=png_path,
        alternate_paths=[svg_path],
        source_files=[nodes_path, edges_path],
    )
    return png_path, svg_path


def _draw_flow_diagram(
    figures_dir: Path,
    sources_dir: Path,
    manifest: list[dict[str, object]],
) -> tuple[Path, Path]:
    """Create the white-box ABM lifecycle diagram and source CSVs."""

    steps = pd.DataFrame(
        [
            {"step": 1, "label": "Generate new tasks\nand merge carryover", "x": 0.12},
            {"step": 2, "label": "Self-serve or\ndelegate decision", "x": 0.32},
            {"step": 3, "label": "Service-pool\nmatching", "x": 0.52},
            {"step": 4, "label": "Unmatched tasks\nreturn as backlog", "x": 0.72},
            {"step": 5, "label": "Stress update and\npreference adaptation", "x": 0.90},
        ]
    )
    links = pd.DataFrame(
        [
            {"source_step": 1, "target_step": 2},
            {"source_step": 2, "target_step": 3},
            {"source_step": 3, "target_step": 4},
            {"source_step": 4, "target_step": 5},
        ]
    )
    steps_path = _save_csv(steps, sources_dir / "figure_02_white_box_flow_steps.csv")
    links_path = _save_csv(links, sources_dir / "figure_02_white_box_flow_links.csv")

    fig, ax = plt.subplots(figsize=(12, 3.8))
    ax.axis("off")
    ax.set_facecolor("white")

    y = 0.55
    for _, row in steps.iterrows():
        ax.text(
            row["x"],
            y,
            row["label"],
            ha="center",
            va="center",
            fontsize=10,
            bbox={"boxstyle": "round,pad=0.55", "fc": "#F7F7F7", "ec": "#444444", "lw": 1.2},
        )
        ax.text(
            row["x"],
            0.83,
            f"Step {int(row['step'])}",
            ha="center",
            va="center",
            fontsize=9,
            fontweight="bold",
            color=COLORS["neutral"],
        )

    for _, row in links.iterrows():
        x0 = steps.loc[steps["step"] == row["source_step"], "x"].iloc[0]
        x1 = steps.loc[steps["step"] == row["target_step"], "x"].iloc[0]
        ax.annotate(
            "",
            xy=(x1 - 0.06, y),
            xytext=(x0 + 0.06, y),
            arrowprops={"arrowstyle": "->", "lw": 2.0, "color": COLORS["type_b"]},
        )

    ax.text(
        0.52,
        0.12,
        "The research engine is white-box: backlog, coordination cost, match-rate, and labor accounting\nare explicit rule-based mechanisms rather than latent LLM behavior.",
        ha="center",
        va="center",
        fontsize=9,
        color=COLORS["neutral"],
    )
    ax.set_title(
        "Figure 2. White-box research-model lifecycle used in the formal report",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )

    png_path = figures_dir / "figure_02_white_box_flow.png"
    svg_path = figures_dir / "figure_02_white_box_flow.svg"
    _save_figure(fig, png_path, svg_path)
    _add_manifest_entry(
        manifest,
        kind="figure",
        slug="figure_02_white_box_flow",
        path=png_path,
        alternate_paths=[svg_path],
        source_files=[steps_path, links_path],
    )
    return png_path, svg_path


def _draw_baseline_horizon_panel(
    baseline_source: pd.DataFrame,
    figures_dir: Path,
    sources_dir: Path,
    manifest: list[dict[str, object]],
) -> tuple[Path, Path]:
    """Plot the formal baseline-horizon comparison panel."""

    source_path = _save_csv(baseline_source, sources_dir / "figure_03_baseline_horizon_source.csv")
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), sharex=True)
    metrics = [
        ("tail_total_labor_hours_mean", "Tail total labor hours", "Hours"),
        ("tail_avg_stress_mean", "Tail average stress", "Stress [0-1]"),
        ("final_available_time_mean_mean", "Final mean available time", "Hours"),
        ("tail_tasks_delegated_frac_mean", "Tail delegated task share", "Fraction"),
    ]
    for ax, (metric, title, ylabel) in zip(axes.flatten(), metrics):
        for society, color, linestyle in [
            ("Type A", COLORS["type_a"], "-"),
            ("Type B", COLORS["type_b"], "--"),
        ]:
            subset = baseline_source[baseline_source["society"] == society]
            ax.plot(
                subset["steps"],
                subset[metric],
                color=color,
                lw=2.4,
                linestyle=linestyle,
                marker="o",
                label=society,
            )
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_ylabel(ylabel, fontsize=10)
        ax.grid(True, color=COLORS["grid"], lw=0.8)
    for ax in axes[1]:
        ax.set_xlabel("Simulation horizon (steps)", fontsize=10)
    axes[0, 0].legend(loc="best", fontsize=9)
    fig.suptitle(
        "Figure 3. Type A and Type B remain structurally different across longer horizons",
        fontsize=14,
        fontweight="bold",
        y=0.99,
    )
    fig.text(
        0.5,
        0.01,
        "Package A summary metrics use tail-window aggregates from the research_v2 campaign.",
        ha="center",
        fontsize=9,
        color=COLORS["neutral"],
    )
    png_path = figures_dir / "figure_03_baseline_horizon_panel.png"
    svg_path = figures_dir / "figure_03_baseline_horizon_panel.svg"
    _save_figure(fig, png_path, svg_path)
    _add_manifest_entry(
        manifest,
        kind="figure",
        slug="figure_03_baseline_horizon_panel",
        path=png_path,
        alternate_paths=[svg_path],
        source_files=[source_path],
    )
    return png_path, svg_path


def _draw_story_case_panel(
    combined_timeseries: pd.DataFrame,
    figures_dir: Path,
    sources_dir: Path,
    manifest: list[dict[str, object]],
) -> tuple[Path, Path]:
    """Plot the four key story-case trajectories."""

    source_path = _save_csv(combined_timeseries, sources_dir / "figure_04_story_case_timeseries.csv")
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), sharex=True)
    case_order = [
        ("Autonomy Baseline", COLORS["type_a"]),
        ("Convenience Baseline", COLORS["type_b"]),
        ("Threshold Pressure", COLORS["provider"]),
        ("Overloaded Convenience", COLORS["backlog"]),
    ]
    metrics = [
        ("avg_stress", "Average stress", "Stress [0-1]"),
        ("total_labor_hours", "Total labor hours", "Hours"),
        ("backlog_tasks", "Backlog tasks", "Tasks"),
        ("delegation_match_rate", "Delegation match rate", "Rate"),
    ]
    for ax, (metric, title, ylabel) in zip(axes.flatten(), metrics):
        for case_title, color in case_order:
            subset = combined_timeseries[combined_timeseries["case_title"] == case_title]
            ax.plot(subset["Step"], subset[metric], lw=2.0, color=color, label=case_title)
        if metric == "backlog_tasks":
            ax.set_yscale("symlog", linthresh=1.0)
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_ylabel(ylabel, fontsize=10)
        ax.grid(True, color=COLORS["grid"], lw=0.8)
    for ax in axes[1]:
        ax.set_xlabel("Simulation step", fontsize=10)
    axes[0, 0].legend(loc="upper left", fontsize=8)
    fig.suptitle(
        "Figure 4. Dynamic story cases expose how convenience shifts from relief to overload",
        fontsize=14,
        fontweight="bold",
        y=0.99,
    )
    png_path = figures_dir / "figure_04_story_case_panel.png"
    svg_path = figures_dir / "figure_04_story_case_panel.svg"
    _save_figure(fig, png_path, svg_path)
    _add_manifest_entry(
        manifest,
        kind="figure",
        slug="figure_04_story_case_panel",
        path=png_path,
        alternate_paths=[svg_path],
        source_files=[source_path],
    )
    return png_path, svg_path


def _draw_threshold_phase_map(
    atlas_source: pd.DataFrame,
    threshold_onset: pd.DataFrame,
    threshold_refinement_summary: pd.DataFrame,
    figures_dir: Path,
    sources_dir: Path,
    manifest: list[dict[str, object]],
) -> tuple[Path, Path]:
    """Plot the threshold phase-map with a refined transition band."""

    atlas_path = _save_csv(atlas_source, sources_dir / "figure_05_threshold_phase_atlas.csv")
    onset_path = _save_csv(threshold_onset, sources_dir / "figure_05_threshold_onset.csv")
    refinement_path = _save_csv(
        threshold_refinement_summary,
        sources_dir / "figure_05_threshold_refinement_summary.csv",
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), gridspec_kw={"width_ratios": [1.25, 1.0]})

    x_vals = sorted(atlas_source["delegation_preference_mean"].unique())
    y_vals = sorted(atlas_source["tasks_per_step_mean"].unique())
    heatmap = (
        atlas_source.assign(log_backlog=np.log10(1.0 + atlas_source["tail_backlog_tasks_mean"]))
        .pivot(index="tasks_per_step_mean", columns="delegation_preference_mean", values="log_backlog")
        .reindex(index=y_vals, columns=x_vals)
    )
    im = axes[0].imshow(
        heatmap.values,
        origin="lower",
        aspect="auto",
        cmap="magma",
        extent=[min(x_vals) - 0.05, max(x_vals) + 0.05, min(y_vals) - 0.125, max(y_vals) + 0.125],
    )
    axes[0].axhspan(3.0, 3.25, facecolor="white", alpha=0.18, hatch="///", edgecolor="white")
    axes[0].plot(
        threshold_onset["delegation_preference_mean"],
        threshold_onset["first_backlog_task_load"],
        color="white",
        lw=2.2,
        marker="o",
        ms=4.5,
        label="First visible backlog (>0.1)",
    )
    axes[0].set_title("Backlog phase map", fontsize=11, fontweight="bold")
    axes[0].set_xlabel("Delegation preference mean", fontsize=10)
    axes[0].set_ylabel("Task load mean", fontsize=10)
    axes[0].legend(loc="upper left", fontsize=8)
    cbar = fig.colorbar(im, ax=axes[0], fraction=0.046, pad=0.04)
    cbar.set_label("log10(1 + tail backlog tasks)", fontsize=9)

    axes[1].plot(
        threshold_refinement_summary["tasks_per_step_mean"],
        threshold_refinement_summary["stress_min"],
        color=COLORS["type_a"],
        lw=2.0,
        label="Stress min",
    )
    axes[1].plot(
        threshold_refinement_summary["tasks_per_step_mean"],
        threshold_refinement_summary["stress_max"],
        color=COLORS["type_b"],
        lw=2.0,
        label="Stress max",
    )
    axes[1].fill_between(
        threshold_refinement_summary["tasks_per_step_mean"],
        threshold_refinement_summary["stress_min"],
        threshold_refinement_summary["stress_max"],
        color=COLORS["type_b"],
        alpha=0.15,
    )
    axes[1].axvspan(3.0, 3.25, color=COLORS["coordination"], alpha=0.18)
    axes[1].set_title("Refined low-delegation transition band", fontsize=11, fontweight="bold")
    axes[1].set_xlabel("Task load mean", fontsize=10)
    axes[1].set_ylabel("Tail average stress", fontsize=10)
    axes[1].grid(True, color=COLORS["grid"], lw=0.8)
    axes[1].legend(loc="upper left", fontsize=8)

    fig.suptitle(
        "Figure 5. Threshold evidence remains narrow: the critical band is observed around task load 3.0-3.25",
        fontsize=14,
        fontweight="bold",
        y=0.99,
    )
    fig.text(
        0.5,
        0.01,
        "The shaded band is an observed transition window from the refined low-delegation scan, not a universal constant.",
        ha="center",
        fontsize=9,
        color=COLORS["neutral"],
    )

    png_path = figures_dir / "figure_05_threshold_phase_map.png"
    svg_path = figures_dir / "figure_05_threshold_phase_map.svg"
    _save_figure(fig, png_path, svg_path)
    _add_manifest_entry(
        manifest,
        kind="figure",
        slug="figure_05_threshold_phase_map",
        path=png_path,
        alternate_paths=[svg_path],
        source_files=[atlas_path, onset_path, refinement_path],
    )
    return png_path, svg_path


def _draw_labor_transfer_decomposition(
    key_cases: pd.DataFrame,
    figures_dir: Path,
    sources_dir: Path,
    manifest: list[dict[str, object]],
) -> tuple[Path, Path]:
    """Plot the labor composition and labor-delta comparison."""

    raw_source = key_cases.copy()
    source_path = _save_csv(raw_source, sources_dir / "figure_06_labor_transfer_decomposition.csv")

    fig, ax1 = plt.subplots(figsize=(12, 6.5))
    positions = np.arange(len(key_cases))
    width = 0.62

    self_vals = key_cases["tail_self_labor_hours"]
    service_vals = key_cases["tail_service_labor_hours"]
    coord_vals = key_cases["tail_coordination_hours"]
    delta_vals = key_cases["tail_delegation_labor_delta"]

    ax1.bar(positions, self_vals, width=width, color=COLORS["type_a"], label="Self labor")
    ax1.bar(
        positions,
        service_vals,
        width=width,
        bottom=self_vals,
        color=COLORS["provider"],
        label="Service labor",
    )
    ax1.bar(
        positions,
        coord_vals,
        width=width,
        bottom=self_vals + service_vals,
        color=COLORS["coordination"],
        label="Coordination labor",
    )
    ax1.set_ylabel("Tail labor hours", fontsize=10)
    ax1.set_xticks(positions)
    ax1.set_xticklabels(key_cases["case"], rotation=12, ha="right")
    ax1.grid(True, axis="y", color=COLORS["grid"], lw=0.8)

    ax2 = ax1.twinx()
    ax2.plot(
        positions,
        delta_vals,
        color=COLORS["threshold"],
        lw=2.4,
        marker="D",
        ms=6,
        label="Delegation labor delta",
    )
    ax2.axhline(0.0, color=COLORS["neutral"], lw=1.2, linestyle=":")
    ax2.set_ylabel("Tail delegation labor delta", fontsize=10, color=COLORS["threshold"])
    ax2.tick_params(axis="y", labelcolor=COLORS["threshold"])

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2, loc="upper left", fontsize=9)
    fig.suptitle(
        "Figure 6. Convenience changes the composition of labor before it changes the total amount of strain",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    png_path = figures_dir / "figure_06_labor_transfer_decomposition.png"
    svg_path = figures_dir / "figure_06_labor_transfer_decomposition.svg"
    _save_figure(fig, png_path, svg_path)
    _add_manifest_entry(
        manifest,
        kind="figure",
        slug="figure_06_labor_transfer_decomposition",
        path=png_path,
        alternate_paths=[svg_path],
        source_files=[source_path],
    )
    return png_path, svg_path


def _draw_service_cost_context(
    service_cost_context: pd.DataFrame,
    service_cost_flip: pd.DataFrame,
    figures_dir: Path,
    sources_dir: Path,
    manifest: list[dict[str, object]],
) -> tuple[Path, Path]:
    """Plot the context scan and the low-cost flip onset."""

    context_path = _save_csv(service_cost_context, sources_dir / "figure_07_service_cost_context.csv")
    flip_path = _save_csv(service_cost_flip, sources_dir / "figure_07_service_cost_flip.csv")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8))

    contexts = service_cost_context["context"].tolist()
    x = np.arange(len(contexts))
    axes[0].plot(x, service_cost_context["low_cost_stress"], marker="o", lw=2.0, color=COLORS["type_b"], label="Low cost stress")
    axes[0].plot(x, service_cost_context["high_cost_stress"], marker="s", lw=2.0, color=COLORS["type_a"], label="High cost stress")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(contexts, rotation=15, ha="right")
    axes[0].set_ylabel("Tail average stress", fontsize=10)
    axes[0].set_title("Context scan: low vs high service cost", fontsize=11, fontweight="bold")
    axes[0].grid(True, color=COLORS["grid"], lw=0.8)
    axes[0].legend(loc="upper left", fontsize=8)
    for idx, row in service_cost_context.iterrows():
        axes[0].annotate(
            f"backlog {row['low_cost_backlog']:.1f}/{row['high_cost_backlog']:.1f}",
            (x[idx], max(row["low_cost_stress"], row["high_cost_stress"])),
            textcoords="offset points",
            xytext=(0, 6),
            ha="center",
            fontsize=7.5,
            color=COLORS["neutral"],
        )

    axes[1].plot(
        service_cost_flip["delegation_preference_mean"],
        service_cost_flip["flip_task_load"],
        color=COLORS["threshold"],
        lw=2.2,
        marker="o",
        label="First low-cost stress flip",
    )
    for _, row in service_cost_flip.iterrows():
        axes[1].annotate(
            f"dStress={row['stress_delta_low_minus_high']:.2f}",
            (row["delegation_preference_mean"], row["flip_task_load"]),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=7.5,
        )
    axes[1].axhspan(3.0, 3.25, color=COLORS["coordination"], alpha=0.18)
    axes[1].set_title("Where low price flips into amplification", fontsize=11, fontweight="bold")
    axes[1].set_xlabel("Delegation preference mean", fontsize=10)
    axes[1].set_ylabel("First task load where low cost > high cost stress", fontsize=10)
    axes[1].grid(True, color=COLORS["grid"], lw=0.8)
    axes[1].legend(loc="upper left", fontsize=8)

    fig.suptitle(
        "Figure 7. Low service price is conditional: it relieves low-load contexts but amplifies pressure near the threshold",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )
    png_path = figures_dir / "figure_07_service_cost_context.png"
    svg_path = figures_dir / "figure_07_service_cost_context.svg"
    _save_figure(fig, png_path, svg_path)
    _add_manifest_entry(
        manifest,
        kind="figure",
        slug="figure_07_service_cost_context",
        path=png_path,
        alternate_paths=[svg_path],
        source_files=[context_path, flip_path],
    )
    return png_path, svg_path


def _draw_mixed_stability(
    mixed_heatmap: pd.DataFrame,
    mixed_points: pd.DataFrame,
    figures_dir: Path,
    sources_dir: Path,
    manifest: list[dict[str, object]],
) -> tuple[Path, Path]:
    """Plot the mixed-system dispersion and final-rate distribution."""

    heatmap_path = _save_csv(mixed_heatmap, sources_dir / "figure_08_mixed_stability_heatmap.csv")
    points_path = _save_csv(mixed_points, sources_dir / "figure_08_mixed_stability_points.csv")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8), gridspec_kw={"width_ratios": [1.0, 1.15]})
    x_vals = sorted(mixed_heatmap["social_conformity_pressure"].unique())
    y_vals = sorted(mixed_heatmap["delegation_preference_mean"].unique())
    heatmap = (
        mixed_heatmap.pivot(
            index="delegation_preference_mean",
            columns="social_conformity_pressure",
            values="final_avg_delegation_rate_std",
        )
        .reindex(index=y_vals, columns=x_vals)
    )
    im = axes[0].imshow(
        heatmap.values,
        origin="lower",
        aspect="auto",
        cmap="Blues",
        extent=[min(x_vals) - 0.1, max(x_vals) + 0.1, min(y_vals) - 0.05, max(y_vals) + 0.05],
    )
    axes[0].set_title("Dispersion stays modest across mixed starts", fontsize=11, fontweight="bold")
    axes[0].set_xlabel("Social conformity pressure", fontsize=10)
    axes[0].set_ylabel("Initial delegation mean", fontsize=10)
    cbar = fig.colorbar(im, ax=axes[0], fraction=0.046, pad=0.04)
    cbar.set_label("Final delegation std across seeds", fontsize=9)

    for conformity, subset in mixed_points.groupby("social_conformity_pressure"):
        axes[1].scatter(
            subset["delegation_preference_mean"] + np.random.default_rng(42).normal(0.0, 0.002, len(subset)),
            subset["final_avg_delegation_rate"],
            s=22,
            alpha=0.45,
            label=f"Conformity {conformity:.1f}",
        )
    axes[1].plot([0.33, 0.67], [0.33, 0.67], linestyle="--", color=COLORS["neutral"], lw=1.4, label="Identity")
    axes[1].set_xlim(0.32, 0.68)
    axes[1].set_ylim(0.32, 0.68)
    axes[1].set_title("Per-seed final delegation stays close to the start", fontsize=11, fontweight="bold")
    axes[1].set_xlabel("Initial delegation mean", fontsize=10)
    axes[1].set_ylabel("Final delegation rate", fontsize=10)
    axes[1].grid(True, color=COLORS["grid"], lw=0.8)
    axes[1].legend(loc="upper left", fontsize=7.5, ncol=2)

    fig.suptitle(
        "Figure 8. Mixed-system instability is detectable but weak under the current parameter slice",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )
    png_path = figures_dir / "figure_08_mixed_stability.png"
    svg_path = figures_dir / "figure_08_mixed_stability.svg"
    _save_figure(fig, png_path, svg_path)
    _add_manifest_entry(
        manifest,
        kind="figure",
        slug="figure_08_mixed_stability",
        path=png_path,
        alternate_paths=[svg_path],
        source_files=[heatmap_path, points_path],
    )
    return png_path, svg_path


def _render_english_report(
    *,
    report_path: Path,
    campaign_dir: Path,
    stats: dict[str, object],
    table_paths: dict[str, Path],
    figure_paths: dict[str, Path],
    table_views: dict[str, pd.DataFrame],
    manifest_path: Path,
) -> str:
    """Render the canonical English Markdown report."""

    rows = stats["campaign_rows"]
    mixed_max_row = stats["mixed_max_row"]
    edge_row = stats["edge_row"]
    overloaded_row = stats["overloaded_row"]
    threshold_30 = stats["threshold_30"]
    threshold_325 = stats["threshold_325"]
    threshold_35 = stats["threshold_35"]

    table_1 = _markdown_table(table_views["question_map"])
    table_2 = _markdown_table(table_views["model_delta"])
    table_3 = _markdown_table(table_views["key_cases"])
    table_4 = _markdown_table(table_views["hypothesis_matrix"])
    table_5 = _markdown_table(table_views["claim_boundaries"])

    text = f"""# Formal Research Report: `{campaign_dir.name}`

**Date**: {date.today().isoformat()}  
**Campaign directory**: `{campaign_dir}`  
**Engine**: `research_v2`  
**Asset manifest**: { _link_relative(report_path, manifest_path, "formal report manifest") }

## Abstract

This report examines the most complete `research_v2` campaign currently available for *The Convenience Paradox* and reworks it into a paper-style, white-box analysis package. The study is motivated by repeated everyday observations that some social settings feel more convenience-heavy while others preserve wider autonomy and time boundaries. The report does **not** treat those observations as conclusions. Instead, it translates them into explicit mechanism questions, tests them in an abstract agent-based model, and evaluates only what the model and campaign outputs can honestly support.

The campaign covers {rows['combo_summary']} aggregated scenario cells, {rows['per_seed_summary']} seed-level summary rows, and {rows['threshold_refinement']} additional refinement rows, all generated from the research-only engine with backlog carryover, stricter matching, and explicit labor-delta accounting. Three findings are especially robust. First, higher delegation is consistently associated with higher total system labor, with the Type B baseline retaining a {_fmt_pct(stats['type_b_labor_delta_450_pct'], 2)} labor premium at 450 steps. Second, overload does not emerge gradually across all settings; it appears within a narrow observed transition band around task load 3.0-3.25. Third, low service price is conditional rather than universally beneficial: it reduces pressure in low-load contexts but amplifies backlog once the system moves close to capacity.

This should be read as an exploratory modeling study and as an example of disciplined synthesis, model specification, and data stewardship. The current report is strongest when it speaks about abstract labor transfer, overload thresholds, and norm-sensitive stability. It is deliberately cautious about broader claims because prices remain exogenous, delay tolerance is not directly modeled, and the outputs are not evidence about any named real-world population.

## Problem Definition and Motivation

The formal problem addressed here is whether a high-convenience social configuration truly reduces total work, or whether it mainly redistributes work across agents while changing who feels the burden and when that burden becomes visible. The motivating intuition is straightforward: everyday convenience can feel individually efficient even when it requires someone else, somewhere in the system, to absorb additional coordination, service labor, or time pressure.

The model is therefore used as a structured translation layer between qualitative observation and quantitative mechanism analysis. That translation is itself part of the contribution. The point of the exercise is not to claim final truth about a social phenomenon, but to show how loosely framed observations can be turned into explicit feedback loops, white-box agent rules, reproducible campaigns, and auditable outputs. In that sense, the report is both a substantive analysis and a demonstration of computational social science workflow discipline.

{_markdown_image(report_path, figure_paths['figure_01_causal_loop'], 'Figure 1 causal loop')}

*Figure 1. Conceptual causal loop linking convenience, delegation, provider burden, time scarcity, backlog, and norm reinforcement.*

## Research Questions and Hypotheses

The study follows four linked hypothesis families derived from the broader convenience-versus-autonomy observation:

1. **H1**: Higher delegation rates increase total system labor hours.
2. **H2**: A critical threshold triggers a convenience-to-involution transition.
3. **H3**: Higher autonomy lowers convenience but improves broader well-being proxies.
4. **H4**: Mixed systems are unstable and drift toward extremes.

Table 1 maps the core research questions and hypotheses onto the campaign packages and their primary metrics.

{table_1}

Source CSV: {_link_relative(report_path, table_paths['table_01_question_hypothesis_mapping'], 'Table 1 CSV')}

## Model Specification and White-Box Mechanism Mapping

The report is based on the research-only `ConvenienceParadoxResearchModel`, not the stable dashboard engine. This distinction matters because the formal analysis relies on mechanisms that the dashboard line intentionally does not expose yet: carryover backlog, explicit requester coordination cost, stricter provider matching, and labor accounting that separates self labor, service labor, coordination labor, and delegation labor delta.

{_markdown_image(report_path, figure_paths['figure_02_white_box_flow'], 'Figure 2 white-box flow')}

*Figure 2. White-box lifecycle of the research engine used for this report.*

Table 2 summarizes the practical model delta that matters for interpretation.

{table_2}

Source CSV: {_link_relative(report_path, table_paths['table_02_model_delta'], 'Table 2 CSV')}

## Experimental Basis and Data Stewardship

This report uses only persisted outputs from the existing campaign directory. No new simulations are run during report generation. The input basis is therefore auditable and finite:

- `summaries/combo_summary.csv` for package-level aggregates
- `summaries/per_seed_summary.csv` for seed-level distributions
- `summaries/threshold_refinement_per_seed.csv` for the refined threshold band
- `summaries/preset_decomposition_per_seed.csv` for the cheap-service mechanism decomposition
- `summaries/story_case_selection.csv` plus saved case traces for representative trajectories
- writing-support notes for claim boundaries and evidence crosswalks

The report builder writes every derived figure and table into `report_assets/formal_report/` under the same campaign, including compact source CSVs and a provenance manifest. This matters for two reasons. First, it keeps the analysis reproducible and inspectable. Second, it preserves downstream reuse value for later portfolio or blog-oriented writing without requiring another round of manual extraction.

## Results

### 1. Baseline divergence remains stable rather than fading away

{_markdown_image(report_path, figure_paths['figure_03_baseline_horizon_panel'], 'Figure 3 baseline horizons')}

*Figure 3. Type A and Type B maintain distinct labor, stress, available-time, and delegation profiles across 120, 200, 300, and 450 steps.*

The baseline horizon comparison shows that the high-delegation Type B configuration does not converge back toward the Type A baseline as the horizon extends. At 450 steps, Type B still carries a {_fmt_pct(stats['type_b_labor_delta_450_pct'], 2)} labor premium, a stress level that is {_fmt_num(stats['type_b_stress_delta_450'], 4)} higher, and a lower mean remaining-time level ({_fmt_num(stats['type_b_available_time_450'], 3)} vs. {_fmt_num(stats['type_a_available_time_450'], 3)}). This is analytically important because it indicates that the convenience-heavy configuration is not merely a short-run transition artifact within the current model.

### 2. Convenience behaves more like labor transfer than labor elimination

Table 3 compares the four representative cases selected for narrative and diagnostic value.

{table_3}

Source CSV: {_link_relative(report_path, table_paths['table_03_key_scenario_comparison'], 'Table 3 CSV')}

{_markdown_image(report_path, figure_paths['figure_04_story_case_panel'], 'Figure 4 story cases')}

*Figure 4. Dynamic trajectories for the four representative cases used throughout the report.*

{_markdown_image(report_path, figure_paths['figure_06_labor_transfer_decomposition'], 'Figure 6 labor transfer decomposition')}

*Figure 6. Self labor, service labor, coordination labor, and delegation labor delta across representative cases.*

The story-case evidence makes the transfer mechanism concrete. The convenience-heavy baseline maintains relatively low stress for long stretches, but it does so by moving more work into provider time and coordination overhead. In the overloaded convenience case, the average user-facing convenience does not disappear first; instead, the provider side absorbs escalating hidden effort until backlog dominates the system state. This is exactly where the `delegation_labor_delta` metric becomes useful: it reveals whether delegation is reducing labor in aggregate or merely relocating it.

### 3. The overload threshold is narrow and should not be overstated

{_markdown_image(report_path, figure_paths['figure_05_threshold_phase_map'], 'Figure 5 threshold phase map')}

*Figure 5. Package B phase map and refined transition evidence around task load 3.0-3.25.*

The main atlas shows where visible backlog first appears, but the refined scan is what supports a disciplined threshold claim. In the low-delegation refinement band, stress remains within {_fmt_num(threshold_30['stress_min'], 3)}-{_fmt_num(threshold_30['stress_max'], 3)} at task load 3.0 and backlog stays negligible. By 3.25, stress jumps to {_fmt_num(threshold_325['stress_min'], 3)}-{_fmt_num(threshold_325['stress_max'], 3)} and backlog becomes visible at {_fmt_num(threshold_325['backlog_min'], 2)}-{_fmt_num(threshold_325['backlog_max'], 2)}. At 3.5, the system is effectively saturated: stress reaches {_fmt_num(threshold_35['stress_min'], 3)}-{_fmt_num(threshold_35['stress_max'], 3)} while backlog grows to {_fmt_num(threshold_35['backlog_min'], 2)}-{_fmt_num(threshold_35['backlog_max'], 2)}. The correct interpretation is therefore not that there is a universal threshold constant, but that the current model repeatedly exposes a narrow transition band around 3.0-3.25 under the audited parameter slice.

### 4. Low service price is a conditional buffer that can turn into an amplifier

{_markdown_image(report_path, figure_paths['figure_07_service_cost_context'], 'Figure 7 service cost context')}

*Figure 7. Context scan and low-price flip onset in Package C.*

The context scan makes the conditional nature of price effects explicit. In the Edge context, low price raises stress from {_fmt_num(edge_row['high_cost_stress'], 4)} to {_fmt_num(edge_row['low_cost_stress'], 4)} and increases backlog from {_fmt_num(edge_row['high_cost_backlog'], 4)} to {_fmt_num(edge_row['low_cost_backlog'], 4)}. In the Overloaded context, both cost regimes are saturated on stress, but the low-cost regime expands backlog to {_fmt_num(overloaded_row['low_cost_backlog'], 2)} versus {_fmt_num(overloaded_row['high_cost_backlog'], 2)} under the high-cost comparison. This supports a sharper claim than "cheap service matters": price only looks like a relief valve while the system is comfortably below capacity.

### 5. Mixed-system instability exists, but the strongest result is still a restrained one

{_markdown_image(report_path, figure_paths['figure_08_mixed_stability'], 'Figure 8 mixed stability')}

*Figure 8. Dispersion and per-seed final delegation outcomes in the mixed-system slice.*

The mixed-state analysis does detect some extra variability in the middle zone, but the effect is modest. The largest final-delegation standard deviation in the deep-dive slice is only {_fmt_num(mixed_max_row['final_avg_delegation_rate_std'], 4)}, observed at initial delegation {_fmt_num(mixed_max_row['delegation_preference_mean'], 2)} and conformity {_fmt_num(mixed_max_row['social_conformity_pressure'], 2)}. This is exactly the sort of result that should be reported carefully: it gives partial support to the intuition that mixed systems are harder to stabilize, yet it also functions as a negative result because the current settings do **not** produce a dramatic bifurcation.

## Discussion, Boundaries, and Humble Claims

The strongest defensible interpretation of the campaign is not "convenience is bad." It is narrower and more useful: convenience-heavy configurations can remain subjectively smooth while becoming objectively more labor-intensive and more fragile near capacity. The report is also strongest when it treats the model as a mechanism probe rather than a stand-in for real societies.

This caution is not an afterthought. It is part of the quality standard of the exercise. The present work is meant to demonstrate the ability to transform qualitative observations into explicit model structure, map that structure onto measurable outputs, and maintain data provenance throughout the analysis. It is **not** a claim that the current model exhausts the social phenomenon or that it can adjudicate real institutional histories.

Table 4 states the formal hypothesis judgments used throughout the report.

{table_4}

Source CSV: {_link_relative(report_path, table_paths['table_04_hypothesis_verdict_matrix'], 'Table 4 CSV')}

Table 5 makes the claim boundaries explicit.

{table_5}

Source CSV: {_link_relative(report_path, table_paths['table_05_claim_boundaries'], 'Table 5 CSV')}

## Conclusion and Next-Step Model Extensions

Four conclusions follow from the current campaign.

1. The evidence strongly supports H1: higher delegation is associated with higher total labor.
2. The evidence strongly supports H2, but only in the disciplined form of an observed transition band around task load 3.0-3.25 under the current mechanism set.
3. H3 receives partial support because the model is stronger on available-time and stress proxies than on direct convenience perception.
4. H4 receives partial support together with an important negative result: mixed systems are somewhat more variable, but they do not collapse into a dramatic lock-in story under the present slice.

The clearest next extensions are already visible from the report's boundaries: endogenous price formation, explicit delay-tolerance dynamics, differentiated provider/requester roles, and richer skill-retention mechanisms. Until then, the current report is most credible when it is read as a transparent, exploratory, and well-audited mechanism study.
"""
    return text


def _render_chinese_report(
    *,
    report_path: Path,
    campaign_dir: Path,
    stats: dict[str, object],
    table_paths: dict[str, Path],
    figure_paths: dict[str, Path],
    table_views: dict[str, pd.DataFrame],
    manifest_path: Path,
) -> str:
    """Render the standalone Chinese translation."""

    rows = stats["campaign_rows"]
    mixed_max_row = stats["mixed_max_row"]
    edge_row = stats["edge_row"]
    overloaded_row = stats["overloaded_row"]
    threshold_30 = stats["threshold_30"]
    threshold_325 = stats["threshold_325"]
    threshold_35 = stats["threshold_35"]

    zh_question_map = table_views["question_map"].replace(
        {
            "Do stable everyday frictions signal a deeper time-allocation architecture?": "稳定存在的日常摩擦，是否意味着更深层的时间分配结构？",
            "Does convenience eliminate labor or relocate it inside the system?": "便利究竟是在消灭劳动，还是在系统内部转移劳动？",
            "How much can low service price explain by itself?": "低服务价格本身究竟能解释多少现象？",
            "Do mixed systems drift toward extremes under norm pressure?": "混合系统是否会在规范压力下向极端漂移？",
            "H3 (partial)": "H3（部分支持）",
            "H1 (strong), H2 (strong)": "H1（强支持），H2（强支持）",
            "H2 (strong contextual support)": "H2（在上下文层面获得强支持）",
            "H4 (partial, important negative result)": "H4（部分支持，且包含重要负结果）",
            "Package A": "Package A",
            "Package B": "Package B",
            "Package C": "Package C",
            "Package D": "Package D",
            "Long-horizon baseline comparison": "长 horizon 基线对比",
            "Labor-transfer decomposition and threshold mapping": "劳动转移拆解与阈值映射",
            "Context scan and cost-flip analysis": "上下文扫描与价格翻转分析",
            "Mixed-state dispersion and stability assessment": "混合状态离散度与稳定性评估",
        }
    )
    zh_model_delta = table_views["model_delta"].replace(
        {
            "Unmatched delegated work": "未匹配委托任务",
            "Provider eligibility": "提供者可接单条件",
            "Requester-side delegation friction": "请求者侧委托摩擦",
            "Provider-side service friction": "提供者侧服务摩擦",
            "Labor accounting": "劳动核算方式",
            "Interpretation boundary": "解释边界",
            "Counted as unmatched but does not return as next-step work": "只统计 unmatched，但不会作为下一步真实任务返回",
            "Returns to requester carryover backlog": "返回请求者的 carryover backlog",
            "Loose matching threshold": "较宽松的匹配门槛",
            "Provider must have enough remaining time for the full service": "提供者必须有足够剩余时间完成整项服务",
            "Implicit only": "仅隐含存在",
            "Explicit coordination-time cost": "显式 coordination-time cost",
            "Simpler provider service timing": "较简化的 provider 服务耗时",
            "Explicit provider overhead factor": "显式 provider overhead factor",
            "Primarily total labor aggregate": "以总劳动聚合为主",
            "Separates self labor, service labor, coordination labor, and labor delta": "拆分 self labor、service labor、coordination labor 与 labor delta",
            "Dashboard-facing baseline contract": "面向 dashboard 的稳定契约",
            "Research-only `research_v2` contract": "研究专用 `research_v2` 契约",
            "Makes overload cumulative instead of purely retrospective": "让过载从事后统计变成可累积的真实压力",
            "Makes supply tightness observable": "让供给紧张变得可观测",
            "Prevents delegation from looking costless to the requester": "避免 delegation 在请求者视角下显得“零成本”",
            "Captures extra effort needed to serve others": "刻画为他人提供服务所需的额外努力",
            "Supports direct testing of the labor-transfer claim": "支持直接检验“劳动转移”命题",
            "Preserves web compatibility while expanding explanation capacity": "在不破坏网页兼容性的前提下扩展解释能力",
        }
    )
    zh_key_cases = table_views["key_cases"].replace(
        {
            "Autonomy Baseline": "Autonomy Baseline",
            "Convenience Baseline": "Convenience Baseline",
            "Threshold Pressure": "Threshold Pressure",
            "Overloaded Convenience": "Overloaded Convenience",
        }
    )
    zh_hypothesis_matrix = table_views["hypothesis_matrix"].replace(
        {
            "Strong support": "强支持",
            "Partial support": "部分支持",
            "Partial support with an important negative result": "部分支持，并包含重要负结果",
            "Type B keeps a 30.0% labor premium at 450 steps.": "Type B 在 450 步时仍保持约 30.0% 的劳动溢价。",
            "Observed threshold band centers on task load 3.10 and is refined to 3.0-3.25.": "观测到的阈值带集中在任务负载 3.10 左右，并被细化到 3.0-3.25。",
            "Type A keeps higher final available time while low-cost overload cells reach backlog 71926.0.": "Type A 保持更高的最终可支配时间，而低价过载格点的 backlog 可达 71926.0。",
            "The largest mixed-state standard deviation remains only 0.0125.": "混合状态下最大的标准差也仅为 0.0125。",
            "Higher delegation is consistently associated with more total system labor.": "更高 delegation 与更高系统总劳动稳定同向。",
            "A narrow overload band appears before the high-backlog regime.": "在高 backlog 区出现之前，存在一个狭窄的过载过渡带。",
            "Autonomy aligns with more remaining time and lower structural pressure, but convenience is not measured directly.": "自治与更高剩余时间、较低结构性压力同向，但模型并未直接度量 convenience 感知。",
            "Middle states are somewhat noisier, but the current settings do not produce a dramatic lock-in split.": "中间状态确实更易波动，但当前设定并未产生强烈的 lock-in 分裂。",
        }
    )
    zh_claim_boundaries = table_views["claim_boundaries"].replace(
        {
            "Can Say Confidently": "可以较有把握地说",
            "Can Say With Caveat": "可以在保留条件下说",
            "Cannot Claim From Current Model": "当前模型不能主张",
            "The current ABM can identify parameter regions where higher delegation is associated with higher total labour hours in abstract Type A / Type B systems.": "当前 ABM 可以识别出在抽象 Type A / Type B 系统中，高 delegation 与更高总劳动小时相关联的参数区间。",
            "The current ABM can compare how stress, labour, and inequality proxies evolve under different levels of task pressure, price friction, and conformity.": "当前 ABM 可以比较 stress、labor 与 inequality proxy 在不同任务压力、价格摩擦和 conformity 下的演化。",
            "The current ABM can test whether moderate initial delegation states remain stable under the model's conformity and stress feedback rules.": "当前 ABM 可以检验中等初始 delegation 状态在模型的 conformity 与 stress feedback 规则下是否稳定。",
            "The model can show that lower external service prices push behaviour toward more delegation, but only as an exogenous price-friction experiment.": "模型可以显示更低的外生服务价格会把行为推向更高 delegation，但这仅限于外生价格摩擦实验。",
            "The model can approximate norm lock-in and speed expectations through delegation convergence proxies, not through a direct measure of delay tolerance.": "模型可以通过 delegation convergence proxy 近似刻画 norm lock-in 与速度预期，但并没有直接测量 delay tolerance。",
            "The model can visualise how convenience shifts time burdens toward providers, but the exact labour market structure of real societies is outside scope.": "模型可以可视化 convenience 如何把时间负担转移给 providers，但现实社会的具体劳动力市场结构不在当前范围内。",
            "The model cannot identify the full real-world causal loop between cheap services and service dependence because prices are not endogenous.": "由于价格不是内生变量，模型不能识别廉价服务与服务依赖之间完整的现实因果回路。",
            "The model cannot measure real populations, named countries, or concrete policy outcomes.": "模型不能测量真实人口、具体国家或明确政策结果。",
            "The model cannot directly test skill decay, demographic inequality, or explicit tolerance-for-delay dynamics because those mechanisms are absent.": "由于缺少相关机制，模型不能直接检验技能退化、人口结构不平等或显式的等待耐受度动态。",
        }
    )

    zh_table_1 = _markdown_table(
        zh_question_map.rename(
            columns={
                "research_question": "研究问题",
                "hypothesis": "对应假设",
                "package": "实验包",
                "primary_metrics": "主要指标",
                "analysis_role": "分析角色",
            }
        )
    )
    zh_table_2 = _markdown_table(
        zh_model_delta.rename(
            columns={
                "mechanism": "机制维度",
                "stable_model": "稳定版模型",
                "research_model": "研究版模型",
                "why_it_matters": "研究意义",
            }
        )
    )
    zh_table_3 = _markdown_table(
        zh_key_cases.rename(
            columns={
                "case": "案例",
                "delegation_mean": "委托均值",
                "task_load_mean": "任务负载均值",
                "service_cost_factor": "服务成本系数",
                "conformity": "规范压力",
                "tail_stress": "尾段压力",
                "tail_total_labor_hours": "尾段总劳动小时",
                "tail_backlog_tasks": "尾段 backlog",
                "tail_delegation_labor_delta": "尾段委托劳动增量",
                "final_available_time_mean": "最终平均可支配时间",
                "final_provider_time_mean": "最终平均提供服务时间",
            }
        )
    )
    zh_table_4 = _markdown_table(
        zh_hypothesis_matrix.rename(
            columns={
                "hypothesis": "假设",
                "judgment": "判断",
                "evidence": "关键证据",
                "interpretation": "解释",
            }
        )
    )
    zh_table_5 = _markdown_table(
        zh_claim_boundaries.rename(
            columns={
                "claim_status": "主张边界",
                "statement": "表述",
            }
        )
    )

    text = f"""# 正式研究分析报告：`{campaign_dir.name}`

**日期**：{date.today().isoformat()}  
**实验目录**：`{campaign_dir}`  
**研究引擎**：`research_v2`  
**资产清单**：{_link_relative(report_path, manifest_path, "正式报告清单")}

## 摘要

本报告针对当前仓库中最完整的一组 `research_v2` campaign 输出，构建一份更接近正式研究分析文体的白盒报告。它的出发点是一些跨系统的日常生活观察：有的社会配置更强调便利与委托，有的配置保留更大的自治与时间边界。但这些观察在这里并不被当作结论，而是被转化为明确的机制问题，再交由抽象 agent-based model 检验。换言之，本报告回答的是“在当前模型里，哪些推论是站得住的”，而不是“现实世界一定如此”。

本次 campaign 覆盖 {rows['combo_summary']} 个聚合情景、{rows['per_seed_summary']} 条 seed 级汇总记录，以及 {rows['threshold_refinement']} 条额外阈值细化记录，全部来自带有 backlog 回流、严格匹配与劳动增量核算的研究专用引擎。最稳健的三点结论是：第一，更高 delegation 与更高系统总劳动稳定同向，Type B 在 450 步时仍保留 {_fmt_pct(stats['type_b_labor_delta_450_pct'], 2)} 的劳动溢价；第二，过载并不是在所有参数区缓慢出现，而是在任务负载 3.0-3.25 的窄带附近明显跳变；第三，低服务价格并非普遍有利，它在低负载区减压，但在接近容量边界时会放大 backlog。

因此，这份报告最适合被理解为一项探索性白盒建模研究，也是一项关于“如何把 qualitative observation 转化为透明模型结构、并用数据治理方式约束分析结论”的能力展示。它在解释抽象的劳动转移、过载阈值和规范敏感性时最有说服力；而在价格内生性、等待耐受度或现实社会映射等问题上，则保持明确克制。

## 问题定义与研究动机

本报告要处理的正式问题是：高便利配置究竟是否真正减少了系统总劳动，还是主要改变了劳动在系统内部的分布方式，并由此改变了“谁感受到负担”以及“负担何时变得可见”。其核心直觉很简单：个体层面的便利体验，可能建立在系统其他位置更多的服务劳动、协调成本或时间压力之上。

因此，这个模型被当作一层结构化翻译器，用来把松散的社会观察转化为清晰的 feedback loop、white-box agent rule、可复现实验 campaign，以及可审计的输出资产。这里的重点不只是现象分析本身，也包括这种转译过程本身所体现的能力：把 qualitative input 转成 formal model specification，再把 model output 落成有出处、有边界的研究分析。

{_markdown_image(report_path, figure_paths['figure_01_causal_loop'], '图 1 因果回路')}

*图 1. 便利、委托、提供者负担、时间稀缺、backlog 与规范强化之间的概念性因果回路。*

## 研究问题与假设

本研究围绕四条相互关联的假设展开：

1. **H1**：更高 delegation 会提高系统总劳动小时数。
2. **H2**：存在从“便利”滑向“内卷/过载”的临界区间。
3. **H3**：更高自治会降低便利性，但改善更广义的福祉代理指标。
4. **H4**：混合系统不稳定，会向极端漂移。

表 1 给出研究问题、假设、实验包与核心指标之间的映射。

{zh_table_1}

源 CSV：{_link_relative(report_path, table_paths['table_01_question_hypothesis_mapping'], '表 1 CSV')}

## 模型定义与白盒机制映射

本报告基于研究专用的 `ConvenienceParadoxResearchModel`，而不是网页稳定版引擎。这个区分非常重要，因为正式分析依赖的关键机制都位于 research line：carryover backlog、requester coordination cost、更严格的 provider matching，以及将 self/service/coordination/labor delta 拆开的劳动核算。

{_markdown_image(report_path, figure_paths['figure_02_white_box_flow'], '图 2 白盒流程图')}

*图 2. 本报告使用的研究版引擎生命周期。*

表 2 概括了稳定版与研究版模型之间最关键的解释边界。

{zh_table_2}

源 CSV：{_link_relative(report_path, table_paths['table_02_model_delta'], '表 2 CSV')}

## 实验基础与数据治理

本报告严格只使用已有 campaign 输出，不执行任何新的 simulation run。因此，它的证据基础是有限、稳定且可审计的：

- `summaries/combo_summary.csv`：包级聚合输出
- `summaries/per_seed_summary.csv`：seed 级分布
- `summaries/threshold_refinement_per_seed.csv`：阈值细化扫描
- `summaries/preset_decomposition_per_seed.csv`：低价服务机制拆解
- `summaries/story_case_selection.csv` 及对应案例时间序列
- writing-support 目录中的证据映射与 claim boundary 文档

报告生成器会把所有衍生图表和表格写入同一 campaign 目录下的 `report_assets/formal_report/`，同时保存每张图与每张表对应的源 CSV 与 provenance manifest。这样做的意义有两层：一是保证本轮分析本身可追溯；二是为后续作品集展示或技术博客撰写保留可复用的下游资产。

## 结果

### 1. 基线差异并未随更长 horizon 消失

{_markdown_image(report_path, figure_paths['figure_03_baseline_horizon_panel'], '图 3 基线 horizon 对比')}

*图 3. Type A 与 Type B 在 120、200、300、450 步下仍保持不同的劳动、压力、可支配时间与委托比例结构。*

Package A 的 horizon comparison 表明，高 delegation 的 Type B 并不会随着时间延长而自动回归到 Type A。到 450 步时，Type B 仍然保持 {_fmt_pct(stats['type_b_labor_delta_450_pct'], 2)} 的总劳动溢价，平均压力比 Type A 高 {_fmt_num(stats['type_b_stress_delta_450'], 4)}，平均剩余时间则更低（{_fmt_num(stats['type_b_available_time_450'], 3)} 对 {_fmt_num(stats['type_a_available_time_450'], 3)}）。这说明在当前模型里，“便利型配置”不是短期扰动，而是一组更稳定的结构性差异。

### 2. 便利更像劳动转移，而不是劳动消失

表 3 汇总了四个代表性 story case。

{zh_table_3}

源 CSV：{_link_relative(report_path, table_paths['table_03_key_scenario_comparison'], '表 3 CSV')}

{_markdown_image(report_path, figure_paths['figure_04_story_case_panel'], '图 4 代表性案例时间序列')}

*图 4. 四个代表性案例的动态轨迹。*

{_markdown_image(report_path, figure_paths['figure_06_labor_transfer_decomposition'], '图 6 劳动拆解')}

*图 6. 代表性案例中的 self labor、service labor、coordination labor 与 delegation labor delta。*

这些案例把“劳动转移”机制变得非常具体。高便利基线在较长时期内可以维持较低压力，但它是通过把更多工作推向 provider 侧与协调成本来实现的。在 overloaded convenience 情景中，首先崩溃的并不是“表面的便利体验”，而是提供者一侧的隐性劳动与 backlog 指标。这正是 `delegation_labor_delta` 的价值所在：它能直接回答 delegation 究竟是节省了系统劳动，还是仅仅换了劳动承担者。

### 3. 过载阈值存在，但它是窄带而不是万能常数

{_markdown_image(report_path, figure_paths['figure_05_threshold_phase_map'], '图 5 阈值相图')}

*图 5. Package B 的相图与低 delegation 带的细化阈值证据。*

主 atlas 只告诉我们 backlog 在哪里第一次可见，而细化扫描才支撑更克制、更正式的阈值陈述。在低 delegation refinement band 中，任务负载 3.0 时，压力仍维持在 {_fmt_num(threshold_30['stress_min'], 3)}-{_fmt_num(threshold_30['stress_max'], 3)}，backlog 基本可忽略；到了 3.25，压力跃升到 {_fmt_num(threshold_325['stress_min'], 3)}-{_fmt_num(threshold_325['stress_max'], 3)}，backlog 变为 {_fmt_num(threshold_325['backlog_min'], 2)}-{_fmt_num(threshold_325['backlog_max'], 2)}；到 3.5，系统几乎进入饱和，压力达到 {_fmt_num(threshold_35['stress_min'], 3)}-{_fmt_num(threshold_35['stress_max'], 3)}，backlog 扩大到 {_fmt_num(threshold_35['backlog_min'], 2)}-{_fmt_num(threshold_35['backlog_max'], 2)}。因此，比较稳妥的说法不是“找到了普适阈值”，而是“在当前模型切片下，反复观察到了 3.0-3.25 的狭窄过渡带”。

### 4. 低服务价格只在低负载区是缓冲器

{_markdown_image(report_path, figure_paths['figure_07_service_cost_context'], '图 7 服务价格上下文')}

*图 7. Package C 中的上下文扫描与低价翻转点。*

Package C 显示，价格效应是强上下文依赖的。在 Edge context 中，低价把压力从 {_fmt_num(edge_row['high_cost_stress'], 4)} 推高到 {_fmt_num(edge_row['low_cost_stress'], 4)}，同时把 backlog 从 {_fmt_num(edge_row['high_cost_backlog'], 4)} 放大到 {_fmt_num(edge_row['low_cost_backlog'], 4)}。在 Overloaded context 中，两种价格情景的压力都已饱和，但低价仍把 backlog 扩大到 {_fmt_num(overloaded_row['low_cost_backlog'], 2)}，而高价情景约为 {_fmt_num(overloaded_row['high_cost_backlog'], 2)}。因此，最值得保留的结论并不是“低价服务好或不好”，而是“低价是否减压，取决于系统离容量边界还有多远”。

### 5. Mixed-system instability 存在，但更有价值的是其负结果

{_markdown_image(report_path, figure_paths['figure_08_mixed_stability'], '图 8 mixed-system stability')}

*图 8. Mixed-system 区间内的离散程度与 seed 级最终 delegation 分布。*

Package D 的 mixed-state 分析确实检测到中间区间比极端区间更容易波动，但波动幅度相当有限。当前 deep dive 中最大的最终 delegation 标准差也只有 {_fmt_num(mixed_max_row['final_avg_delegation_rate_std'], 4)}，对应初始 delegation {_fmt_num(mixed_max_row['delegation_preference_mean'], 2)}、conformity {_fmt_num(mixed_max_row['social_conformity_pressure'], 2)}。这正是需要谦卑表达的地方：它给 H4 提供了部分支持，但同时也是一个有价值的负结果，因为当前参数带下并没有出现强烈的 bifurcation 或 lock-in 极化。

## 讨论、边界与谦卑表述

如果用一句话概括本轮实验，最稳健的结论并不是“便利一定更糟”，而是：便利型配置可以在主观体验上保持顺滑，同时在系统层面变得更劳动密集，并在接近容量边界时更脆弱。与此同时，本报告最有价值的地方也不只是具体结论，而是它如何把 qualitative observation 转译成可检验机制，并通过显式的数据落盘和证据边界控制分析强度。

这种克制并不是附加说明，而是研究质量本身的一部分。当前工作要展示的是：如何把社会观察 formalize 成模型结构，如何把模型结构映射为可追踪指标，以及如何在输出研究结论时持续提醒自己“哪些能说，哪些只能谨慎说，哪些当前根本不能说”。这也是本项目最直接体现 synthesis、conceptualization 与 data stewardship 能力的部分。

表 4 给出正式假设判断矩阵。

{zh_table_4}

源 CSV：{_link_relative(report_path, table_paths['table_04_hypothesis_verdict_matrix'], '表 4 CSV')}

表 5 给出 claim boundary 与 limitation table。

{zh_table_5}

源 CSV：{_link_relative(report_path, table_paths['table_05_claim_boundaries'], '表 5 CSV')}

## 结论与下一步模型扩展

基于当前 campaign，可以给出四点阶段性结论：

1. H1 获得强支持：更高 delegation 与更高总劳动稳定同向。
2. H2 获得强支持，但应严格表述为“在当前机制设定下观察到 3.0-3.25 的过渡带”。
3. H3 获得部分支持，因为模型更擅长度量 available time 与 stress proxy，而不是直接度量 convenience perception。
4. H4 获得部分支持，同时包含一个重要负结果：mixed systems 的确略不稳定，但远没有强烈滑向两极。

下一轮最值得扩展的机制已经很清楚：内生价格形成、显式等待耐受度、provider/requester 类型分化，以及更丰富的技能保持或技能退化机制。在这些机制加入之前，当前报告最适合被视为一项透明、克制且可审计的机制探索研究。
"""
    return text


def build_formal_report(
    campaign_dir: Path,
    *,
    report_dir: Path | None = None,
    asset_root: Path | None = None,
) -> ReportOutputs:
    """Build the full formal report package for one existing campaign.

    Args:
        campaign_dir: Existing narrative-campaign output directory.
        report_dir: Directory for the English and Chinese Markdown reports.
        asset_root: Directory for generated figures, tables, and manifest.

    Returns:
        ReportOutputs describing the generated artefacts.
    """

    report_dir = report_dir or REPORTS_DIR
    asset_root = asset_root or (campaign_dir / "report_assets" / "formal_report")
    figures_dir = _ensure_dir(asset_root / "figures")
    sources_dir = _ensure_dir(asset_root / "sources")
    tables_dir = _ensure_dir(asset_root / "tables")
    _ensure_dir(report_dir)

    inputs = _load_inputs(campaign_dir)
    combo_summary = inputs["combo_summary"]
    per_seed_summary = inputs["per_seed_summary"]
    threshold_refinement = inputs["threshold_refinement"]
    story_case_selection = inputs["story_case_selection"]

    question_map = _question_hypothesis_mapping()
    model_delta = _stable_vs_research_delta_table()
    key_cases = _story_case_key_table(story_case_selection)
    combined_timeseries = _combined_story_timeseries(story_case_selection)
    baseline_source = _baseline_horizon_source(combo_summary)
    atlas_source = _threshold_atlas_source(combo_summary)
    threshold_onset = _threshold_onset_table(atlas_source)
    threshold_summary = _threshold_refinement_summary(threshold_refinement)
    service_cost_context = _service_cost_context_source(combo_summary)
    service_cost_flip = _service_cost_flip_source(combo_summary)
    mixed_heatmap, mixed_points = _mixed_stability_sources(combo_summary, per_seed_summary)
    claim_boundaries = _parse_claim_safety_table(inputs["claim_safety_text"])
    hypothesis_matrix = _hypothesis_verdict_table(
        baseline_source,
        threshold_onset,
        service_cost_context,
        mixed_heatmap,
    )
    stats = _narrative_stats(
        combo_summary,
        per_seed_summary,
        threshold_refinement,
        service_cost_context,
        service_cost_flip,
        mixed_heatmap,
    )
    table_views = _table_display_frames(
        question_map,
        model_delta,
        key_cases,
        hypothesis_matrix,
        claim_boundaries,
    )

    table_paths = {
        "table_01_question_hypothesis_mapping": _save_csv(question_map, tables_dir / "table_01_question_hypothesis_mapping.csv"),
        "table_02_model_delta": _save_csv(model_delta, tables_dir / "table_02_model_delta.csv"),
        "table_03_key_scenario_comparison": _save_csv(key_cases, tables_dir / "table_03_key_scenario_comparison.csv"),
        "table_04_hypothesis_verdict_matrix": _save_csv(hypothesis_matrix, tables_dir / "table_04_hypothesis_verdict_matrix.csv"),
        "table_05_claim_boundaries": _save_csv(claim_boundaries, tables_dir / "table_05_claim_boundaries.csv"),
    }

    manifest_items: list[dict[str, object]] = []

    figure_paths = {}
    figure_paths["figure_01_causal_loop"], _ = _draw_causal_loop(figures_dir, sources_dir, manifest_items)
    figure_paths["figure_02_white_box_flow"], _ = _draw_flow_diagram(figures_dir, sources_dir, manifest_items)
    figure_paths["figure_03_baseline_horizon_panel"], _ = _draw_baseline_horizon_panel(
        baseline_source, figures_dir, sources_dir, manifest_items
    )
    figure_paths["figure_04_story_case_panel"], _ = _draw_story_case_panel(
        combined_timeseries, figures_dir, sources_dir, manifest_items
    )
    figure_paths["figure_05_threshold_phase_map"], _ = _draw_threshold_phase_map(
        atlas_source, threshold_onset, threshold_summary, figures_dir, sources_dir, manifest_items
    )
    figure_paths["figure_06_labor_transfer_decomposition"], _ = _draw_labor_transfer_decomposition(
        key_cases, figures_dir, sources_dir, manifest_items
    )
    figure_paths["figure_07_service_cost_context"], _ = _draw_service_cost_context(
        service_cost_context, service_cost_flip, figures_dir, sources_dir, manifest_items
    )
    figure_paths["figure_08_mixed_stability"], _ = _draw_mixed_stability(
        mixed_heatmap, mixed_points, figures_dir, sources_dir, manifest_items
    )

    for slug, path in table_paths.items():
        _add_manifest_entry(
            manifest_items,
            kind="table",
            slug=slug,
            path=path,
            alternate_paths=[],
            source_files=[path],
        )

    date_prefix = date.today().isoformat()
    english_report_path = report_dir / f"{date_prefix}_formal_campaign_{campaign_dir.name}_en.md"
    chinese_report_path = report_dir / f"{date_prefix}_formal_campaign_{campaign_dir.name}_zh.md"

    manifest_path = asset_root / "formal_report_manifest.json"
    english_report = _render_english_report(
        report_path=english_report_path,
        campaign_dir=campaign_dir,
        stats=stats,
        table_paths=table_paths,
        figure_paths=figure_paths,
        table_views=table_views,
        manifest_path=manifest_path,
    )
    chinese_report = _render_chinese_report(
        report_path=chinese_report_path,
        campaign_dir=campaign_dir,
        stats=stats,
        table_paths=table_paths,
        figure_paths=figure_paths,
        table_views=table_views,
        manifest_path=manifest_path,
    )

    _write_text(english_report_path, english_report)
    _write_text(chinese_report_path, chinese_report)
    _add_manifest_entry(
        manifest_items,
        kind="report",
        slug="formal_report_en",
        path=english_report_path,
        alternate_paths=[],
        source_files=list(table_paths.values()) + [Path(p) for p in figure_paths.values()],
    )
    _add_manifest_entry(
        manifest_items,
        kind="report",
        slug="formal_report_zh",
        path=chinese_report_path,
        alternate_paths=[],
        source_files=list(table_paths.values()) + [Path(p) for p in figure_paths.values()],
    )

    manifest_payload = {
        "campaign_dir": str(campaign_dir),
        "asset_root": str(asset_root),
        "reports": {
            "english": str(english_report_path),
            "chinese": str(chinese_report_path),
        },
        "items": manifest_items,
    }
    _write_text(manifest_path, json.dumps(manifest_payload, indent=2))

    return ReportOutputs(
        campaign_dir=campaign_dir,
        asset_root=asset_root,
        manifest_path=manifest_path,
        english_report_path=english_report_path,
        chinese_report_path=chinese_report_path,
    )


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the report builder."""

    parser = argparse.ArgumentParser(description="Build a formal report from an existing campaign.")
    parser.add_argument("--campaign-dir", required=True, help="Existing campaign directory.")
    parser.add_argument(
        "--report-dir",
        default=str(REPORTS_DIR),
        help="Directory for the English and Chinese Markdown reports.",
    )
    parser.add_argument(
        "--asset-root",
        default=None,
        help="Optional override for generated figures/tables/manifest.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    args = _parse_args()
    outputs = build_formal_report(
        Path(args.campaign_dir),
        report_dir=Path(args.report_dir),
        asset_root=Path(args.asset_root) if args.asset_root else None,
    )
    logger.info("English report: %s", outputs.english_report_path)
    logger.info("Chinese report: %s", outputs.chinese_report_path)
    logger.info("Manifest: %s", outputs.manifest_path)


if __name__ == "__main__":
    main()
