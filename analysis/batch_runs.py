"""analysis/batch_runs.py — Parameter Sweep Scripts using Mesa's batch_run

Architecture role:
    This script runs systematic parameter sweeps of the ConvenienceParadoxModel
    using Mesa's built-in `batch_run` facility. It is the primary tool for
    hypothesis testing (H1–H4) and the sensitivity analysis described in
    docs/plans/06_phase6_analysis_portfolio.md.

    Output is saved to CSV files in data/results/ (gitignored) and accompanied
    by a markdown summary report in analysis/reports/.

How to run:
    conda activate convenience-paradox
    cd /path/to/project
    python analysis/batch_runs.py --experiment h1_delegation_vs_labor
    python analysis/batch_runs.py --experiment h2_involution_threshold
    python analysis/batch_runs.py --experiment h4_mixed_stability
    python analysis/batch_runs.py --experiment full_sensitivity

Outputs:
    data/results/<experiment_name>_<timestamp>.csv   — raw batch_run results
    analysis/reports/<YYYY-MM-DD>_<experiment>.md    — structured summary report

Documentation standards (CLAUDE.md §9):
    Every experiment generates a markdown report with:
      - Experiment configuration (parameters, steps, replications)
      - Key findings summary
      - References to output CSV and plot files
      - Interpretation and next steps
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from mesa.batchrunner import batch_run

# Ensure the project root is on the path when running this script directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from model.model import ConvenienceParadoxModel
from model.params import TYPE_A_PRESET, TYPE_B_PRESET

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Output directory setup
# ---------------------------------------------------------------------------
RESULTS_DIR = PROJECT_ROOT / "data" / "results"
REPORTS_DIR = PROJECT_ROOT / "analysis" / "reports"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Experiment definitions
# ---------------------------------------------------------------------------

def run_h1_delegation_vs_labor(
    steps: int = 50,
    replications: int = 5,
    n_agents: int = 80,
) -> pd.DataFrame:
    """Experiment for Hypothesis H1: Higher delegation → higher total labour.

    Design:
        Sweep delegation_preference_mean from 0.10 to 0.90 in 9 increments.
        Hold all other parameters at their default (midpoint) values.
        For each combination, run `replications` independent realisations
        with different seeds to average out stochastic variation.

    Research question addressed:
        H1: "Higher service delegation rates lead to higher total systemic
        labor hours."

    Expected result:
        total_labor_hours should increase monotonically with
        delegation_preference_mean once delegation is high enough to
        trigger service provision overhead.

    Args:
        steps: Simulation steps (days) per run.
        replications: Number of independent runs per parameter combination.
        n_agents: Number of agents (lower than default for speed).

    Returns:
        DataFrame of batch_run results (one row per replication per step).
    """
    logger.info("Running H1 experiment: delegation rate vs. total labour hours.")

    # Sweep delegation preference across the full range.
    delegation_values = np.linspace(0.10, 0.90, 9).tolist()

    params = {
        "num_agents": n_agents,
        "delegation_preference_mean": delegation_values,
        "delegation_preference_std": [0.10],
        "service_cost_factor": [0.40],          # Held constant
        "social_conformity_pressure": [0.30],   # Held constant
        "tasks_per_step_mean": [2.5],
        "tasks_per_step_std": [0.75],
        "stress_threshold": [2.5],
        "stress_recovery_rate": [0.10],
        "adaptation_rate": [0.03],
        "initial_available_time": [8.0],
        "seed": list(range(replications)),       # Each seed = one replication
    }

    results = batch_run(
        ConvenienceParadoxModel,
        parameters=params,
        iterations=1,           # One run per parameter+seed combination
        max_steps=steps,
        number_processes=1,     # Single process for reproducibility on M4 Pro
        data_collection_period=1,
        display_progress=True,
    )

    df = pd.DataFrame(results)
    logger.info("H1 experiment complete: %d rows collected.", len(df))
    return df


def run_h2_involution_threshold(
    steps: int = 80,
    replications: int = 5,
    n_agents: int = 80,
) -> pd.DataFrame:
    """Experiment for Hypothesis H2: Critical threshold for involution spiral.

    Design:
        Sweep delegation_preference_mean and social_conformity_pressure
        simultaneously across a 7×5 grid. For each combination, run
        `replications` realisations. Look for the parameter region where
        avg_stress rises sharply or total_labor_hours jumps discontinuously —
        this is the involution threshold.

    Research question addressed:
        H2: "A critical delegation threshold exists beyond which the system
        enters an involution spiral."

    Expected result:
        A phase transition in avg_stress or social_efficiency as
        delegation_preference_mean crosses a threshold value.
        The threshold location may shift with conformity pressure.

    Args:
        steps: Steps per run (longer than H1 to allow spiral to emerge).
        replications: Replications per parameter combination.
        n_agents: Number of agents.

    Returns:
        DataFrame of batch_run results.
    """
    logger.info("Running H2 experiment: involution threshold detection.")

    delegation_values = np.linspace(0.10, 0.85, 7).tolist()
    conformity_values = np.linspace(0.10, 0.70, 5).tolist()

    params = {
        "num_agents": n_agents,
        "delegation_preference_mean": delegation_values,
        "social_conformity_pressure": conformity_values,
        "delegation_preference_std": [0.10],
        "service_cost_factor": [0.40],
        "tasks_per_step_mean": [2.5],
        "tasks_per_step_std": [0.75],
        "stress_threshold": [2.5],
        "stress_recovery_rate": [0.10],
        "adaptation_rate": [0.03],
        "initial_available_time": [8.0],
        "seed": list(range(replications)),
    }

    results = batch_run(
        ConvenienceParadoxModel,
        parameters=params,
        iterations=1,
        max_steps=steps,
        number_processes=1,
        data_collection_period=1,
        display_progress=True,
    )

    df = pd.DataFrame(results)
    logger.info("H2 experiment complete: %d rows collected.", len(df))
    return df


def run_h4_mixed_stability(
    steps: int = 100,
    replications: int = 8,
    n_agents: int = 80,
) -> pd.DataFrame:
    """Experiment for Hypothesis H4: Instability of mixed-delegation systems.

    Design:
        Focus on the moderate-delegation range (0.35–0.65).
        Run for more steps (100) to observe long-run convergence or drift.
        Compare variance of final avg_delegation_rate across replications
        with low (0.10) and high (0.80) starting preference — if mixed
        systems are unstable, their variance will be higher (they drift
        to different attractors depending on initial noise).

    Research question addressed:
        H4: "Mixed systems (moderate delegation) may be unstable, tending
        to drift toward extremes."

    Expected result:
        Runs starting at moderate delegation (≈0.50) should show higher
        variance in final avg_delegation_rate than runs starting at
        extreme values (0.10 or 0.80), consistent with an unstable
        mixed equilibrium between two stable attractors.

    Args:
        steps: Steps per run (long enough to observe convergence).
        replications: Replications per configuration (higher for variance).
        n_agents: Number of agents.

    Returns:
        DataFrame of batch_run results.
    """
    logger.info("Running H4 experiment: mixed-system stability analysis.")

    # Include extreme and mixed delegation starting points.
    delegation_values = [0.10, 0.35, 0.50, 0.65, 0.80]

    params = {
        "num_agents": n_agents,
        "delegation_preference_mean": delegation_values,
        "delegation_preference_std": [0.10],
        "service_cost_factor": [0.40],
        "social_conformity_pressure": [0.40],  # Moderate conformity to allow drift
        "tasks_per_step_mean": [2.5],
        "tasks_per_step_std": [0.75],
        "stress_threshold": [2.5],
        "stress_recovery_rate": [0.10],
        "adaptation_rate": [0.04],
        "initial_available_time": [8.0],
        "seed": list(range(replications)),
    }

    results = batch_run(
        ConvenienceParadoxModel,
        parameters=params,
        iterations=1,
        max_steps=steps,
        number_processes=1,
        data_collection_period=1,
        display_progress=True,
    )

    df = pd.DataFrame(results)
    logger.info("H4 experiment complete: %d rows collected.", len(df))
    return df


def run_full_sensitivity(
    steps: int = 50,
    replications: int = 3,
    n_agents: int = 60,
) -> pd.DataFrame:
    """Full sensitivity analysis: sweep all key parameters independently.

    Design:
        One-at-a-time (OAT) sensitivity analysis. Each parameter is swept
        across its valid range while all others are held at default values.
        This identifies which parameters have the greatest influence on
        avg_stress and total_labor_hours (the primary outcome metrics).

    Args:
        steps: Steps per run.
        replications: Replications per combination.
        n_agents: Number of agents.

    Returns:
        DataFrame of batch_run results.
    """
    logger.info("Running full sensitivity analysis (OAT).")

    # Each parameter is swept; others held at a representative midpoint.
    params = {
        "num_agents": n_agents,
        "delegation_preference_mean": np.linspace(0.10, 0.90, 7).tolist(),
        "service_cost_factor": np.linspace(0.10, 0.80, 5).tolist(),
        "social_conformity_pressure": np.linspace(0.10, 0.70, 5).tolist(),
        "tasks_per_step_mean": [1.5, 2.0, 2.5, 3.0, 3.5],
        "stress_threshold": [1.0, 1.5, 2.0, 2.5, 3.0],
        "delegation_preference_std": [0.10],  # Held constant
        "tasks_per_step_std": [0.75],
        "stress_recovery_rate": [0.10],
        "adaptation_rate": [0.03],
        "initial_available_time": [8.0],
        "seed": list(range(replications)),
    }

    results = batch_run(
        ConvenienceParadoxModel,
        parameters=params,
        iterations=1,
        max_steps=steps,
        number_processes=1,
        data_collection_period=1,
        display_progress=True,
    )

    df = pd.DataFrame(results)
    logger.info("Full sensitivity complete: %d rows collected.", len(df))
    return df


# ---------------------------------------------------------------------------
# Save and report utilities
# ---------------------------------------------------------------------------

def save_results(df: pd.DataFrame, experiment_name: str) -> Path:
    """Save batch_run results to a timestamped CSV file.

    Args:
        df: Results DataFrame from batch_run.
        experiment_name: Short name used in the filename.

    Returns:
        Path to the saved CSV file.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{experiment_name}_{timestamp}.csv"
    output_path = RESULTS_DIR / filename
    df.to_csv(output_path, index=False)
    logger.info("Results saved to %s", output_path)
    return output_path


def write_summary_report(
    experiment_name: str,
    df: pd.DataFrame,
    params_used: dict,
    csv_path: Path,
) -> Path:
    """Write a structured markdown summary report for the experiment.

    The report follows the CLAUDE.md §9.4 Summary Documentation standard:
      - Date and run configuration
      - Key findings in bullet-point form
      - CSV file reference
      - Conclusions and next steps

    Args:
        experiment_name: Short name for the experiment.
        df: Full results DataFrame.
        params_used: Dict describing the parameter sweep configuration.
        csv_path: Path to the saved CSV for reference.

    Returns:
        Path to the written markdown report.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    report_path = REPORTS_DIR / f"{date_str}_{experiment_name}.md"

    # Compute summary statistics for the report.
    outcome_cols = [
        c for c in ["avg_stress", "total_labor_hours", "social_efficiency",
                     "avg_delegation_rate", "tasks_delegated_frac"]
        if c in df.columns
    ]
    summary = df[outcome_cols].describe().round(4) if outcome_cols else None

    with open(report_path, "w") as f:
        f.write(f"# Batch Run Report: {experiment_name}\n\n")
        f.write(f"**Date**: {date_str}  \n")
        f.write(f"**Script**: `analysis/batch_runs.py`  \n")
        f.write(f"**Results file**: `{csv_path.name}`  \n\n")
        f.write("---\n\n")

        f.write("## Run Configuration\n\n")
        f.write("| Parameter | Value |\n|---|---|\n")
        for k, v in params_used.items():
            v_str = str(v)[:80]  # Truncate long lists for readability
            f.write(f"| `{k}` | {v_str} |\n")
        f.write(f"\n**Total rows collected**: {len(df):,}  \n")
        f.write(f"**Unique parameter combinations**: "
                f"{df.drop_duplicates(subset=['RunId']).shape[0] if 'RunId' in df.columns else 'N/A'}  \n\n")

        f.write("---\n\n")
        f.write("## Key Findings\n\n")
        f.write("*(Fill in after reviewing plots generated by analysis/plots.py)*\n\n")
        f.write("- [ ] Finding 1: \n")
        f.write("- [ ] Finding 2: \n")
        f.write("- [ ] Finding 3: \n\n")

        if summary is not None:
            f.write("## Outcome Variable Summary Statistics\n\n")
            f.write("```\n")
            f.write(summary.to_string())
            f.write("\n```\n\n")

        f.write("---\n\n")
        f.write("## Interpretation\n\n")
        f.write("*(Complete after visual inspection of plots)*\n\n")
        f.write("## Limitations\n\n")
        f.write("- Stochastic variation: each parameter combination was run with "
                f"{params_used.get('seed', 'N/A')} seeds.\n")
        f.write("- Network topology held constant (small_world) across all runs.\n")
        f.write("- Agent skill distributions are random and not varied in this sweep.\n\n")
        f.write("## Next Steps\n\n")
        f.write("- Run `analysis/plots.py` to generate heatmaps and time-series plots.\n")
        f.write("- Cross-reference findings with hypotheses in `docs/plans/00_master_plan.md`.\n")

    logger.info("Summary report written to %s", report_path)
    return report_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

EXPERIMENTS = {
    "h1_delegation_vs_labor": run_h1_delegation_vs_labor,
    "h2_involution_threshold": run_h2_involution_threshold,
    "h4_mixed_stability": run_h4_mixed_stability,
    "full_sensitivity": run_full_sensitivity,
}


def main() -> None:
    """Command-line interface for running batch experiments."""
    parser = argparse.ArgumentParser(
        description="Run parameter sweep experiments for The Convenience Paradox."
    )
    parser.add_argument(
        "--experiment",
        choices=list(EXPERIMENTS.keys()),
        required=True,
        help="Which experiment to run.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Override the number of simulation steps per run.",
    )
    parser.add_argument(
        "--replications",
        type=int,
        default=None,
        help="Override the number of replications per parameter combination.",
    )
    parser.add_argument(
        "--agents",
        type=int,
        default=None,
        help="Override the number of agents per run.",
    )
    args = parser.parse_args()

    run_fn = EXPERIMENTS[args.experiment]

    # Build kwargs, only passing overrides if provided.
    kwargs = {}
    if args.steps is not None:
        kwargs["steps"] = args.steps
    if args.replications is not None:
        kwargs["replications"] = args.replications
    if args.agents is not None:
        kwargs["n_agents"] = args.agents

    df = run_fn(**kwargs)
    csv_path = save_results(df, args.experiment)
    write_summary_report(args.experiment, df, kwargs, csv_path)


if __name__ == "__main__":
    main()
