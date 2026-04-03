"""
Blog chart generator for "What a Toy World Taught Me About Convenience."

Produces 9 blog-optimized figures from campaign source CSVs.
Outputs PNG (300 dpi) and SVG to a specified directory.

Usage:
    python generate_blog_charts.py [--output-dir PATH]
"""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

# --- Paths (repo-relative; override output with --output-dir) ---
_REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = (
    _REPO_ROOT
    / "data/results/campaigns/20260401_235956_research_v2_15k_parallel_20260401"
)
SOURCES = CAMPAIGN / "report_assets" / "formal_report_v2" / "sources"
DEFAULT_OUT = Path(__file__).resolve().parent / "output"

# --- Consistent blog palette ---
PALETTE = {
    "type_a": "#3B6E8C",       # soft navy
    "type_b": "#C2665A",       # terracotta
    "safe": "#E8E4D9",         # warm off-white
    "transition": "#E8A855",   # warm amber
    "overload": "#B5362A",     # deep red
    "self_labor": "#3B6E8C",   # navy (self)
    "service_labor": "#6B9E6B",# sage green (service)
    "coordination": "#E8A855", # amber (coordination)
    "accent": "#D47B3E",       # warm orange
    "bg": "#FAFAF5",           # off-white background
    "text": "#2D2D2D",         # near-black text
    "grid": "#E0DDD4",         # warm grid
}


def blog_style(ax, title=None, xlabel=None, ylabel=None):
    """Apply consistent blog styling to an axes."""
    ax.set_facecolor(PALETTE["bg"])
    ax.figure.set_facecolor(PALETTE["bg"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(PALETTE["grid"])
    ax.spines["bottom"].set_color(PALETTE["grid"])
    ax.tick_params(colors=PALETTE["text"], labelsize=9)
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.5, alpha=0.7)
    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", color=PALETTE["text"],
                      pad=12)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=10, color=PALETTE["text"])
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10, color=PALETTE["text"])


def save(fig, out_dir, name):
    """Save figure as PNG and SVG."""
    fig.savefig(out_dir / f"{name}.png", dpi=300, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    fig.savefig(out_dir / f"{name}.svg", bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  saved {name}.png / .svg")


# ═══════════════════════════════════════════════════════════════════
# Figure 1: Causal loop diagram
# ═══════════════════════════════════════════════════════════════════
def fig_causal_loop(out_dir):
    nodes = pd.read_csv(SOURCES / "figure_01_causal_loop_nodes.csv")
    edges = pd.read_csv(SOURCES / "figure_01_causal_loop_edges.csv")

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_facecolor(PALETTE["bg"])
    fig.set_facecolor(PALETTE["bg"])
    ax.set_xlim(-0.15, 1.15)
    ax.set_ylim(-0.15, 1.15)
    ax.set_aspect("equal")
    ax.axis("off")

    # Draw nodes
    node_positions = {}
    for _, row in nodes.iterrows():
        name = row["node"].strip()
        x, y = row["x"], row["y"]
        node_positions[name] = (x, y)
        bbox_color = PALETTE["type_b"] if name in [
            "Delegation\nIntensity", "Provider\nBurden", "Stress &\nAdaptation",
            "Backlog\nCarryover"
        ] else PALETTE["type_a"]
        ax.annotate(
            name.replace("\n", "\n"), (x, y),
            ha="center", va="center", fontsize=8, fontweight="bold",
            color="white",
            bbox=dict(boxstyle="round,pad=0.4", facecolor=bbox_color, alpha=0.85,
                      edgecolor="none"),
        )

    # Draw edges
    for _, row in edges.iterrows():
        src = row["src"].strip()
        tgt = row["tgt"].strip()
        sign = row["sign"].strip()
        if src in node_positions and tgt in node_positions:
            sx, sy = node_positions[src]
            tx, ty = node_positions[tgt]
            color = PALETTE["overload"] if sign == "+" else PALETTE["type_a"]
            ax.annotate(
                "", xy=(tx, ty), xytext=(sx, sy),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.5,
                                connectionstyle="arc3,rad=0.15"),
            )
            # Sign label at midpoint
            mx, my = (sx + tx) / 2, (sy + ty) / 2
            ax.text(mx + 0.03, my + 0.03, sign, fontsize=9, fontweight="bold",
                    color=color, ha="center", va="center")

    # Loop labels
    ax.text(0.42, 0.55, "R1", fontsize=14, fontweight="bold",
            color=PALETTE["overload"], ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                      edgecolor=PALETTE["overload"], linewidth=1.5))
    ax.text(0.22, 0.65, "R2", fontsize=14, fontweight="bold",
            color=PALETTE["type_b"], ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                      edgecolor=PALETTE["type_b"], linewidth=1.5))

    fig.suptitle("Conceptual Causal Loop: Convenience, Backlog, and Norm Reinforcement",
                 fontsize=12, fontweight="bold", color=PALETTE["text"], y=0.96)
    ax.text(0.5, -0.08,
            "R1: Stress → Delegation → Provider Burden → Time Loss → Backlog → Stress (reinforcing)\n"
            "R2: Delegation → Norm → Convenience → Delegation (reinforcing)",
            transform=ax.transAxes, fontsize=7, ha="center", va="top",
            color=PALETTE["text"], fontstyle="italic", alpha=0.7)

    save(fig, out_dir, "fig-causal-loop")


# ═══════════════════════════════════════════════════════════════════
# Figure 2: Horizon panel (6-metric comparison)
# ═══════════════════════════════════════════════════════════════════
def fig_horizon_panel(out_dir):
    df = pd.read_csv(SOURCES / "figure_04_horizon_panel.csv")

    metrics = [
        ("tail_total_labor_hours_mean", "Total Labor Hours", "Hours"),
        ("tail_avg_stress_mean", "Average Stress", "Stress [0–1]"),
        ("final_available_time_mean_mean", "Final Available Time", "Hours"),
        ("tail_tasks_delegated_frac_mean", "Delegated Task Share", "Fraction"),
        ("tail_gini_income_mean", "Income Inequality (Gini)", "Gini"),
        ("tail_gini_available_time_mean", "Time Inequality (Gini)", "Gini"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(13, 7.5))
    fig.set_facecolor(PALETTE["bg"])

    for ax, (col, title, ylabel) in zip(axes.flat, metrics):
        for society, color, marker in [
            ("Type A", PALETTE["type_a"], "o"),
            ("Type B", PALETTE["type_b"], "s"),
        ]:
            sub = df[df["society"] == society].sort_values("steps")
            ax.plot(sub["steps"], sub[col], marker=marker, color=color,
                    linewidth=2, markersize=6, label=society)
        blog_style(ax, title=title, xlabel="Simulation Horizon (steps)",
                   ylabel=ylabel)
        ax.legend(fontsize=8, frameon=False)

    fig.suptitle("Type A and Type B Remain Structurally Different Across Longer Horizons",
                 fontsize=13, fontweight="bold", color=PALETTE["text"], y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    save(fig, out_dir, "fig-horizon-panel")


# ═══════════════════════════════════════════════════════════════════
# Figure 3: Available time density
# ═══════════════════════════════════════════════════════════════════
def fig_available_time_density(out_dir):
    df = pd.read_csv(SOURCES / "figure_10_available_time_density.csv")

    fig, ax = plt.subplots(figsize=(8, 4.5))

    for society, color, label in [
        ("Type A", PALETTE["type_a"], "Type A (Autonomy)"),
        ("Type B", PALETTE["type_b"], "Type B (Convenience)"),
    ]:
        vals = df[df["society"] == society]["available_time"]
        ax.hist(vals, bins=30, alpha=0.55, color=color, label=label,
                edgecolor="white", linewidth=0.5, density=True)

    blog_style(ax, title="Available Time Distribution at Final Step",
               xlabel="Available Time (hours)", ylabel="Density")
    ax.legend(fontsize=10, frameon=False)

    # Annotate means
    for society, color, va in [("Type A", PALETTE["type_a"], "bottom"),
                                ("Type B", PALETTE["type_b"], "top")]:
        mean_val = df[df["society"] == society]["available_time"].mean()
        ax.axvline(mean_val, color=color, linestyle="--", linewidth=1.5, alpha=0.7)
        ax.text(mean_val + 0.1, ax.get_ylim()[1] * (0.9 if va == "top" else 0.7),
                f"mean: {mean_val:.1f}h", fontsize=9, color=color, fontweight="bold")

    save(fig, out_dir, "fig-available-time-density")


# ═══════════════════════════════════════════════════════════════════
# Figure 4: Phase atlas (hero image)
# ═══════════════════════════════════════════════════════════════════
def fig_phase_atlas(out_dir):
    df = pd.read_csv(SOURCES / "figure_06_phase_atlas.csv")
    onset = pd.read_csv(SOURCES / "figure_06_threshold_onset.csv")

    # Pivot for heatmap
    pivot = df.pivot_table(
        index="tasks_per_step_mean", columns="delegation_preference_mean",
        values="tail_backlog_tasks_mean"
    )

    fig, ax = plt.subplots(figsize=(9, 6.5))

    # Log-scale colormap
    data = np.log1p(pivot.values)
    im = ax.imshow(
        data, aspect="auto", origin="lower",
        extent=[
            pivot.columns.min() - 0.025, pivot.columns.max() + 0.025,
            pivot.index.min() - 0.125, pivot.index.max() + 0.125,
        ],
        cmap="YlOrRd", interpolation="bilinear",
    )

    # Threshold onset line
    if "delegation_preference_mean" in onset.columns and "first_backlog_task_load" in onset.columns:
        onset_sorted = onset.sort_values("delegation_preference_mean")
        ax.plot(
            onset_sorted["delegation_preference_mean"],
            onset_sorted["first_backlog_task_load"],
            "o-", color=PALETTE["type_a"], linewidth=2, markersize=5,
            label="First visible backlog", zorder=5,
        )

    cb = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cb.set_label("log(1 + backlog tasks)", fontsize=9, color=PALETTE["text"])

    blog_style(ax, title="Delegation–Task Load Phase Atlas: Backlog Emergence",
               xlabel="Delegation Preference Mean",
               ylabel="Task Load Mean (tasks/step)")
    ax.legend(fontsize=9, frameon=True, facecolor="white", edgecolor=PALETTE["grid"],
              loc="upper left")

    # Zone annotations
    ax.text(0.15, 2.0, "Safe zone", fontsize=10, color=PALETTE["type_a"],
            fontstyle="italic", alpha=0.8)
    ax.text(0.15, 3.1, "Transition band", fontsize=10, color=PALETTE["accent"],
            fontstyle="italic", alpha=0.9)
    ax.text(0.15, 4.5, "Overloaded regime", fontsize=10, color=PALETTE["overload"],
            fontstyle="italic", fontweight="bold", alpha=0.9)

    save(fig, out_dir, "fig-phase-atlas")


# ═══════════════════════════════════════════════════════════════════
# Figure 5: Story timeseries (4 cases)
# ═══════════════════════════════════════════════════════════════════
def fig_story_timeseries(out_dir):
    df = pd.read_csv(SOURCES / "figure_08_story_timeseries.csv")

    case_colors = {
        "Autonomy Baseline": PALETTE["type_a"],
        "Convenience Baseline": PALETTE["service_labor"],
        "Threshold Pressure": PALETTE["transition"],
        "Overloaded Convenience": PALETTE["overload"],
    }

    metrics = [
        ("avg_stress", "Average Stress", "Stress [0–1]"),
        ("total_labor_hours", "Total Labor Hours", "Hours"),
        ("backlog_tasks", "Backlog Tasks", "Tasks"),
        ("delegation_match_rate", "Delegation Match Rate", "Rate [0–1]"),
        ("avg_delegation_rate", "Delegation Preference", "Preference [0–1]"),
        ("service_labor_hours", "Service Labor Hours", "Hours"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(14, 7.5))
    fig.set_facecolor(PALETTE["bg"])

    for ax, (col, title, ylabel) in zip(axes.flat, metrics):
        for case, color in case_colors.items():
            sub = df[df["case_title"] == case].sort_values("Step")
            ax.plot(sub["Step"], sub[col], color=color, linewidth=1.2,
                    label=case, alpha=0.85)
        blog_style(ax, title=title, xlabel="Simulation Step", ylabel=ylabel)

    # Single legend at bottom
    handles = [mpatches.Patch(color=c, label=l) for l, c in case_colors.items()]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=9,
               frameon=False, bbox_to_anchor=(0.5, -0.02))

    fig.suptitle("System Dynamics: Four Story Cases from Relief to Overload",
                 fontsize=13, fontweight="bold", color=PALETTE["text"], y=0.98)
    fig.tight_layout(rect=[0, 0.04, 1, 0.94])
    save(fig, out_dir, "fig-story-timeseries")


# ═══════════════════════════════════════════════════════════════════
# Figure 6: Labor decomposition (stacked bar)
# ═══════════════════════════════════════════════════════════════════
def fig_labor_decomposition(out_dir):
    df = pd.read_csv(SOURCES / "figure_09_labor_decomposition.csv")

    cases = df["case"].tolist()
    self_h = df["tail_self_labor_hours"].values
    service_h = df["tail_service_labor_hours"].values
    coord_h = df["tail_coordination_hours"].values
    total_h = df["tail_total_labor_hours"].values
    delta = df["tail_delegation_labor_delta"].values

    x = np.arange(len(cases))
    width = 0.55

    fig, ax1 = plt.subplots(figsize=(9, 5.5))

    # Stacked bars
    ax1.bar(x, self_h, width, label="Self Labor", color=PALETTE["self_labor"],
            edgecolor="white", linewidth=0.5)
    ax1.bar(x, service_h, width, bottom=self_h, label="Service Labor",
            color=PALETTE["service_labor"], edgecolor="white", linewidth=0.5)
    ax1.bar(x, coord_h, width, bottom=self_h + service_h,
            label="Coordination", color=PALETTE["coordination"],
            edgecolor="white", linewidth=0.5)

    blog_style(ax1, title="Labor Composition: Convenience Reshapes Before It Overloads",
               ylabel="Tail Labor Hours")

    ax1.set_xticks(x)
    ax1.set_xticklabels(cases, fontsize=9, rotation=15, ha="right")
    ax1.legend(fontsize=9, frameon=False, loc="upper left")

    # Delta line on secondary axis
    ax2 = ax1.twinx()
    ax2.plot(x, delta, "D-", color=PALETTE["accent"], linewidth=2, markersize=7,
             label="Labor Delta", zorder=5)
    ax2.set_ylabel("Delegation Labor Delta", fontsize=10, color=PALETTE["accent"])
    ax2.tick_params(axis="y", colors=PALETTE["accent"])
    ax2.spines["right"].set_color(PALETTE["accent"])
    ax2.spines["top"].set_visible(False)
    ax2.legend(fontsize=9, frameon=False, loc="upper right")

    # Total annotations
    for i, t in enumerate(total_h):
        ax1.text(i, t + 8, f"{t:.0f}h", ha="center", fontsize=8,
                 fontweight="bold", color=PALETTE["text"])

    fig.tight_layout()
    save(fig, out_dir, "fig-labor-decomposition")


# ═══════════════════════════════════════════════════════════════════
# Figure 7: Cost sensitivity
# ═══════════════════════════════════════════════════════════════════
def fig_cost_sensitivity(out_dir):
    ctx = pd.read_csv(SOURCES / "figure_13_cost_context.csv")
    flip = pd.read_csv(SOURCES / "figure_13_cost_flip.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5),
                                    gridspec_kw={"width_ratios": [1.3, 1]})
    fig.set_facecolor(PALETTE["bg"])

    # Panel (a): stress comparison across contexts
    x = np.arange(len(ctx))
    w = 0.3
    ax1.scatter(x - w/2, ctx["low_cost_stress"], s=80, color=PALETTE["type_a"],
                marker="o", label="Low Cost", zorder=5)
    ax1.scatter(x + w/2, ctx["high_cost_stress"], s=80, color=PALETTE["type_b"],
                marker="s", label="High Cost", zorder=5)
    for i in range(len(ctx)):
        ax1.plot([i - w/2, i + w/2],
                 [ctx["low_cost_stress"].iloc[i], ctx["high_cost_stress"].iloc[i]],
                 color=PALETTE["grid"], linewidth=1, zorder=1)

    ax1.set_xticks(x)
    ax1.set_xticklabels(ctx["context"], fontsize=9, rotation=15, ha="right")
    blog_style(ax1, title="(a) Stress: Low vs High Service Cost",
               ylabel="Tail Average Stress")
    ax1.legend(fontsize=9, frameon=False)

    # Panel (b): flip-point
    flip_sorted = flip.sort_values("delegation_preference_mean")
    ax2.plot(flip_sorted["delegation_preference_mean"],
             flip_sorted["flip_task_load"],
             "o-", color=PALETTE["accent"], linewidth=2, markersize=7)
    ax2.fill_between(flip_sorted["delegation_preference_mean"],
                     flip_sorted["flip_task_load"],
                     ax2.get_ylim()[0] if ax2.get_ylim()[0] > 0 else 0,
                     alpha=0.1, color=PALETTE["transition"])
    blog_style(ax2, title="(b) Cost-Amplification Threshold",
               xlabel="Delegation Preference Mean",
               ylabel="Task Load Where Low Cost\nFlips to Higher Stress")

    fig.suptitle("Service Cost Is Conditional: Relief at Low Load, Amplification Near Threshold",
                 fontsize=12, fontweight="bold", color=PALETTE["text"], y=1.02)
    fig.tight_layout()
    save(fig, out_dir, "fig-cost-sensitivity")


# ═══════════════════════════════════════════════════════════════════
# Figure 8: Mixed-system stability
# ═══════════════════════════════════════════════════════════════════
def fig_mixed_stability(out_dir):
    scatter = pd.read_csv(SOURCES / "figure_12_mixed_scatter.csv")

    fig, ax = plt.subplots(figsize=(7, 5.5))

    # Color by conformity pressure
    cmap = plt.cm.YlOrRd
    norm = plt.Normalize(
        scatter["social_conformity_pressure"].min(),
        scatter["social_conformity_pressure"].max()
    )

    sc = ax.scatter(
        scatter["delegation_preference_mean"],
        scatter["final_avg_delegation_rate"],
        c=scatter["social_conformity_pressure"],
        cmap=cmap, norm=norm, s=20, alpha=0.6, edgecolors="none",
    )

    # Identity line
    lim = [0.3, 0.7]
    ax.plot(lim, lim, "--", color=PALETTE["grid"], linewidth=1.5,
            label="Identity (no drift)")

    cb = fig.colorbar(sc, ax=ax, shrink=0.8)
    cb.set_label("Social Conformity Pressure", fontsize=9, color=PALETTE["text"])

    blog_style(ax, title="Mixed-System Stability: The Middle Holds",
               xlabel="Initial Delegation Preference Mean",
               ylabel="Final Delegation Rate")
    ax.legend(fontsize=9, frameon=True, facecolor="white", edgecolor=PALETTE["grid"])
    ax.set_xlim(0.3, 0.7)
    ax.set_ylim(0.3, 0.7)

    # Annotate max drift
    ax.text(0.55, 0.38, "Max drift: 0.0125 std\n(on 0–1 scale)",
            fontsize=9, fontstyle="italic", color=PALETTE["text"],
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor=PALETTE["grid"], alpha=0.9))

    save(fig, out_dir, "fig-mixed-stability")


# ═══════════════════════════════════════════════════════════════════
# Figure 9: Claim boundaries
# ═══════════════════════════════════════════════════════════════════
def fig_claim_boundaries(out_dir):
    tiers = [
        ("Can Say\nConfidently", [
            "ABM identifies parameter regions where\nhigher delegation → higher total labor",
            "ABM compares stress, labor, inequality\nevolution under different configs",
            "ABM tests whether moderate delegation\nstates remain stable",
        ], "#6B9E6B"),
        ("Can Say\nWith Caveat", [
            "Lower prices push toward more delegation\n(exogenous experiment only)",
            "Norm lock-in approximated through\ndelegation convergence proxies",
            "Convenience shifts burdens toward providers\n(exact labor market outside scope)",
        ], PALETTE["transition"]),
        ("Cannot Claim\nFrom Model", [
            "Full causal loop (prices not endogenous)",
            "Real population measurements\nor named societies",
            "Skill decay, demographic inequality,\ndelay-tolerance dynamics",
        ], PALETTE["overload"]),
    ]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_facecolor(PALETTE["bg"])
    fig.set_facecolor(PALETTE["bg"])
    ax.axis("off")

    for col, (tier_name, claims, color) in enumerate(tiers):
        x_center = 0.17 + col * 0.33

        # Tier header
        ax.text(x_center, 0.92, tier_name, transform=ax.transAxes,
                fontsize=12, fontweight="bold", ha="center", va="top",
                color="white",
                bbox=dict(boxstyle="round,pad=0.4", facecolor=color,
                          edgecolor="none", alpha=0.9))

        # Claims
        for i, claim in enumerate(claims):
            y = 0.68 - i * 0.25
            ax.text(x_center, y, claim, transform=ax.transAxes,
                    fontsize=8.5, ha="center", va="top", color=PALETTE["text"],
                    bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                              edgecolor=color, linewidth=1.2, alpha=0.95))

    fig.suptitle("Claim Boundaries: What the Model Can and Cannot Assert",
                 fontsize=13, fontweight="bold", color=PALETTE["text"], y=0.98)
    save(fig, out_dir, "fig-claim-boundaries")


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Generate blog charts")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {out}")

    generators = [
        ("fig-causal-loop", fig_causal_loop),
        ("fig-horizon-panel", fig_horizon_panel),
        ("fig-available-time-density", fig_available_time_density),
        ("fig-phase-atlas", fig_phase_atlas),
        ("fig-story-timeseries", fig_story_timeseries),
        ("fig-labor-decomposition", fig_labor_decomposition),
        ("fig-cost-sensitivity", fig_cost_sensitivity),
        ("fig-mixed-stability", fig_mixed_stability),
        ("fig-claim-boundaries", fig_claim_boundaries),
    ]

    for name, gen_func in generators:
        print(f"Generating {name}...")
        try:
            gen_func(out)
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\nDone. {len(generators)} figures generated in {out}")


if __name__ == "__main__":
    main()
