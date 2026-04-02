"""analysis/narrative_campaign.py — Narrative-first experiment campaigns.

Architecture role:
    This module implements a campaign runner for the "blog sequel" analysis
    workflow. It complements the legacy Mesa batch runner by organising
    experiments around narrative questions from
    analysis/reports/Social Phenomena and Reflections-1.md rather than only
    around H1-H4 hypothesis labels.

    The campaign runner provides three capabilities:
      1. Run parameter sweeps and preset comparisons with a multiprocessing
         pipeline that is safe on macOS spawn-based execution.
      2. Persist compact, blog-friendly artefacts: research summaries,
         figure manifests, story-case metadata, and writing-support notes.
      3. Generate publication/blog figures directly from aggregated outputs,
         avoiding the inflated agent-level CSV shape produced by Mesa's
         generic batch_run helper.

How to run:
    conda activate convenience-paradox
    python -m analysis.narrative_campaign --scale smoke --packages package_a
    python -m analysis.narrative_campaign --scale full --workers 8 --tag blog_pack

Output layout:
    data/results/campaigns/<YYYYMMDD_HHMMSS>_<tag>/
      manifest.json
      summaries/
      writing_support/
      package_a_everyday_friction/
      package_b_convenience_transfer/
      package_c_cheap_service_trap/
      package_d_norm_lock_in/

Design boundaries:
    - The ABM mechanism is not altered here. This module only orchestrates
      experiments and presentation artefacts around the current white-box model.
    - Real-world mappings are intentionally excluded from generated artefacts;
      formal outputs continue to use Type A / Type B and abstract parameter
      language only.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import product
from multiprocessing import get_context
from pathlib import Path
from typing import Any, Iterable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / "data" / "results" / ".mplconfig"))

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Use a headless backend for CLI and CI execution.
matplotlib.use("Agg")
sys.path.insert(0, str(PROJECT_ROOT))

from model.model import ConvenienceParadoxModel
from model.params import TYPE_A_PRESET, TYPE_B_PRESET, get_preset
from model.research_model import ConvenienceParadoxResearchModel

logger = logging.getLogger(__name__)

RESULTS_DIR = PROJECT_ROOT / "data" / "results"
CAMPAIGNS_DIR = RESULTS_DIR / "campaigns"
REPORTS_DIR = PROJECT_ROOT / "analysis" / "reports"
CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_METRICS = [
    "avg_stress",
    "avg_delegation_rate",
    "total_labor_hours",
    "social_efficiency",
    "gini_income",
    "gini_available_time",
    "tasks_delegated_frac",
    "unmatched_tasks",
    "avg_income",
]
TAIL_METRICS = [f"tail_{metric}" for metric in MODEL_METRICS]

PACKAGE_A = "package_a_everyday_friction"
PACKAGE_B = "package_b_convenience_transfer"
PACKAGE_C = "package_c_cheap_service_trap"
PACKAGE_D = "package_d_norm_lock_in"

PROGRESS_WRITE_INTERVAL_SECONDS = 2.0
PROGRESS_LOG_INTERVAL_SECONDS = 20.0
CHECKPOINT_WRITE_INTERVAL_SECONDS = 30.0
CHECKPOINT_WRITE_EVERY_RUNS = 50


@dataclass(frozen=True)
class PackageDefinition:
    """Narrative package metadata for grouping experiments and artefacts."""

    slug: str
    title: str
    chapter_heading: str
    narrative_focus: str
    question_prompt: str


@dataclass(frozen=True)
class ScaleConfig:
    """Runtime scale profile for smoke and full campaign execution."""

    name: str
    horizon_steps: tuple[int, ...]
    horizon_seeds: int
    atlas_delegation_values: tuple[float, ...]
    atlas_task_load_values: tuple[float, ...]
    atlas_cost_values: tuple[float, ...]
    atlas_conformity_values: tuple[float, ...]
    atlas_task_steps: int
    atlas_cost_steps: int
    atlas_conformity_steps: int
    atlas_seeds: int
    decomposition_steps: int
    decomposition_seeds: int
    threshold_steps: int
    threshold_seeds: int
    mixed_steps: int
    mixed_seeds: int
    mixed_conformity_values: tuple[float, ...]
    mixed_delegation_values: tuple[float, ...]
    story_steps: int
    story_seeds: int
    story_snapshot_steps: tuple[int, ...] | None = None


class _CampaignProgressTracker:
    """Track campaign progress and persist user-readable progress snapshots."""

    def __init__(self, campaign_dir: Path, engine: str) -> None:
        self.campaign_dir = campaign_dir
        self.engine = engine
        self.progress_path = campaign_dir / "progress.json"
        self.progress_log_path = campaign_dir / "progress.log"
        self.started_monotonic = time.monotonic()
        self.total_runs = 0
        self.total_weight = 0
        self.completed_runs = 0
        self.completed_weight = 0
        self.phase_name = "planning"
        self.phase_total_runs = 0
        self.phase_total_weight = 0
        self.phase_completed_runs = 0
        self.phase_completed_weight = 0
        self.phase_total_cells = 0
        self.phase_completed_cells: set[str] = set()
        self.phase_cell_lookup: dict[str, int] = {}
        self.status = "planning"
        self.last_completed_task: dict[str, Any] | None = None
        self._last_progress_write = 0.0
        self._last_progress_log = 0.0
        self._write_progress(force=True)
        self._append_log("Progress tracker initialised.")

    def add_planned_tasks(self, tasks: Sequence[dict[str, Any]]) -> None:
        """Increase the expected workload as soon as a task set is known."""
        self.total_runs += len(tasks)
        self.total_weight += sum(_task_weight(task) for task in tasks)
        self._write_progress(force=True)

    def start_phase(self, phase_name: str, tasks: Sequence[dict[str, Any]]) -> None:
        """Reset phase-local counters and announce a new phase."""
        self.phase_name = phase_name
        self.phase_total_runs = len(tasks)
        self.phase_total_weight = sum(_task_weight(task) for task in tasks)
        scenario_ids = sorted({_task_cell_id(task) for task in tasks})
        self.phase_total_cells = len(scenario_ids)
        self.phase_cell_lookup = {scenario_id: index + 1 for index, scenario_id in enumerate(scenario_ids)}
        self.phase_completed_runs = 0
        self.phase_completed_weight = 0
        self.phase_completed_cells = set()
        self.status = "running"
        self._write_progress(force=True)
        if tasks:
            self._append_log(
                f"Starting phase {phase_name}: {self.phase_total_runs} runs across "
                f"{self.phase_total_cells} cells."
            )

    def record_completion(self, task: dict[str, Any], *, force: bool = False) -> None:
        """Update counters after one simulation task completes."""
        weight = _task_weight(task)
        self.completed_runs += 1
        self.completed_weight += weight
        self.phase_completed_runs += 1
        self.phase_completed_weight += weight
        self.phase_completed_cells.add(_task_cell_id(task))
        self.last_completed_task = _task_progress_view(task)
        self._write_progress(force=force)
        self._log_progress(force=force)

    def mark_simulation_complete(self) -> None:
        """Mark the simulation phases complete before output generation."""
        self.status = "simulation_complete"
        self.phase_name = "simulation_complete"
        self.phase_total_runs = 0
        self.phase_total_weight = 0
        self.phase_completed_runs = 0
        self.phase_completed_weight = 0
        self.phase_total_cells = 0
        self.phase_completed_cells = set()
        self.phase_cell_lookup = {}
        self._write_progress(force=True)
        self._append_log("Simulation phases complete. Writing artefacts and reports.")

    def mark_completed(self) -> None:
        """Mark the entire campaign complete."""
        self.status = "completed"
        self.phase_name = "completed"
        self._write_progress(force=True)
        self._append_log("Campaign completed.")

    def _elapsed_seconds(self) -> float:
        return max(0.0, time.monotonic() - self.started_monotonic)

    def _eta_seconds(self) -> float | None:
        if self.completed_weight <= 0:
            return None
        if self.total_weight <= self.completed_weight:
            return 0.0
        rate = self.completed_weight / max(self._elapsed_seconds(), 1e-9)
        remaining = max(self.total_weight - self.completed_weight, 0)
        return remaining / max(rate, 1e-9)

    def _progress_payload(self) -> dict[str, Any]:
        percent_complete = 0.0
        if self.total_weight > 0:
            percent_complete = min(100.0, (self.completed_weight / self.total_weight) * 100.0)
        phase_percent = 0.0
        if self.phase_total_weight > 0:
            phase_percent = min(100.0, (self.phase_completed_weight / self.phase_total_weight) * 100.0)
        eta_seconds = self._eta_seconds()
        return {
            "status": self.status,
            "engine": self.engine,
            "campaign_dir": str(self.campaign_dir),
            "progress_log_path": str(self.progress_log_path),
            "phase": self.phase_name,
            "completed_runs": self.completed_runs,
            "total_runs": self.total_runs,
            "phase_completed_runs": self.phase_completed_runs,
            "phase_total_runs": self.phase_total_runs,
            "completed_cells_in_phase": len(self.phase_completed_cells),
            "total_cells_in_phase": self.phase_total_cells,
            "completed_weight": self.completed_weight,
            "total_weight": self.total_weight,
            "phase_completed_weight": self.phase_completed_weight,
            "phase_total_weight": self.phase_total_weight,
            "percent_complete": round(percent_complete, 2),
            "phase_percent_complete": round(phase_percent, 2),
            "elapsed_seconds": round(self._elapsed_seconds(), 1),
            "eta_seconds": None if eta_seconds is None else round(float(eta_seconds), 1),
            "elapsed_human": _format_duration(self._elapsed_seconds()),
            "eta_human": _format_duration(eta_seconds),
            "last_completed_task": self.last_completed_task,
            "updated_at": _utc_now_iso(),
        }

    def _write_progress(self, *, force: bool = False) -> None:
        now = time.monotonic()
        if not force and (now - self._last_progress_write) < PROGRESS_WRITE_INTERVAL_SECONDS:
            return
        _save_json(self.progress_path, self._progress_payload())
        self._last_progress_write = now

    def _render_progress_line(self) -> str:
        payload = self._progress_payload()
        last = payload["last_completed_task"] or {}
        return (
            "[progress] "
            f"phase={payload['phase']} "
            f"overall={payload['completed_runs']}/{payload['total_runs']} runs "
            f"({payload['percent_complete']:.2f}%) "
            f"phase_runs={payload['phase_completed_runs']}/{payload['phase_total_runs']} "
            f"phase_cells={payload['completed_cells_in_phase']}/{payload['total_cells_in_phase']} "
            f"elapsed={payload['elapsed_human']} "
            f"eta={payload['eta_human']} "
            f"last={last.get('package_slug', 'n/a')}/"
            f"{last.get('experiment_slug', 'n/a')}/"
            f"{last.get('scenario_id', 'n/a')} "
            f"seed={last.get('seed', 'n/a')}"
        )

    def _append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.progress_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.progress_log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} {message}\n")

    def _log_progress(self, *, force: bool = False) -> None:
        now = time.monotonic()
        if not force and (now - self._last_progress_log) < PROGRESS_LOG_INTERVAL_SECONDS:
            return
        line = self._render_progress_line()
        logger.info(line)
        self._append_log(line)
        self._last_progress_log = now


@dataclass(frozen=True)
class ExperimentDefinition:
    """Single experiment family within the narrative campaign."""

    slug: str
    package_slug: str
    title: str
    description: str
    steps: int
    seeds: tuple[int, ...]
    base_params: dict[str, Any]
    sweep_params: dict[str, tuple[Any, ...]] = field(default_factory=dict)
    scenario_prefix: str = ""
    narrative_question: str = ""


@dataclass(frozen=True)
class StoryCaseDefinition:
    """Narrative case used to build blog-ready story scenes."""

    slug: str
    package_slug: str
    title: str
    narrative_role: str
    question_prompt: str
    observation_hook: str
    params: dict[str, Any]
    steps: int
    seeds: tuple[int, ...]


PACKAGE_DEFINITIONS: dict[str, PackageDefinition] = {
    PACKAGE_A: PackageDefinition(
        slug=PACKAGE_A,
        title="Package A: Everyday Friction",
        chapter_heading="Why do everyday frictions make systems feel different?",
        narrative_focus=(
            "Show that the difference is not a single inconvenience but a "
            "different time-allocation architecture."
        ),
        question_prompt=(
            "Why do small frictions like store closures or self-service errands "
            "feel like signals of a deeper system difference?"
        ),
    ),
    PACKAGE_B: PackageDefinition(
        slug=PACKAGE_B,
        title="Package B: Convenience Transfer",
        chapter_heading="Does convenience erase labour, or relocate it?",
        narrative_focus=(
            "Track how delegated work reappears as provider burden, labour "
            "hours, and unequal time buffers."
        ),
        question_prompt=(
            "If convenience saves time for me, who spends that time inside the "
            "system instead?"
        ),
    ),
    PACKAGE_C: PackageDefinition(
        slug=PACKAGE_C,
        title="Package C: Cheap Service Trap",
        chapter_heading="How far can price alone push a society toward delegation?",
        narrative_focus=(
            "Use service-cost sweeps and preset decomposition to separate "
            "external price friction from other social drivers."
        ),
        question_prompt=(
            "Are cheap services enough to create convenience dependence, or are "
            "they only one driver among several?"
        ),
    ),
    PACKAGE_D: PackageDefinition(
        slug=PACKAGE_D,
        title="Package D: Norm Lock-in",
        chapter_heading="Why does the middle become unstable?",
        narrative_focus=(
            "Show how conformity turns moderate systems into unstable basins and "
            "why exits from high-delegation norms become harder over time."
        ),
        question_prompt=(
            "Can a mixed system stay mixed, or do local norms and stress push it "
            "toward one side?"
        ),
    ),
}

DEFAULT_WORKERS = min(8, os.cpu_count() or 1)
DEFAULT_MODEL_PARAMS = {
    key: value
    for key, value in get_preset("default").items()
    if key not in {"label", "description", "empirical_basis"}
}

FULL_SCALE = ScaleConfig(
    name="full",
    horizon_steps=(60, 120, 200, 300),
    horizon_seeds=12,
    atlas_delegation_values=tuple(np.round(np.linspace(0.10, 0.90, 9), 2)),
    atlas_task_load_values=(1.5, 2.0, 2.5, 3.0, 3.5),
    atlas_cost_values=tuple(np.round(np.linspace(0.10, 0.90, 9), 2)),
    atlas_conformity_values=(0.0, 0.2, 0.4, 0.6, 0.8),
    atlas_task_steps=150,
    atlas_cost_steps=120,
    atlas_conformity_steps=150,
    atlas_seeds=8,
    decomposition_steps=200,
    decomposition_seeds=10,
    threshold_steps=250,
    threshold_seeds=20,
    mixed_steps=250,
    mixed_seeds=20,
    mixed_conformity_values=(0.2, 0.4, 0.6),
    mixed_delegation_values=(0.45, 0.50, 0.55),
    story_steps=300,
    story_seeds=10,
)
SMOKE_SCALE = ScaleConfig(
    name="smoke",
    horizon_steps=(30, 60),
    horizon_seeds=2,
    atlas_delegation_values=(0.2, 0.5, 0.8),
    atlas_task_load_values=(2.0, 3.0),
    atlas_cost_values=(0.2, 0.5, 0.8),
    atlas_conformity_values=(0.1, 0.5, 0.8),
    atlas_task_steps=50,
    atlas_cost_steps=50,
    atlas_conformity_steps=50,
    atlas_seeds=2,
    decomposition_steps=80,
    decomposition_seeds=3,
    threshold_steps=90,
    threshold_seeds=3,
    mixed_steps=90,
    mixed_seeds=3,
    mixed_conformity_values=(0.2, 0.6),
    mixed_delegation_values=(0.45, 0.55),
    story_steps=80,
    story_seeds=3,
)
RESEARCH_FOCUS_SCALE = ScaleConfig(
    name="research_focus",
    horizon_steps=(120, 200, 300),
    horizon_seeds=12,
    atlas_delegation_values=tuple(np.round(np.linspace(0.10, 0.90, 9), 2)),
    atlas_task_load_values=tuple(np.round(np.arange(2.0, 5.01, 0.25), 2)),
    atlas_cost_values=tuple(np.round(np.arange(0.05, 1.01, 0.05), 2)),
    atlas_conformity_values=(0.0, 0.2, 0.4, 0.6, 0.8),
    atlas_task_steps=200,
    atlas_cost_steps=200,
    atlas_conformity_steps=150,
    atlas_seeds=6,
    decomposition_steps=200,
    decomposition_seeds=10,
    threshold_steps=150,
    threshold_seeds=8,
    mixed_steps=150,
    mixed_seeds=8,
    mixed_conformity_values=(0.2, 0.4, 0.6),
    mixed_delegation_values=(0.45, 0.50, 0.55),
    story_steps=300,
    story_seeds=10,
)
RESEARCH_OVERNIGHT_SCALE = ScaleConfig(
    name="research_overnight",
    horizon_steps=(120, 200, 300, 450),
    horizon_seeds=14,
    atlas_delegation_values=tuple(np.round(np.arange(0.05, 0.96, 0.10), 2)),
    atlas_task_load_values=tuple(np.round(np.arange(1.5, 5.51, 0.25), 2)),
    atlas_cost_values=(0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.55, 0.70, 0.90, 1.20),
    atlas_conformity_values=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    atlas_task_steps=240,
    atlas_cost_steps=240,
    atlas_conformity_steps=180,
    atlas_seeds=6,
    decomposition_steps=240,
    decomposition_seeds=10,
    threshold_steps=240,
    threshold_seeds=8,
    mixed_steps=240,
    mixed_seeds=8,
    mixed_conformity_values=(0.10, 0.30, 0.50, 0.70, 0.90),
    mixed_delegation_values=(0.35, 0.45, 0.50, 0.55, 0.65),
    story_steps=400,
    story_seeds=6,
)
RESEARCH_15K_SCALE = ScaleConfig(
    name="research_15k",
    horizon_steps=(120, 200, 300, 450),
    horizon_seeds=20,
    atlas_delegation_values=tuple(np.round(np.arange(0.05, 0.96, 0.10), 2)),
    atlas_task_load_values=tuple(np.round(np.arange(1.5, 5.51, 0.25), 2)),
    atlas_cost_values=(0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.55, 0.70, 0.90, 1.20),
    atlas_conformity_values=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    atlas_task_steps=240,
    atlas_cost_steps=240,
    atlas_conformity_steps=180,
    atlas_seeds=12,
    decomposition_steps=240,
    decomposition_seeds=14,
    threshold_steps=240,
    threshold_seeds=16,
    mixed_steps=240,
    mixed_seeds=14,
    mixed_conformity_values=(0.10, 0.30, 0.50, 0.70, 0.90),
    mixed_delegation_values=(0.35, 0.45, 0.50, 0.55, 0.65),
    story_steps=400,
    story_seeds=8,
)
SCALES = {
    "full": FULL_SCALE,
    "smoke": SMOKE_SCALE,
    "research_focus": RESEARCH_FOCUS_SCALE,
    "research_overnight": RESEARCH_OVERNIGHT_SCALE,
    "research_15k": RESEARCH_15K_SCALE,
}

CLAIM_SAFETY = {
    "can_say_confidently": [
        "The current ABM can identify parameter regions where higher delegation is associated with higher total labour hours in abstract Type A / Type B systems.",
        "The current ABM can compare how stress, labour, and inequality proxies evolve under different levels of task pressure, price friction, and conformity.",
        "The current ABM can test whether moderate initial delegation states remain stable under the model's conformity and stress feedback rules.",
    ],
    "can_say_with_caveat": [
        "The model can show that lower external service prices push behaviour toward more delegation, but only as an exogenous price-friction experiment.",
        "The model can approximate norm lock-in and speed expectations through delegation convergence proxies, not through a direct measure of delay tolerance.",
        "The model can visualise how convenience shifts time burdens toward providers, but the exact labour market structure of real societies is outside scope.",
    ],
    "cannot_claim_from_current_model": [
        "The model cannot identify the full real-world causal loop between cheap services and service dependence because prices are not endogenous.",
        "The model cannot measure real populations, named countries, or concrete policy outcomes.",
        "The model cannot directly test skill decay, demographic inequality, or explicit tolerance-for-delay dynamics because those mechanisms are absent.",
    ],
}


def _round(value: float, digits: int = 4) -> float:
    """Return a JSON-safe rounded float."""
    return round(float(value), digits)


def _json_default(value: Any) -> Any:
    """Convert numpy/path objects to JSON-safe builtins."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Object of type {type(value)!r} is not JSON serialisable")


def _save_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    """Write JSON payload with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True, default=_json_default)
    temp_path.replace(path)


def _save_markdown(path: Path, content: str) -> None:
    """Write markdown text to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _save_dataframe(path: Path, frame: pd.DataFrame) -> None:
    """Write a CSV atomically so checkpoint files stay readable mid-run."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    frame.to_csv(temp_path, index=False)
    temp_path.replace(path)


MODEL_ENGINES: dict[str, type[ConvenienceParadoxModel]] = {
    "stable": ConvenienceParadoxModel,
    "research_v2": ConvenienceParadoxResearchModel,
}


def _model_class_for_engine(engine: str) -> type[ConvenienceParadoxModel]:
    """Resolve the runtime model class for a campaign engine tag."""
    try:
        return MODEL_ENGINES[engine]
    except KeyError as exc:
        raise ValueError(f"Unsupported campaign engine: {engine}") from exc


def _utc_now_iso() -> str:
    """Return a UTC ISO timestamp suitable for manifests."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _campaign_stamp() -> str:
    """Return a compact local timestamp for filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _format_duration(seconds: float | None) -> str:
    """Format a duration for progress logs and status files."""
    if seconds is None:
        return "n/a"
    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _task_weight(task: dict[str, Any]) -> int:
    """Approximate simulation cost for progress and ETA calculations."""
    num_agents = int(task.get("params", {}).get("num_agents", task.get("num_agents", 100)))
    steps = int(task.get("steps", 0))
    return max(1, num_agents * steps)


def _task_cell_id(task: dict[str, Any]) -> str:
    """Return the phase-level cell identifier for a task."""
    return str(task.get("scenario_id", "unknown"))


def _task_progress_view(task: dict[str, Any]) -> dict[str, Any]:
    """Extract the small task summary used in progress payloads."""
    return {
        "package_slug": task.get("package_slug"),
        "experiment_slug": task.get("experiment_slug"),
        "scenario_id": task.get("scenario_id"),
        "scenario_label": task.get("scenario_label"),
        "seed": int(task.get("seed", -1)),
        "steps": int(task.get("steps", 0)),
    }


def _git_metadata() -> dict[str, str | None]:
    """Collect branch/commit metadata for reproducibility manifests."""
    metadata: dict[str, str | None] = {"branch": None, "commit": None}
    try:
        metadata["branch"] = subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=PROJECT_ROOT,
            text=True,
        ).strip() or None
    except (OSError, subprocess.SubprocessError):
        metadata["branch"] = None
    try:
        metadata["commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
        ).strip() or None
    except (OSError, subprocess.SubprocessError):
        metadata["commit"] = None
    return metadata


def _serialisable_params(params: dict[str, Any]) -> dict[str, Any]:
    """Remove non-runtime preset metadata from model parameter dictionaries."""
    return {
        key: value
        for key, value in params.items()
        if key not in {"label", "description", "empirical_basis"}
    }


def _build_param_grid(base_params: dict[str, Any], sweep_params: dict[str, Sequence[Any]]) -> list[dict[str, Any]]:
    """Expand a parameter grid into a list of fully materialised model configs."""
    if not sweep_params:
        return [dict(base_params)]

    keys = list(sweep_params.keys())
    combos: list[dict[str, Any]] = []
    for values in product(*(sweep_params[key] for key in keys)):
        params = dict(base_params)
        params.update(dict(zip(keys, values, strict=True)))
        combos.append(params)
    return combos


def _tail_window(max_step: int) -> int:
    """Tail window for equilibrium summaries."""
    return max(10, int(max_step * 0.10))


def _gini_from_series(values: Sequence[float]) -> float:
    """Compute a Gini coefficient for a numeric sequence."""
    if not values:
        return 0.0
    arr = np.array(values, dtype=float)
    if np.allclose(arr.sum(), 0.0):
        return 0.0
    if np.min(arr) < 0:
        arr = arr - np.min(arr)
    arr = np.sort(arr)
    n = len(arr)
    cumulative = np.cumsum(arr)
    denominator = cumulative[-1]
    if denominator <= 0:
        return 0.0
    numerator = np.sum((2 * np.arange(1, n + 1) - n - 1) * arr)
    return float(numerator / (n * denominator))


def _normalise_model_dataframe(model_df: pd.DataFrame) -> pd.DataFrame:
    """Return a model-level dataframe with an explicit Step column."""
    frame = model_df.reset_index()
    first_col = frame.columns[0]
    return frame.rename(columns={first_col: "Step"})


def _normalise_agent_dataframe(agent_df: pd.DataFrame) -> pd.DataFrame:
    """Return an agent-level dataframe with Step and AgentID columns."""
    frame = agent_df.reset_index()
    columns = {col: str(col) for col in frame.columns}
    frame = frame.rename(columns=columns)
    if "AgentId" in frame.columns:
        frame = frame.rename(columns={"AgentId": "AgentID"})
    return frame


def _summarisable_model_metrics(model_frame: pd.DataFrame) -> list[str]:
    """Return all model-level metrics present in the run dataframe.

    The stable dashboard model and the research engine expose different model
    reporters. The campaign summaries therefore need to adapt to whichever
    engine produced the run rather than relying on a fixed metric whitelist.
    """
    return [column for column in model_frame.columns if column != "Step"]


def _summarise_single_run(
    *,
    package_slug: str,
    experiment_slug: str,
    experiment_title: str,
    scenario_id: str,
    scenario_label: str,
    narrative_question: str,
    params: dict[str, Any],
    steps: int,
    seed: int,
    engine: str,
    model_df: pd.DataFrame,
    agent_df: pd.DataFrame,
) -> dict[str, Any]:
    """Summarise one simulation run into a compact per-seed row."""
    model_frame = _normalise_model_dataframe(model_df)
    agent_frame = _normalise_agent_dataframe(agent_df)
    max_step = int(model_frame["Step"].max())
    tail_steps = _tail_window(max_step)
    tail_df = model_frame[model_frame["Step"] >= max(1, max_step - tail_steps + 1)]
    final_step = int(agent_frame["Step"].max())
    final_agents = agent_frame[agent_frame["Step"] == final_step]

    row: dict[str, Any] = {
        "package_slug": package_slug,
        "package_title": PACKAGE_DEFINITIONS[package_slug].title,
        "experiment_slug": experiment_slug,
        "experiment_title": experiment_title,
        "scenario_id": scenario_id,
        "scenario_label": scenario_label,
        "narrative_question": narrative_question,
        "steps": steps,
        "seed": seed,
        "engine": engine,
    }
    row.update(params)

    for metric in _summarisable_model_metrics(model_frame):
        row[f"tail_{metric}"] = _round(tail_df[metric].mean())
        row[f"peak_{metric}"] = _round(model_frame[metric].max())
        row[f"final_{metric}"] = _round(model_frame[metric].iloc[-1])

    row["tail_window_steps"] = tail_steps
    row["final_available_time_mean"] = _round(final_agents["available_time"].mean())
    row["final_available_time_p10"] = _round(final_agents["available_time"].quantile(0.10))
    row["final_available_time_p90"] = _round(final_agents["available_time"].quantile(0.90))
    row["final_time_spent_providing_mean"] = _round(final_agents["time_spent_providing"].mean())
    row["final_time_spent_providing_p90"] = _round(final_agents["time_spent_providing"].quantile(0.90))
    row["final_tasks_delegated_mean"] = _round(final_agents["tasks_delegated"].mean())
    row["final_income_mean_agent"] = _round(final_agents["income"].mean())
    row["final_income_gini_agent"] = _round(_gini_from_series(final_agents["income"].tolist()))
    row["final_provider_burden_share"] = _round(
        final_agents["time_spent_providing"].sum()
        / max(final_agents["tasks_delegated"].sum(), 1.0)
    )
    return row


def _run_single_summary(task: dict[str, Any]) -> dict[str, Any]:
    """Worker-safe top-level function for one simulation summary."""
    params = dict(task["params"])
    params["seed"] = int(task["seed"])
    model_cls = _model_class_for_engine(str(task["engine"]))
    model = model_cls(**params)
    for _ in range(int(task["steps"])):
        model.step()
    return _summarise_single_run(
        package_slug=task["package_slug"],
        experiment_slug=task["experiment_slug"],
        experiment_title=task["experiment_title"],
        scenario_id=task["scenario_id"],
        scenario_label=task["scenario_label"],
        narrative_question=task["narrative_question"],
        params=params,
        steps=int(task["steps"]),
        seed=int(task["seed"]),
        engine=str(task["engine"]),
        model_df=model.get_model_dataframe(),
        agent_df=model.get_agent_dataframe(),
    )


def _run_story_case_full(
    case: StoryCaseDefinition,
    seed: int,
    engine: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run one story case again and return full timeseries for the selected seed."""
    params = dict(case.params)
    params["seed"] = seed
    model_cls = _model_class_for_engine(engine)
    model = model_cls(**params)
    for _ in range(case.steps):
        model.step()
    return _normalise_model_dataframe(model.get_model_dataframe()), _normalise_agent_dataframe(
        model.get_agent_dataframe()
    )


def _aggregate_per_seed(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-seed summaries to per-scenario means/stds."""
    measure_cols = [
        column
        for column in df.columns
        if column.startswith(("tail_", "peak_", "final_"))
    ]
    group_cols = [column for column in df.columns if column not in measure_cols + ["seed"]]
    aggregated = df.groupby(group_cols, dropna=False).agg(
        {column: ["mean", "std", "min", "max"] for column in measure_cols}
    )
    aggregated.columns = ["_".join(part for part in col if part) for col in aggregated.columns]
    aggregated = aggregated.reset_index()
    return aggregated


def _run_tasks(
    tasks: list[dict[str, Any]],
    max_workers: int,
    *,
    tracker: _CampaignProgressTracker | None = None,
    phase_name: str,
    partial_path: Path | None = None,
) -> pd.DataFrame:
    """Execute simulation tasks in serial or with spawn-safe multiprocessing."""
    if not tasks:
        return pd.DataFrame()
    logger.info("Running %d %s tasks with %d worker(s).", len(tasks), phase_name, max_workers)
    if tracker is not None:
        tracker.start_phase(phase_name, tasks)

    def checkpoint_rows(rows: list[dict[str, Any]]) -> None:
        if partial_path is None or not rows:
            return
        _save_dataframe(partial_path, pd.DataFrame(rows))

    checkpoint_timer = time.monotonic()
    if max_workers <= 1:
        rows: list[dict[str, Any]] = []
        for task in tasks:
            rows.append(_run_single_summary(task))
            if tracker is not None:
                tracker.record_completion(task)
            now = time.monotonic()
            if (
                len(rows) % CHECKPOINT_WRITE_EVERY_RUNS == 0
                or (now - checkpoint_timer) >= CHECKPOINT_WRITE_INTERVAL_SECONDS
            ):
                checkpoint_rows(rows)
                checkpoint_timer = now
        checkpoint_rows(rows)
        if tracker is not None:
            tracker._log_progress(force=True)
        return pd.DataFrame(rows)

    rows: list[dict[str, Any]] = []
    mp_context = get_context("spawn")
    try:
        with ProcessPoolExecutor(max_workers=max_workers, mp_context=mp_context) as executor:
            future_to_task = {executor.submit(_run_single_summary, task): task for task in tasks}
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                rows.append(future.result())
                if tracker is not None:
                    tracker.record_completion(task)
                now = time.monotonic()
                if (
                    len(rows) % CHECKPOINT_WRITE_EVERY_RUNS == 0
                    or (now - checkpoint_timer) >= CHECKPOINT_WRITE_INTERVAL_SECONDS
                ):
                    checkpoint_rows(rows)
                    checkpoint_timer = now
    except PermissionError as exc:
        logger.warning(
            "Multiprocessing unavailable in the current environment (%s). "
            "Falling back to serial execution.",
            exc,
        )
        rows = []
        for task in tasks:
            rows.append(_run_single_summary(task))
            if tracker is not None:
                tracker.record_completion(task)
            now = time.monotonic()
            if (
                len(rows) % CHECKPOINT_WRITE_EVERY_RUNS == 0
                or (now - checkpoint_timer) >= CHECKPOINT_WRITE_INTERVAL_SECONDS
            ):
                checkpoint_rows(rows)
                checkpoint_timer = now
    checkpoint_rows(rows)
    if tracker is not None:
        tracker._log_progress(force=True)
    return pd.DataFrame(rows)


def _format_value(value: Any) -> str:
    """Format scalar values for labels and manifests."""
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _scenario_id(prefix: str, params: dict[str, Any], extra: str = "") -> str:
    """Build a stable scenario identifier from varying parameters."""
    pieces = [prefix] if prefix else []
    if extra:
        pieces.append(extra)
    for key in sorted(params):
        pieces.append(f"{key[:4]}{_format_value(params[key]).replace('.', 'p')}")
    return "_".join(pieces)


def _scenario_label(prefix: str, params: dict[str, Any], extra: str = "") -> str:
    """Build a readable scenario label from varying parameters."""
    pieces = [prefix] if prefix else []
    if extra:
        pieces.append(extra)
    pieces.extend(f"{key}={_format_value(value)}" for key, value in sorted(params.items()))
    return " | ".join(pieces)


def _build_experiment_tasks(experiment: ExperimentDefinition, engine: str) -> list[dict[str, Any]]:
    """Expand an experiment definition to individual seed tasks."""
    tasks: list[dict[str, Any]] = []
    param_grid = _build_param_grid(experiment.base_params, experiment.sweep_params)
    varying_keys = list(experiment.sweep_params.keys())
    for params in param_grid:
        scenario_params = {key: params[key] for key in varying_keys}
        scenario_id = _scenario_id(experiment.scenario_prefix or experiment.slug, scenario_params)
        scenario_label = _scenario_label(experiment.scenario_prefix or experiment.title, scenario_params)
        for seed in experiment.seeds:
            tasks.append(
                {
                    "package_slug": experiment.package_slug,
                    "experiment_slug": experiment.slug,
                    "experiment_title": experiment.title,
                    "scenario_id": scenario_id,
                    "scenario_label": scenario_label,
                    "narrative_question": experiment.narrative_question,
                    "steps": experiment.steps,
                    "seed": seed,
                    "engine": engine,
                    "params": params,
                }
            )
    return tasks


def build_campaign_plan(
    *,
    scale: ScaleConfig,
    packages: Sequence[str] | None = None,
    engine: str = "stable",
) -> tuple[list[ExperimentDefinition], list[StoryCaseDefinition]]:
    """Build the full experiment plan for the requested narrative packages."""
    selected_packages = set(packages or PACKAGE_DEFINITIONS.keys())

    type_a = _serialisable_params(TYPE_A_PRESET)
    type_b = _serialisable_params(TYPE_B_PRESET)
    default_params = dict(DEFAULT_MODEL_PARAMS)

    experiments: list[ExperimentDefinition] = []
    story_cases: list[StoryCaseDefinition] = []

    if PACKAGE_A in selected_packages:
        for preset_name, preset_params in [("type_a", type_a), ("type_b", type_b)]:
            experiments.append(
                ExperimentDefinition(
                    slug="preset_horizon_scan",
                    package_slug=PACKAGE_A,
                    title="Preset Horizon Scan",
                    description="Type A / Type B horizon comparison across short and long runs.",
                    steps=max(scale.horizon_steps),
                    seeds=tuple(range(scale.horizon_seeds)),
                    base_params=preset_params,
                    sweep_params={"steps_marker": scale.horizon_steps},
                    scenario_prefix=preset_name,
                    narrative_question=PACKAGE_DEFINITIONS[PACKAGE_A].question_prompt,
                )
            )

        story_cases.extend(
            [
                StoryCaseDefinition(
                    slug="autonomy_baseline",
                    package_slug=PACKAGE_A,
                    title="Autonomy Baseline",
                    narrative_role="A slower, self-service rhythm with a wider personal time boundary.",
                    question_prompt=PACKAGE_DEFINITIONS[PACKAGE_A].question_prompt,
                    observation_hook="The small friction is not a bug; it is a visible trace of a different time-allocation system.",
                    params=type_a,
                    steps=scale.story_steps,
                    seeds=tuple(range(scale.story_seeds)),
                ),
                StoryCaseDefinition(
                    slug="convenience_baseline",
                    package_slug=PACKAGE_A,
                    title="Convenience Baseline",
                    narrative_role="A fast, service-heavy rhythm where everyday life is reorganised around delegation.",
                    question_prompt=PACKAGE_DEFINITIONS[PACKAGE_A].question_prompt,
                    observation_hook="The easy option is built into the environment, not just chosen by one individual.",
                    params=type_b,
                    steps=scale.story_steps,
                    seeds=tuple(range(scale.story_seeds)),
                ),
            ]
        )

    if PACKAGE_B in selected_packages:
        experiments.append(
            ExperimentDefinition(
                slug="delegation_task_load_atlas",
                package_slug=PACKAGE_B,
                title="Delegation x Task-Load Atlas",
                description="Primary convenience-transfer sweep over delegation and task pressure.",
                steps=scale.atlas_task_steps,
                seeds=tuple(range(scale.atlas_seeds)),
                base_params=default_params,
                sweep_params={
                    "delegation_preference_mean": scale.atlas_delegation_values,
                    "tasks_per_step_mean": scale.atlas_task_load_values,
                },
                scenario_prefix="taskload",
                narrative_question=PACKAGE_DEFINITIONS[PACKAGE_B].question_prompt,
            )
        )
        story_cases.extend(
            [
                StoryCaseDefinition(
                    slug="threshold_pressure",
                    package_slug=PACKAGE_B,
                    title="Threshold Pressure",
                    narrative_role="A near-threshold case where convenience starts to look cheap but the system is close to overload.",
                    question_prompt=PACKAGE_DEFINITIONS[PACKAGE_B].question_prompt,
                    observation_hook="This is the point where saved effort begins to reappear as someone else's burden.",
                    params={
                        **default_params,
                        "delegation_preference_mean": 0.55,
                        "tasks_per_step_mean": 3.0,
                        "social_conformity_pressure": 0.40,
                    },
                    steps=scale.story_steps,
                    seeds=tuple(range(scale.story_seeds)),
                ),
                StoryCaseDefinition(
                    slug="overloaded_convenience",
                    package_slug=PACKAGE_B,
                    title="Overloaded Convenience",
                    narrative_role="A high-delegation, high-load regime where convenience survives only through escalating provider effort.",
                    question_prompt=PACKAGE_DEFINITIONS[PACKAGE_B].question_prompt,
                    observation_hook="The convenience never vanished; it was reassembled as invisible provider work.",
                    params={
                        **type_b,
                        "tasks_per_step_mean": max(scale.atlas_task_load_values),
                        "social_conformity_pressure": 0.80,
                    },
                    steps=scale.story_steps,
                    seeds=tuple(range(scale.story_seeds)),
                ),
            ]
        )

    if PACKAGE_C in selected_packages:
        if engine == "research_v2":
            context_definitions: list[tuple[str, dict[str, Any]]] = [
                ("default_context", default_params),
                ("type_a_context", type_a),
                ("type_b_context", type_b),
                (
                    "overloaded_context",
                    {
                        **type_b,
                        "tasks_per_step_mean": 4.0,
                        "social_conformity_pressure": 0.65,
                    },
                ),
            ]
            delegation_slices: list[tuple[str, float]] = [
                ("mid_delegation", 0.55),
                ("high_delegation", 0.72),
            ]
            if scale.name in {"research_overnight", "research_15k"}:
                context_definitions = [
                    ("default_context", default_params),
                    ("type_a_context", type_a),
                    ("type_b_context", type_b),
                    (
                        "edge_context",
                        {
                            **type_b,
                            "tasks_per_step_mean": 3.0,
                            "social_conformity_pressure": 0.65,
                        },
                    ),
                    (
                        "overloaded_context",
                        {
                            **type_b,
                            "tasks_per_step_mean": 4.5,
                            "social_conformity_pressure": 0.75,
                        },
                    ),
                ]
                delegation_slices = [
                    ("low_delegation", 0.35),
                    ("mid_delegation", 0.55),
                    ("high_delegation", 0.72),
                    ("extreme_delegation", 0.90),
                ]

            for prefix, base_params in context_definitions:
                experiments.append(
                    ExperimentDefinition(
                        slug="service_cost_context_scan",
                        package_slug=PACKAGE_C,
                        title="Service-Cost Context Scan",
                        description="Single-variable price-friction sweep inside a fixed context.",
                        steps=scale.atlas_cost_steps,
                        seeds=tuple(range(scale.horizon_seeds)),
                        base_params=base_params,
                        sweep_params={"service_cost_factor": scale.atlas_cost_values},
                        scenario_prefix=prefix,
                        narrative_question=PACKAGE_DEFINITIONS[PACKAGE_C].question_prompt,
                    )
                )

            for prefix, delegation_mean in delegation_slices:
                experiments.append(
                    ExperimentDefinition(
                        slug="service_cost_task_load_atlas",
                        package_slug=PACKAGE_C,
                        title="Service Cost x Task-Load Atlas",
                        description="Research-engine sweep over price friction and task pressure at fixed delegation.",
                        steps=scale.atlas_task_steps,
                        seeds=tuple(range(scale.atlas_seeds)),
                        base_params={
                            **default_params,
                            "delegation_preference_mean": delegation_mean,
                        },
                        sweep_params={
                            "service_cost_factor": scale.atlas_cost_values,
                            "tasks_per_step_mean": scale.atlas_task_load_values,
                        },
                        scenario_prefix=prefix,
                        narrative_question=PACKAGE_DEFINITIONS[PACKAGE_C].question_prompt,
                    )
                )
        else:
            experiments.append(
                ExperimentDefinition(
                    slug="delegation_service_cost_atlas",
                    package_slug=PACKAGE_C,
                    title="Delegation x Service-Cost Atlas",
                    description="Price-friction sweep for the cheap-service question.",
                    steps=scale.atlas_cost_steps,
                    seeds=tuple(range(scale.atlas_seeds)),
                    base_params=default_params,
                    sweep_params={
                        "delegation_preference_mean": scale.atlas_delegation_values,
                        "service_cost_factor": scale.atlas_cost_values,
                    },
                    scenario_prefix="servicecost",
                    narrative_question=PACKAGE_DEFINITIONS[PACKAGE_C].question_prompt,
                )
            )
        story_cases.append(
            StoryCaseDefinition(
                slug="cheap_low_conformity",
                package_slug=PACKAGE_C,
                title="Cheap but Low-Conformity",
                narrative_role="A case where price friction is low but norm pressure remains weak.",
                question_prompt=PACKAGE_DEFINITIONS[PACKAGE_C].question_prompt,
                observation_hook="Cheap services matter, but they do not explain the whole system by themselves.",
                params={
                    **default_params,
                    "delegation_preference_mean": 0.55,
                    "service_cost_factor": 0.20,
                    "social_conformity_pressure": 0.15,
                },
                steps=scale.story_steps,
                seeds=tuple(range(scale.story_seeds)),
            )
        )

    if PACKAGE_D in selected_packages:
        experiments.extend(
            [
                ExperimentDefinition(
                    slug="delegation_conformity_atlas",
                    package_slug=PACKAGE_D,
                    title="Delegation x Conformity Atlas",
                    description="Norm-lock-in sweep across delegation and conformity pressure.",
                    steps=scale.atlas_conformity_steps,
                    seeds=tuple(range(scale.atlas_seeds)),
                    base_params=default_params,
                    sweep_params={
                        "delegation_preference_mean": scale.atlas_delegation_values,
                        "social_conformity_pressure": scale.atlas_conformity_values,
                    },
                    scenario_prefix="conformity",
                    narrative_question=PACKAGE_DEFINITIONS[PACKAGE_D].question_prompt,
                ),
                ExperimentDefinition(
                    slug="mixed_stability_deep_dive",
                    package_slug=PACKAGE_D,
                    title="Mixed-System Stability Deep Dive",
                    description="Moderate delegation initial states under different conformity levels.",
                    steps=scale.mixed_steps,
                    seeds=tuple(range(scale.mixed_seeds)),
                    base_params=default_params,
                    sweep_params={
                        "delegation_preference_mean": scale.mixed_delegation_values,
                        "social_conformity_pressure": scale.mixed_conformity_values,
                    },
                    scenario_prefix="mixed",
                    narrative_question=PACKAGE_DEFINITIONS[PACKAGE_D].question_prompt,
                ),
            ]
        )
        story_cases.append(
            StoryCaseDefinition(
                slug="mixed_unstable",
                package_slug=PACKAGE_D,
                title="Mixed and Unstable",
                narrative_role="A middle zone that looks balanced at the start but can split into different norm basins.",
                question_prompt=PACKAGE_DEFINITIONS[PACKAGE_D].question_prompt,
                observation_hook="The most interesting middle state may be unstable rather than moderate in a durable way.",
                params={
                    **default_params,
                    "delegation_preference_mean": 0.50,
                    "social_conformity_pressure": 0.40,
                },
                steps=scale.story_steps,
                seeds=tuple(range(scale.story_seeds)),
            )
        )

    if PACKAGE_C in selected_packages or PACKAGE_B in selected_packages or PACKAGE_D in selected_packages:
        experiments.append(
            ExperimentDefinition(
                slug="preset_decomposition_v2" if engine == "research_v2" else "preset_decomposition",
                package_slug=PACKAGE_C if PACKAGE_C in selected_packages else PACKAGE_B,
                title="Preset Decomposition V2" if engine == "research_v2" else "Preset Decomposition",
                description=(
                    "Swap one parameter family at a time across Type A / Type B baselines."
                    if engine != "research_v2"
                    else "Swap one mechanism at a time across Type A / Type B baselines."
                ),
                steps=scale.decomposition_steps,
                seeds=tuple(range(scale.decomposition_seeds)),
                base_params=default_params,
                scenario_prefix="decompose",
                narrative_question=(
                    "Which family of parameters matters most: economic friction, "
                    "task pressure, or norm diffusion?"
                ),
            )
        )

    return experiments, story_cases


def _expand_horizon_experiments(
    experiments: list[ExperimentDefinition],
    scale: ScaleConfig,
) -> list[ExperimentDefinition]:
    """Replace horizon marker experiments with one experiment per horizon."""
    expanded: list[ExperimentDefinition] = []
    for experiment in experiments:
        if experiment.slug != "preset_horizon_scan":
            expanded.append(experiment)
            continue
        for horizon in scale.horizon_steps:
            base_params = dict(experiment.base_params)
            expanded.append(
                ExperimentDefinition(
                    slug=f"{experiment.slug}_{horizon}",
                    package_slug=experiment.package_slug,
                    title=f"{experiment.title} ({horizon} steps)",
                    description=experiment.description,
                    steps=horizon,
                    seeds=experiment.seeds,
                    base_params=base_params,
                    sweep_params={},
                    scenario_prefix=f"{experiment.scenario_prefix}_{horizon}",
                    narrative_question=experiment.narrative_question,
                )
            )
    return expanded


def _build_decomposition_tasks(
    *,
    scale: ScaleConfig,
    experiment_slug: str,
    package_slug: str,
    engine: str,
) -> list[dict[str, Any]]:
    """Build preset-decomposition summary tasks."""
    type_a = _serialisable_params(TYPE_A_PRESET)
    type_b = _serialisable_params(TYPE_B_PRESET)
    if engine == "research_v2":
        family_map = {
            "service_cost": ["service_cost_factor"],
            "task_load_mean": ["tasks_per_step_mean"],
            "task_load_std": ["tasks_per_step_std"],
            "conformity": ["social_conformity_pressure"],
            "adaptation": ["adaptation_rate"],
        }
    else:
        family_map = {
            "economic_friction": ["service_cost_factor"],
            "norm_lock_in": ["social_conformity_pressure", "adaptation_rate"],
            "task_pressure": ["tasks_per_step_mean", "tasks_per_step_std"],
        }
    scenarios: list[tuple[str, dict[str, Any]]] = [
        ("type_a_baseline", type_a),
        ("type_b_baseline", type_b),
    ]
    for anchor_name, anchor in [("type_a", type_a), ("type_b", type_b)]:
        donor = type_b if anchor_name == "type_a" else type_a
        for family, keys in family_map.items():
            hybrid = dict(anchor)
            for key in keys:
                hybrid[key] = donor[key]
            scenarios.append((f"{anchor_name}_with_{family}", hybrid))

    tasks: list[dict[str, Any]] = []
    for scenario_name, params in scenarios:
        for seed in range(scale.decomposition_seeds):
            tasks.append(
                {
                    "package_slug": package_slug,
                    "experiment_slug": experiment_slug,
                    "experiment_title": "Preset Decomposition",
                    "scenario_id": scenario_name,
                    "scenario_label": scenario_name.replace("_", " ").title(),
                    "narrative_question": (
                        "Which mechanism family matters most for the observed "
                        "difference: cost, norms, or task pressure?"
                    ),
                    "steps": scale.decomposition_steps,
                    "seed": seed,
                    "engine": engine,
                    "params": params,
                }
            )
    return tasks


def _threshold_band_from_atlas(atlas_agg: pd.DataFrame) -> list[float]:
    """Estimate a delegation band for threshold refinement from task-load atlas data."""
    centers: list[float] = []
    if atlas_agg.empty:
        return [0.40, 0.45, 0.50, 0.55, 0.60]

    for _, group in atlas_agg.groupby("tasks_per_step_mean", dropna=False):
        ordered = group.sort_values("delegation_preference_mean")
        if len(ordered) < 2:
            continue
        delegation_values = ordered["delegation_preference_mean"].to_numpy(dtype=float)
        stress_values = ordered["tail_avg_stress_mean"].to_numpy(dtype=float)
        diffs = np.abs(np.diff(stress_values))
        if len(diffs) == 0:
            continue
        idx = int(np.argmax(diffs))
        centers.append(float((delegation_values[idx] + delegation_values[idx + 1]) / 2.0))

    if not centers:
        return [0.40, 0.45, 0.50, 0.55, 0.60]

    center = float(np.median(centers))
    band = sorted(
        {
            _round(np.clip(center + offset, 0.05, 0.95), 2)
            for offset in (-0.10, -0.05, 0.0, 0.05, 0.10)
        }
    )
    return band


def _build_threshold_tasks(
    scale: ScaleConfig,
    delegation_band: Sequence[float],
    engine: str,
) -> list[dict[str, Any]]:
    """Build threshold-refinement tasks based on an inferred delegation band."""
    tasks: list[dict[str, Any]] = []
    for task_load in scale.atlas_task_load_values:
        params = dict(DEFAULT_MODEL_PARAMS)
        params["tasks_per_step_mean"] = task_load
        for delegation in delegation_band:
            params_variant = dict(params)
            params_variant["delegation_preference_mean"] = delegation
            for seed in range(scale.threshold_seeds):
                tasks.append(
                    {
                        "package_slug": PACKAGE_B,
                        "experiment_slug": "threshold_refinement",
                        "experiment_title": "Threshold Refinement",
                        "scenario_id": f"threshold_task{str(task_load).replace('.', 'p')}_del{str(delegation).replace('.', 'p')}",
                        "scenario_label": (
                            f"Threshold refinement | tasks_per_step_mean={task_load:.2f} | "
                            f"delegation_preference_mean={delegation:.2f}"
                        ),
                        "narrative_question": PACKAGE_DEFINITIONS[PACKAGE_B].question_prompt,
                        "steps": scale.threshold_steps,
                        "seed": seed,
                        "engine": engine,
                        "params": params_variant,
                    }
                )
    return tasks


def _select_story_seed(group: pd.DataFrame) -> int:
    """Select the seed whose summary is closest to the group's median vector."""
    metrics = [
        "tail_avg_stress",
        "tail_total_labor_hours",
        "tail_social_efficiency",
        "tail_tasks_delegated_frac",
        "tail_gini_available_time",
    ]
    matrix = group[metrics].astype(float).copy()
    median_vector = matrix.median(axis=0)
    scale = matrix.std(axis=0).replace(0.0, 1.0)
    distances = ((matrix - median_vector) / scale).pow(2).sum(axis=1)
    return int(group.loc[distances.idxmin(), "seed"])


def _story_snapshot_steps(total_steps: int) -> tuple[int, ...]:
    """Return sparse checkpoint steps for story-case snapshots."""
    midpoint = max(1, total_steps // 2)
    return (0, midpoint, total_steps)


def _save_story_case_outputs(
    *,
    case: StoryCaseDefinition,
    selected_seed: int,
    package_dir: Path,
    engine: str,
) -> dict[str, str]:
    """Re-run a selected story case and persist full model/snapshot artefacts."""
    cases_dir = package_dir / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    model_df, agent_df = _run_story_case_full(case, selected_seed, engine)
    model_path = cases_dir / f"{case.slug}_model_timeseries.csv.gz"
    snapshot_path = cases_dir / f"{case.slug}_agent_snapshots.csv.gz"
    model_df.to_csv(model_path, index=False, compression="gzip")
    keep_steps = _story_snapshot_steps(case.steps)
    snapshots = agent_df[agent_df["Step"].isin(keep_steps)].copy()
    snapshots.to_csv(snapshot_path, index=False, compression="gzip")
    return {
        "model_timeseries": str(model_path),
        "agent_snapshots": str(snapshot_path),
    }


def _plot_matrix(
    pivot: pd.DataFrame,
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    colorbar_label: str,
    cmap: str,
    output_path: Path,
) -> None:
    """Draw a heatmap from a pivot table."""
    fig, ax = plt.subplots(figsize=(9, 6))
    im = ax.imshow(pivot.values, origin="lower", aspect="auto", cmap=cmap)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([_format_value(v) for v in pivot.columns], rotation=45, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([_format_value(v) for v in pivot.index])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(colorbar_label)
    plt.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    fig.savefig(output_path.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)


def _plot_horizon_comparison(package_dir: Path, summary: pd.DataFrame) -> list[dict[str, Any]]:
    """Generate short-run and long-run horizon comparison figures."""
    figures: list[dict[str, Any]] = []
    if summary.empty:
        return figures
    figures_dir = package_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    horizon_df = summary[summary["experiment_slug"] == "preset_horizon_scan"].copy()
    if horizon_df.empty:
        return figures

    horizon_df["preset_label"] = np.where(
        horizon_df["scenario_id"].str.startswith("type_a"),
        "Type A",
        "Type B",
    )
    horizon_df["horizon"] = horizon_df["steps"].astype(int)

    groups = [
        ("horizon_short", {min(horizon_df["horizon"]), sorted(horizon_df["horizon"].unique())[1] if len(horizon_df["horizon"].unique()) > 1 else min(horizon_df["horizon"])}, "Short-run horizon comparison"),
        ("horizon_long", set(sorted(horizon_df["horizon"].unique())[-2:]), "Long-run horizon comparison"),
    ]
    for slug, selected_horizons, title in groups:
        selected = horizon_df[horizon_df["horizon"].isin(selected_horizons)].copy()
        if selected.empty:
            continue
        fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharex=True)
        metrics = [
            ("tail_total_labor_hours_mean", "Tail Mean Labour Hours"),
            ("tail_avg_stress_mean", "Tail Mean Stress"),
            ("tail_gini_available_time_mean", "Tail Mean Time Gini"),
        ]
        for ax, (metric, label) in zip(axes, metrics, strict=True):
            for preset_label, color in [("Type A", "#2166AC"), ("Type B", "#D6604D")]:
                subset = selected[selected["preset_label"] == preset_label].sort_values("horizon")
                ax.plot(
                    subset["horizon"],
                    subset[metric],
                    marker="o",
                    linewidth=2.0,
                    label=preset_label,
                    color=color,
                )
            ax.set_title(label)
            ax.set_xlabel("Steps")
            ax.grid(True, alpha=0.3)
        axes[0].legend()
        fig.suptitle(title, fontsize=13, fontweight="bold")
        fig.tight_layout()
        output_path = figures_dir / f"{slug}.png"
        fig.savefig(output_path, dpi=180, bbox_inches="tight")
        fig.savefig(output_path.with_suffix(".svg"), bbox_inches="tight")
        plt.close(fig)
        figures.append(
            {
                "slug": slug,
                "path": str(output_path),
                "source_tables": ["research_summary.csv"],
                "technical_caption": (
                    "Tail-window comparison of Type A and Type B preset runs across "
                    f"{', '.join(str(h) for h in sorted(selected_horizons))} steps."
                ),
                "blog_caption": (
                    "The friction is not a one-off inconvenience; it is the visible "
                    "surface of a different time-allocation architecture."
                ),
                "so_what": "It separates short-run convenience from the longer-run structure beneath it.",
                "limitation": (
                    "These are abstract preset comparisons; they do not identify any "
                    "specific real population."
                ),
            }
        )
    return figures


def _plot_task_load_heatmap(package_dir: Path, summary: pd.DataFrame) -> dict[str, Any] | None:
    """Generate the delegation x task-load heatmap."""
    selected = summary[summary["experiment_slug"] == "delegation_task_load_atlas"].copy()
    if selected.empty:
        return None
    figures_dir = package_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    pivot = selected.pivot_table(
        index="tasks_per_step_mean",
        columns="delegation_preference_mean",
        values="tail_total_labor_hours_mean",
        aggfunc="mean",
    )
    output_path = figures_dir / "task_load_heatmap.png"
    _plot_matrix(
        pivot,
        title="Convenience Transfer Atlas",
        xlabel="Delegation Preference Mean",
        ylabel="Tasks Per Step Mean",
        colorbar_label="Tail Mean Total Labour Hours",
        cmap="magma",
        output_path=output_path,
    )
    return {
        "slug": "task_load_heatmap",
        "path": str(output_path),
        "source_tables": ["research_summary.csv"],
        "technical_caption": (
            "Heatmap of tail-window total labour hours over delegation preference "
            "and task-load pressure."
        ),
        "blog_caption": (
            "When the day gets busier, convenience stops looking like time saved "
            "and starts looking like more hours somewhere else."
        ),
        "so_what": "It shows where convenience becomes a labour-transfer regime instead of a time-saving one.",
        "limitation": "Task burden is exogenous here; the model does not endogenise why a society becomes busier.",
    }


def _plot_service_cost_heatmap(package_dir: Path, summary: pd.DataFrame) -> dict[str, Any] | None:
    """Generate the delegation x service-cost heatmap."""
    selected = summary[summary["experiment_slug"] == "delegation_service_cost_atlas"].copy()
    figures_dir = package_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    if not selected.empty:
        pivot = selected.pivot_table(
            index="service_cost_factor",
            columns="delegation_preference_mean",
            values="tail_tasks_delegated_frac_mean",
            aggfunc="mean",
        )
        output_path = figures_dir / "service_cost_heatmap.png"
        _plot_matrix(
            pivot,
            title="Cheap Service Trap Atlas",
            xlabel="Delegation Preference Mean",
            ylabel="Service Cost Factor",
            colorbar_label="Tail Mean Delegated-Task Fraction",
            cmap="viridis",
            output_path=output_path,
        )
        return {
            "slug": "service_cost_heatmap",
            "path": str(output_path),
            "source_tables": ["research_summary.csv"],
            "technical_caption": (
                "Heatmap of realised delegated-task fractions over delegation "
                "preference and exogenous service cost."
            ),
            "blog_caption": (
                "Cheap services can push behaviour a long way, but they do not act alone."
            ),
            "so_what": "It quantifies how much of the convenience pattern can be explained by price friction alone.",
            "limitation": "Service prices are externally set in the current model; they do not respond to supply or demand.",
        }

    selected = summary[summary["experiment_slug"] == "service_cost_task_load_atlas"].copy()
    if selected.empty or "tail_backlog_tasks_mean" not in selected.columns:
        return None
    high_delegation = selected[selected["scenario_id"].str.startswith("high_delegation")].copy()
    if high_delegation.empty:
        high_delegation = selected.copy()
    pivot = high_delegation.pivot_table(
        index="tasks_per_step_mean",
        columns="service_cost_factor",
        values="tail_backlog_tasks_mean",
        aggfunc="mean",
    )
    output_path = figures_dir / "service_cost_taskload_backlog_heatmap.png"
    _plot_matrix(
        pivot,
        title="Research Backlog Atlas",
        xlabel="Service Cost Factor",
        ylabel="Tasks Per Step Mean",
        colorbar_label="Tail Mean Backlog Tasks",
        cmap="magma",
        output_path=output_path,
    )
    return {
        "slug": "service_cost_taskload_backlog_heatmap",
        "path": str(output_path),
        "source_tables": ["research_summary.csv"],
        "technical_caption": (
            "Heatmap of tail-window backlog tasks over service cost and task-load "
            "pressure in the research engine."
        ),
        "blog_caption": (
            "Cheap service stays comfortable only while the queue remains hidden."
        ),
        "so_what": "It shows where lower prices stop diffusing pressure and start creating visible carry-over overload.",
        "limitation": "This figure is specific to the research_v2 mechanism set and is not shown in the stable dashboard.",
    }


def _plot_conformity_heatmap(package_dir: Path, summary: pd.DataFrame) -> dict[str, Any] | None:
    """Generate the delegation x conformity heatmap."""
    selected = summary[summary["experiment_slug"] == "delegation_conformity_atlas"].copy()
    if selected.empty:
        return None
    figures_dir = package_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    pivot = selected.pivot_table(
        index="social_conformity_pressure",
        columns="delegation_preference_mean",
        values="tail_avg_delegation_rate_mean",
        aggfunc="mean",
    )
    output_path = figures_dir / "conformity_heatmap.png"
    _plot_matrix(
        pivot,
        title="Norm Lock-in Atlas",
        xlabel="Delegation Preference Mean",
        ylabel="Social Conformity Pressure",
        colorbar_label="Tail Mean Delegation Rate",
        cmap="plasma",
        output_path=output_path,
    )
    return {
        "slug": "conformity_heatmap",
        "path": str(output_path),
        "source_tables": ["research_summary.csv"],
        "technical_caption": (
            "Heatmap of tail-window delegation convergence over starting "
            "delegation preference and conformity pressure."
        ),
        "blog_caption": (
            "The system starts training expectations when copying others becomes the safe move."
        ),
        "so_what": "It makes norm lock-in visible instead of treating delegation as a purely private preference.",
        "limitation": "This is a convergence proxy, not a direct measure of tolerance for delay.",
    }


def _plot_threshold_strip(package_dir: Path, summary: pd.DataFrame) -> dict[str, Any] | None:
    """Generate the threshold refinement strip plot."""
    selected = summary[summary["experiment_slug"] == "threshold_refinement"].copy()
    if selected.empty:
        return None
    figures_dir = package_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.5, 5.0))
    for task_load, group in selected.groupby("tasks_per_step_mean", dropna=False):
        ordered = group.sort_values("delegation_preference_mean")
        ax.plot(
            ordered["delegation_preference_mean"],
            ordered["tail_avg_stress_mean"],
            marker="o",
            linewidth=2.0,
            label=f"tasks_per_step_mean={task_load:.2f}",
        )
    ax.set_xlabel("Delegation Preference Mean")
    ax.set_ylabel("Tail Mean Stress")
    ax.set_title("Threshold Refinement Strip")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    output_path = figures_dir / "threshold_strip.png"
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    fig.savefig(output_path.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)
    return {
        "slug": "threshold_strip",
        "path": str(output_path),
        "source_tables": ["research_summary.csv"],
        "technical_caption": "Stress trajectories across the refined delegation band inferred from the task-load atlas.",
        "blog_caption": "This is the strip where convenience starts to feel less like relief and more like a trap.",
        "so_what": "It isolates the narrow band where the system's behaviour changes fastest.",
        "limitation": "The threshold is model-specific and reflects current assumptions, including fixed provider proficiency.",
    }


def _plot_mixed_distribution(package_dir: Path, per_seed_summary: pd.DataFrame) -> dict[str, Any] | None:
    """Generate the mixed-system distribution plot."""
    selected = per_seed_summary[per_seed_summary["experiment_slug"] == "mixed_stability_deep_dive"].copy()
    if selected.empty:
        return None
    figures_dir = package_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    labels: list[str] = []
    values: list[np.ndarray] = []
    grouped = selected.groupby(
        ["delegation_preference_mean", "social_conformity_pressure"],
        dropna=False,
    )
    for (delegation, conformity), group in grouped:
        labels.append(f"d={delegation:.2f}\nc={conformity:.2f}")
        values.append(group["final_avg_delegation_rate"].to_numpy(dtype=float))

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.boxplot(values, tick_labels=labels, patch_artist=True)
    ax.set_ylabel("Final Avg Delegation Rate")
    ax.set_title("Mixed-System Stability Distribution")
    ax.grid(True, axis="y", alpha=0.3)
    output_path = figures_dir / "mixed_stability_distribution.png"
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    fig.savefig(output_path.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)
    return {
        "slug": "mixed_stability_distribution",
        "path": str(output_path),
        "source_tables": ["research_summary.csv"],
        "technical_caption": "Distribution of final delegation rates across mixed-start conditions and conformity levels.",
        "blog_caption": "The middle looks balanced only until the system has time to choose a side.",
        "so_what": "It reveals whether the apparent middle is stable or just a staging point before divergence.",
        "limitation": "The plotted distribution comes from model seeds, not empirical samples of real societies.",
    }


def _plot_burden_transfer(package_dir: Path, story_case_summary: pd.DataFrame) -> dict[str, Any] | None:
    """Generate the burden-transfer figure from selected story cases."""
    if story_case_summary.empty:
        return None
    figures_dir = package_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    selected = story_case_summary[
        story_case_summary["package_slug"] == PACKAGE_B
    ].copy()
    if selected.empty:
        return None

    selected = selected.sort_values("tail_tasks_delegated_frac")
    labels = selected["title"].tolist()
    x = np.arange(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(
        x - width / 2,
        selected["final_time_spent_providing_mean"],
        width=width,
        label="Mean provider time",
        color="#D6604D",
    )
    ax.bar(
        x + width / 2,
        selected["final_available_time_mean"],
        width=width,
        label="Mean remaining time",
        color="#2166AC",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("Hours / Cumulative Hours")
    ax.set_title("Burden Transfer in Story Cases")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    output_path = figures_dir / "burden_transfer.png"
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    fig.savefig(output_path.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)
    return {
        "slug": "burden_transfer",
        "path": str(output_path),
        "source_tables": ["story_case_seed_scan.csv"],
        "technical_caption": "Selected story cases comparing mean provider burden against remaining daily time.",
        "blog_caption": "The time saved does not disappear; it reappears as provider effort somewhere else in the system.",
        "so_what": "It turns an abstract labour-transfer claim into a concrete, visual burden shift.",
        "limitation": "Provider burden is measured inside the model's abstract service pool, not a full labour-market institution.",
    }


def _plot_limits_figure(package_dir: Path) -> dict[str, Any]:
    """Generate a figure summarising what the model can and cannot claim."""
    figures_dir = package_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.axis("off")
    x_positions = [0.02, 0.35, 0.68]
    blocks = [
        ("Can Say Confidently", CLAIM_SAFETY["can_say_confidently"], "#D9EAF7"),
        ("Can Say With Caveat", CLAIM_SAFETY["can_say_with_caveat"], "#FBE3C0"),
        ("Cannot Claim", CLAIM_SAFETY["cannot_claim_from_current_model"], "#F6D0D0"),
    ]
    for x_pos, (title, lines, color) in zip(x_positions, blocks, strict=True):
        ax.add_patch(plt.Rectangle((x_pos, 0.05), 0.28, 0.88, facecolor=color, edgecolor="#444444"))
        ax.text(x_pos + 0.01, 0.90, title, fontsize=12, fontweight="bold", va="top")
        y = 0.84
        for line in lines:
            ax.text(x_pos + 0.01, y, f"- {line}", fontsize=9, va="top", wrap=True)
            y -= 0.22
    output_path = figures_dir / "limits_figure.png"
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    fig.savefig(output_path.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)
    return {
        "slug": "limits_figure",
        "path": str(output_path),
        "source_tables": ["writing_support/claim_safety_table.md"],
        "technical_caption": "Summary of model-valid claims, caveated claims, and out-of-scope claims.",
        "blog_caption": "This is the boundary line between a useful formal model and an overconfident story.",
        "so_what": "It protects the sequel blog from sounding more certain than the model actually is.",
        "limitation": "The figure itself is editorial guidance, not a simulation result.",
    }


def _package_highlights(package_slug: str, research_summary: pd.DataFrame) -> dict[str, Any]:
    """Extract key blog-ready numbers for one package."""
    highlights: list[dict[str, Any]] = []
    if research_summary.empty:
        return {"package": package_slug, "highlights": highlights}

    if package_slug == PACKAGE_A:
        horizons = sorted(research_summary["steps"].dropna().unique().tolist())
        for horizon in horizons:
            subset = research_summary[research_summary["steps"] == horizon]
            if subset["scenario_id"].str.startswith("type_a").any() and subset["scenario_id"].str.startswith("type_b").any():
                a_row = subset[subset["scenario_id"].str.startswith("type_a")].iloc[0]
                b_row = subset[subset["scenario_id"].str.startswith("type_b")].iloc[0]
                labor_delta = _round(
                    ((b_row["tail_total_labor_hours_mean"] - a_row["tail_total_labor_hours_mean"])
                     / max(a_row["tail_total_labor_hours_mean"], 1e-9)) * 100.0,
                    2,
                )
                highlights.append(
                    {
                        "label": f"Type B labour delta at {int(horizon)} steps",
                        "value_pct": labor_delta,
                        "explanation": "Percent difference in tail mean total labour hours relative to Type A.",
                    }
                )
    elif package_slug == PACKAGE_B:
        peak_row = research_summary.loc[research_summary["tail_total_labor_hours_mean"].idxmax()]
        highlights.append(
            {
                "label": "Peak labour-transfer cell",
                "delegation_preference_mean": _round(peak_row["delegation_preference_mean"], 2),
                "tasks_per_step_mean": _round(peak_row["tasks_per_step_mean"], 2),
                "tail_total_labor_hours_mean": _round(peak_row["tail_total_labor_hours_mean"], 2),
            }
        )
    elif package_slug == PACKAGE_C:
        midpoint_rows = research_summary[np.isclose(research_summary["delegation_preference_mean"], 0.5, atol=0.06)]
        if midpoint_rows.empty:
            midpoint_rows = research_summary[
                (research_summary["experiment_slug"] == "service_cost_context_scan")
                & (research_summary["scenario_id"].str.startswith("default_context"))
            ].copy()
        if not midpoint_rows.empty:
            low_cost = midpoint_rows.sort_values("service_cost_factor").iloc[0]
            high_cost = midpoint_rows.sort_values("service_cost_factor").iloc[-1]
            highlights.append(
                {
                    "label": "Midpoint delegation cost effect",
                    "low_cost_delegated_frac": _round(low_cost["tail_tasks_delegated_frac_mean"]),
                    "high_cost_delegated_frac": _round(high_cost["tail_tasks_delegated_frac_mean"]),
                    "difference": _round(
                        low_cost["tail_tasks_delegated_frac_mean"] - high_cost["tail_tasks_delegated_frac_mean"]
                    ),
                }
            )
    elif package_slug == PACKAGE_D:
        center = research_summary[np.isclose(research_summary["delegation_preference_mean"], 0.50, atol=0.02)]
        if not center.empty:
            most_unstable = center.sort_values("final_avg_delegation_rate_std", ascending=False).iloc[0]
            highlights.append(
                {
                    "label": "Most unstable mixed-start cell",
                    "social_conformity_pressure": _round(most_unstable["social_conformity_pressure"], 2),
                    "final_avg_delegation_rate_std": _round(most_unstable["final_avg_delegation_rate_std"]),
                }
            )
    return {"package": package_slug, "highlights": highlights}


def _write_question_to_evidence_crosswalk(
    campaign_dir: Path,
    package_figure_manifests: dict[str, list[dict[str, Any]]],
) -> Path:
    """Write a markdown crosswalk from narrative questions to evidence artefacts."""
    figure_lookup: dict[str, list[str]] = {
        package_slug: [Path(item["path"]).name for item in items]
        for package_slug, items in package_figure_manifests.items()
    }
    rows = [
        (
            "Why do small frictions feel like system signals rather than isolated annoyances?",
            PACKAGE_A,
            "Preset horizon scan + story cases",
            "tail_total_labor_hours, tail_avg_stress, tail_gini_available_time",
            ", ".join(figure_lookup.get(PACKAGE_A, [])),
            "Can answer in abstract Type A / Type B terms.",
        ),
        (
            "Is convenience saving labour, or relocating it?",
            PACKAGE_B,
            "Task-load atlas + burden transfer story cases",
            "total_labor_hours, time_spent_providing, gini_available_time",
            ", ".join(figure_lookup.get(PACKAGE_B, [])),
            "Can answer inside the model's abstract service-pool mechanism.",
        ),
        (
            "How much can cheap service alone explain?",
            PACKAGE_C,
            "Service-cost atlas + preset decomposition",
            "tasks_delegated_frac, avg_delegation_rate, total_labor_hours",
            ", ".join(figure_lookup.get(PACKAGE_C, [])),
            "Only answers exogenous price-friction questions, not full circular causality.",
        ),
        (
            "Why does the system train faster expectations and make exit harder?",
            PACKAGE_D,
            "Conformity atlas + mixed-system deep dive",
            "avg_delegation_rate, tasks_delegated_frac, final_avg_delegation_rate_std",
            ", ".join(figure_lookup.get(PACKAGE_D, [])),
            "Answers through delegation-convergence proxies, not direct delay-tolerance measurement.",
        ),
        (
            "What can this model not honestly claim?",
            PACKAGE_D,
            "Claim safety table + limits figure",
            "N/A",
            ", ".join(name for name in figure_lookup.get(PACKAGE_D, []) if "limits" in name),
            "Explicit boundary statement.",
        ),
    ]

    lines = [
        "# Question to Evidence Crosswalk",
        "",
        "| Narrative Question | Package | Primary Evidence | Metrics | Figures | Answer Scope |",
        "|---|---|---|---|---|---|",
    ]
    for question, package_slug, evidence, metrics, figures, scope in rows:
        lines.append(
            f"| {question} | {PACKAGE_DEFINITIONS[package_slug].title} | {evidence} | "
            f"{metrics} | {figures or 'Pending'} | {scope} |"
        )
    output_path = campaign_dir / "writing_support" / "question_to_evidence_crosswalk.md"
    _save_markdown(output_path, "\n".join(lines) + "\n")
    return output_path


def _write_claim_safety_table(campaign_dir: Path) -> Path:
    """Write the claim safety markdown table."""
    lines = ["# Claim Safety Table", ""]
    sections = [
        ("Can Say Confidently", CLAIM_SAFETY["can_say_confidently"]),
        ("Can Say With Caveat", CLAIM_SAFETY["can_say_with_caveat"]),
        ("Cannot Claim From Current Model", CLAIM_SAFETY["cannot_claim_from_current_model"]),
    ]
    for heading, items in sections:
        lines.append(f"## {heading}")
        lines.append("")
        for item in items:
            lines.append(f"- {item}")
        lines.append("")
    output_path = campaign_dir / "writing_support" / "claim_safety_table.md"
    _save_markdown(output_path, "\n".join(lines))
    return output_path


def _write_scene_bank(campaign_dir: Path, selected_story_cases: pd.DataFrame) -> Path:
    """Write story-case notes for sequel-blog drafting."""
    lines = ["# Scene Bank", ""]
    for _, row in selected_story_cases.sort_values(["package_slug", "title"]).iterrows():
        lines.append(f"## {row['title']}")
        lines.append("")
        lines.append(f"- Narrative role: {row['narrative_role']}")
        lines.append(f"- Observation hook: {row['observation_hook']}")
        lines.append(
            "- What to watch: "
            f"tail stress {row['tail_avg_stress']:.3f}, tail labour {row['tail_total_labor_hours']:.2f}, "
            f"provider burden mean {row['final_time_spent_providing_mean']:.2f}."
        )
        lines.append(
            "- Easy misread: this is an abstract role scene under the current "
            "model assumptions, not a literal portrait of any named society."
        )
        lines.append("")
    output_path = campaign_dir / "writing_support" / "scene_bank.md"
    _save_markdown(output_path, "\n".join(lines))
    return output_path


def _write_report(
    *,
    campaign_dir: Path,
    scale: ScaleConfig,
    selected_packages: Sequence[str],
    package_dirs: dict[str, Path],
) -> Path:
    """Write a compact narrative-campaign report into analysis/reports/."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    report_path = REPORTS_DIR / f"{date_str}_narrative_campaign_{campaign_dir.name}.md"
    lines = [
        "# Narrative Campaign Report",
        "",
        f"**Date**: {date_str}",
        f"**Campaign Directory**: `{campaign_dir}`",
        f"**Scale**: `{scale.name}`",
        f"**Packages**: {', '.join(PACKAGE_DEFINITIONS[p].title for p in selected_packages)}",
        "",
        "## Outputs",
        "",
    ]
    for package_slug in selected_packages:
        package_dir = package_dirs[package_slug]
        lines.append(f"### {PACKAGE_DEFINITIONS[package_slug].title}")
        lines.append("")
        lines.append(f"- Research summary: `{package_dir / 'research_summary.csv'}`")
        lines.append(f"- Blog numbers: `{package_dir / 'blog_numbers.json'}`")
        lines.append(f"- Figure manifest: `{package_dir / 'figure_manifest.json'}`")
        lines.append("")
    lines.extend(
        [
            "## Writing Support",
            "",
            f"- Crosswalk: `{campaign_dir / 'writing_support' / 'question_to_evidence_crosswalk.md'}`",
            f"- Claim safety table: `{campaign_dir / 'writing_support' / 'claim_safety_table.md'}`",
            f"- Scene bank: `{campaign_dir / 'writing_support' / 'scene_bank.md'}`",
            "",
            "## Notes",
            "",
            "- This report intentionally uses abstract Type A / Type B language only.",
            "- The campaign runner writes compact summaries instead of the legacy agent-expanded Mesa batch CSV shape.",
            "- Any downstream blog mapping to concrete observations should cite the claim-safety table before making real-world interpretations.",
            "",
        ]
    )
    _save_markdown(report_path, "\n".join(lines))
    return report_path


def _summaries_for_package(summary_df: pd.DataFrame, package_slug: str) -> pd.DataFrame:
    """Filter an aggregated summary dataframe to one package."""
    if summary_df.empty:
        return summary_df.copy()
    return summary_df[summary_df["package_slug"] == package_slug].copy()


def _story_case_seed_rows(story_cases: Sequence[StoryCaseDefinition], engine: str) -> list[dict[str, Any]]:
    """Expand story-case seed scan tasks."""
    tasks: list[dict[str, Any]] = []
    for case in story_cases:
        for seed in case.seeds:
            tasks.append(
                {
                    "package_slug": case.package_slug,
                    "experiment_slug": "story_case_seed_scan",
                    "experiment_title": "Story Case Seed Scan",
                    "scenario_id": case.slug,
                    "scenario_label": case.title,
                    "narrative_question": case.question_prompt,
                    "steps": case.steps,
                    "seed": seed,
                    "engine": engine,
                    "params": case.params,
                }
            )
    return tasks


def _story_case_replay_rows(story_cases: Sequence[StoryCaseDefinition], engine: str) -> list[dict[str, Any]]:
    """Return pseudo-tasks representing the final full rerun for each story case."""
    tasks: list[dict[str, Any]] = []
    for case in story_cases:
        tasks.append(
            {
                "package_slug": case.package_slug,
                "experiment_slug": "story_case_replay",
                "experiment_title": "Story Case Replay",
                "scenario_id": case.slug,
                "scenario_label": case.title,
                "narrative_question": case.question_prompt,
                "steps": case.steps,
                "seed": -1,
                "engine": engine,
                "params": case.params,
            }
        )
    return tasks


def _story_case_replay_task(case: StoryCaseDefinition, selected_seed: int, engine: str) -> dict[str, Any]:
    """Build one completed-task record for a selected story-case replay."""
    return {
        "package_slug": case.package_slug,
        "experiment_slug": "story_case_replay",
        "experiment_title": "Story Case Replay",
        "scenario_id": case.slug,
        "scenario_label": case.title,
        "narrative_question": case.question_prompt,
        "steps": case.steps,
        "seed": selected_seed,
        "engine": engine,
        "params": case.params,
    }


def run_campaign(
    *,
    scale: ScaleConfig,
    packages: Sequence[str] | None = None,
    workers: int = DEFAULT_WORKERS,
    tag: str | None = None,
    output_root: Path | None = None,
    write_report: bool = True,
    engine: str = "stable",
) -> dict[str, Any]:
    """Execute the narrative campaign and return key output paths."""
    selected_packages = list(packages or PACKAGE_DEFINITIONS.keys())
    stamp = _campaign_stamp()
    safe_tag = tag or scale.name
    campaign_dir = (output_root or CAMPAIGNS_DIR) / f"{stamp}_{safe_tag}"
    summaries_dir = campaign_dir / "summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)

    experiments, story_cases = build_campaign_plan(scale=scale, packages=selected_packages, engine=engine)
    experiments = _expand_horizon_experiments(experiments, scale)

    main_tasks: list[dict[str, Any]] = []
    decomposition_tasks: list[dict[str, Any]] = []
    for experiment in experiments:
        if experiment.slug in {"preset_decomposition", "preset_decomposition_v2"}:
            decomposition_tasks.extend(
                _build_decomposition_tasks(
                    scale=scale,
                    experiment_slug=experiment.slug,
                    package_slug=experiment.package_slug,
                    engine=engine,
                )
            )
            continue
        if experiment.slug.startswith("preset_horizon_scan_"):
            scenario_label = experiment.scenario_prefix.replace("_", " ").title()
            for seed in experiment.seeds:
                main_tasks.append(
                    {
                        "package_slug": experiment.package_slug,
                        "experiment_slug": "preset_horizon_scan",
                        "experiment_title": experiment.title,
                        "scenario_id": experiment.scenario_prefix,
                        "scenario_label": scenario_label,
                        "narrative_question": experiment.narrative_question,
                        "steps": experiment.steps,
                        "seed": seed,
                        "engine": engine,
                        "params": dict(experiment.base_params),
                    }
                )
            continue
        main_tasks.extend(_build_experiment_tasks(experiment, engine))

    story_seed_tasks = _story_case_seed_rows(story_cases, engine)
    story_replay_tasks = _story_case_replay_rows(story_cases, engine)

    progress_tracker = _CampaignProgressTracker(campaign_dir=campaign_dir, engine=engine)
    for task_group in [main_tasks, decomposition_tasks, story_seed_tasks, story_replay_tasks]:
        progress_tracker.add_planned_tasks(task_group)

    per_seed_summary = _run_tasks(
        main_tasks,
        workers,
        tracker=progress_tracker,
        phase_name="summary_tasks",
        partial_path=summaries_dir / "per_seed_summary.partial.csv",
    )
    if not per_seed_summary.empty:
        per_seed_summary.to_csv(summaries_dir / "per_seed_summary.csv", index=False)

    decomposition_summary = pd.DataFrame()
    if decomposition_tasks:
        decomposition_summary = _run_tasks(
            decomposition_tasks,
            workers,
            tracker=progress_tracker,
            phase_name="preset_decomposition",
            partial_path=summaries_dir / "preset_decomposition_per_seed.partial.csv",
        )
        if not decomposition_summary.empty:
            decomposition_summary.to_csv(summaries_dir / "preset_decomposition_per_seed.csv", index=False)

    task_atlas_agg = _aggregate_per_seed(
        per_seed_summary[per_seed_summary["experiment_slug"] == "delegation_task_load_atlas"].copy()
    )
    delegation_band = _threshold_band_from_atlas(task_atlas_agg)
    threshold_tasks = (
        _build_threshold_tasks(scale, delegation_band, engine) if PACKAGE_B in selected_packages else []
    )
    threshold_summary = pd.DataFrame()
    if threshold_tasks:
        progress_tracker.add_planned_tasks(threshold_tasks)
        threshold_summary = _run_tasks(
            threshold_tasks,
            workers,
            tracker=progress_tracker,
            phase_name="threshold_refinement",
            partial_path=summaries_dir / "threshold_refinement_per_seed.partial.csv",
        )
        if not threshold_summary.empty:
            threshold_summary.to_csv(summaries_dir / "threshold_refinement_per_seed.csv", index=False)

    story_seed_summary = pd.DataFrame()
    if story_seed_tasks:
        story_seed_summary = _run_tasks(
            story_seed_tasks,
            workers,
            tracker=progress_tracker,
            phase_name="story_case_seed_scan",
            partial_path=summaries_dir / "story_case_seed_scan.partial.csv",
        )
        if not story_seed_summary.empty:
            story_seed_summary.to_csv(summaries_dir / "story_case_seed_scan.csv", index=False)

    combined_per_seed = pd.concat(
        [frame for frame in [per_seed_summary, decomposition_summary, threshold_summary] if not frame.empty],
        ignore_index=True,
    ) if any(not frame.empty for frame in [per_seed_summary, decomposition_summary, threshold_summary]) else pd.DataFrame()

    combined_agg = _aggregate_per_seed(combined_per_seed) if not combined_per_seed.empty else pd.DataFrame()
    if not combined_agg.empty:
        combined_agg.to_csv(summaries_dir / "combo_summary.csv", index=False)

    selected_story_rows: list[dict[str, Any]] = []
    package_dirs: dict[str, Path] = {}
    for package_slug in selected_packages:
        package_dir = campaign_dir / package_slug
        package_dir.mkdir(parents=True, exist_ok=True)
        package_dirs[package_slug] = package_dir

    if story_replay_tasks:
        progress_tracker.start_phase("story_case_replays", story_replay_tasks)
    for case in story_cases:
        case_group = story_seed_summary[story_seed_summary["scenario_id"] == case.slug].copy()
        if case_group.empty:
            continue
        seed = _select_story_seed(case_group)
        selected_row = case_group[case_group["seed"] == seed].iloc[0].to_dict()
        selected_row.update(
            {
                "title": case.title,
                "narrative_role": case.narrative_role,
                "observation_hook": case.observation_hook,
                "selected_seed": seed,
            }
        )
        selected_row.update(
            _save_story_case_outputs(
                case=case,
                selected_seed=seed,
                package_dir=package_dirs[case.package_slug],
                engine=engine,
            )
        )
        progress_tracker.record_completion(_story_case_replay_task(case, seed, engine), force=True)
        selected_story_rows.append(selected_row)

    progress_tracker.mark_simulation_complete()
    selected_story_df = pd.DataFrame(selected_story_rows)
    if not selected_story_df.empty:
        selected_story_df.to_csv(summaries_dir / "story_case_selection.csv", index=False)

    package_figure_manifests: dict[str, list[dict[str, Any]]] = {}
    for package_slug in selected_packages:
        package_dir = package_dirs[package_slug]
        package_summary = _summaries_for_package(combined_agg, package_slug)
        package_summary.to_csv(package_dir / "research_summary.csv", index=False)

        figures: list[dict[str, Any]] = []
        if package_slug == PACKAGE_A:
            figures.extend(_plot_horizon_comparison(package_dir, combined_agg))
        elif package_slug == PACKAGE_B:
            for figure in [
                _plot_task_load_heatmap(package_dir, combined_agg),
                _plot_threshold_strip(package_dir, combined_agg),
                _plot_burden_transfer(package_dir, selected_story_df),
            ]:
                if figure:
                    figures.append(figure)
        elif package_slug == PACKAGE_C:
            figure = _plot_service_cost_heatmap(package_dir, combined_agg)
            if figure:
                figures.append(figure)
        elif package_slug == PACKAGE_D:
            for figure in [
                _plot_conformity_heatmap(package_dir, combined_agg),
                _plot_mixed_distribution(package_dir, combined_per_seed),
                _plot_limits_figure(package_dir),
            ]:
                if figure:
                    figures.append(figure)

        package_figure_manifests[package_slug] = figures
        _save_json(package_dir / "figure_manifest.json", figures)
        _save_json(package_dir / "blog_numbers.json", _package_highlights(package_slug, package_summary))

    crosswalk_path = _write_question_to_evidence_crosswalk(campaign_dir, package_figure_manifests)
    claim_safety_path = _write_claim_safety_table(campaign_dir)
    scene_bank_path = _write_scene_bank(campaign_dir, selected_story_df)

    manifest = {
        "created_at": _utc_now_iso(),
        "campaign_dir": str(campaign_dir),
        "scale": scale.name,
        "engine": engine,
        "workers": workers,
        "selected_packages": selected_packages,
        "delegation_threshold_band": delegation_band,
        "git": _git_metadata(),
        "machine": {
            "os_cpu_count": os.cpu_count(),
            "default_workers": DEFAULT_WORKERS,
        },
        "notes": [
            "Formal outputs remain in abstract Type A / Type B language.",
            "Narrative packages are designed for a sequel blog that begins from observation and moves into mechanism plus evidence.",
            "Service prices are exogenous; any cheap-service interpretation must remain within that boundary.",
        ],
        "writing_support": {
            "question_to_evidence_crosswalk": str(crosswalk_path),
            "claim_safety_table": str(claim_safety_path),
            "scene_bank": str(scene_bank_path),
        },
        "progress": {
            "json": str(progress_tracker.progress_path),
            "log": str(progress_tracker.progress_log_path),
        },
    }
    _save_json(campaign_dir / "manifest.json", manifest)

    report_path: Path | None = None
    if write_report:
        report_path = _write_report(
            campaign_dir=campaign_dir,
            scale=scale,
            selected_packages=selected_packages,
            package_dirs=package_dirs,
        )

    progress_tracker.mark_completed()

    return {
        "campaign_dir": str(campaign_dir),
        "manifest_path": str(campaign_dir / "manifest.json"),
        "report_path": str(report_path) if report_path else None,
        "crosswalk_path": str(crosswalk_path),
        "claim_safety_path": str(claim_safety_path),
        "scene_bank_path": str(scene_bank_path),
        "progress_path": str(progress_tracker.progress_path),
        "progress_log_path": str(progress_tracker.progress_log_path),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for narrative campaign execution."""
    parser = argparse.ArgumentParser(
        description="Run narrative-first experiment campaigns for The Convenience Paradox."
    )
    parser.add_argument(
        "--scale",
        choices=sorted(SCALES.keys()),
        default="full",
        help="Runtime scale profile. Use 'smoke' for fast validation.",
    )
    parser.add_argument(
        "--packages",
        nargs="*",
        choices=sorted(PACKAGE_DEFINITIONS.keys()),
        default=list(PACKAGE_DEFINITIONS.keys()),
        help="Optional subset of narrative packages to run.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Number of worker processes. Defaults to min(8, cpu_count).",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default=None,
        help="Optional tag appended to the campaign directory name.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Override the output root directory (defaults to data/results/campaigns).",
    )
    parser.add_argument(
        "--engine",
        choices=sorted(MODEL_ENGINES.keys()),
        default="stable",
        help="Runtime model engine. 'stable' preserves the dashboard model contract; 'research_v2' uses the research-only engine.",
    )
    parser.add_argument(
        "--skip-report",
        action="store_true",
        help="Do not write a markdown report into analysis/reports/.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    for noisy_logger in ["MESA", "MESA.mesa.model", "model.model", "matplotlib"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
    args = parse_args(argv)
    scale = SCALES[args.scale]
    result = run_campaign(
        scale=scale,
        packages=args.packages,
        workers=max(1, int(args.workers)),
        tag=args.tag,
        output_root=args.output_root,
        write_report=not args.skip_report,
        engine=args.engine,
    )
    logger.info("Narrative campaign completed: %s", result["campaign_dir"])


if __name__ == "__main__":
    main()
