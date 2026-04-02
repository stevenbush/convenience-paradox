"""analysis/plots.py — Publication-Quality Static Plots (matplotlib)

Architecture role:
    This module generates the publication-quality figures used in the
    README, analysis reports, and any potential conference presentations.
    All figures are produced with matplotlib and saved as PNG/PDF files.

    Unlike the interactive Plotly.js dashboard (Phase 3), these plots are
    designed for static export: clear labels, clean styling, and sufficient
    resolution for print or poster use.

Coverage:
    1. Type A vs. Type B time-series comparison (H1, H3).
    2. Delegation rate evolution trajectories.
    3. Agent-level stress distribution histograms.
    4. Social efficiency over time (H1/H2).
    5. Income inequality (Gini) trajectory.
    6. Individual agent trace (delegation preference over time).

How to run:
    conda activate convenience-paradox
    cd /path/to/project

    # Compare Type A vs. Type B over 50 steps:
    python analysis/plots.py --preset comparison --steps 50

    # Single run with custom parameters:
    python analysis/plots.py --preset custom --steps 30
                             --delegation 0.6 --conformity 0.5

Documentation standards (CLAUDE.md §9):
    Each saved figure includes a companion caption in the report describing
    what the chart shows in the context of the research hypotheses.

See also:
    - analysis/batch_runs.py — generates bulk data for sensitivity plots
    - analysis/sensitivity.py — heatmaps and OAT charts from batch data
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from model.model import ConvenienceParadoxModel
from model.params import TYPE_A_PRESET, TYPE_B_PRESET

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

RESULTS_DIR = PROJECT_ROOT / "data" / "results"
REPORTS_DIR = PROJECT_ROOT / "analysis" / "reports"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Use Agg backend for headless rendering (important for server contexts).
matplotlib.use("Agg")

# ---------------------------------------------------------------------------
# Colour scheme (consistent with dashboard styling)
# ---------------------------------------------------------------------------
# Type A: blue family (autonomy, cool, open)
# Type B: red family (convenience, warm, intense)
COLORS = {
    "type_a": "#2166AC",
    "type_b": "#D6604D",
    "neutral": "#4DAF4A",
    "accent": "#984EA3",
    "grid": "#E8E8E8",
}


# ---------------------------------------------------------------------------
# Simulation runners
# ---------------------------------------------------------------------------

def run_preset(preset_name: str, steps: int, seed: int = 42) -> tuple[ConvenienceParadoxModel, pd.DataFrame, pd.DataFrame]:
    """Run a simulation with a named preset and return the model + DataFrames.

    Args:
        preset_name: "type_a" or "type_b".
        steps: Number of simulation steps to run.
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (model instance, model_df, agent_df).
    """
    p = TYPE_A_PRESET if preset_name == "type_a" else TYPE_B_PRESET
    model = ConvenienceParadoxModel(
        num_agents=p["num_agents"],
        delegation_preference_mean=p["delegation_preference_mean"],
        delegation_preference_std=p["delegation_preference_std"],
        service_cost_factor=p["service_cost_factor"],
        social_conformity_pressure=p["social_conformity_pressure"],
        tasks_per_step_mean=p["tasks_per_step_mean"],
        tasks_per_step_std=p["tasks_per_step_std"],
        stress_threshold=p["stress_threshold"],
        stress_recovery_rate=p["stress_recovery_rate"],
        adaptation_rate=p["adaptation_rate"],
        initial_available_time=p["initial_available_time"],
        seed=seed,
    )
    logger.info("Running %s preset for %d steps...", preset_name, steps)
    for _ in range(steps):
        model.step()

    return model, model.get_model_dataframe(), model.get_agent_dataframe()


# ---------------------------------------------------------------------------
# Individual plot functions
# ---------------------------------------------------------------------------

def plot_type_ab_comparison(
    steps: int = 50,
    output_path: Path | None = None,
) -> plt.Figure:
    """Six-panel comparison of Type A vs. Type B society outcomes.

    This is the primary "money chart" for the portfolio: it shows at a glance
    how the two abstract societies diverge across the key outcome metrics.

    Panels:
        1. Average Stress (well-being proxy — H3)
        2. Total Labour Hours (involution indicator — H1)
        3. Average Delegation Rate (preference evolution — H4)
        4. Social Efficiency (collective productivity — H1/H2)
        5. Income Gini (inequality — exploratory)
        6. Unmatched Tasks (service shortage — H2 precursor)

    Args:
        steps: Simulation steps to run.
        output_path: Save path. If None, auto-generated in data/results/.

    Returns:
        matplotlib Figure.
    """
    logger.info("Generating Type A vs. Type B comparison plot (%d steps).", steps)

    _, df_a, _ = run_preset("type_a", steps)
    _, df_b, _ = run_preset("type_b", steps)

    # Reset index so Step is a column.
    df_a = df_a.reset_index().rename(columns={"index": "Step"})
    df_b = df_b.reset_index().rename(columns={"index": "Step"})

    metrics = [
        ("avg_stress",          "Average Stress Level",      "Stress [0–1]",           "H3: Lower in autonomy?"),
        ("total_labor_hours",   "Total System Labour Hours", "Hours/day",              "H1: Higher under delegation?"),
        ("avg_delegation_rate", "Mean Delegation Preference","Preference [0–1]",       "H4: Drift to extremes?"),
        ("social_efficiency",   "Social Efficiency",         "Tasks per labour-hour",  "H1/H2: Falls under involution?"),
        ("gini_income",         "Income Gini Coefficient",   "Gini [0–1]",             "Inequality measure"),
        ("unmatched_tasks",     "Unmatched Service Tasks",   "Tasks/day",              "H2: Demand overload signal"),
    ]

    fig = plt.figure(figsize=(15, 10))
    fig.suptitle(
        "The Convenience Paradox — Type A (Autonomy-Oriented) vs. "
        "Type B (Convenience-Oriented)\n"
        f"N=100 agents, {steps} simulated days, seed=42",
        fontsize=13, fontweight="bold", y=0.98,
    )

    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.40, wspace=0.35)

    for idx, (metric, label, ylabel, hypothesis_note) in enumerate(metrics):
        ax = fig.add_subplot(gs[idx // 3, idx % 3])

        if metric in df_a.columns:
            ax.plot(df_a["Step"], df_a[metric],
                    color=COLORS["type_a"], linewidth=2.0, label="Type A (Autonomy)")
        if metric in df_b.columns:
            ax.plot(df_b["Step"], df_b[metric],
                    color=COLORS["type_b"], linewidth=2.0, linestyle="--",
                    label="Type B (Convenience)")

        ax.set_xlabel("Simulation Day", fontsize=9)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.set_title(label, fontsize=11, fontweight="bold")
        ax.tick_params(labelsize=8)
        ax.grid(True, color=COLORS["grid"], linewidth=0.5)
        # Hypothesis note as a small annotation in the corner.
        ax.text(0.02, 0.97, hypothesis_note, transform=ax.transAxes,
                fontsize=7, va="top", color="#555555", style="italic")

        if idx == 0:
            ax.legend(fontsize=8, loc="upper right")

    # Neutrality disclaimer as figure-level footnote.
    fig.text(
        0.5, 0.01,
        "Note: 'Type A' and 'Type B' are abstract society configurations. "
        "This model does not characterise any specific country, culture, or people.",
        ha="center", fontsize=8, color="#666666", style="italic",
    )

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = RESULTS_DIR / f"type_ab_comparison_{ts}.png"

    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    logger.info("Type A/B comparison saved to %s", output_path)
    return fig


def plot_agent_stress_distribution(
    steps: int = 50,
    output_path: Path | None = None,
) -> plt.Figure:
    """Histogram of final agent stress levels for Type A vs. Type B.

    Shows the *distribution* of well-being, not just the mean.
    A high-delegation society may have a similar mean but a much heavier
    tail (some agents under severe time pressure).

    Args:
        steps: Steps to run before sampling agent states.
        output_path: Save path.

    Returns:
        matplotlib Figure.
    """
    model_a, _, agent_df_a = run_preset("type_a", steps)
    model_b, _, agent_df_b = run_preset("type_b", steps)

    # Final-step agent data.
    final_step = steps  # DataCollector index is 0-based; step 0 = initial state
    stress_a = agent_df_a.xs(final_step, level="Step")["stress_level"].values
    stress_b = agent_df_b.xs(final_step, level="Step")["stress_level"].values

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    fig.suptitle(
        f"Agent Stress Distribution at Day {steps} — Type A vs. Type B",
        fontsize=13, fontweight="bold",
    )

    bins = np.linspace(0, 1, 20)
    for ax, stress, color, label in [
        (axes[0], stress_a, COLORS["type_a"], "Type A (Autonomy-Oriented)"),
        (axes[1], stress_b, COLORS["type_b"], "Type B (Convenience-Oriented)"),
    ]:
        ax.hist(stress, bins=bins, color=color, alpha=0.8, edgecolor="white")
        ax.axvline(np.mean(stress), color="black", linestyle="--", linewidth=1.5,
                   label=f"Mean = {np.mean(stress):.3f}")
        ax.set_xlabel("Stress Level [0–1]", fontsize=11)
        ax.set_ylabel("Number of Agents", fontsize=11)
        ax.set_title(label, fontsize=11)
        ax.legend(fontsize=9)
        ax.grid(True, color=COLORS["grid"], linewidth=0.5)

    plt.tight_layout()

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = RESULTS_DIR / f"stress_distribution_{ts}.png"

    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    logger.info("Stress distribution plot saved to %s", output_path)
    return fig


def plot_single_run(
    delegation_preference_mean: float = 0.50,
    service_cost_factor: float = 0.40,
    social_conformity_pressure: float = 0.40,
    steps: int = 60,
    seed: int = 42,
    output_path: Path | None = None,
) -> plt.Figure:
    """Plot a single simulation run with custom parameters.

    Useful for exploring specific parameter combinations outside the presets.
    Shows all key metrics in a 3-panel layout.

    Args:
        delegation_preference_mean: Starting delegation preference.
        service_cost_factor: Service price multiplier.
        social_conformity_pressure: Peer influence strength.
        steps: Simulation steps to run.
        seed: Random seed.
        output_path: Save path.

    Returns:
        matplotlib Figure.
    """
    model = ConvenienceParadoxModel(
        num_agents=100,
        delegation_preference_mean=delegation_preference_mean,
        service_cost_factor=service_cost_factor,
        social_conformity_pressure=social_conformity_pressure,
        seed=seed,
    )
    for _ in range(steps):
        model.step()

    df = model.get_model_dataframe().reset_index().rename(columns={"index": "Step"})

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    fig.suptitle(
        f"Single Run: delegation={delegation_preference_mean:.2f}, "
        f"cost={service_cost_factor:.2f}, conformity={social_conformity_pressure:.2f}",
        fontsize=12, fontweight="bold",
    )

    plot_specs = [
        ("avg_stress",          "Average Stress",         COLORS["type_b"]),
        ("total_labor_hours",   "Total Labour Hours/Day", COLORS["neutral"]),
        ("avg_delegation_rate", "Mean Delegation Rate",   COLORS["accent"]),
    ]
    for ax, (metric, label, color) in zip(axes, plot_specs):
        if metric in df.columns:
            ax.plot(df["Step"], df[metric], color=color, linewidth=2.0)
        ax.set_xlabel("Simulation Day", fontsize=10)
        ax.set_ylabel(label, fontsize=10)
        ax.set_title(label, fontsize=11, fontweight="bold")
        ax.grid(True, color=COLORS["grid"], linewidth=0.5)

    plt.tight_layout()

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = RESULTS_DIR / f"single_run_{ts}.png"

    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    logger.info("Single run plot saved to %s", output_path)
    return fig


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Command-line interface for generating publication plots."""
    parser = argparse.ArgumentParser(
        description="Generate publication-quality plots for The Convenience Paradox."
    )
    parser.add_argument(
        "--preset",
        choices=["comparison", "distribution", "custom"],
        default="comparison",
        help="Which plot to generate.",
    )
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--delegation", type=float, default=0.50)
    parser.add_argument("--conformity", type=float, default=0.40)
    parser.add_argument("--cost", type=float, default=0.40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    output = Path(args.output) if args.output else None

    if args.preset == "comparison":
        plot_type_ab_comparison(steps=args.steps, output_path=output)
    elif args.preset == "distribution":
        plot_agent_stress_distribution(steps=args.steps, output_path=output)
    elif args.preset == "custom":
        plot_single_run(
            delegation_preference_mean=args.delegation,
            service_cost_factor=args.cost,
            social_conformity_pressure=args.conformity,
            steps=args.steps,
            seed=args.seed,
            output_path=output,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
