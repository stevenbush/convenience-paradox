"""analysis/formal_campaign_report_v2.py — Publication-quality research report builder.

Architecture role:
    Reads an existing narrative-campaign output directory and produces:
      - 15 publication-quality figures (PNG 250 dpi + SVG)
      - source CSVs for every figure and table
      - one English Markdown report
      - one Chinese Markdown translation
      - a provenance manifest

    This module never runs simulations. It is strictly post-hoc.

Design principles:
    - Abstract labels only (Type A / Type B). No country references.
    - Every figure has a saved source CSV for auditability.
    - Report explicitly frames itself as a methodological demonstration,
      not authoritative social science.
"""

from __future__ import annotations

import argparse
import gzip
import json
import logging
import math
import os
import textwrap
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / "data" / "results" / ".mplconfig"))

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

REPORTS_DIR = PROJECT_ROOT / "analysis" / "reports"
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PACKAGE_A = "package_a_everyday_friction"
PACKAGE_B = "package_b_convenience_transfer"
PACKAGE_C = "package_c_cheap_service_trap"
PACKAGE_D = "package_d_norm_lock_in"

COLORS = {
    "type_a": "#2166AC",
    "type_b": "#B2182B",
    "threshold": "#E66101",
    "overloaded": "#7A0177",
    "neutral": "#636363",
    "provider": "#1B7837",
    "coordination": "#E6AB02",
    "backlog": "#762A83",
    "self_labor": "#2166AC",
    "service_labor": "#1B7837",
    "coord_labor": "#E6AB02",
    "grid": "#EEEEEE",
    "fill_a": "#D1E5F0",
    "fill_b": "#FDDBC7",
    "bg": "#FAFAFA",
}

STYLE = {
    "font_family": "DejaVu Serif",
    "base_size": 10.5,
    "figure_title_size": 13,
    "panel_title_size": 11,
    "axis_label_size": 10.5,
    "legend_size": 9,
    "tick_size": 9,
    "annotation_size": 8.5,
    "legend_edge": "#D9D9D9",
    "note_bg": (1.0, 1.0, 1.0, 0.82),
}

FIGURE_DISPLAY_WIDTHS = {
    "wide": 1040,
    "standard": 920,
    "compact": 760,
}

WIDE_FIGURES = {
    "figure_02_model_lifecycle",
    "figure_04_horizon_panel",
    "figure_05_agent_distributions",
    "figure_07_threshold_detail",
    "figure_08_story_timeseries",
    "figure_13_cost_sensitivity",
    "figure_14_param_sensitivity",
}

COMPACT_FIGURES = {
    "figure_03_radar_profile",
    "figure_10_available_time_density",
    "figure_11_mixed_heatmap",
    "figure_12_mixed_scatter",
}

FIGURE_CAPTIONS_EN = {
    "figure_01_causal_loop": "Figure 1. Conceptual causal loop.",
    "figure_02_model_lifecycle": "Figure 2. White-box model lifecycle.",
    "figure_03_radar_profile": "Figure 3. Type A and Type B parameter profiles.",
    "figure_04_horizon_panel": "Figure 4. Horizon comparison across key metrics.",
    "figure_05_agent_distributions": "Figure 5. Agent-level outcome distributions.",
    "figure_06_phase_atlas": "Figure 6. Delegation-task load phase atlas.",
    "figure_07_threshold_detail": "Figure 7. Threshold transition detail.",
    "figure_08_story_timeseries": "Figure 8. Four story-case system trajectories.",
    "figure_09_labor_decomposition": "Figure 9. Labor decomposition by case.",
    "figure_10_available_time_density": "Figure 10. Available-time distribution.",
    "figure_11_mixed_heatmap": "Figure 11. Mixed-system stability heatmap.",
    "figure_12_mixed_scatter": "Figure 12. Per-seed mixed-system outcomes.",
    "figure_13_cost_sensitivity": "Figure 13. Service-cost sensitivity.",
    "figure_14_param_sensitivity": "Figure 14. Parameter sensitivity panel.",
    "figure_15_campaign_coverage": "Figure 15. Campaign coverage map.",
}

FIGURE_CAPTIONS_ZH = {
    "figure_01_causal_loop": "图 1. 概念因果环路。",
    "figure_02_model_lifecycle": "图 2. 白盒模型生命周期。",
    "figure_03_radar_profile": "图 3. A 类与 B 类参数画像。",
    "figure_04_horizon_panel": "图 4. 关键指标的时长对比。",
    "figure_05_agent_distributions": "图 5. 代理层结果分布。",
    "figure_06_phase_atlas": "图 6. 委托-任务负荷相位图谱。",
    "figure_07_threshold_detail": "图 7. 阈值转变细节。",
    "figure_08_story_timeseries": "图 8. 四类故事案例动态轨迹。",
    "figure_09_labor_decomposition": "图 9. 各案例劳动结构分解。",
    "figure_10_available_time_density": "图 10. 可用时间分布。",
    "figure_11_mixed_heatmap": "图 11. 混合系统稳定性热力图。",
    "figure_12_mixed_scatter": "图 12. 混合系统逐种子结果。",
    "figure_13_cost_sensitivity": "图 13. 服务成本敏感性。",
    "figure_14_param_sensitivity": "图 14. 参数敏感性面板。",
    "figure_15_campaign_coverage": "图 15. 实验覆盖范围图。",
}

STORY_ORDER = [
    "autonomy_baseline",
    "convenience_baseline",
    "threshold_pressure",
    "overloaded_convenience",
]

STORY_LABELS = {
    "autonomy_baseline": "Autonomy Baseline",
    "convenience_baseline": "Convenience Baseline",
    "threshold_pressure": "Threshold Pressure",
    "overloaded_convenience": "Overloaded Convenience",
}

STORY_COLORS = {
    "autonomy_baseline": COLORS["type_a"],
    "convenience_baseline": COLORS["type_b"],
    "threshold_pressure": COLORS["threshold"],
    "overloaded_convenience": COLORS["overloaded"],
}


@dataclass(frozen=True)
class ReportOutputs:
    """Paths returned by the formal report pipeline."""
    campaign_dir: Path
    asset_root: Path
    manifest_path: Path
    english_report_path: Path
    chinese_report_path: Path


# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------

def _apply_style() -> None:
    """Configure matplotlib for publication-quality output.

    Note: constrained_layout is deliberately *not* used.  Instead, each
    figure calls :func:`_finalize_fig` which applies ``tight_layout`` with
    explicit top margin and a uniformly-positioned suptitle.
    """
    plt.rcParams.update({
        "font.family": STYLE["font_family"],
        "font.size": STYLE["base_size"],
        "axes.titlesize": STYLE["panel_title_size"],
        "axes.titleweight": "bold",
        "axes.labelsize": STYLE["axis_label_size"],
        "axes.labelcolor": "#2E2E2E",
        "axes.titlepad": 10,
        "axes.facecolor": COLORS["bg"],
        "axes.edgecolor": "#444444",
        "axes.linewidth": 0.9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": COLORS["grid"],
        "grid.linewidth": 0.6,
        "grid.alpha": 0.75,
        "legend.frameon": True,
        "legend.framealpha": 0.95,
        "legend.fontsize": STYLE["legend_size"],
        "legend.edgecolor": STYLE["legend_edge"],
        "xtick.labelsize": STYLE["tick_size"],
        "ytick.labelsize": STYLE["tick_size"],
        "xtick.color": "#333333",
        "ytick.color": "#333333",
        "figure.facecolor": "white",
        "figure.dpi": 100,
        "savefig.dpi": 250,
        "image.interpolation": "nearest",
    })


def _finalize_fig(fig: plt.Figure, title: str, *, top: float = 0.91,
                  use_tight: bool = True) -> None:
    """Apply tight layout and add a non-overlapping suptitle.

    Call immediately before ``_save_figure``.  Using a single helper keeps
    title position, font size, and margin allocation uniform across all 15
    figures, resolving the title-overlap issues caused by constrained_layout.
    """
    if use_tight:
        try:
            fig.tight_layout(rect=[0.025, 0.035, 0.985, top])
        except Exception:
            pass
    fig.patch.set_facecolor("white")
    fig.suptitle(
        title,
        fontsize=STYLE["figure_title_size"],
        fontweight="bold",
        y=top + 0.042,
    )


def _set_panel_title(ax: plt.Axes, title: str) -> None:
    """Apply a consistent panel-title style across multi-panel figures."""
    ax.set_title(title, fontsize=STYLE["panel_title_size"], fontweight="bold", pad=10)


def _style_legend(ax: plt.Axes, **kwargs) -> None:
    """Render legends with a consistent framed style."""
    fontsize = kwargs.pop("fontsize", STYLE["legend_size"])
    legend = ax.legend(frameon=True, fontsize=fontsize, **kwargs)
    if legend is None:
        return
    frame = legend.get_frame()
    frame.set_facecolor("white")
    frame.set_edgecolor(STYLE["legend_edge"])
    frame.set_linewidth(0.8)


def _style_colorbar(cbar, label: str) -> None:
    """Apply consistent font sizing to colorbars."""
    cbar.set_label(label, fontsize=STYLE["axis_label_size"])
    cbar.ax.tick_params(labelsize=STYLE["tick_size"])


def _outlined(artist, *, foreground: str = "white", linewidth: float = 2.4) -> None:
    """Add a halo so lines and text remain readable over heatmaps."""
    artist.set_path_effects([pe.Stroke(linewidth=linewidth, foreground=foreground), pe.Normal()])


def _annotate_note(ax: plt.Axes, text: str, *, x: float = 0.02, y: float = 0.02,
                   ha: str = "left", color: str = "#2E2E2E") -> None:
    """Place a boxed note inside an axis with consistent styling."""
    ax.text(
        x,
        y,
        text,
        transform=ax.transAxes,
        ha=ha,
        va="bottom",
        fontsize=STYLE["annotation_size"],
        color=color,
        style="italic",
        bbox={"boxstyle": "round,pad=0.25", "fc": STYLE["note_bg"], "ec": "none"},
    )


def _heatmap_extent(values: list[float] | np.ndarray) -> list[float]:
    """Return padded imshow extents so edge cells and annotations are not clipped."""
    vals = np.array(sorted(values), dtype=float)
    if len(vals) == 1:
        delta = 0.5
    else:
        deltas = np.diff(vals)
        delta = float(np.min(deltas)) / 2
    return [float(vals[0] - delta), float(vals[-1] + delta)]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")


def _save_csv(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def _save_figure(fig: plt.Figure, png_path: Path, svg_path: Path) -> None:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=250, bbox_inches="tight", facecolor="white")
    fig.savefig(svg_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _markdown_table(df: pd.DataFrame) -> str:
    string_df = df.fillna("").astype(str)
    headers = list(string_df.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in string_df.iterrows():
        lines.append("| " + " | ".join(row.tolist()) + " |")
    return "\n".join(lines)


def _fmt(v: float, d: int = 3) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{v:.{d}f}"


def _fmt_pct(v: float, d: int = 1) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{v:.{d}f}%"


def _preferred_report_asset(target: Path) -> Path:
    """Prefer SVG in reports for sharper text rendering when available."""
    svg_target = target.with_suffix(".svg")
    return svg_target if svg_target.exists() else target


def _figure_display_width(slug: str) -> int:
    """Choose a consistent display width tier by figure layout type."""
    if slug in WIDE_FIGURES:
        return FIGURE_DISPLAY_WIDTHS["wide"]
    if slug in COMPACT_FIGURES:
        return FIGURE_DISPLAY_WIDTHS["compact"]
    return FIGURE_DISPLAY_WIDTHS["standard"]


def _figure_caption(slug: str, language: str) -> str:
    """Return a localized short caption for the rendered report figure card."""
    if language == "zh":
        return FIGURE_CAPTIONS_ZH.get(slug, slug)
    return FIGURE_CAPTIONS_EN.get(slug, slug)


def _md_img(from_path: Path, target: Path, alt: str, *, language: str = "en") -> str:
    render_target = _preferred_report_asset(target)
    rel = os.path.relpath(render_target.resolve(), start=from_path.resolve().parent).replace(os.sep, "/")
    width = _figure_display_width(alt)
    caption = _figure_caption(alt, language)
    return (
        f'<figure style="margin:1.6rem auto 1.25rem auto; width:100%; max-width:{width}px;">'
        f'<div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; '
        f'padding:14px 14px 10px 14px; box-shadow:0 1px 2px rgba(15,23,42,0.06);">'
        f'<img src="{rel}" alt="{alt}" width="{width}" loading="lazy" '
        f'style="display:block; width:100%; max-width:{width}px; height:auto; margin:0 auto;" />'
        f"</div>"
        f'<figcaption style="margin-top:0.55rem; text-align:center; font-size:0.92rem; '
        f'line-height:1.45; color:#6b7280;">{caption}</figcaption>'
        f"</figure>"
    )


def _strip_indent(text: str) -> str:
    """Remove exactly 4-space leading indent from lines (for indented f-strings)."""
    lines = text.splitlines()
    return "\n".join(line[4:] if line.startswith("    ") else line for line in lines)


def _md_link(from_path: Path, target: Path, label: str) -> str:
    rel = os.path.relpath(target.resolve(), start=from_path.resolve().parent).replace(os.sep, "/")
    return f"[{label}](<{rel}>)"


def _add_manifest(
    items: list[dict],
    *,
    kind: str,
    slug: str,
    path: Path,
    sources: list[Path],
    alts: list[Path] | None = None,
) -> None:
    items.append({
        "kind": kind,
        "slug": slug,
        "path": str(path),
        "alternate_paths": [str(p) for p in (alts or [])],
        "source_files": [str(p) for p in sources],
    })


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_inputs(campaign_dir: Path) -> dict:
    """Load all persisted campaign inputs needed for the report."""
    sd = campaign_dir / "summaries"
    inputs = {
        "manifest": json.loads(_read_text(campaign_dir / "manifest.json")),
        "combo": pd.read_csv(sd / "combo_summary.csv"),
        "per_seed": pd.read_csv(sd / "per_seed_summary.csv"),
        "threshold_refine": pd.read_csv(sd / "threshold_refinement_per_seed.csv"),
        "preset_decomp": pd.read_csv(sd / "preset_decomposition_per_seed.csv"),
        "story_sel": pd.read_csv(sd / "story_case_selection.csv"),
        "claim_text": _read_text(campaign_dir / "writing_support" / "claim_safety_table.md"),
    }
    return inputs


def _load_agent_snapshots(campaign_dir: Path, scenarios: list[str]) -> dict[str, pd.DataFrame]:
    """Load agent snapshots at the final step for selected story cases.

    Returns dict: scenario_id -> DataFrame of agent-level data (final step only).
    """
    result: dict[str, pd.DataFrame] = {}
    story_sel = pd.read_csv(campaign_dir / "summaries" / "story_case_selection.csv")
    for _, row in story_sel.iterrows():
        sid = row["scenario_id"]
        if sid not in scenarios:
            continue
        snap_path = row.get("agent_snapshots")
        if not snap_path or not Path(snap_path).exists():
            continue
        with gzip.open(snap_path, "rt") as f:
            df = pd.read_csv(f)
        max_step = df["Step"].max()
        result[sid] = df[df["Step"] == max_step].copy()
    return result


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------

def _baseline_horizon_source(combo: pd.DataFrame) -> pd.DataFrame:
    pkg_a = combo[
        (combo["package_slug"] == PACKAGE_A)
        & (combo["experiment_slug"] == "preset_horizon_scan")
    ].copy()
    pkg_a["society"] = np.where(
        pkg_a["scenario_id"].str.startswith("type_a"), "Type A", "Type B"
    )
    cols = [
        "society", "steps",
        "tail_total_labor_hours_mean", "tail_avg_stress_mean",
        "tail_tasks_delegated_frac_mean", "final_available_time_mean_mean",
        "tail_gini_income_mean", "tail_gini_available_time_mean",
        "tail_backlog_tasks_mean",
    ]
    return pkg_a[cols].sort_values(["steps", "society"]).reset_index(drop=True)


def _story_case_key_table(story_sel: pd.DataFrame) -> pd.DataFrame:
    table = story_sel[story_sel["scenario_id"].isin(STORY_ORDER)].copy()
    cols_map = {
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
    available_cols = [c for c in cols_map if c in table.columns]
    table = table[available_cols].rename(columns=cols_map)
    return table.reset_index(drop=True)


def _combined_story_timeseries(story_sel: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for _, record in story_sel.iterrows():
        if record["scenario_id"] not in STORY_ORDER:
            continue
        ts_path = record.get("model_timeseries")
        if not ts_path or not Path(ts_path).exists():
            continue
        frame = pd.read_csv(ts_path, compression="gzip")
        frame["scenario_id"] = record["scenario_id"]
        frame["case_title"] = record["title"]
        rows.append(frame)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _threshold_atlas_source(combo: pd.DataFrame) -> pd.DataFrame:
    atlas = combo[
        (combo["package_slug"] == PACKAGE_B)
        & (combo["experiment_slug"] == "delegation_task_load_atlas")
    ].copy()
    return atlas[
        ["delegation_preference_mean", "tasks_per_step_mean",
         "tail_backlog_tasks_mean", "tail_avg_stress_mean",
         "tail_total_labor_hours_mean", "tail_delegation_labor_delta_mean"]
    ].sort_values(["delegation_preference_mean", "tasks_per_step_mean"]).reset_index(drop=True)


def _threshold_onset_table(atlas: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for deleg, sub in atlas.groupby("delegation_preference_mean"):
        sub = sub.sort_values("tasks_per_step_mean")
        visible = sub[sub["tail_backlog_tasks_mean"] > 0.1]
        if visible.empty:
            continue
        first = visible.iloc[0]
        rows.append({
            "delegation_preference_mean": deleg,
            "first_backlog_task_load": first["tasks_per_step_mean"],
            "avg_stress_at_onset": first["tail_avg_stress_mean"],
            "backlog_at_onset": first["tail_backlog_tasks_mean"],
        })
    return pd.DataFrame(rows).sort_values("delegation_preference_mean").reset_index(drop=True)


def _threshold_refinement_summary(refine: pd.DataFrame) -> pd.DataFrame:
    focus = refine[refine["delegation_preference_mean"].isin([0.05, 0.10, 0.15, 0.20])].copy()
    cell = focus.groupby(["delegation_preference_mean", "tasks_per_step_mean"]).agg(
        tail_avg_stress_mean=("tail_avg_stress", "mean"),
        tail_backlog_tasks_mean=("tail_backlog_tasks", "mean"),
    ).reset_index()
    return cell.groupby("tasks_per_step_mean").agg(
        stress_min=("tail_avg_stress_mean", "min"),
        stress_max=("tail_avg_stress_mean", "max"),
        backlog_min=("tail_backlog_tasks_mean", "min"),
        backlog_max=("tail_backlog_tasks_mean", "max"),
    ).reset_index().sort_values("tasks_per_step_mean")


def _context_label(raw: str) -> str:
    mapping = {
        "default_context": "Default", "type_a_context": "Type A",
        "type_b_context": "Type B", "edge_context": "Edge",
        "overloaded_context": "Overloaded",
    }
    return mapping.get(raw, raw.replace("_", " ").title())


def _service_cost_context_source(combo: pd.DataFrame) -> pd.DataFrame:
    cs = combo[
        (combo["package_slug"] == PACKAGE_C)
        & (combo["experiment_slug"] == "service_cost_context_scan")
    ].copy()
    cs["context"] = cs["scenario_id"].str.extract(r"^(.*)_serv")
    cs["context"] = cs["context"].map(_context_label)
    rows: list[dict] = []
    for ctx, sub in cs.groupby("context"):
        sub = sub.sort_values("service_cost_factor")
        lo, hi = sub.iloc[0], sub.iloc[-1]
        rows.append({
            "context": ctx,
            "low_cost_factor": lo["service_cost_factor"],
            "high_cost_factor": hi["service_cost_factor"],
            "low_cost_stress": lo["tail_avg_stress_mean"],
            "high_cost_stress": hi["tail_avg_stress_mean"],
            "low_cost_labor": lo["tail_total_labor_hours_mean"],
            "high_cost_labor": hi["tail_total_labor_hours_mean"],
            "low_cost_delegated_frac": lo["tail_tasks_delegated_frac_mean"],
            "high_cost_delegated_frac": hi["tail_tasks_delegated_frac_mean"],
            "low_cost_backlog": lo["tail_backlog_tasks_mean"],
            "high_cost_backlog": hi["tail_backlog_tasks_mean"],
        })
    return pd.DataFrame(rows)


def _service_cost_flip_source(combo: pd.DataFrame) -> pd.DataFrame:
    atlas = combo[
        (combo["package_slug"] == PACKAGE_C)
        & (combo["experiment_slug"] == "service_cost_task_load_atlas")
    ].copy()
    lo_cost = atlas["service_cost_factor"].min()
    hi_cost = atlas["service_cost_factor"].max()
    rows: list[dict] = []
    for deleg, sub in atlas.groupby("delegation_preference_mean"):
        if deleg < 0.35:
            continue
        lo = sub[sub["service_cost_factor"] == lo_cost].sort_values("tasks_per_step_mean")
        hi = sub[sub["service_cost_factor"] == hi_cost].sort_values("tasks_per_step_mean")
        merged = lo.merge(hi, on=["delegation_preference_mean", "tasks_per_step_mean"],
                          suffixes=("_low", "_high"))
        flipped = merged[merged["tail_avg_stress_mean_low"] > merged["tail_avg_stress_mean_high"]]
        if flipped.empty:
            continue
        first = flipped.iloc[0]
        rows.append({
            "delegation_preference_mean": deleg,
            "flip_task_load": first["tasks_per_step_mean"],
            "dStress": first["tail_avg_stress_mean_low"] - first["tail_avg_stress_mean_high"],
        })
    return pd.DataFrame(rows).sort_values("delegation_preference_mean").reset_index(drop=True)


def _mixed_stability_sources(combo: pd.DataFrame, per_seed: pd.DataFrame):
    hm = combo[
        (combo["package_slug"] == PACKAGE_D)
        & (combo["experiment_slug"] == "mixed_stability_deep_dive")
    ][["delegation_preference_mean", "social_conformity_pressure",
       "final_avg_delegation_rate_mean", "final_avg_delegation_rate_std",
       "tail_backlog_tasks_mean"]].copy()
    pt = per_seed[
        (per_seed["package_slug"] == PACKAGE_D)
        & (per_seed["experiment_slug"] == "mixed_stability_deep_dive")
    ][["scenario_id", "seed", "delegation_preference_mean",
       "social_conformity_pressure", "final_avg_delegation_rate",
       "tail_backlog_tasks"]].copy()
    return hm, pt


def _parse_claim_safety(text: str) -> pd.DataFrame:
    rows: list[dict] = []
    section = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("## "):
            section = line[3:].strip()
        elif line.startswith("- "):
            rows.append({"claim_status": section, "statement": line[2:].strip()})
    return pd.DataFrame(rows)


def _question_hypothesis_mapping() -> pd.DataFrame:
    return pd.DataFrame([
        {"research_question": "Do stable everyday frictions signal a deeper time-allocation architecture?",
         "hypothesis": "H3 (partial)", "package": "Package A",
         "primary_metrics": "labor hours, stress, available time, delegation fraction",
         "analysis_role": "Long-horizon baseline comparison"},
        {"research_question": "Does convenience eliminate labor or relocate it inside the system?",
         "hypothesis": "H1, H2", "package": "Package B",
         "primary_metrics": "self/service/coordination labor, backlog, labor delta",
         "analysis_role": "Labor-transfer decomposition and threshold mapping"},
        {"research_question": "How much can low service price explain by itself?",
         "hypothesis": "H2 (contextual)", "package": "Package C",
         "primary_metrics": "stress, backlog, delegation fraction, labor hours",
         "analysis_role": "Service-cost sensitivity and cost-flip analysis"},
        {"research_question": "Do mixed systems drift toward extremes under norm pressure?",
         "hypothesis": "H4 (partial negative)", "package": "Package D",
         "primary_metrics": "final delegation rate, delegation rate std",
         "analysis_role": "Mixed-state dispersion assessment"},
    ])


def _model_delta_table() -> pd.DataFrame:
    return pd.DataFrame([
        {"mechanism": "Unmatched tasks", "stable": "Discarded each step",
         "research_v2": "Carried over as backlog", "significance": "Makes overload cumulative"},
        {"mechanism": "Provider eligibility", "stable": "Loose threshold",
         "research_v2": "Must cover full service time", "significance": "Tighter supply constraint"},
        {"mechanism": "Delegation friction", "stable": "Implicit",
         "research_v2": "15% coordination cost", "significance": "Delegation is not free"},
        {"mechanism": "Provider overhead", "stable": "Simple timing",
         "research_v2": "11% service overhead", "significance": "Serving others costs extra"},
        {"mechanism": "Labor accounting", "stable": "Aggregate only",
         "research_v2": "Self / service / coordination split", "significance": "Tests labor-transfer claim"},
    ])


def _hypothesis_verdict(baseline: pd.DataFrame, onset: pd.DataFrame,
                         cost_ctx: pd.DataFrame, mixed_hm: pd.DataFrame) -> pd.DataFrame:
    h450 = baseline[baseline["steps"] == 450].set_index("society")
    labor_pct = ((h450.loc["Type B", "tail_total_labor_hours_mean"]
                  / h450.loc["Type A", "tail_total_labor_hours_mean"]) - 1.0) * 100.0
    avg_onset = onset["first_backlog_task_load"].mean()
    over = cost_ctx[cost_ctx["context"] == "Overloaded"]
    over_bl = over.iloc[0]["low_cost_backlog"] if len(over) else 0
    max_std = mixed_hm["final_avg_delegation_rate_std"].max()
    return pd.DataFrame([
        {"hypothesis": "H1", "judgment": "Strong support",
         "evidence": f"Type B maintains a {_fmt_pct(labor_pct)} labor premium at 450 steps.",
         "interpretation": "Higher delegation is consistently linked to more total system labor."},
        {"hypothesis": "H2", "judgment": "Strong support",
         "evidence": f"Threshold band at task load {_fmt(avg_onset, 2)}, refined to 3.0\u20133.25.",
         "interpretation": "A narrow overload band precedes the high-backlog regime."},
        {"hypothesis": "H3", "judgment": "Partial support",
         "evidence": f"Type A retains {_fmt(h450.loc['Type A', 'final_available_time_mean_mean'], 2)}h "
                     f"vs {_fmt(h450.loc['Type B', 'final_available_time_mean_mean'], 2)}h for Type B.",
         "interpretation": "Autonomy preserves more personal time; convenience is not directly measured."},
        {"hypothesis": "H4", "judgment": "Partial (important negative)",
         "evidence": f"Max mixed-state std = {_fmt(max_std, 4)}.",
         "interpretation": "Moderate instability, but no dramatic bifurcation under current parameters."},
    ])


def _narrative_stats(combo, per_seed, refine, cost_ctx, cost_flip, mixed_hm,
                     *, key_table=None) -> dict:
    """Compute all scalar values referenced by the report f-strings."""
    bl = _baseline_horizon_source(combo)
    h450 = bl[bl["steps"] == 450].set_index("society")
    ta, tb = h450.loc["Type A"], h450.loc["Type B"]
    ref_sum = _threshold_refinement_summary(refine)
    ref30 = ref_sum[ref_sum["tasks_per_step_mean"] == 3.0]
    mixed_max = mixed_hm.sort_values("final_avg_delegation_rate_std", ascending=False).iloc[0]
    over = cost_ctx[cost_ctx["context"] == "Overloaded"]
    stats: dict = {
        "n_combo": len(combo), "n_per_seed": len(per_seed),
        "labor_delta_pct": ((tb["tail_total_labor_hours_mean"] / ta["tail_total_labor_hours_mean"]) - 1) * 100,
        "ta_avail": ta["final_available_time_mean_mean"],
        "tb_avail": tb["final_available_time_mean_mean"],
        "ta_stress": ta["tail_avg_stress_mean"],
        "tb_stress": tb["tail_avg_stress_mean"],
        "ta_labor": ta["tail_total_labor_hours_mean"],
        "tb_labor": tb["tail_total_labor_hours_mean"],
        "ta_deleg_frac": ta["tail_tasks_delegated_frac_mean"],
        "tb_deleg_frac": tb["tail_tasks_delegated_frac_mean"],
        "threshold_center": ref30.iloc[0]["tasks_per_step_mean"] if len(ref30) else 3.0,
        "mixed_max_std": mixed_max["final_avg_delegation_rate_std"],
        "over_backlog": over.iloc[0]["low_cost_backlog"] if len(over) else 0,
    }
    # --- Horizon comparison at earlier steps ---
    for horizon in [120, 200, 300]:
        hx = bl[bl["steps"] == horizon].set_index("society")
        if "Type A" in hx.index and "Type B" in hx.index:
            ta_l = hx.loc["Type A", "tail_total_labor_hours_mean"]
            stats[f"h{horizon}_ta_labor"] = ta_l
            stats[f"h{horizon}_tb_labor"] = hx.loc["Type B", "tail_total_labor_hours_mean"]
            stats[f"h{horizon}_delta_pct"] = (
                (hx.loc["Type B", "tail_total_labor_hours_mean"] / ta_l) - 1
            ) * 100 if ta_l else 0
    # --- Gini coefficients at 450 steps ---
    for suffix in ["gini_income", "gini_available_time"]:
        col = f"tail_{suffix}_mean"
        stats[f"ta_{suffix}"] = ta.get(col, float("nan"))
        stats[f"tb_{suffix}"] = tb.get(col, float("nan"))
    # --- Story-case data (used in expanded per-figure analysis) ---
    if key_table is not None and not key_table.empty:
        prefix_map = {
            "Autonomy Baseline": "auto", "Convenience Baseline": "conv",
            "Threshold Pressure": "thresh", "Overloaded Convenience": "overload",
        }
        for _, row in key_table.iterrows():
            pfx = prefix_map.get(str(row.get("case", "")), "")
            if not pfx:
                continue
            for col in row.index:
                if col == "case":
                    continue
                try:
                    stats[f"{pfx}_{col}"] = float(row[col])
                except (ValueError, TypeError):
                    stats[f"{pfx}_{col}"] = row[col]
    # --- Cost-context summary ---
    for _, row in cost_ctx.iterrows():
        ctx = str(row["context"]).lower().replace(" ", "_")
        stats[f"cost_{ctx}_low_stress"] = row["low_cost_stress"]
        stats[f"cost_{ctx}_high_stress"] = row["high_cost_stress"]
        stats[f"cost_{ctx}_low_backlog"] = row["low_cost_backlog"]
        stats[f"cost_{ctx}_high_backlog"] = row["high_cost_backlog"]
    return stats


# ---------------------------------------------------------------------------
# Figure functions
# ---------------------------------------------------------------------------

def _fig01_causal_loop(fdir: Path, sdir: Path, manifest: list) -> tuple[Path, Path]:
    """Improved causal loop diagram with R/B loop labels and polarity markers."""
    nodes = pd.DataFrame([
        {"node": "Delegation\nIntensity", "x": 0.50, "y": 0.92},
        {"node": "Provider\nBurden", "x": 0.85, "y": 0.72},
        {"node": "Available\nPersonal Time", "x": 0.85, "y": 0.32},
        {"node": "Stress &\nAdaptation", "x": 0.15, "y": 0.32},
        {"node": "Delegation\nConvenience", "x": 0.15, "y": 0.72},
        {"node": "Norm\nReinforcement", "x": 0.50, "y": 0.52},
        {"node": "Backlog\nCarryover", "x": 0.50, "y": 0.12},
    ])
    edges = pd.DataFrame([
        {"src": "Delegation\nIntensity", "tgt": "Provider\nBurden", "sign": "+"},
        {"src": "Provider\nBurden", "tgt": "Available\nPersonal Time", "sign": "\u2212"},
        {"src": "Available\nPersonal Time", "tgt": "Backlog\nCarryover", "sign": "\u2212"},
        {"src": "Backlog\nCarryover", "tgt": "Stress &\nAdaptation", "sign": "+"},
        {"src": "Stress &\nAdaptation", "tgt": "Delegation\nIntensity", "sign": "+"},
        {"src": "Delegation\nIntensity", "tgt": "Norm\nReinforcement", "sign": "+"},
        {"src": "Norm\nReinforcement", "tgt": "Delegation\nConvenience", "sign": "+"},
        {"src": "Delegation\nConvenience", "tgt": "Delegation\nIntensity", "sign": "+"},
        {"src": "Norm\nReinforcement", "tgt": "Stress &\nAdaptation", "sign": "+"},
    ])
    np_csv = _save_csv(nodes, sdir / "figure_01_causal_loop_nodes.csv")
    ep_csv = _save_csv(edges, sdir / "figure_01_causal_loop_edges.csv")

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.axis("off")
    lookup = {r["node"]: (r["x"], r["y"]) for _, r in nodes.iterrows()}

    for _, e in edges.iterrows():
        x0, y0 = lookup[e["src"]]
        x1, y1 = lookup[e["tgt"]]
        is_pos = e["sign"] == "+"
        color = COLORS["type_b"] if is_pos else COLORS["type_a"]
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                     arrowprops={"arrowstyle": "-|>", "color": color, "lw": 2.0,
                                 "connectionstyle": "arc3,rad=0.15"})
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        ax.text(mx, my, e["sign"], ha="center", va="center", fontsize=13,
                fontweight="bold", color=color,
                bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": color, "lw": 0.8})

    for _, n in nodes.iterrows():
        ax.text(n["x"], n["y"], n["node"], ha="center", va="center", fontsize=10.5,
                bbox={"boxstyle": "round,pad=0.5", "fc": "white", "ec": "#333333", "lw": 1.3})

    # Loop labels: place them in open interior space so they do not sit on top of links.
    ax.text(
        0.535,
        0.705,
        "R1",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=COLORS["type_b"],
        alpha=0.55,
        bbox={"boxstyle": "round,pad=0.14", "fc": (1, 1, 1, 0.78), "ec": "none"},
    )
    ax.text(
        0.295,
        0.475,
        "R2",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=COLORS["type_b"],
        alpha=0.55,
        bbox={"boxstyle": "round,pad=0.14", "fc": (1, 1, 1, 0.78), "ec": "none"},
    )

    _finalize_fig(fig, "Figure 1. Conceptual Causal Loop: Convenience, Backlog, and Norm Reinforcement",
                  use_tight=False, top=0.93)
    ax.text(0.5, -0.02, "All links are conceptual and remain within the model\u2019s abstract Type A / Type B framing.\n"
            "R1: Stress\u2192Delegation\u2192Provider Burden\u2192Time Loss\u2192Backlog\u2192Stress (reinforcing)\n"
            "R2: Delegation\u2192Norm\u2192Convenience\u2192Delegation (reinforcing)",
            transform=ax.transAxes, ha="center", fontsize=9, color=COLORS["neutral"], style="italic")

    png = fdir / "figure_01_causal_loop.png"
    svg = fdir / "figure_01_causal_loop.svg"
    _save_figure(fig, png, svg)
    _add_manifest(manifest, kind="figure", slug="figure_01_causal_loop",
                  path=png, alts=[svg], sources=[np_csv, ep_csv])
    return png, svg


def _fig02_model_lifecycle(fdir: Path, sdir: Path, manifest: list) -> tuple[Path, Path]:
    """White-box model lifecycle flow diagram with color-coded phases."""
    steps_data = [
        (1, "Generate Tasks\n& Merge Backlog", "#D1E5F0"),
        (2, "Self-Serve or\nDelegate Decision", "#FEE08B"),
        (3, "Service-Pool\nMatching", "#FDAE61"),
        (4, "Unmatched \u2192\nBacklog", "#F46D43"),
        (5, "Stress Update &\nPreference Adapt", "#D73027"),
    ]
    steps_df = pd.DataFrame([(s, l, c) for s, l, c in steps_data],
                             columns=["step", "label", "color"])
    sp = _save_csv(steps_df[["step", "label"]], sdir / "figure_02_lifecycle_steps.csv")

    fig, ax = plt.subplots(figsize=(14, 4))
    ax.axis("off")
    xs = [0.10, 0.28, 0.46, 0.64, 0.82]
    y = 0.50
    for i, (step, label, color) in enumerate(steps_data):
        ax.text(xs[i], y, label, ha="center", va="center", fontsize=10.5,
                bbox={"boxstyle": "round,pad=0.6", "fc": color, "ec": "#333333", "lw": 1.2})
        ax.text(xs[i], 0.85, f"Phase {step}", ha="center", va="center",
                fontsize=10, fontweight="bold", color=COLORS["neutral"])
        if i < len(xs) - 1:
            ax.annotate("", xy=(xs[i + 1] - 0.07, y), xytext=(xs[i] + 0.07, y),
                         arrowprops={"arrowstyle": "-|>", "lw": 2.5, "color": "#333333"})

    _finalize_fig(fig, "Figure 2. White-Box Research Model Lifecycle (One Simulation Step)",
                  use_tight=False, top=0.88)
    ax.text(0.5, 0.10, "All mechanisms are explicit, parameterized rules. No latent LLM behavior in the simulation loop.",
            transform=ax.transAxes, ha="center", fontsize=9.5, color=COLORS["neutral"], style="italic")

    png = fdir / "figure_02_model_lifecycle.png"
    svg = fdir / "figure_02_model_lifecycle.svg"
    _save_figure(fig, png, svg)
    _add_manifest(manifest, kind="figure", slug="figure_02_model_lifecycle",
                  path=png, alts=[svg], sources=[sp])
    return png, svg


def _fig03_radar_profile(fdir: Path, sdir: Path, manifest: list) -> tuple[Path, Path]:
    """Radar chart comparing Type A vs Type B parameter profiles."""
    params = [
        ("Delegation\nPreference", 0.25, 0.72, 0, 1),
        ("Service\nCost", 0.65, 0.20, 0, 1),
        ("Conformity\nPressure", 0.15, 0.65, 0, 1),
        ("Task Load\nMean", 2.2, 2.8, 1, 5),
        ("Adaptation\nRate", 0.02, 0.05, 0, 0.1),
        ("Task Load\nStd", 0.7, 0.8, 0, 2),
    ]
    labels = [p[0] for p in params]
    a_vals = [(p[1] - p[3]) / (p[4] - p[3]) for p in params]
    b_vals = [(p[2] - p[3]) / (p[4] - p[3]) for p in params]

    src = pd.DataFrame({"parameter": labels,
                         "type_a_raw": [p[1] for p in params],
                         "type_b_raw": [p[2] for p in params],
                         "type_a_norm": a_vals, "type_b_norm": b_vals})
    sp = _save_csv(src, sdir / "figure_03_radar_profile.csv")

    n = len(labels)
    angles = [i / n * 2 * math.pi for i in range(n)]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"polar": True})
    a_plot = a_vals + a_vals[:1]
    b_plot = b_vals + b_vals[:1]
    ax.plot(angles, a_plot, "o-", color=COLORS["type_a"], lw=2.5, label="Type A (Autonomy)")
    ax.fill(angles, a_plot, alpha=0.15, color=COLORS["type_a"])
    ax.plot(angles, b_plot, "s--", color=COLORS["type_b"], lw=2.5, label="Type B (Convenience)")
    ax.fill(angles, b_plot, alpha=0.15, color=COLORS["type_b"])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([l.replace("\n", " ") for l in labels])
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], fontsize=8, color=COLORS["neutral"])
    _style_legend(ax, loc="upper right", bbox_to_anchor=(1.25, 1.1))
    _finalize_fig(fig, "Figure 3. Parameter Profiles: Type A vs Type B (Normalized)",
                  use_tight=False, top=0.92)

    png = fdir / "figure_03_radar_profile.png"
    svg = fdir / "figure_03_radar_profile.svg"
    _save_figure(fig, png, svg)
    _add_manifest(manifest, kind="figure", slug="figure_03_radar_profile",
                  path=png, alts=[svg], sources=[sp])
    return png, svg


def _fig04_horizon_panel(baseline: pd.DataFrame, fdir: Path, sdir: Path,
                          manifest: list) -> tuple[Path, Path]:
    """2x3 panel comparing Type A vs B across simulation horizons (6 metrics)."""
    sp = _save_csv(baseline, sdir / "figure_04_horizon_panel.csv")
    metrics = [
        ("tail_total_labor_hours_mean", "Total Labor Hours", "Hours"),
        ("tail_avg_stress_mean", "Average Stress", "Stress [0\u20131]"),
        ("final_available_time_mean_mean", "Final Available Time", "Hours"),
        ("tail_tasks_delegated_frac_mean", "Delegated Task Share", "Fraction"),
        ("tail_gini_income_mean", "Income Inequality (Gini)", "Gini [0\u20131]"),
        ("tail_gini_available_time_mean", "Time Inequality (Gini)", "Gini [0\u20131]"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(16, 10), sharex=True)
    for ax, (col, title, ylabel) in zip(axes.flatten(), metrics):
        for soc, color, ls, marker in [
            ("Type A", COLORS["type_a"], "-", "o"),
            ("Type B", COLORS["type_b"], "--", "s"),
        ]:
            sub = baseline[baseline["society"] == soc]
            ax.plot(sub["steps"], sub[col], color=color, lw=2.2, ls=ls, marker=marker,
                    markersize=6, label=soc)
        _set_panel_title(ax, title)
        ax.set_ylabel(ylabel)
        _style_legend(ax, loc="best")
    for ax in axes[-1]:
        ax.set_xlabel("Simulation Horizon (steps)")
    _finalize_fig(fig, "Figure 4. Type A and Type B Remain Structurally Different Across Longer Horizons")

    png = fdir / "figure_04_horizon_panel.png"
    svg = fdir / "figure_04_horizon_panel.svg"
    _save_figure(fig, png, svg)
    _add_manifest(manifest, kind="figure", slug="figure_04_horizon_panel",
                  path=png, alts=[svg], sources=[sp])
    return png, svg


def _fig05_agent_distributions(snapshots: dict[str, pd.DataFrame], fdir: Path,
                                sdir: Path, manifest: list) -> tuple[Path, Path]:
    """Violin plots of agent-level distributions at final step (Type A vs B)."""
    a_df = snapshots.get("autonomy_baseline", pd.DataFrame())
    b_df = snapshots.get("convenience_baseline", pd.DataFrame())
    if a_df.empty or b_df.empty:
        logger.warning("Agent snapshots missing; skipping Figure 05.")
        png = fdir / "figure_05_agent_distributions.png"
        svg = fdir / "figure_05_agent_distributions.svg"
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.text(0.5, 0.5, "Agent snapshot data unavailable", ha="center", va="center")
        _save_figure(fig, png, svg)
        return png, svg

    metrics = [
        ("available_time", "Available Time (hours)"),
        ("stress_level", "Stress Level [0\u20131]"),
        ("delegation_preference", "Delegation Preference [0\u20131]"),
        ("income", "Cumulative Income"),
    ]
    combined_rows = []
    for sid, label in [("autonomy_baseline", "Type A"), ("convenience_baseline", "Type B")]:
        df = snapshots[sid].copy()
        df["society"] = label
        combined_rows.append(df)
    combined = pd.concat(combined_rows, ignore_index=True)
    sp = _save_csv(combined[["society"] + [m[0] for m in metrics]], sdir / "figure_05_agent_distributions.csv")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, (col, ylabel) in zip(axes.flatten(), metrics):
        a_data = combined[combined["society"] == "Type A"][col].dropna().values
        b_data = combined[combined["society"] == "Type B"][col].dropna().values
        parts_a = ax.violinplot([a_data], positions=[0.8], showmeans=True, showextrema=True)
        parts_b = ax.violinplot([b_data], positions=[1.2], showmeans=True, showextrema=True)
        for pc in parts_a["bodies"]:
            pc.set_facecolor(COLORS["fill_a"])
            pc.set_edgecolor(COLORS["type_a"])
            pc.set_alpha(0.7)
        for key in ("cmeans", "cmins", "cmaxes", "cbars"):
            if key in parts_a:
                parts_a[key].set_color(COLORS["type_a"])
        for pc in parts_b["bodies"]:
            pc.set_facecolor(COLORS["fill_b"])
            pc.set_edgecolor(COLORS["type_b"])
            pc.set_alpha(0.7)
        for key in ("cmeans", "cmins", "cmaxes", "cbars"):
            if key in parts_b:
                parts_b[key].set_color(COLORS["type_b"])
        ax.set_ylabel(ylabel)
        ax.set_xticks([0.8, 1.2])
        ax.set_xticklabels(["Type A", "Type B"])
        _set_panel_title(ax, ylabel.split("(")[0].strip())

    _finalize_fig(fig, "Figure 5. Agent-Level Distributions at Final Step: Type A vs Type B")

    png = fdir / "figure_05_agent_distributions.png"
    svg = fdir / "figure_05_agent_distributions.svg"
    _save_figure(fig, png, svg)
    _add_manifest(manifest, kind="figure", slug="figure_05_agent_distributions",
                  path=png, alts=[svg], sources=[sp])
    return png, svg


def _fig06_phase_atlas(atlas: pd.DataFrame, onset: pd.DataFrame,
                        fdir: Path, sdir: Path, manifest: list) -> tuple[Path, Path]:
    """Delegation x Task-Load phase atlas heatmap with contour overlays."""
    sp1 = _save_csv(atlas, sdir / "figure_06_phase_atlas.csv")
    sp2 = _save_csv(onset, sdir / "figure_06_threshold_onset.csv")

    deleg_vals = sorted(atlas["delegation_preference_mean"].unique())
    task_vals = sorted(atlas["tasks_per_step_mean"].unique())
    pivot = atlas.pivot_table(index="tasks_per_step_mean", columns="delegation_preference_mean",
                              values="tail_backlog_tasks_mean", aggfunc="mean")
    Z = np.log10(pivot.values + 1)

    fig, ax = plt.subplots(figsize=(12, 8))
    x_extent = _heatmap_extent(deleg_vals)
    y_extent = _heatmap_extent(task_vals)

    ax.grid(False)
    im = ax.imshow(
        Z,
        origin="lower",
        aspect="auto",
        cmap="YlOrRd",
        extent=[x_extent[0], x_extent[1], y_extent[0], y_extent[1]],
    )
    cb = fig.colorbar(im, ax=ax, shrink=0.85)
    _style_colorbar(cb, "log\u2081\u2080(1 + backlog tasks)")

    # Contour lines
    X, Y = np.meshgrid(deleg_vals, task_vals)
    try:
        cs = ax.contour(
            X,
            Y,
            Z,
            levels=[0.01, 0.5, 1.0, 2.0, 3.0],
            colors="#2F3E46",
            linewidths=1.35,
            linestyles="--",
        )
        for collection in cs.collections:
            _outlined(collection, foreground="white", linewidth=2.8)
        labels = ax.clabel(cs, inline=True, fontsize=STYLE["annotation_size"], fmt="%.1f")
        for label in labels:
            label.set_color("#24323A")
            _outlined(label, foreground="white", linewidth=2.5)
    except Exception:
        pass

    # Onset line
    if not onset.empty:
        line = ax.plot(
            onset["delegation_preference_mean"],
            onset["first_backlog_task_load"],
            "o-",
            color="#244C5A",
            lw=2.6,
            markersize=5.5,
            markerfacecolor="white",
            markeredgewidth=1.2,
            label="First visible backlog",
            zorder=5,
        )[0]
        _outlined(line, foreground="white", linewidth=4.0)
        _style_legend(ax, loc="upper left")

    ax.set_xlabel("Delegation Preference Mean")
    ax.set_ylabel("Task Load Mean (tasks/step)")
    ax.set_xticks(deleg_vals)
    ax.set_yticks(task_vals)
    _finalize_fig(fig, "Figure 6. Delegation\u2013Task Load Phase Atlas: Backlog Emergence",
                  top=0.93)
    _annotate_note(
        ax,
        "Safe zone (bottom-left) \u2192 Transition band \u2192 Overloaded regime (top-right)",
    )

    png = fdir / "figure_06_phase_atlas.png"
    svg = fdir / "figure_06_phase_atlas.svg"
    _save_figure(fig, png, svg)
    _add_manifest(manifest, kind="figure", slug="figure_06_phase_atlas",
                  path=png, alts=[svg], sources=[sp1, sp2])
    return png, svg


def _fig07_threshold_detail(onset: pd.DataFrame, ref_sum: pd.DataFrame,
                             fdir: Path, sdir: Path, manifest: list) -> tuple[Path, Path]:
    """Three-panel threshold transition detail."""
    sp1 = _save_csv(onset, sdir / "figure_07_threshold_onset.csv")
    sp2 = _save_csv(ref_sum, sdir / "figure_07_refinement_summary.csv")

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Panel a: Stress at onset vs delegation
    ax = axes[0]
    ax.plot(onset["delegation_preference_mean"], onset["avg_stress_at_onset"],
            "o-", color=COLORS["type_b"], lw=2, markersize=7)
    ax.set_xlabel("Delegation Preference Mean")
    ax.set_ylabel("Stress at Backlog Onset")
    _set_panel_title(ax, "(a) Stress at Threshold")

    # Panel b: Task load at onset vs delegation
    ax = axes[1]
    ax.plot(onset["delegation_preference_mean"], onset["first_backlog_task_load"],
            "s-", color=COLORS["threshold"], lw=2, markersize=7)
    ax.set_xlabel("Delegation Preference Mean")
    ax.set_ylabel("Task Load at First Backlog")
    _set_panel_title(ax, "(b) Threshold Task Load")
    ax.axhspan(3.0, 3.25, alpha=0.2, color=COLORS["threshold"], label="3.0\u20133.25 band")
    _style_legend(ax, loc="best")

    # Panel c: Refinement band stress range
    ax = axes[2]
    ax.fill_between(ref_sum["tasks_per_step_mean"], ref_sum["stress_min"],
                     ref_sum["stress_max"], alpha=0.3, color=COLORS["type_b"])
    ax.plot(ref_sum["tasks_per_step_mean"], ref_sum["stress_min"],
            "-", color=COLORS["type_a"], lw=1.5, label="Stress min")
    ax.plot(ref_sum["tasks_per_step_mean"], ref_sum["stress_max"],
            "-", color=COLORS["type_b"], lw=1.5, label="Stress max")
    ax.set_xlabel("Task Load Mean")
    ax.set_ylabel("Tail Average Stress")
    _set_panel_title(ax, "(c) Refined Transition Band")
    ax.axvspan(3.0, 3.25, alpha=0.15, color=COLORS["threshold"])
    _style_legend(ax, loc="best")

    _finalize_fig(fig, "Figure 7. Threshold Transition Detail: The 3.0\u20133.25 Critical Band")

    png = fdir / "figure_07_threshold_detail.png"
    svg = fdir / "figure_07_threshold_detail.svg"
    _save_figure(fig, png, svg)
    _add_manifest(manifest, kind="figure", slug="figure_07_threshold_detail",
                  path=png, alts=[svg], sources=[sp1, sp2])
    return png, svg


def _fig08_story_timeseries(ts: pd.DataFrame, fdir: Path, sdir: Path,
                             manifest: list) -> tuple[Path, Path]:
    """2x3 time-series panel for 4 story cases, 6 metrics."""
    sp = _save_csv(ts[["Step", "scenario_id", "case_title", "avg_stress", "total_labor_hours",
                        "backlog_tasks", "delegation_match_rate", "avg_delegation_rate",
                        "self_labor_hours", "service_labor_hours"]],
                    sdir / "figure_08_story_timeseries.csv")

    metrics = [
        ("avg_stress", "Average Stress", "Stress [0\u20131]", False),
        ("total_labor_hours", "Total Labor Hours", "Hours", False),
        ("backlog_tasks", "Backlog Tasks", "Tasks", True),
        ("delegation_match_rate", "Delegation Match Rate", "Rate [0\u20131]", False),
        ("avg_delegation_rate", "Delegation Preference", "Preference [0\u20131]", False),
        ("service_labor_hours", "Service Labor Hours", "Hours", False),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(18, 10), sharex=True)
    for ax, (col, title, ylabel, use_log) in zip(axes.flatten(), metrics):
        for sid in STORY_ORDER:
            sub = ts[ts["scenario_id"] == sid]
            if sub.empty:
                continue
            ax.plot(sub["Step"], sub[col], color=STORY_COLORS[sid], lw=1.5,
                    label=STORY_LABELS[sid], alpha=0.85)
        _set_panel_title(ax, title)
        ax.set_ylabel(ylabel)
        if use_log:
            ax.set_yscale("symlog", linthresh=1)
        _style_legend(ax, loc="best", fontsize=8)
    for ax in axes[-1]:
        ax.set_xlabel("Simulation Step")

    _finalize_fig(fig, "Figure 8. System Dynamics: Four Story Cases from Relief to Overload")

    png = fdir / "figure_08_story_timeseries.png"
    svg = fdir / "figure_08_story_timeseries.svg"
    _save_figure(fig, png, svg)
    _add_manifest(manifest, kind="figure", slug="figure_08_story_timeseries",
                  path=png, alts=[svg], sources=[sp])
    return png, svg


def _fig09_labor_decomposition(key_table: pd.DataFrame, fdir: Path, sdir: Path,
                                manifest: list) -> tuple[Path, Path]:
    """Stacked bar chart of labor composition + delegation labor delta line."""
    sp = _save_csv(key_table, sdir / "figure_09_labor_decomposition.csv")

    fig, ax1 = plt.subplots(figsize=(12, 7))
    cases = key_table["case"].tolist()
    x = np.arange(len(cases))
    w = 0.55

    self_l = key_table["tail_self_labor_hours"].astype(float).values
    svc_l = key_table["tail_service_labor_hours"].astype(float).values
    coord_l = key_table["tail_coordination_hours"].astype(float).values

    ax1.bar(x, self_l, w, label="Self Labor", color=COLORS["self_labor"], alpha=0.85)
    ax1.bar(x, svc_l, w, bottom=self_l, label="Service Labor", color=COLORS["service_labor"], alpha=0.85)
    ax1.bar(x, coord_l, w, bottom=self_l + svc_l, label="Coordination", color=COLORS["coord_labor"], alpha=0.85)
    ax1.set_ylabel("Tail Labor Hours")
    ax1.set_xticks(x)
    ax1.set_xticklabels(cases, rotation=15, ha="right")
    _style_legend(ax1, loc="upper left")

    # Delta line on secondary axis
    ax2 = ax1.twinx()
    delta = key_table["tail_delegation_labor_delta"].astype(float).values
    ax2.plot(x, delta, "D-", color=COLORS["threshold"], lw=2.5, markersize=8, label="Labor Delta")
    ax2.set_ylabel("Delegation Labor Delta", color=COLORS["threshold"])
    ax2.tick_params(axis="y", labelcolor=COLORS["threshold"])
    _style_legend(ax2, loc="upper right")

    _finalize_fig(fig, "Figure 9. Labor Composition: Convenience Reshapes Before It Overloads",
                  top=0.93)

    png = fdir / "figure_09_labor_decomposition.png"
    svg = fdir / "figure_09_labor_decomposition.svg"
    _save_figure(fig, png, svg)
    _add_manifest(manifest, kind="figure", slug="figure_09_labor_decomposition",
                  path=png, alts=[svg], sources=[sp])
    return png, svg


def _fig10_available_time_density(snapshots: dict[str, pd.DataFrame], fdir: Path,
                                   sdir: Path, manifest: list) -> tuple[Path, Path]:
    """Overlaid histograms of available time distribution for Type A vs B."""
    a_df = snapshots.get("autonomy_baseline", pd.DataFrame())
    b_df = snapshots.get("convenience_baseline", pd.DataFrame())

    fig, ax = plt.subplots(figsize=(10, 6))
    if not a_df.empty:
        ax.hist(a_df["available_time"].dropna(), bins=30, alpha=0.6, color=COLORS["type_a"],
                label="Type A (Autonomy)", density=True, edgecolor="white")
    if not b_df.empty:
        ax.hist(b_df["available_time"].dropna(), bins=30, alpha=0.6, color=COLORS["type_b"],
                label="Type B (Convenience)", density=True, edgecolor="white")
    ax.set_xlabel("Available Time (hours)")
    ax.set_ylabel("Density")
    _style_legend(ax, loc="best")
    _finalize_fig(fig, "Figure 10. Available Time Distribution at Final Step",
                  top=0.93)

    # Save source
    combined = pd.concat([
        a_df[["available_time"]].assign(society="Type A") if not a_df.empty else pd.DataFrame(),
        b_df[["available_time"]].assign(society="Type B") if not b_df.empty else pd.DataFrame(),
    ], ignore_index=True)
    sp = _save_csv(combined, sdir / "figure_10_available_time_density.csv")

    png = fdir / "figure_10_available_time_density.png"
    svg = fdir / "figure_10_available_time_density.svg"
    _save_figure(fig, png, svg)
    _add_manifest(manifest, kind="figure", slug="figure_10_available_time_density",
                  path=png, alts=[svg], sources=[sp])
    return png, svg


def _fig11_mixed_heatmap(hm: pd.DataFrame, fdir: Path, sdir: Path,
                          manifest: list) -> tuple[Path, Path]:
    """Heatmap of delegation rate std across mixed-system parameter space."""
    sp = _save_csv(hm, sdir / "figure_11_mixed_heatmap.csv")

    pivot = hm.pivot_table(index="delegation_preference_mean",
                            columns="social_conformity_pressure",
                            values="final_avg_delegation_rate_std", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(9, 7))
    x_vals = pivot.columns.to_list()
    y_vals = pivot.index.to_list()
    x_extent = _heatmap_extent(x_vals)
    y_extent = _heatmap_extent(y_vals)

    ax.grid(False)
    im = ax.imshow(
        pivot.values,
        origin="lower",
        aspect="auto",
        cmap="Blues",
        extent=[x_extent[0], x_extent[1], y_extent[0], y_extent[1]],
    )
    cb = fig.colorbar(im, ax=ax, shrink=0.85)
    _style_colorbar(cb, "Final Delegation Rate Std Dev")

    # Annotate cells
    for i, deleg in enumerate(pivot.index):
        for j, conf in enumerate(pivot.columns):
            val = pivot.values[i, j]
            ax.text(
                conf,
                deleg,
                f"{val:.4f}",
                ha="center",
                va="center",
                fontsize=STYLE["annotation_size"],
                color="#1F2937",
                bbox={"boxstyle": "round,pad=0.16", "fc": (1, 1, 1, 0.72), "ec": "none"},
            )

    ax.set_xlabel("Social Conformity Pressure")
    ax.set_ylabel("Initial Delegation Preference Mean")
    ax.set_xticks(x_vals)
    ax.set_yticks(y_vals)
    _finalize_fig(fig, "Figure 11. Mixed-System Stability: Dispersion Remains Modest",
                  top=0.93)

    png = fdir / "figure_11_mixed_heatmap.png"
    svg = fdir / "figure_11_mixed_heatmap.svg"
    _save_figure(fig, png, svg)
    _add_manifest(manifest, kind="figure", slug="figure_11_mixed_heatmap",
                  path=png, alts=[svg], sources=[sp])
    return png, svg


def _fig12_mixed_scatter(pt: pd.DataFrame, fdir: Path, sdir: Path,
                          manifest: list) -> tuple[Path, Path]:
    """Per-seed scatter: initial vs final delegation rate with identity line."""
    sp = _save_csv(pt, sdir / "figure_12_mixed_scatter.csv")

    fig, ax = plt.subplots(figsize=(9, 8))
    sc = ax.scatter(pt["delegation_preference_mean"], pt["final_avg_delegation_rate"],
                     c=pt["social_conformity_pressure"], cmap="coolwarm",
                     s=30, alpha=0.7, edgecolors="white", linewidths=0.3)
    cb = fig.colorbar(sc, ax=ax, shrink=0.85)
    _style_colorbar(cb, "Conformity Pressure")
    lims = [0.3, 0.7]
    ax.plot(lims, lims, "--", color=COLORS["neutral"], lw=1.5, label="Identity line")
    ax.set_xlabel("Initial Delegation Preference Mean")
    ax.set_ylabel("Final Delegation Rate (per seed)")
    _style_legend(ax, loc="best")
    _finalize_fig(fig, "Figure 12. Per-Seed Delegation Outcomes Stay Close to Initial Values",
                  top=0.93)

    png = fdir / "figure_12_mixed_scatter.png"
    svg = fdir / "figure_12_mixed_scatter.svg"
    _save_figure(fig, png, svg)
    _add_manifest(manifest, kind="figure", slug="figure_12_mixed_scatter",
                  path=png, alts=[svg], sources=[sp])
    return png, svg


def _fig13_cost_sensitivity(ctx: pd.DataFrame, flip: pd.DataFrame,
                             fdir: Path, sdir: Path, manifest: list) -> tuple[Path, Path]:
    """Paired dot/slope chart: low vs high service cost across contexts."""
    sp1 = _save_csv(ctx, sdir / "figure_13_cost_context.csv")
    sp2 = _save_csv(flip, sdir / "figure_13_cost_flip.csv")

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: Stress comparison
    ax = axes[0]
    contexts = ctx["context"].tolist()
    x = np.arange(len(contexts))
    ax.scatter(x - 0.1, ctx["low_cost_stress"], s=80, color=COLORS["type_a"],
               marker="o", zorder=5, label="Low Cost")
    ax.scatter(x + 0.1, ctx["high_cost_stress"], s=80, color=COLORS["type_b"],
               marker="s", zorder=5, label="High Cost")
    for i in range(len(contexts)):
        ax.plot([i - 0.1, i + 0.1],
                [ctx.iloc[i]["low_cost_stress"], ctx.iloc[i]["high_cost_stress"]],
                "-", color=COLORS["neutral"], lw=1, alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(contexts, rotation=20, ha="right")
    ax.set_ylabel("Tail Average Stress")
    _set_panel_title(ax, "(a) Stress: Low vs High Service Cost")
    _style_legend(ax, loc="best")

    # Right: Flip point
    ax = axes[1]
    if not flip.empty:
        ax.plot(flip["delegation_preference_mean"], flip["flip_task_load"],
                "o-", color=COLORS["threshold"], lw=2, markersize=8)
        ax.fill_between(flip["delegation_preference_mean"], 0, flip["flip_task_load"],
                         alpha=0.1, color=COLORS["threshold"])
    ax.set_xlabel("Delegation Preference Mean")
    ax.set_ylabel("Task Load Where Low Cost Flips to Higher Stress")
    _set_panel_title(ax, "(b) Cost-Amplification Threshold")

    _finalize_fig(fig, "Figure 13. Service Cost Is Conditional: Relief at Low Load, Amplification Near Threshold")

    png = fdir / "figure_13_cost_sensitivity.png"
    svg = fdir / "figure_13_cost_sensitivity.svg"
    _save_figure(fig, png, svg)
    _add_manifest(manifest, kind="figure", slug="figure_13_cost_sensitivity",
                  path=png, alts=[svg], sources=[sp1, sp2])
    return png, svg


def _fig14_param_sensitivity(atlas: pd.DataFrame, fdir: Path, sdir: Path,
                              manifest: list) -> tuple[Path, Path]:
    """Small-multiples: stress, labor, backlog vs task load at different delegation levels."""
    sp = _save_csv(atlas, sdir / "figure_14_param_sensitivity.csv")

    deleg_levels = [0.05, 0.25, 0.45, 0.65, 0.85]
    metrics = [
        ("tail_avg_stress_mean", "Average Stress"),
        ("tail_total_labor_hours_mean", "Total Labor Hours"),
        ("tail_backlog_tasks_mean", "Backlog Tasks (log)"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharex=True)
    cmap = plt.cm.viridis
    for ax, (col, title) in zip(axes, metrics):
        for i, dl in enumerate(deleg_levels):
            sub = atlas[np.isclose(atlas["delegation_preference_mean"], dl, atol=0.01)]
            if sub.empty:
                continue
            color = cmap(i / (len(deleg_levels) - 1))
            ax.plot(sub["tasks_per_step_mean"], sub[col], "o-", color=color,
                    lw=1.8, markersize=4, label=f"Deleg={dl:.2f}")
        _set_panel_title(ax, title)
        ax.set_xlabel("Task Load Mean")
        if "log" in title.lower():
            ax.set_yscale("symlog", linthresh=1)
        _style_legend(ax, loc="best", fontsize=8)

    _finalize_fig(fig, "Figure 14. Parameter Sensitivity: How Task Load and Delegation Jointly Shape Outcomes")

    png = fdir / "figure_14_param_sensitivity.png"
    svg = fdir / "figure_14_param_sensitivity.svg"
    _save_figure(fig, png, svg)
    _add_manifest(manifest, kind="figure", slug="figure_14_param_sensitivity",
                  path=png, alts=[svg], sources=[sp])
    return png, svg


def _fig15_campaign_coverage(combo: pd.DataFrame, fdir: Path, sdir: Path,
                              manifest: list) -> tuple[Path, Path]:
    """Campaign coverage map: parameter space explored across all packages."""
    pkg_colors = {
        PACKAGE_A: COLORS["type_a"], PACKAGE_B: COLORS["threshold"],
        PACKAGE_C: COLORS["provider"], PACKAGE_D: COLORS["backlog"],
    }
    pkg_labels = {
        PACKAGE_A: "A: Everyday Friction", PACKAGE_B: "B: Convenience Transfer",
        PACKAGE_C: "C: Cheap Service Trap", PACKAGE_D: "D: Norm Lock-in",
    }
    src = combo[["package_slug", "delegation_preference_mean", "tasks_per_step_mean",
                  "social_conformity_pressure", "service_cost_factor"]].drop_duplicates()
    sp = _save_csv(src, sdir / "figure_15_campaign_coverage.csv")

    fig, ax = plt.subplots(figsize=(11, 7))
    for pkg, color in pkg_colors.items():
        sub = src[src["package_slug"] == pkg]
        ax.scatter(sub["delegation_preference_mean"], sub["tasks_per_step_mean"],
                    c=color, s=25, alpha=0.6, label=pkg_labels.get(pkg, pkg), edgecolors="white",
                    linewidths=0.3)
    ax.set_xlabel("Delegation Preference Mean")
    ax.set_ylabel("Task Load Mean")
    _style_legend(ax, loc="best", title="Package")
    _finalize_fig(fig, "Figure 15. Campaign Coverage: 14,656 Runs Across the Parameter Space",
                  top=0.93)

    png = fdir / "figure_15_campaign_coverage.png"
    svg = fdir / "figure_15_campaign_coverage.svg"
    _save_figure(fig, png, svg)
    _add_manifest(manifest, kind="figure", slug="figure_15_campaign_coverage",
                  path=png, alts=[svg], sources=[sp])
    return png, svg


# ---------------------------------------------------------------------------
# Report rendering — English
# ---------------------------------------------------------------------------

def _render_english(report_path: Path, fig_paths: dict[str, Path],
                     tables: dict[str, pd.DataFrame], stats: dict) -> str:
    """Generate the full English Markdown research report."""
    I = lambda slug: _md_img(report_path, fig_paths[slug], slug, language="en")

    report = textwrap.dedent(f"""\
    # The Convenience Paradox: An Agent-Based Exploration of Service Delegation, Labor Transfer, and Social Involution

    **Author:** Jiyuan Shi | Computational Social Science Portfolio Study
    **Date:** {date.today().isoformat()}
    **Campaign:** 14,656 simulation runs across 4 research packages (research_v2 engine)

    ---

    > *A few years into living abroad, I found myself standing in front of a closed supermarket on a Sunday
    > afternoon. Back in a different city on another continent, I could have walked into any convenience
    > store at nearly any hour. That small friction stuck with me -- not because it was a hardship, but
    > because it was a thread I kept pulling. The more I pulled, the more I realized it was connected to
    > something much larger: a web of interdependent social mechanisms that shape how entire societies
    > function.*
    >
    > *Which came first -- the cheap service or the dependency on it? Is the low price a cause or a
    > consequence? And once the feedback loop is in motion, would raising prices even change anything?*

    ---

    ## 1. Abstract

    This report presents an agent-based modeling (ABM) study of the **convenience-autonomy tension** --
    the observation that societies exhibit markedly different equilibria in how individuals balance
    self-reliance against service delegation, and that these equilibria appear self-reinforcing.

    Using a Mesa-based simulation with 100 agents on a Watts-Strogatz small-world network, we explore
    four hypotheses about how delegation rates, service costs, social conformity, and task loads interact
    to produce emergent patterns in total system labor, individual stress, and inequality. A campaign of
    **14,656 runs** across four research packages provides the evidence base.

    Key findings within the model: (1) a convenience-oriented configuration (Type B) consistently
    generates approximately **{_fmt_pct(stats['labor_delta_pct'])}** more total system labor than an
    autonomy-oriented configuration (Type A); (2) a narrow task-load threshold band (3.0--3.25 tasks/step)
    marks the transition from manageable delegation to cumulative overload; (3) autonomy-oriented agents
    retain more available time ({_fmt(stats['ta_avail'], 2)}h vs {_fmt(stats['tb_avail'], 2)}h).

    **Important framing note:** This work serves as a methodological demonstration of translating
    qualitative social observations into formal agent-based models, showcasing capabilities in structured
    information synthesis and computational data stewardship. The author is a computational professional,
    not a domain expert in sociology or economics. The model design, theoretical framework, and resulting
    conclusions are exploratory in nature and should not be interpreted as definitive social science
    findings. Readers are encouraged to evaluate the rigor of the methodology and the transparency of the
    analytical process, rather than treating the substantive conclusions as authoritative.

    ---

    ## 2. Problem Definition and Theoretical Framework

    ### 2.1 The Convenience-Autonomy Tension

    Everyday life in different societies exhibits strikingly different rhythms. In some settings,
    individuals manage most daily tasks themselves -- cooking, errands, minor repairs -- accepting higher
    time costs and slower service timelines. In other settings, affordable third-party services enable
    widespread delegation, producing a faster-paced, more interconnected service ecosystem.

    These patterns are not random. From a **complex adaptive systems** perspective, they can be understood
    as emergent properties of interacting feedback loops among individual decisions, service availability,
    price structures, social norms, and time constraints. The key insight is that *convenience and
    autonomy are not merely preferences but systemic outcomes* -- shaped by, and in turn shaping, the
    environments in which they arise.

    ### 2.2 Conceptual Causal Loop

    {I('figure_01_causal_loop')}

    *Figure 1* maps the conceptual feedback structure embedded in the model. Two reinforcing loops
    dominate: **R1** (stress-driven delegation spiral) and **R2** (norm-driven convenience lock-in).
    When delegation increases, provider burden grows, squeezing available time, raising stress, and
    further encouraging delegation. Simultaneously, high delegation normalizes itself through social
    conformity, lowering the perceived friction of delegating.

    ### 2.3 From Observation to Formal Model

    The translation from qualitative observation to computational model proceeds through three stages:

    1. **Identify feedback mechanisms** from lived experience (e.g., "cheap service creates dependency
       which creates demand which extends working hours")
    2. **Formalize as agent rules** with explicit parameters (delegation probability, stress thresholds,
       conformity weights)
    3. **Design experiments** that isolate each mechanism and test boundary conditions

    This structured translation -- from anecdote to causal loop to parameterized ABM -- is itself a core
    contribution of this work, demonstrating the capability to synthesize qualitative input into
    structured, testable computational outputs.

    ---

    ## 3. Research Questions and Hypotheses

    {_markdown_table(tables['question_map'])}

    The four hypotheses tested:

    - **H1**: Higher delegation rates lead to higher total systemic labor hours.
    - **H2**: A critical delegation threshold triggers an involution spiral.
    - **H3**: Higher autonomy correlates with lower perceived convenience but higher aggregate well-being.
    - **H4**: Mixed systems (moderate delegation) are unstable and drift toward extremes.

    ---

    ## 4. Model Specification

    ### 4.1 Agent Architecture

    Each **Resident** agent has a daily time budget of 8.0 hours and receives 1--5 tasks per step. The
    delegation decision integrates four factors:

    *p_eff = clamp( p_base + 0.30 * stress + 0.25 * skill_gap - 0.25 * cost, 0, 1 )*

    Where *p_base* is the agent's delegation preference (evolves via social conformity), *stress* is the
    current stress level [0,1], *skill_gap* is the difference between task requirements and agent
    proficiency, and *cost* is the exogenous service cost factor.

    Task time cost: *t = base_time / max(0.1, proficiency)*, with an additive penalty when
    proficiency < skill_requirement.

    ### 4.2 Model Lifecycle

    {I('figure_02_model_lifecycle')}

    Each simulation step proceeds through five phases (Figure 2): task generation with backlog merge,
    delegation decision, service-pool matching (greedy, most-available-time-first), backlog return for
    unmatched tasks, and stress/preference update.

    ### 4.3 Parameter Profiles

    {I('figure_03_radar_profile')}

    Figure 3 shows the normalized parameter profiles for the two abstract society types. Type A
    (Autonomy-Oriented) features low delegation preference (0.25), high service cost (0.65), and weak
    conformity (0.15). Type B (Convenience-Oriented) features high delegation preference (0.72), low
    service cost (0.20), and strong conformity (0.65). Parameter ranges are informed by ILO, WVS, and
    OECD stylized facts but are not calibrated to specific empirical data.

    ### 4.4 Research Engine Enhancements (research_v2)

    {_markdown_table(tables['model_delta'])}

    ---

    ## 5. Experimental Design and Data Stewardship

    The campaign comprises **14,656 completed runs** organized into four packages, each targeting a
    specific research question:

    | Package | Focus | Scenarios | Key Parameters Varied |
    | --- | --- | --- | --- |
    | A: Everyday Friction | Type A vs B baseline | 8 (4 horizons x 2 types) | Simulation length |
    | B: Convenience Transfer | Labor transfer atlas | ~1,000+ grid cells | Delegation x Task load |
    | C: Cheap Service Trap | Service cost sensitivity | ~500+ grid cells | Cost x Task load |
    | D: Norm Lock-in | Mixed stability | ~150+ grid cells | Delegation x Conformity |

    All runs use the **research_v2 engine** with explicit backlog carryover, coordination costs, and
    decomposed labor accounting. Summary statistics use a **tail-window aggregation** over the final 20%
    of simulation steps to capture stabilized behavior. Each scenario cell is replicated across multiple
    random seeds (12--20) for statistical robustness.

    Data provenance is maintained through: (1) a campaign manifest with git commit hash, (2) per-figure
    source CSVs enabling independent verification, and (3) a three-tier claim safety framework.

    ---

    ## 6. Results

    ### 6.1 H1: Delegation Increases Total System Labor (Strong Support)

    {I('figure_04_horizon_panel')}

    Figure 4 compares Type A (Autonomy-Oriented) and Type B (Convenience-Oriented) across four simulation
    horizons (120, 200, 300, and 450 steps). Six key metrics reveal persistent structural differences that
    neither converge nor diverge with simulation length, suggesting genuine equilibrium separation rather
    than transient startup dynamics.

    **Total labor hours** show the most striking gap. At 450 steps, Type B generates
    {_fmt(stats['tb_labor'], 1)} hours versus {_fmt(stats['ta_labor'], 1)} for Type A -- a
    **{_fmt_pct(stats['labor_delta_pct'])} premium**. Crucially, this gap is already visible at 120 steps
    ({_fmt(stats.get('h120_tb_labor', 0), 1)} vs {_fmt(stats.get('h120_ta_labor', 0), 1)} hours,
    ~{_fmt_pct(stats.get('h120_delta_pct', 0))} difference) and remains stable through all subsequent
    horizons, confirming that the labor overhead is a *structural* feature of the high-delegation
    configuration rather than an initialization artifact.

    **Stress levels** mirror this pattern: Type B agents maintain consistently higher average stress
    ({_fmt(stats['tb_stress'], 3)} vs {_fmt(stats['ta_stress'], 3)} at 450 steps). Although both values
    remain below the acute-distress saturation level (1.0), the persistent gap reflects the tighter time
    budgets imposed by coordination overhead and service provision duties in the convenience configuration.

    **Available time** tells the agent-level story most directly: Type A agents retain
    {_fmt(stats['ta_avail'], 2)} hours of uncommitted time on average versus only
    {_fmt(stats['tb_avail'], 2)} hours for Type B -- a gap of approximately
    {_fmt(stats['ta_avail'] - stats['tb_avail'], 2)} hours. Within the model's 8-hour daily budget, this
    means Type A agents preserve roughly {_fmt_pct(stats['ta_avail'] / 8.0 * 100)} of their time budget as
    discretionary, compared to {_fmt_pct(stats['tb_avail'] / 8.0 * 100)} for Type B. This difference
    accumulates through coordination costs and provider burden that Type B agents bear.

    **Delegation rates** confirm configuration integrity: Type B agents delegate
    {_fmt_pct(stats['tb_deleg_frac'] * 100)} of tasks versus {_fmt_pct(stats['ta_deleg_frac'] * 100)} for
    Type A, with separation remaining sharp and persistent across all horizons.

    **Income inequality** (Gini coefficient) is modestly higher in Type B
    ({_fmt(stats.get('tb_gini_income', 0), 3)} vs {_fmt(stats.get('ta_gini_income', 0), 3)}), reflecting
    the service-economy structure where some agents accumulate more service income while others bear
    disproportionate provider burden. **Time inequality** shows smaller differences
    ({_fmt(stats.get('ta_gini_available_time', 0), 3)} vs
    {_fmt(stats.get('tb_gini_available_time', 0), 3)}), suggesting that the time cost of the convenience
    economy is distributed relatively evenly -- everyone loses time, not just providers.

    {I('figure_05_agent_distributions')}

    Figure 5 reveals the agent-level distributions behind these population aggregates. In Type A, available
    time shows a wide distribution centered around {_fmt(stats['ta_avail'], 1)} hours, reflecting individual
    variation in task loads and skill levels. In Type B, available time clusters lower with a tighter
    distribution, consistent with the conformity-driven convergence of delegation behavior. Delegation
    preference in Type B converges tightly near the high-delegation mean, while Type A agents maintain more
    heterogeneous preferences -- a direct consequence of stronger conformity pressure in the convenience
    configuration (0.65 vs 0.15). Income distributions in Type B display a longer right tail, a signature
    of the service economy where a subset of agents earns significantly more from service provision.

    **What this does not tell us:** The model uses exogenous, fixed service costs. In a real economy, the
    {_fmt_pct(stats['labor_delta_pct'])} labor premium might be partially offset by endogenous price
    adjustments, productivity gains from specialization, or quality improvements in delegated services. The
    premium reflects the *structural cost of coordination and provider overhead* within this model's
    accounting framework, not a universal law of delegation economics.

    ### 6.2 H2: Threshold Triggers Involution (Strong Support)

    {I('figure_06_phase_atlas')}

    Figure 6 presents the delegation--task load phase atlas, mapping system-level backlog accumulation
    across the two most important control parameters. The color gradient (log-scaled) reveals three
    distinct regimes:

    1. **Safe zone** (bottom-left, dark): Low task load and/or low delegation. The system absorbs all
       tasks without residual backlog. Stress remains manageable and all agents have time remaining at
       the end of each step.
    2. **Transition band** (diagonal corridor, yellow-orange): A narrow region where backlog first becomes
       visible. Small parameter changes in this zone produce disproportionately large outcome differences --
       a hallmark of phase-transition behavior in complex systems.
    3. **Overloaded regime** (top-right, deep red): High task load combined with moderate-to-high delegation.
       Backlog grows cumulatively each step, driving all agents toward maximum stress and labor saturation.

    The white onset line traces the boundary where backlog first exceeds zero. This boundary is not a
    single point but a *band* -- its exact position shifts slightly with delegation level, but remains
    confined to the **task load 3.0--3.25 range** across all delegation levels tested. The consistency of
    this threshold across varying delegation preferences suggests that the bottleneck is system-level
    provider capacity (total available service hours), not individual agent decisions.

    {I('figure_07_threshold_detail')}

    Figure 7 isolates the threshold mechanics through three complementary panels:

    **(a) Stress at threshold onset**: When backlog first appears, agents are already experiencing elevated
    stress, indicating that the system is operating at capacity even before visible overload. Higher
    delegation levels shift the onset to slightly lower stress values -- agents who delegate more hit the
    capacity wall sooner because they contribute less self-service labor.

    **(b) Task load at first backlog**: The threshold task load is remarkably consistent across delegation
    levels, hovering between 3.0 and 3.25 tasks/step. This narrow 0.25-unit band represents the critical
    window: below it, the system finds equilibrium; above it, cumulative overload begins.

    **(c) Refined transition band**: The stress envelope between minimum and maximum delegation levels shows
    tight convergence above the threshold. Once backlog begins accumulating, the system trajectory is
    largely determined by task load alone, with delegation level becoming a secondary factor. The shaded
    band between 3.0 and 3.25 marks where the model transitions from one behavioral regime to another.

    {I('figure_08_story_timeseries')}

    Figure 8 illustrates these regimes through four story cases, tracking six metrics over time:

    - **Autonomy Baseline**: Stable equilibrium with low stress
      ({_fmt(stats.get('auto_tail_stress', 0), 3)}), moderate total labor
      ({_fmt(stats.get('auto_tail_total_labor_hours', 0), 1)}h), and zero backlog. The system operates
      well within capacity, with delegation match rate near 1.0 (virtually all delegated tasks find
      providers).
    - **Convenience Baseline**: Higher but still stable equilibrium with stress at
      {_fmt(stats.get('conv_tail_stress', 0), 3)} and total labor at
      {_fmt(stats.get('conv_tail_total_labor_hours', 0), 1)}h. Service labor constitutes a major fraction
      of the total. Delegation preference converges quickly as conformity pressure homogenizes behavior.
    - **Threshold Pressure**: Near-critical operation with stress at
      {_fmt(stats.get('thresh_tail_stress', 0), 3)} and total labor at
      {_fmt(stats.get('thresh_tail_total_labor_hours', 0), 1)}h. Backlog may appear intermittently but
      does not spiral out of control -- the system teeters at the edge of the transition band.
    - **Overloaded Convenience**: Catastrophic collapse. Stress saturates at 1.0 within the first ~50
      steps. Backlog grows exponentially to {_fmt(stats.get('overload_tail_backlog_tasks', 0), 0)} tasks
      by the tail window. Total labor hits the ceiling
      ({_fmt(stats.get('overload_tail_total_labor_hours', 0), 1)}h) as every agent spends all available
      hours working. This is the involution spiral in its pure form: delegation generates more work than
      the system can process, the excess carries over, and the gap widens each step.

    **What this does not tell us:** The 3.0--3.25 threshold band is specific to this model's configuration
    (100 agents, 8-hour budgets, 15% coordination overhead, 11% provider overhead, greedy matching).
    Real-world thresholds would depend on labor market flexibility, skill distributions, institutional
    buffers, and adaptive mechanisms not captured here. The threshold *concept* -- a narrow band separating
    manageable from catastrophic dynamics -- is the transferable insight; the specific numerical values
    are properties of this particular model.

    ### 6.3 H3: Autonomy Preserves Well-Being (Partial Support)

    {I('figure_09_labor_decomposition')}

    Figure 9 decomposes the labor budget across the four story cases into three components: self-labor
    (tasks completed by the agent who generated them), service labor (tasks completed by providers on
    behalf of delegators), and coordination costs (overhead from the matching and delegation transaction).

    The decomposition reveals how convenience *reshapes* the labor structure before it *overloads* it:

    - **Autonomy Baseline**: Self-labor dominates at {_fmt(stats.get('auto_tail_self_labor_hours', 0), 1)}h,
      with minimal service labor ({_fmt(stats.get('auto_tail_service_labor_hours', 0), 1)}h) and negligible
      coordination ({_fmt(stats.get('auto_tail_coordination_hours', 0), 1)}h). Total:
      {_fmt(stats.get('auto_tail_total_labor_hours', 0), 1)}h.
    - **Convenience Baseline**: Self-labor drops to
      {_fmt(stats.get('conv_tail_self_labor_hours', 0), 1)}h, but service labor rises to
      {_fmt(stats.get('conv_tail_service_labor_hours', 0), 1)}h and coordination costs add
      {_fmt(stats.get('conv_tail_coordination_hours', 0), 1)}h. Total:
      {_fmt(stats.get('conv_tail_total_labor_hours', 0), 1)}h -- *higher* than the autonomy case despite
      substantially less self-labor. This is the core mechanism of H1 made visible at the component level.
    - **Threshold Pressure** and **Overloaded Convenience**: The labor mix shifts further as coordination
      and service costs dominate. In the overloaded case, all labor categories saturate at maximum capacity.

    The delegation labor delta line (orange, right axis) quantifies the *net* labor effect of delegation:
    it is consistently positive in the convenience configurations, confirming that within this model,
    delegation is a *net labor creator*, not a labor saver. Each delegated task generates more total
    system work-hours than the same task completed self-sufficiently -- because coordination overhead (15%)
    and provider time penalties (11%) add to the baseline task cost.

    {I('figure_10_available_time_density')}

    Figure 10 compares the distribution of available time at the final simulation step across 100 agents.
    Type A agents cluster around {_fmt(stats['ta_avail'], 1)} hours with a spread reflecting individual
    variation in task loads and skill proficiencies. Type B agents cluster lower at
    {_fmt(stats['tb_avail'], 1)} hours with a tighter distribution -- the conformity pressure that
    homogenizes delegation behavior also homogenizes its consequences.

    The {_fmt(stats['ta_avail'] - stats['tb_avail'], 2)}-hour gap in available time represents a
    meaningful lifestyle difference within the model's abstract framing: Type A agents retain roughly
    {_fmt_pct(stats['ta_avail'] / 8.0 * 100)} of their daily budget as uncommitted time, compared to
    {_fmt_pct(stats['tb_avail'] / 8.0 * 100)} for Type B. Within the model, this is the "price of
    convenience" -- though the model cannot assess whether agents would subjectively prefer this tradeoff.

    **What this does not tell us:** "Well-being" is proxied only by available time and stress. The model
    cannot measure subjective satisfaction, perceived convenience, quality of delegated services, or the
    psychological value of free time versus service access. Type B agents may experience higher perceived
    quality of life despite lower available time -- this dimension is entirely outside the model's
    measurement capability. The partial support verdict reflects this important gap between what we can
    measure (time, stress) and what we would need to measure for a complete well-being assessment.

    ### 6.4 H4: Mixed Systems and Norm Lock-in (Partial, Important Negative Result)

    {I('figure_11_mixed_heatmap')}

    Figure 11 maps the standard deviation of final delegation rates across the mixed-system parameter
    space, testing whether moderate-delegation populations drift toward extremes under varying conformity
    pressures. The experiment varies initial delegation preference (0.35--0.65, spanning the moderate
    range) against social conformity pressure (0.1--0.9, from weak to strong).

    The result is clear and noteworthy: the maximum observed standard deviation is only
    **{_fmt(stats['mixed_max_std'], 4)}**. Across all 30 parameter combinations tested, the system
    remains remarkably stable. Higher conformity pressure does not produce measurably greater dispersion
    in final outcomes. The delegation rate standard deviation varies by less than 0.002 across the entire
    conformity range -- cell annotations in the heatmap show near-uniform values throughout the grid.

    {I('figure_12_mixed_scatter')}

    Figure 12 reinforces this finding from the per-seed perspective. Each point represents one simulation
    run's final delegation rate plotted against its initial delegation preference mean, with color
    encoding conformity pressure. Points cluster tightly along the identity line (initial = final), with
    no visible dependence on conformity pressure. Even at the highest conformity setting (0.9), final
    delegation rates remain within {_fmt(stats['mixed_max_std'], 4)} of their initial values.

    This is an **important negative result**, scientifically valuable precisely because it constrains the
    model's explanatory power. Several factors may explain why the hypothesized bifurcation does not
    emerge under current parameters:

    1. **Weak adaptation rate**: The preference adaptation rate (0.02--0.05 per step) may be too slow
       relative to the simulation length (200 steps in Package D) to produce visible drift.
    2. **Symmetric conformity**: The current conformity mechanism pushes agents toward the local
       neighborhood mean equally in both directions, rather than amplifying deviations asymmetrically.
    3. **No threshold feedback**: The model lacks mechanisms that would make delegation self-reinforcing
       beyond a critical adoption level -- e.g., skill decay that makes self-service progressively
       harder once an agent has delegated for many steps.
    4. **Homogeneous starting conditions**: All agents in a given scenario share the same mean delegation
       preference; true mixed populations with bimodal distributions might show different dynamics.

    This negative result identifies specific directions for future work: stronger feedback mechanisms
    (endogenous pricing, skill atrophy, explicit norm cascades with tipping points) would be needed to
    reproduce the hypothesized lock-in dynamics. The current model establishes a *baseline* from which
    to measure whether additional mechanisms produce qualitatively different behavior.

    ### 6.5 Service Cost Sensitivity (Cross-Cutting)

    {I('figure_13_cost_sensitivity')}

    Figure 13 examines the role of service cost as a contextual moderator, probing whether cheaper
    services uniformly benefit agents or whether their effect depends on system state. The left panel
    compares stress levels under low versus high service costs across five parameter environments; the
    right panel identifies the task load at which low cost transitions from beneficial to harmful.

    The central finding is that **low service cost is conditionally beneficial**:

    - In the **Default** context (moderate parameters), lower service cost modestly reduces stress
      ({_fmt(stats.get('cost_default_low_stress', 0), 3)} vs
      {_fmt(stats.get('cost_default_high_stress', 0), 3)}) -- cheaper services enable occasional
      delegation that genuinely relieves time pressure without overwhelming provider capacity.
    - In the **Type A** context (low delegation, high self-reliance), the cost difference has minimal
      impact because few agents delegate regardless of price.
    - In the **Overloaded** context (high task loads, high delegation), both low and high cost produce
      near-maximum stress ({_fmt(stats.get('cost_overloaded_low_stress', 0), 3)} vs
      {_fmt(stats.get('cost_overloaded_high_stress', 0), 3)}) -- the system has passed the point where
      price signals can influence outcomes.
    - Near the **threshold band** (task load 3.0--3.25), low service cost can *amplify* stress by
      encouraging more delegation than the system's provider capacity can absorb. Cheaper services
      attract more delegation requests, overwhelming providers and generating *more* backlog than the
      higher-cost scenario where agents self-serve more frequently.

    The right panel maps the "flip point" -- the task load at which low cost transitions from
    stress-reducing to stress-amplifying. This flip point consistently falls in the 3.0--3.5 range,
    reinforcing the threshold dynamics identified in H2. The interaction between service cost and task
    load is a classic nonlinear phenomenon: the same intervention (lowering price) produces opposite
    effects depending on whether the system is below or near its capacity boundary.

    ---

    ## 7. Hypothesis Verdict Matrix

    {_markdown_table(tables['hypothesis_verdict'])}

    ---

    ## 8. Discussion

    ### 8.1 Claim Boundaries

    This analysis employs a three-tier claim structure to maintain transparency:

    **Can Say Confidently:**
    - The ABM identifies parameter regions where higher delegation associates with higher total labor.
    - The ABM compares how stress, labor, and inequality evolve under different configurations.
    - The ABM tests whether moderate delegation states remain stable under its feedback rules.

    **Can Say With Caveat:**
    - Lower service prices push behavior toward more delegation, but only as an exogenous experiment.
    - Norm lock-in is approximated through delegation convergence, not direct delay-tolerance measurement.
    - Convenience shifts burdens toward providers, but the exact labor market structure is outside scope.

    **Cannot Claim:**
    - The model cannot identify the full causal loop because prices are not endogenous.
    - The model cannot measure real populations, named societies, or concrete policy outcomes.
    - The model cannot test skill decay, demographic inequality, or explicit delay-tolerance dynamics.

    ### 8.2 The Translation as Contribution

    The primary contribution of this work lies not in the specific findings about delegation dynamics, but
    in the demonstrated process of **structured translation**: taking a vague observation ("something feels
    different about convenience here"), formalizing it as a feedback loop structure, implementing it as
    white-box agent decision rules, running systematic experiments, and reporting honestly what was found.

    This process demonstrates two specific capabilities:

    1. **Synthesizing and conceptualizing information**, transforming qualitative observations into
       structured outputs (causal loop diagrams, agent decision functions, parameter presets) relevant for
       model specification.
    2. **Data stewardship**, using empirical stylized facts to inform model parameters, designing
       reproducible experiments, maintaining source-level auditability for every figure and table, and
       applying a transparent three-tier claim framework.

    ### 8.3 Relation to Complexity Science

    The convenience-autonomy tension maps onto well-established concepts in complex adaptive systems:
    positive feedback loops driving path dependence, threshold effects marking regime transitions, and
    emergent inequality from homogeneous agent rules. The model's results are consistent with these
    theoretical expectations, though the specific quantitative findings are contingent on the model's
    parameterization.

    ---

    ## 9. Scope of This Work and Limitations

    ### 9.1 Methodological Demonstration, Not Domain Contribution

    The author is a computational and IT professional with experience in system design, data engineering,
    and AI applications -- **not a trained social scientist or economist**. This report demonstrates the
    *process* of translating qualitative observations into formal computational models, specifically
    showcasing capabilities in:

    - Synthesizing qualitative and quantitative input into structured, testable computational frameworks
    - Designing and executing systematic simulation experiments
    - Maintaining rigorous data stewardship with transparent provenance

    **The model design, theoretical derivations, and the conclusions drawn may not be accurate from a
    domain-expert perspective.** The ABM is a deliberately simplified, stylized representation of vastly
    more complex social phenomena. Readers should evaluate the *methodology and process quality* rather
    than treating the substantive conclusions as authoritative social science findings.

    ### 9.2 Technical Limitations

    - **Exogenous prices**: Service costs are fixed parameters, not market-determined. This prevents
      testing the full circular causality between cheap services and service dependency.
    - **No delay tolerance**: The model does not capture the "tolerance for delay" variable identified
      in the original observations. This would require explicit temporal preference mechanisms.
    - **Scale**: 100 agents on a small-world network. Larger populations might reveal different dynamics.
    - **Absent mechanisms**: Skill decay, demographic heterogeneity, institutional buffers, and explicit
      quality-of-service variation are not modeled.
    - **Stylized facts, not calibration**: Parameters are informed by ILO/WVS/OECD data ranges but are
      not fitted to specific empirical distributions.

    ### 9.3 Future Extensions

    - **Endogenous price formation**: Service costs that respond to supply and demand.
    - **Delay tolerance dynamics**: Agents that develop expectations about service speed.
    - **Skill decay and learning**: Competence that changes with practice or delegation frequency.
    - **Larger networks with community structure**: Clustered norms and heterogeneous neighborhoods.
    - **Empirical calibration**: Partnership with domain experts to ground the model in specific data.

    ---

    ## 10. Conclusion

    This agent-based modeling study explored the **convenience-autonomy tension** through 14,656
    simulation runs, testing four hypotheses about service delegation, labor transfer, threshold effects,
    and norm lock-in. The key findings within the model:

    1. **Delegation increases system labor** (H1, strong support): Type B generates ~{_fmt_pct(stats['labor_delta_pct'])}
       more total labor, a persistent structural gap across all simulation horizons.
    2. **A narrow threshold triggers involution** (H2, strong support): The transition from manageable
       delegation to cumulative overload occurs in a narrow band (task load 3.0--3.25).
    3. **Autonomy preserves available time** (H3, partial support): Type A retains more personal time,
       though "well-being" is only approximated by time and stress proxies.
    4. **Mixed-system instability is weak** (H4, partial, important negative): Under current parameters,
       mixed systems do not bifurcate dramatically -- a constraint on future modeling.

    **The contribution of this work lies in demonstrating a rigorous methodology for structured
    translation -- from qualitative social observation to formal computational model to transparent
    experimental analysis -- rather than in the specific substantive conclusions.** The model is a
    proof-of-concept that illustrates how everyday observations about social systems can be formalized,
    tested, and honestly reported, while maintaining clear boundaries on what the analysis can and cannot
    claim.

    ---

    ## Appendix

    ### A.1 Parameter Sensitivity

    {I('figure_14_param_sensitivity')}

    Figure 14 presents small-multiples showing how three key outcome metrics -- average stress, total
    labor hours, and backlog tasks -- respond to task load at five different delegation levels (0.05,
    0.25, 0.45, 0.65, 0.85). Several patterns are visible:

    - **Stress**: At low task loads (< 2.5), stress is uniformly low regardless of delegation level.
      Above the threshold band (3.0--3.25), stress saturates rapidly. Higher delegation levels produce
      marginally higher stress at any given task load, but the dominant factor is task load itself.
    - **Total labor hours**: The separation between delegation levels is most visible in the
      sub-threshold range. Higher delegation generates more total labor even when the system is
      comfortable -- confirming H1's finding that the labor premium is not contingent on overload.
    - **Backlog tasks** (log scale): The most dramatic visualization of the threshold. Below 3.0, backlog
      is zero for all delegation levels. Above 3.25, backlog grows by orders of magnitude. The steepness
      of this transition -- spanning from zero to thousands within a 0.25-unit window -- illustrates why
      the threshold is a phase transition rather than a gradual degradation.

    The sensitivity analysis reinforces that **task load is the primary driver** of system behavior, with
    delegation preference acting as a secondary modulator that shifts the equilibrium level but does not
    qualitatively change the regime structure.

    ### A.2 Campaign Coverage

    {I('figure_15_campaign_coverage')}

    Figure 15 maps the parameter-space coverage of all 14,656 runs across four packages. Package B
    (Convenience Transfer) provides the densest coverage of the delegation--task load plane, with
    systematic grid sampling across both dimensions. Package A (Everyday Friction) covers two specific
    configurations (Type A and Type B presets) across four simulation horizons. Package C (Cheap Service
    Trap) explores the service cost dimension across multiple contexts. Package D (Norm Lock-in) probes
    the conformity--delegation interaction space. The combined coverage ensures that the key parameter
    interactions relevant to all four hypotheses are sampled with sufficient density for reliable
    statistical conclusions.

    ---

    *This model explores abstract social dynamics using stylized Type A / Type B configurations. It is
    not intended to characterize or evaluate any specific society, culture, or nation.*

    *Report generated by `formal_campaign_report_v2.py` from campaign data. All figures have
    corresponding source CSV files for independent verification.*
    """)
    return _strip_indent(report)


# ---------------------------------------------------------------------------
# Report rendering — Chinese
# ---------------------------------------------------------------------------

def _render_chinese(report_path: Path, fig_paths: dict[str, Path],
                     tables: dict[str, pd.DataFrame], stats: dict) -> str:
    """Generate the full Chinese Markdown research report."""
    I = lambda slug: _md_img(report_path, fig_paths[slug], slug, language="zh")

    report = textwrap.dedent(f"""\
    # 便利悖论：基于代理的服务委托、劳动转移与社会内卷探索性研究

    **作者：** 施际原 | 计算社会科学作品集研究
    **日期：** {date.today().isoformat()}
    **实验规模：** 14,656 次仿真运行，4 个研究包（research_v2 引擎）

    ---

    > *在海外生活几年后，某个周日下午，我站在一家关门的超市前。在另一个大陆的城市里，我几乎可以
    > 在任何时间走进街角的便利店。这个小小的不便让我思考了很久——不是因为它是什么困难，而是因为
    > 它像一根线头，我越拉越发现它连接着更大的东西：一张由相互依赖的社会机制编织而成的网。*
    >
    > *到底是廉价服务在先，还是对服务的依赖在先？低价是原因还是结果？一旦反馈循环启动，
    > 提高价格还能改变什么吗？*

    ---

    ## 1. 摘要

    本报告采用**代理基模型 (Agent-Based Model, ABM)** 研究**便利-自主权张力**——即不同社会在个人
    自力更生与服务委托之间呈现出显著不同的均衡状态，且这些均衡似乎具有自我强化特性。

    使用基于 Mesa 框架的仿真系统（100 个代理，Watts-Strogatz 小世界网络），我们探索了关于委托率、
    服务成本、社会从众压力和任务负荷如何交互产生系统总劳动、个体压力和不平等涌现模式的四个假设。
    **14,656 次运行**构成了证据基础。

    模型内的主要发现：(1) 便利导向配置（B 类）持续产生约 **{_fmt_pct(stats['labor_delta_pct'])}** 的
    额外系统劳动；(2) 窄任务负荷阈值带（3.0--3.25 任务/步）标志着从可管理委托到累积过载的转变；
    (3) 自主导向代理保留更多可用时间（{_fmt(stats['ta_avail'], 2)}h vs {_fmt(stats['tb_avail'], 2)}h）。

    **重要说明：** 本研究是一项方法论演示，旨在展示将定性社会观察转化为正式代理基模型的过程，
    体现结构化信息综合与计算数据管理能力。作者是计算领域专业人员，而非社会学或经济学领域专家。
    模型设计、理论框架和由此得出的结论均具探索性质，不应被视为权威性社会科学发现。读者应评估
    方法论的严谨性和分析过程的透明度，而非将实质性结论视为定论。

    ---

    ## 2. 问题定义与理论框架

    ### 2.1 便利-自主权张力

    不同社会的日常生活节奏呈现出截然不同的模式。在某些环境中，个人自行管理大部分日常事务——做饭、
    跑腿、小修理——接受更高的时间成本和较慢的服务时效。在其他环境中，价格低廉的第三方服务鼓励
    广泛委托，形成节奏更快、联系更紧密的服务生态系统。

    从**复杂适应系统**的视角来看，这些模式可以被理解为个体决策、服务可用性、价格结构、社会规范
    和时间约束之间交互反馈循环的涌现属性。

    ### 2.2 概念因果环路

    {I('figure_01_causal_loop')}

    图 1 展示了模型中嵌入的概念反馈结构。两个增强回路占主导：**R1**（压力驱动的委托螺旋）和
    **R2**（规范驱动的便利锁定）。

    ### 2.3 从观察到正式模型

    从定性观察到计算模型的翻译经过三个阶段：识别反馈机制、形式化为代理规则、设计隔离实验。
    这种结构化翻译本身就是本工作的核心贡献。

    ---

    ## 3. 研究问题与假设

    {_markdown_table(tables['question_map'])}

    四个假设：

    - **H1**：更高的委托率导致更高的系统总劳动时间。
    - **H2**：临界委托阈值触发内卷螺旋。
    - **H3**：更高的自主权与较低的便利感知但更高的总体福祉相关。
    - **H4**：混合系统（适度委托）不稳定，会向极端漂移。

    ---

    ## 4. 模型规范

    ### 4.1 代理架构

    每个 **Resident** 代理拥有 8.0 小时的日时间预算，每步接收 1-5 个任务。委托决策公式：

    *p_eff = clamp( p_base + 0.30 * stress + 0.25 * skill_gap - 0.25 * cost, 0, 1 )*

    ### 4.2 模型生命周期

    {I('figure_02_model_lifecycle')}

    ### 4.3 参数配置

    {I('figure_03_radar_profile')}

    ### 4.4 研究引擎增强（research_v2）

    {_markdown_table(tables['model_delta'])}

    ---

    ## 5. 实验设计与数据管理

    实验包含 **14,656 次完成的运行**，组织为四个研究包。所有运行使用 research_v2 引擎，
    采用尾窗聚合（最后 20% 步数），每个场景单元跨多个随机种子复制。

    ---

    ## 6. 结果

    ### 6.1 H1：委托增加系统总劳动（强支持）

    {I('figure_04_horizon_panel')}

    图 4 在四个仿真时长（120、200、300、450 步）下比较 A 类（自主导向）与 B 类（便利导向）。
    六项关键指标揭示了持续的结构性差异——这些差异既不随时长收敛也不发散，表明这是真正的均衡分离
    而非瞬态动力学。

    **总劳动时间**差距最为显著：450 步时 B 类产生 {_fmt(stats['tb_labor'], 1)} 小时，A 类为
    {_fmt(stats['ta_labor'], 1)} 小时——**{_fmt_pct(stats['labor_delta_pct'])} 的溢价**。
    该差距在 120 步时即已可见（约 {_fmt_pct(stats.get('h120_delta_pct', 0))} 差异），
    并在所有后续时长中保持稳定，证实劳动开销是高委托配置的*结构性*特征而非初始化假象。

    **压力水平**反映了相同模式：450 步时 B 类代理平均压力为 {_fmt(stats['tb_stress'], 3)}，
    A 类为 {_fmt(stats['ta_stress'], 3)}。虽然两者均低于饱和值（1.0），但持续差距反映了便利配置中
    协调开销和服务提供职责对时间预算的压缩。

    **可用时间**从代理层面最直接地呈现影响：A 类代理平均保留 {_fmt(stats['ta_avail'], 2)} 小时
    自由时间，B 类仅有 {_fmt(stats['tb_avail'], 2)} 小时——约
    {_fmt(stats['ta_avail'] - stats['tb_avail'], 2)} 小时的差距。在 8 小时日预算中，A 类代理保留
    约 {_fmt_pct(stats['ta_avail'] / 8.0 * 100)} 的时间作为可支配时间，B 类仅为
    {_fmt_pct(stats['tb_avail'] / 8.0 * 100)}。

    **委托率**确认了配置差异：B 类委托 {_fmt_pct(stats['tb_deleg_frac'] * 100)} 的任务，
    A 类为 {_fmt_pct(stats['ta_deleg_frac'] * 100)}。**收入基尼系数** B 类略高
    （{_fmt(stats.get('tb_gini_income', 0), 3)} vs {_fmt(stats.get('ta_gini_income', 0), 3)}），
    反映了服务经济结构中的收入分化。

    {I('figure_05_agent_distributions')}

    图 5 揭示了代理层面的分布特征。A 类可用时间以 {_fmt(stats['ta_avail'], 1)} 小时为中心呈宽分布，
    反映了任务负荷和技能水平的个体差异。B 类可用时间更低且分布更紧——从众压力使委托行为趋同，
    也使其后果趋同。B 类收入分布呈现更长的右尾，是服务经济中部分代理从服务提供中获得显著更多
    收入的标志。

    **本结果未能说明的：** 模型使用外生固定服务成本。在真实经济中，{_fmt_pct(stats['labor_delta_pct'])}
    的劳动溢价可能被内生价格调整、专业化带来的生产率提升或服务质量改善部分抵消。该溢价反映的是
    模型核算框架内的*协调和提供者开销的结构性成本*。

    ### 6.2 H2：阈值触发内卷（强支持）

    {I('figure_06_phase_atlas')}

    图 6 展示委托-任务负荷相位图谱，映射两个最重要控制参数空间中的系统级积压。
    颜色梯度（对数标度）揭示三个截然不同的状态域：

    1. **安全区**（左下，深色）：低任务负荷和/或低委托。系统吸收全部任务，无残余积压。
    2. **过渡带**（对角走廊，黄-橙色）：积压首次出现的窄带区域。微小参数变化导致不成比例的
       巨大结果差异——复杂系统中相变行为的特征。
    3. **过载区**（右上，深红色）：高任务负荷结合中高委托率。积压每步累积增长，所有代理
       趋向最大压力和劳动饱和。

    白色起始线追踪积压首次超过零的边界，该边界持续位于**任务负荷 3.0--3.25** 范围内。

    {I('figure_07_threshold_detail')}

    图 7 通过三个互补面板分离阈值机制：

    **(a) 阈值处的压力**：积压首次出现时，代理已经历升高的压力，表明系统在可见过载之前就已
    达到容量极限。更高的委托水平使起始点对应更低的压力值——委托更多的代理更早触及容量壁垒。

    **(b) 首次积压的任务负荷**：阈值任务负荷在各委托水平间高度一致，徘徊在 3.0-3.25 任务/步。
    这一仅 0.25 单位的窄带代表临界窗口：低于此值系统找到均衡，高于此值累积过载开始。

    **(c) 精细过渡带**：最小和最大委托水平之间的压力包络在阈值之上呈现紧密收敛。一旦积压
    开始累积，系统轨迹主要由任务负荷决定，委托水平成为次要因素。

    {I('figure_08_story_timeseries')}

    图 8 通过四个故事案例追踪六项指标的动态轨迹：

    - **自主基线**：稳定均衡，压力低（{_fmt(stats.get('auto_tail_stress', 0), 3)}），
      总劳动适中（{_fmt(stats.get('auto_tail_total_labor_hours', 0), 1)}h），积压为零。
    - **便利基线**：较高但仍稳定的均衡，压力 {_fmt(stats.get('conv_tail_stress', 0), 3)}，
      总劳动 {_fmt(stats.get('conv_tail_total_labor_hours', 0), 1)}h。服务劳动占总劳动的
      主要比例。
    - **阈值压力**：近临界运行，压力 {_fmt(stats.get('thresh_tail_stress', 0), 3)}，
      总劳动 {_fmt(stats.get('thresh_tail_total_labor_hours', 0), 1)}h。积压可能间歇出现但
      不会螺旋失控。
    - **过载便利**：灾难性崩溃。压力在约 50 步内饱和至 1.0。积压指数增长至
      {_fmt(stats.get('overload_tail_backlog_tasks', 0), 0)} 个任务。总劳动达到上限
      （{_fmt(stats.get('overload_tail_total_labor_hours', 0), 1)}h）。这是内卷螺旋的
      纯粹形态。

    **本结果未能说明的：** 3.0--3.25 阈值带是该模型特定配置（100 代理、8 小时预算、15% 协调
    开销、11% 提供者开销、贪心匹配）的属性。阈值*概念*——分隔可管理与灾难性动力学的窄带——
    是可迁移的洞见；具体数值是该特定模型的属性。

    ### 6.3 H3：自主权保留福祉（部分支持）

    {I('figure_09_labor_decomposition')}

    图 9 将劳动预算分解为三个组成部分：自劳动（代理自行完成的任务）、服务劳动（提供者代为完成
    的任务）和协调成本（匹配和委托交易的开销）。

    分解揭示了便利如何在*过载*系统之前先*重塑*劳动结构：

    - **自主基线**：自劳动占主导（{_fmt(stats.get('auto_tail_self_labor_hours', 0), 1)}h），
      服务劳动最低（{_fmt(stats.get('auto_tail_service_labor_hours', 0), 1)}h），
      协调可忽略（{_fmt(stats.get('auto_tail_coordination_hours', 0), 1)}h）。
      总计：{_fmt(stats.get('auto_tail_total_labor_hours', 0), 1)}h。
    - **便利基线**：自劳动降至 {_fmt(stats.get('conv_tail_self_labor_hours', 0), 1)}h，但服务劳动
      升至 {_fmt(stats.get('conv_tail_service_labor_hours', 0), 1)}h，协调成本增加
      {_fmt(stats.get('conv_tail_coordination_hours', 0), 1)}h。总计：
      {_fmt(stats.get('conv_tail_total_labor_hours', 0), 1)}h——尽管自劳动大幅减少，总量反而
      *更高*。这是 H1 在组件层面的具体表现。

    委托劳动增量线（橙色，右轴）量化了委托的*净*劳动效应：在便利配置中始终为正，证实在本模型中
    委托是*净劳动创造者*而非劳动节省者。每个委托任务因协调开销（15%）和提供者时间惩罚（11%）
    而产生比自行完成更多的总系统工时。

    {I('figure_10_available_time_density')}

    图 10 比较最终步的可用时间分布。A 类代理以 {_fmt(stats['ta_avail'], 1)} 小时为中心呈现宽分布。
    B 类代理聚集在更低的 {_fmt(stats['tb_avail'], 1)} 小时处且分布更紧——从众压力使委托行为
    趋同，也使其后果趋同。

    {_fmt(stats['ta_avail'] - stats['tb_avail'], 2)} 小时的可用时间差距代表了模型抽象框架内
    有意义的生活方式差异：A 类代理保留约 {_fmt_pct(stats['ta_avail'] / 8.0 * 100)} 的日预算
    作为自由时间，B 类仅 {_fmt_pct(stats['tb_avail'] / 8.0 * 100)}。在模型中，这是
    "便利的代价"——尽管模型无法评估代理是否会主观偏好这一权衡。

    **本结果未能说明的：** "福祉"仅通过可用时间和压力指标近似。模型无法衡量主观满意度、
    感知便利、委托服务质量或自由时间的心理价值。B 类代理可能尽管可用时间较少但体验到更高的
    感知生活质量——这完全超出模型的测量能力。"部分支持"的判定反映了我们能测量的（时间、压力）
    与完整福祉评估所需测量的之间的重要差距。

    ### 6.4 H4：混合系统与规范锁定（部分支持，重要阴性结果）

    {I('figure_11_mixed_heatmap')}

    图 11 映射混合系统参数空间中最终委托率的标准差，测试中等委托水平的群体是否在从众压力下
    向极端漂移。实验在初始委托偏好（0.35--0.65）和社会从众压力（0.1--0.9）之间进行网格扫描。

    结果清晰且值得注意：最大观察标准差仅为 **{_fmt(stats['mixed_max_std'], 4)}**。在所有 30 个
    参数组合中，系统保持惊人的稳定。更高的从众压力不会产生可测量的更大分散度——热图中的
    单元格标注显示整个网格中数值几乎一致。

    {I('figure_12_mixed_scatter')}

    图 12 从逐种子视角强化了这一发现。每个点代表一次仿真运行的最终委托率与其初始委托偏好均值
    的关系，颜色编码从众压力。点紧密聚集在恒等线（初始 = 最终）附近，对从众压力无可见依赖。
    即使在最高从众压力（0.9）下，最终委托率也在初始值的 {_fmt(stats['mixed_max_std'], 4)} 范围内。

    这是一个**重要的阴性结果**，其科学价值恰恰在于约束了模型的解释力。可能的解释包括：

    1. **弱适应率**：偏好适应率（每步 0.02--0.05）相对于仿真长度可能太慢。
    2. **对称从众**：当前从众机制将代理向邻域均值对称推动，而非不对称放大偏差。
    3. **缺少阈值反馈**：模型缺少使委托在临界采用水平之上自我强化的机制（如使自我服务
       逐渐变难的技能衰退）。

    该阴性结果为未来工作指明了具体方向：需要更强的反馈机制（内生定价、技能退化、显式规范
    级联）才能重现假设中的锁定动力学。当前模型建立了一个*基线*，用以衡量附加机制是否产生
    质性不同的行为。

    ### 6.5 服务成本敏感性（交叉分析）

    {I('figure_13_cost_sensitivity')}

    图 13 检验服务成本作为情境调节因子的角色。左面板比较五种参数环境下低与高服务成本的压力水平；
    右面板识别低成本从有益转变为有害的任务负荷转折点。

    核心发现是**低服务成本是有条件有益的**：

    - 在**默认**环境中，较低的服务成本适度降低压力（{_fmt(stats.get('cost_default_low_stress', 0), 3)}
      vs {_fmt(stats.get('cost_default_high_stress', 0), 3)}）——更便宜的服务使偶尔委托真正减轻了
      时间压力。
    - 在**A 类**环境（低委托、高自给）中，成本差异影响极小，因为无论价格如何，很少有代理选择委托。
    - 在**过载**环境中，低成本和高成本均产生接近最大压力
      （{_fmt(stats.get('cost_overloaded_low_stress', 0), 3)} vs
      {_fmt(stats.get('cost_overloaded_high_stress', 0), 3)}）——系统已超越价格信号能影响结果的范围。
    - 在**阈值带**附近（任务负荷 3.0--3.25），低服务成本反而*放大*压力——更便宜的服务吸引更多委托
      请求，超出提供者容量，产生比高成本场景（代理更多自我服务）更多的积压。

    右面板映射"翻转点"——低成本从减压转变为增压的任务负荷。该翻转点一致落在 3.0--3.5 范围，
    强化了 H2 中识别的阈值动力学。服务成本与任务负荷之间的交互作用是典型的非线性现象：
    同一干预（降价）因系统是否处于容量边界以下或附近而产生相反效果。

    ---

    ## 7. 假设判定矩阵

    {_markdown_table(tables['hypothesis_verdict'])}

    ---

    ## 8. 讨论

    ### 8.1 声明边界

    本分析采用三层声明框架以维持透明度：

    **可以自信地说：**
    - ABM 可以识别更高委托与更高系统总劳动相关联的参数区域。
    - ABM 可以比较不同配置下压力、劳动和不平等的演化轨迹。
    - ABM 可以测试中等委托状态在其反馈规则下是否保持稳定。

    **需附加说明：**
    - 较低的服务价格推动更多委托行为，但仅作为外生实验处理。
    - 规范锁定通过委托收敛近似代理，而非直接测量延迟容忍度。
    - 便利将负担转移向提供者，但确切的劳动市场结构超出模型范围。

    **无法声称：**
    - 模型无法识别完整的因果循环，因为价格不是内生的。
    - 模型无法衡量真实人口、具名社会或具体政策结果。
    - 模型无法测试技能衰退、人口不平等或显式延迟容忍度动力学。

    ### 8.2 翻译过程作为贡献

    本工作的首要贡献不在于关于委托动力学的具体发现，而在于展示的**结构化翻译过程**——从模糊
    的社会观察（"便利在这里感觉不同"）出发，将其形式化为反馈环路结构，实现为白盒代理决策规则，
    运行系统化实验，并诚实报告发现。

    这一过程展示了两项具体能力：

    1. **信息综合与概念化**：将定性观察转化为因果环路图、代理决策函数、参数预设等结构化输出，
       适用于模型规范。
    2. **数据管理**：使用经验风格化事实指导模型参数、设计可重复实验、维护每个图表和表格的
       源级可审计性，并应用透明的三层声明框架。

    ### 8.3 与复杂性科学的关联

    便利-自主权张力映射到复杂适应系统中已确立的概念：驱动路径依赖的正反馈循环、标志状态
    转变的阈值效应、以及从同质代理规则中涌现的不平等。模型结果与这些理论预期一致，尽管具体
    定量发现取决于模型的参数化。

    ---

    ## 9. 本研究的范围与局限性

    ### 9.1 方法论演示，非领域贡献

    作者是计算与 IT 专业人员，**不是受过训练的社会科学家或经济学家**。本报告展示的是将定性观察
    转化为正式计算模型的*过程*，具体展示以下能力：

    - 将定性和定量输入综合为结构化、可测试的计算框架
    - 设计和执行系统化仿真实验
    - 维护具有透明溯源的严格数据管理

    **模型设计、理论推导及所得结论从领域专家角度来看可能并不准确。** ABM 是对极其复杂的社会现象
    的刻意简化的风格化表示。读者应评估*方法论和过程质量*，而非将实质性结论视为权威性社会科学发现。

    ### 9.2 技术局限

    - **外生价格**：服务成本为固定参数，而非由市场决定。这阻止了测试廉价服务与服务依赖
      之间的完整循环因果关系。
    - **无延迟容忍度**：模型未捕捉原始观察中识别的"延迟容忍度"变量。这需要显式的时间
      偏好机制。
    - **规模**：小世界网络上的 100 个代理。更大的群体可能揭示不同的动力学。
    - **缺失机制**：技能衰退、人口异质性、制度缓冲和显式服务质量变化未被建模。
    - **风格化事实而非校准**：参数由 ILO/WVS/OECD 数据范围启发，但未拟合到具体经验分布。

    ### 9.3 未来扩展

    - **内生价格形成**：响应供需的服务成本。
    - **延迟容忍度动力学**：发展服务速度期望的代理。
    - **技能衰退与学习**：随实践或委托频率变化的能力。
    - **更大的社区结构网络**：聚集的规范和异质邻域。
    - **经验校准**：与领域专家合作，将模型扎根于具体数据。

    ---

    ## 10. 结论

    本代理基建模研究通过 14,656 次仿真运行探索了**便利-自主权张力**，测试了关于服务委托、
    劳动转移、阈值效应和规范锁定的四个假设。模型内的关键发现：

    1. **委托增加系统劳动**（H1，强支持）：B 类产生约 {_fmt_pct(stats['labor_delta_pct'])}
       的额外总劳动，这一差距在所有仿真时长中持续存在。
    2. **窄阈值触发内卷**（H2，强支持）：从可管理委托到累积过载的转变发生在任务负荷
       3.0--3.25 的窄带中——仅 0.25 单位的参数窗口分隔了均衡与崩溃。
    3. **自主权保留可用时间**（H3，部分支持）：A 类代理保留更多个人时间
      （{_fmt(stats['ta_avail'], 2)}h vs {_fmt(stats['tb_avail'], 2)}h），尽管"福祉"
       仅通过时间和压力代理指标近似。
    4. **混合系统不稳定性较弱**（H4，部分支持，重要阴性结果）：在当前参数下，混合系统不会
       剧烈分叉——对未来建模的约束条件。

    **本工作的贡献在于展示了从定性社会观察到正式计算模型再到透明实验分析的严谨方法论，
    而非特定的实质性结论。** 模型是一个概念验证，展示了如何将关于社会系统的日常观察
    形式化、测试并诚实报告，同时保持对分析能做和不能做的声明的清晰边界。

    ---

    ## 附录

    ### A.1 参数敏感性

    {I('figure_14_param_sensitivity')}

    图 14 展示三项关键结果指标（平均压力、总劳动时间、积压任务）如何随任务负荷在五个不同
    委托水平（0.05、0.25、0.45、0.65、0.85）下变化：

    - **压力**：低任务负荷（< 2.5）下，无论委托水平如何，压力均匀低。阈值带（3.0--3.25）
      以上压力快速饱和。任务负荷是主导因素。
    - **总劳动时间**：委托水平之间的分离在阈值以下最为可见。更高委托即使在系统舒适时也
      产生更多总劳动——证实 H1 的发现不依赖于过载。
    - **积压任务**（对数标度）：阈值最戏剧性的可视化。3.0 以下积压为零，3.25 以上积压增长
      数个数量级。0.25 单位窗口内从零到数千的陡峭转变说明了为何阈值是相变而非渐进退化。

    ### A.2 实验覆盖

    {I('figure_15_campaign_coverage')}

    图 15 映射所有 14,656 次运行在四个研究包中的参数空间覆盖。B 包（便利转移）在委托-任务
    负荷平面提供最密集覆盖。A 包（日常摩擦）覆盖两种特定配置的四个时长。C 包（廉价服务陷阱）
    探索服务成本维度。D 包（规范锁定）探查从众-委托交互空间。综合覆盖确保与所有四个假设相关
    的关键参数交互以足够密度采样。

    ---

    *本模型使用抽象的 A 类 / B 类配置探索社会动力学。不旨在刻画或评价任何特定社会、文化或国家。*

    *报告由 `formal_campaign_report_v2.py` 从实验数据生成。所有图表均有对应的源 CSV 文件供独立验证。*
    """)
    return _strip_indent(report)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def build_formal_report_v2(
    campaign_dir: Path,
    report_dir: Path = REPORTS_DIR,
    asset_root: Path | None = None,
) -> ReportOutputs:
    """Main pipeline: load data, draw figures, render reports."""

    _apply_style()
    logger.info("Loading campaign inputs from %s", campaign_dir)
    inputs = _load_inputs(campaign_dir)
    combo = inputs["combo"]
    per_seed = inputs["per_seed"]

    if asset_root is None:
        asset_root = campaign_dir / "report_assets" / "formal_report_v2"
    fdir = _ensure_dir(asset_root / "figures")
    sdir = _ensure_dir(asset_root / "sources")
    tdir = _ensure_dir(asset_root / "tables")
    manifest_items: list[dict] = []

    # --- Data preparation ---
    logger.info("Preparing data...")
    baseline = _baseline_horizon_source(combo)
    key_table = _story_case_key_table(inputs["story_sel"])
    timeseries = _combined_story_timeseries(inputs["story_sel"])
    atlas = _threshold_atlas_source(combo)
    onset = _threshold_onset_table(atlas)
    ref_sum = _threshold_refinement_summary(inputs["threshold_refine"])
    cost_ctx = _service_cost_context_source(combo)
    cost_flip = _service_cost_flip_source(combo)
    mixed_hm, mixed_pt = _mixed_stability_sources(combo, per_seed)
    claims = _parse_claim_safety(inputs["claim_text"])
    snapshots = _load_agent_snapshots(campaign_dir, ["autonomy_baseline", "convenience_baseline"])

    # --- Tables ---
    qmap = _question_hypothesis_mapping()
    mdelta = _model_delta_table()
    verdict = _hypothesis_verdict(baseline, onset, cost_ctx, mixed_hm)
    stats = _narrative_stats(combo, per_seed, inputs["threshold_refine"],
                              cost_ctx, cost_flip, mixed_hm,
                              key_table=key_table)

    table_frames = {"question_map": qmap, "model_delta": mdelta,
                     "hypothesis_verdict": verdict, "claims": claims}
    for tname, tdf in table_frames.items():
        tp = _save_csv(tdf, tdir / f"table_{tname}.csv")
        _add_manifest(manifest_items, kind="table", slug=f"table_{tname}",
                      path=tp, sources=[tp])

    # --- Figures ---
    logger.info("Drawing 15 figures...")
    fig_paths: dict[str, Path] = {}

    def _track(slug: str, result: tuple[Path, Path]) -> None:
        fig_paths[slug] = result[0]

    _track("figure_01_causal_loop", _fig01_causal_loop(fdir, sdir, manifest_items))
    _track("figure_02_model_lifecycle", _fig02_model_lifecycle(fdir, sdir, manifest_items))
    _track("figure_03_radar_profile", _fig03_radar_profile(fdir, sdir, manifest_items))
    _track("figure_04_horizon_panel", _fig04_horizon_panel(baseline, fdir, sdir, manifest_items))
    _track("figure_05_agent_distributions", _fig05_agent_distributions(snapshots, fdir, sdir, manifest_items))
    _track("figure_06_phase_atlas", _fig06_phase_atlas(atlas, onset, fdir, sdir, manifest_items))
    _track("figure_07_threshold_detail", _fig07_threshold_detail(onset, ref_sum, fdir, sdir, manifest_items))
    _track("figure_08_story_timeseries", _fig08_story_timeseries(timeseries, fdir, sdir, manifest_items))
    _track("figure_09_labor_decomposition", _fig09_labor_decomposition(key_table, fdir, sdir, manifest_items))
    _track("figure_10_available_time_density", _fig10_available_time_density(snapshots, fdir, sdir, manifest_items))
    _track("figure_11_mixed_heatmap", _fig11_mixed_heatmap(mixed_hm, fdir, sdir, manifest_items))
    _track("figure_12_mixed_scatter", _fig12_mixed_scatter(mixed_pt, fdir, sdir, manifest_items))
    _track("figure_13_cost_sensitivity", _fig13_cost_sensitivity(cost_ctx, cost_flip, fdir, sdir, manifest_items))
    _track("figure_14_param_sensitivity", _fig14_param_sensitivity(atlas, fdir, sdir, manifest_items))
    _track("figure_15_campaign_coverage", _fig15_campaign_coverage(combo, fdir, sdir, manifest_items))

    # --- Reports ---
    logger.info("Rendering reports...")
    campaign_tag = campaign_dir.name
    en_path = report_dir / f"2026-04-02_formal_research_report_v2_{campaign_tag}_en.md"
    zh_path = report_dir / f"2026-04-02_formal_research_report_v2_{campaign_tag}_zh.md"

    en_text = _render_english(en_path, fig_paths, table_frames, stats)
    zh_text = _render_chinese(zh_path, fig_paths, table_frames, stats)

    _write_text(en_path, en_text)
    _write_text(zh_path, zh_text)
    _add_manifest(manifest_items, kind="report", slug="report_en",
                  path=en_path, sources=list(fig_paths.values()))
    _add_manifest(manifest_items, kind="report", slug="report_zh",
                  path=zh_path, sources=list(fig_paths.values()))

    # --- Manifest ---
    manifest_path = asset_root / "formal_report_v2_manifest.json"
    manifest_payload = {
        "campaign_dir": str(campaign_dir),
        "asset_root": str(asset_root),
        "reports": {"english": str(en_path), "chinese": str(zh_path)},
        "items": manifest_items,
    }
    _write_text(manifest_path, json.dumps(manifest_payload, indent=2))

    logger.info("Done. English: %s | Chinese: %s", en_path, zh_path)
    return ReportOutputs(
        campaign_dir=campaign_dir, asset_root=asset_root,
        manifest_path=manifest_path,
        english_report_path=en_path, chinese_report_path=zh_path,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build v2 formal report from campaign data.")
    parser.add_argument("--campaign-dir", required=True, help="Existing campaign directory.")
    parser.add_argument("--report-dir", default=str(REPORTS_DIR), help="Report output directory.")
    parser.add_argument("--asset-root", default=None, help="Override for figure/table assets.")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    args = _parse_args()
    build_formal_report_v2(
        Path(args.campaign_dir),
        report_dir=Path(args.report_dir),
        asset_root=Path(args.asset_root) if args.asset_root else None,
    )


if __name__ == "__main__":
    main()
