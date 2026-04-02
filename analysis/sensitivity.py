"""analysis/sensitivity.py — Sensitivity Analysis and Phase Diagrams

Architecture role:
    This module processes the CSV output from analysis/batch_runs.py and
    produces sensitivity analysis visualisations:
      - Heatmaps: outcome metric as a function of two parameters.
      - Phase diagrams: parameter space coloured by qualitative regime.
      - One-at-a-time (OAT) bar charts: relative parameter importance.

    All outputs are saved to data/results/ (gitignored). Matplotlib is used
    for publication-quality static figures; the Flask dashboard serves
    interactive Plotly versions of the same data.

    This module is run from the command line after batch_runs.py completes.

How to run:
    conda activate convenience-paradox
    python analysis/sensitivity.py --input data/results/<experiment_csv>
                                   --type heatmap
                                   --x_param delegation_preference_mean
                                   --y_param social_conformity_pressure
                                   --outcome avg_stress

Documentation standards (CLAUDE.md §9.2):
    Every heatmap output is accompanied by a written caption in the report
    identifying the axes, colour scale, and the most influential parameters.

See also:
    - analysis/batch_runs.py — generates the input CSV
    - analysis/plots.py      — additional matplotlib publication plots
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

REPORTS_DIR = PROJECT_ROOT / "analysis" / "reports"
RESULTS_DIR = PROJECT_ROOT / "data" / "results"


# ---------------------------------------------------------------------------
# Data loading and preparation
# ---------------------------------------------------------------------------

def load_batch_results(csv_path: Path) -> pd.DataFrame:
    """Load a batch_run CSV and prepare it for sensitivity analysis.

    batch_run produces one row per (run, step). For sensitivity analysis
    we typically want the *final equilibrium* value of each metric (last N steps).

    Args:
        csv_path: Path to the batch_run output CSV.

    Returns:
        DataFrame with one row per run, aggregated over the last 10 steps.

    Note:
        Equilibrium is approximated by averaging the last 10% of steps
        (or last 10 steps, whichever is larger). This smooths out
        short-term fluctuations to reveal the long-run tendency.
    """
    df = pd.read_csv(csv_path)
    logger.info("Loaded %d rows from %s", len(df), csv_path.name)

    # Identify the step column (Mesa batch_run uses "Step").
    step_col = "Step" if "Step" in df.columns else "step"
    if step_col not in df.columns:
        logger.warning("No step column found. Treating all rows as final step.")
        return df

    max_step = df[step_col].max()
    # Use last 10% of steps for equilibrium estimation, minimum 10 steps.
    tail_steps = max(10, int(max_step * 0.10))
    equilibrium_df = df[df[step_col] >= (max_step - tail_steps)]

    # Aggregate over replications: mean ± std of each outcome metric.
    # Group by parameter columns only.  We must exclude:
    #   • bookkeeping indices  (Step, RunId, iteration, AgentId / AgentID)
    #   • agent-level output metrics that are NOT simulation parameters
    # Failing to exclude agent-level columns causes pandas' internal group-index
    # computation to overflow a C long (OverflowError) on large datasets.
    known_agent_metrics = {
        "available_time", "stress_level", "delegation_preference", "income",
        "tasks_completed_self", "tasks_delegated", "time_spent_providing",
    }
    non_param_cols = {
        step_col, "Step", "RunId", "iteration",
        "AgentId", "AgentID",  # both case variants that Mesa / batch_run may produce
    } | known_agent_metrics

    param_cols = [c for c in df.columns if c not in non_param_cols
                  and c not in _get_outcome_cols(df)]

    # Drop any param column that is entirely NaN in the equilibrium window.
    # Mesa batch_run sometimes leaves replication-seed columns unpopulated for
    # agent-level rows; groupby(dropna=True) would then discard every row.
    param_cols = [c for c in param_cols if equilibrium_df[c].notna().any()]

    outcome_cols = _get_outcome_cols(df)
    if not param_cols or not outcome_cols:
        logger.warning("Could not identify parameter or outcome columns.")
        return equilibrium_df

    # Convert param columns to categorical so pandas uses compact integer codes
    # internally, preventing C-long overflow when many columns are grouped.
    eq = equilibrium_df.copy()
    for col in param_cols:
        eq[col] = eq[col].astype("category")

    agg_dict = {col: ["mean", "std"] for col in outcome_cols if col in eq.columns}
    aggregated = eq.groupby(param_cols).agg(agg_dict)
    aggregated.columns = ["_".join(c) for c in aggregated.columns]
    aggregated = aggregated.reset_index()

    logger.info(
        "Aggregated to %d unique parameter combinations (equilibrium values).",
        len(aggregated),
    )
    return aggregated


def _get_outcome_cols(df: pd.DataFrame) -> list[str]:
    """Return columns that are outcome metrics (not parameters or indices)."""
    known_outcomes = [
        "avg_stress", "total_labor_hours", "social_efficiency",
        "avg_delegation_rate", "tasks_delegated_frac", "gini_income",
        "gini_available_time", "unmatched_tasks", "avg_income",
    ]
    return [c for c in known_outcomes if c in df.columns]


# ---------------------------------------------------------------------------
# Heatmap (2D parameter sweep visualisation)
# ---------------------------------------------------------------------------

def plot_heatmap(
    df: pd.DataFrame,
    x_param: str,
    y_param: str,
    outcome: str,
    title: Optional[str] = None,
    output_path: Optional[Path] = None,
) -> plt.Figure:
    """Plot a heatmap of an outcome metric over a 2D parameter grid.

    This is the primary visualisation for H2 (threshold detection) and
    the 2D sensitivity analysis. The colour scale shows the equilibrium
    value of `outcome` for each (x_param, y_param) combination.

    Reading the heatmap:
      - Each cell = one parameter combination's equilibrium outcome.
      - Dark/warm colours = high values; light/cool = low values.
      - Abrupt colour transitions indicate threshold or bifurcation regions.

    Args:
        df: Aggregated batch_run results (one row per parameter combination).
        x_param: Parameter for the x-axis.
        y_param: Parameter for the y-axis.
        outcome: Outcome metric column to plot as colour.
        title: Optional plot title. If None, auto-generated.
        output_path: If provided, save figure to this path.

    Returns:
        matplotlib Figure object.
    """
    outcome_col = f"{outcome}_mean" if f"{outcome}_mean" in df.columns else outcome

    if x_param not in df.columns or y_param not in df.columns:
        raise ValueError(
            f"Parameters '{x_param}' and/or '{y_param}' not found in DataFrame. "
            f"Available: {list(df.columns)}"
        )
    if outcome_col not in df.columns:
        raise ValueError(
            f"Outcome '{outcome_col}' not found. Available: {list(df.columns)}"
        )

    # Pivot to 2D grid for imshow.
    pivot = df.pivot_table(
        index=y_param, columns=x_param, values=outcome_col, aggfunc="mean"
    )

    fig, ax = plt.subplots(figsize=(9, 7))

    # Choose a diverging colourmap for stress metrics, sequential for others.
    cmap = "RdYlGn_r" if "stress" in outcome else "viridis"
    im = ax.imshow(
        pivot.values,
        aspect="auto",
        origin="lower",
        cmap=cmap,
        interpolation="nearest",
    )

    # Axis labels: actual parameter values, not indices.
    x_vals = [f"{v:.2f}" for v in pivot.columns]
    y_vals = [f"{v:.2f}" for v in pivot.index]
    ax.set_xticks(range(len(x_vals)))
    ax.set_xticklabels(x_vals, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(y_vals)))
    ax.set_yticklabels(y_vals, fontsize=9)

    ax.set_xlabel(x_param.replace("_", " ").title(), fontsize=12)
    ax.set_ylabel(y_param.replace("_", " ").title(), fontsize=12)

    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(outcome.replace("_", " ").title(), fontsize=10)

    plot_title = title or (
        f"Sensitivity: {outcome.replace('_', ' ').title()} vs. "
        f"{x_param.replace('_', ' ').title()} × "
        f"{y_param.replace('_', ' ').title()}"
    )
    ax.set_title(plot_title, fontsize=13, pad=15)

    # Add text annotations in each cell (only if grid is small enough).
    if pivot.shape[0] * pivot.shape[1] <= 49:
        for i in range(pivot.shape[0]):
            for j in range(pivot.shape[1]):
                val = pivot.values[i, j]
                if not np.isnan(val):
                    ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                            fontsize=8, color="white" if val > pivot.values.mean() else "black")

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logger.info("Heatmap saved to %s", output_path)

    return fig


# ---------------------------------------------------------------------------
# One-at-a-time (OAT) sensitivity bar chart
# ---------------------------------------------------------------------------

def plot_oat_sensitivity(
    df: pd.DataFrame,
    outcome: str,
    parameters: Optional[list[str]] = None,
    output_path: Optional[Path] = None,
) -> plt.Figure:
    """Bar chart of parameter influence on an outcome metric (OAT analysis).

    For each parameter, compute the range of the outcome across that parameter's
    values (with all others at their modal value). Parameters with larger ranges
    have greater influence. This is a simple, interpretable sensitivity measure
    suitable for a theoretical ABM with relatively few parameters.

    Args:
        df: Aggregated batch_run results.
        outcome: Outcome metric to analyse.
        parameters: List of parameter column names to include. If None,
            auto-detected from known parameter names.
        output_path: If provided, save figure here.

    Returns:
        matplotlib Figure.
    """
    outcome_col = f"{outcome}_mean" if f"{outcome}_mean" in df.columns else outcome

    if parameters is None:
        known_params = [
            "delegation_preference_mean", "service_cost_factor",
            "social_conformity_pressure", "tasks_per_step_mean",
            "stress_threshold", "adaptation_rate",
        ]
        parameters = [p for p in known_params if p in df.columns]

    if not parameters:
        logger.warning("No recognised parameter columns found for OAT analysis.")
        return plt.figure()

    # For each parameter, compute outcome range (max − min across parameter values).
    ranges = {}
    for param in parameters:
        if param not in df.columns or outcome_col not in df.columns:
            continue
        grouped = df.groupby(param)[outcome_col].mean()
        if len(grouped) < 2:
            continue
        ranges[param] = grouped.max() - grouped.min()

    if not ranges:
        logger.warning("Insufficient data for OAT sensitivity chart.")
        return plt.figure()

    # Sort by influence (descending).
    sorted_params = sorted(ranges, key=ranges.get, reverse=True)
    sorted_ranges = [ranges[p] for p in sorted_params]
    labels = [p.replace("_", "\n") for p in sorted_params]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(labels, sorted_ranges, color="steelblue", edgecolor="white", linewidth=0.5)

    ax.set_ylabel(f"Range of {outcome.replace('_', ' ').title()}", fontsize=12)
    ax.set_title(
        f"Parameter Influence on {outcome.replace('_', ' ').title()} (OAT Sensitivity)",
        fontsize=13,
    )
    ax.tick_params(axis="x", labelsize=9)

    # Annotate bars with exact range values.
    for bar, val in zip(bars, sorted_ranges):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(sorted_ranges) * 0.01,
            f"{val:.3f}",
            ha="center", va="bottom", fontsize=8,
        )

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logger.info("OAT sensitivity chart saved to %s", output_path)

    return fig


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Command-line interface for generating sensitivity analysis plots."""
    parser = argparse.ArgumentParser(
        description="Generate sensitivity analysis plots from batch_run CSV output."
    )
    parser.add_argument("--input", required=True, help="Path to batch_run CSV file.")
    parser.add_argument(
        "--type", choices=["heatmap", "oat"], default="heatmap",
        help="Type of sensitivity plot to generate.",
    )
    parser.add_argument("--x_param", default="delegation_preference_mean")
    parser.add_argument("--y_param", default="social_conformity_pressure")
    parser.add_argument("--outcome", default="avg_stress")
    parser.add_argument("--output", default=None, help="Output image path (PNG).")
    args = parser.parse_args()

    csv_path = Path(args.input)
    df = load_batch_results(csv_path)

    output_path = Path(args.output) if args.output else (
        RESULTS_DIR / f"sensitivity_{args.type}_{args.outcome}.png"
    )

    if args.type == "heatmap":
        fig = plot_heatmap(df, args.x_param, args.y_param, args.outcome,
                           output_path=output_path)
    else:
        fig = plot_oat_sensitivity(df, args.outcome, output_path=output_path)

    plt.show()


if __name__ == "__main__":
    main()
