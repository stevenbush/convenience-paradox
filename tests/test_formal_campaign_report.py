"""tests/test_formal_campaign_report.py — Coverage for the formal report builder.

These tests validate that the paper-style reporting pipeline can read the
existing research campaign, generate the expected bilingual outputs, and keep
its headline claims anchored to the saved source tables.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from analysis.formal_campaign_report import build_formal_report

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGET_CAMPAIGN = (
    PROJECT_ROOT
    / "data"
    / "results"
    / "campaigns"
    / "20260401_235956_research_v2_15k_parallel_20260401"
)


def _run_report(tmp_path: Path):
    """Build the formal report into temporary output directories."""

    return build_formal_report(
        TARGET_CAMPAIGN,
        report_dir=tmp_path / "reports",
        asset_root=tmp_path / "assets",
    )


def test_build_formal_report_writes_expected_outputs_for_target_campaign(tmp_path: Path) -> None:
    """The builder should emit reports, figures, tables, and a manifest."""

    outputs = _run_report(tmp_path)

    assert outputs.english_report_path.exists()
    assert outputs.chinese_report_path.exists()
    assert outputs.manifest_path.exists()

    figures_dir = outputs.asset_root / "figures"
    tables_dir = outputs.asset_root / "tables"
    assert len(list(figures_dir.glob("*.png"))) == 8
    assert len(list(figures_dir.glob("*.svg"))) == 8
    assert len(list(tables_dir.glob("*.csv"))) == 5

    manifest = json.loads(outputs.manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["items"]) == 15

    english_text = outputs.english_report_path.read_text(encoding="utf-8")
    chinese_text = outputs.chinese_report_path.read_text(encoding="utf-8")

    assert "## Abstract" in english_text
    assert "## 摘要" in chinese_text
    assert "Strong support" in english_text
    assert "Partial support" in english_text
    assert "强支持" in chinese_text
    assert "部分支持" in chinese_text

    banned_terms = [
        "china",
        "chinese",
        "europe",
        "european",
        "asia",
        "asian",
        "western",
        "nordic",
    ]
    lower_english = english_text.lower()
    lower_chinese = chinese_text.lower()
    for term in banned_terms:
        assert term not in lower_english
        assert term not in lower_chinese


def test_formal_report_sources_capture_expected_headline_values(tmp_path: Path) -> None:
    """Key narrative claims should be recoverable from the saved source CSVs."""

    outputs = _run_report(tmp_path)

    baseline = pd.read_csv(outputs.asset_root / "sources" / "figure_03_baseline_horizon_source.csv")
    horizon_450 = baseline[baseline["steps"] == 450].set_index("society")
    labor_delta_pct = (
        (
            horizon_450.loc["Type B", "tail_total_labor_hours_mean"]
            / horizon_450.loc["Type A", "tail_total_labor_hours_mean"]
        )
        - 1.0
    ) * 100.0
    assert labor_delta_pct == pytest.approx(30.01, abs=0.02)

    threshold = pd.read_csv(outputs.asset_root / "sources" / "figure_05_threshold_refinement_summary.csv")
    row_300 = threshold[threshold["tasks_per_step_mean"] == 3.0].iloc[0]
    row_325 = threshold[threshold["tasks_per_step_mean"] == 3.25].iloc[0]
    row_350 = threshold[threshold["tasks_per_step_mean"] == 3.5].iloc[0]

    assert row_300["stress_min"] == pytest.approx(0.242, abs=0.005)
    assert row_300["stress_max"] == pytest.approx(0.309, abs=0.005)
    assert row_325["backlog_min"] == pytest.approx(0.61, abs=0.05)
    assert row_325["backlog_max"] == pytest.approx(2.25, abs=0.05)
    assert row_350["stress_min"] == pytest.approx(0.992, abs=0.01)
    assert row_350["stress_max"] == pytest.approx(0.999, abs=0.01)

    verdicts = pd.read_csv(outputs.asset_root / "tables" / "table_04_hypothesis_verdict_matrix.csv")
    verdict_map = dict(zip(verdicts["hypothesis"], verdicts["judgment"]))
    assert verdict_map == {
        "H1": "Strong support",
        "H2": "Strong support",
        "H3": "Partial support",
        "H4": "Partial support with an important negative result",
    }
