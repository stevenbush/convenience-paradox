"""
SQLite database utilities for the Dash dashboard.

Provides direct database access for the Run Manager page without
depending on the Flask application context. Reuses the same schema
and database file as the legacy Flask API (api/app.py).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = str(PROJECT_ROOT / "data" / "results" / "runs.db")


def _get_conn(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a connection with row_factory for dict-like access."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Ensure the database schema exists (idempotent)."""
    conn = _get_conn(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                label       TEXT,
                preset      TEXT,
                params_json TEXT    NOT NULL,
                steps_run   INTEGER NOT NULL DEFAULT 0,
                final_avg_stress          REAL,
                final_avg_delegation_rate REAL,
                final_total_labor_hours   REAL,
                final_social_efficiency   REAL
            );
            CREATE TABLE IF NOT EXISTS run_steps (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id     INTEGER NOT NULL REFERENCES runs(id),
                step       INTEGER NOT NULL,
                metrics_json TEXT   NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_run_steps_run_id
                ON run_steps (run_id, step);
        """)
        conn.commit()
    finally:
        conn.close()


def list_runs(
    search: str | None = None,
    preset_filter: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Query saved runs with optional filtering.

    Returns a list of run summary dicts (no step-level data).
    """
    init_db()
    conn = _get_conn()
    try:
        query = """
            SELECT id, created_at, label, preset, steps_run,
                   final_avg_stress, final_avg_delegation_rate,
                   final_total_labor_hours, final_social_efficiency
            FROM runs WHERE 1=1
        """
        params: list[Any] = []

        if search and search.strip():
            query += " AND (label LIKE ? OR preset LIKE ?)"
            like = f"%{search.strip()}%"
            params.extend([like, like])

        if preset_filter and preset_filter != "all":
            query += " AND preset = ?"
            params.append(preset_filter)

        if start_date:
            query += " AND date(created_at) >= date(?)"
            params.append(start_date)
        if end_date:
            query += " AND date(created_at) <= date(?)"
            params.append(end_date)

        query += f" ORDER BY id DESC LIMIT {int(limit)}"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_run_detail(run_id: int) -> dict[str, Any] | None:
    """Return full run metadata + step-by-step metrics for one run."""
    init_db()
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return None

        step_rows = conn.execute(
            "SELECT step, metrics_json FROM run_steps WHERE run_id = ? ORDER BY step",
            (run_id,),
        ).fetchall()

        steps = []
        for sr in step_rows:
            metrics = json.loads(sr["metrics_json"])
            metrics["step"] = sr["step"]
            steps.append(metrics)

        run_data = dict(row)
        if run_data.get("params_json"):
            try:
                run_data["params"] = json.loads(run_data["params_json"])
            except (json.JSONDecodeError, TypeError):
                run_data["params"] = {}
        run_data["steps"] = steps
        return run_data
    finally:
        conn.close()


def delete_runs(run_ids: list[int]) -> int:
    """Delete runs and their step data. Returns count of deleted runs."""
    if not run_ids:
        return 0
    init_db()
    conn = _get_conn()
    try:
        placeholders = ",".join("?" for _ in run_ids)
        conn.execute(
            f"DELETE FROM run_steps WHERE run_id IN ({placeholders})",
            run_ids,
        )
        cursor = conn.execute(
            f"DELETE FROM runs WHERE id IN ({placeholders})",
            run_ids,
        )
        conn.commit()
        deleted = cursor.rowcount
        logger.info("Deleted %d runs: %s", deleted, run_ids)
        return deleted
    finally:
        conn.close()


def save_run(model: Any, label: str | None = None,
             preset: str | None = None) -> int:
    """Persist a completed simulation run to SQLite.

    Args:
        model: A ConvenienceParadoxModel with at least one step.
        label: Optional user-provided label.
        preset: Preset name used.

    Returns:
        The integer ID of the newly created run.
    """
    init_db()
    conn = _get_conn()
    try:
        params_json = json.dumps(model.get_params())
        df = model.get_model_dataframe()

        if len(df) > 0:
            last = df.iloc[-1]
            final_stress = float(last.get("avg_stress", 0))
            final_delegation = float(last.get("avg_delegation_rate", 0))
            final_labor = float(last.get("total_labor_hours", 0))
            final_efficiency = float(last.get("social_efficiency", 0))
        else:
            final_stress = final_delegation = final_labor = final_efficiency = 0.0

        cursor = conn.execute(
            """INSERT INTO runs
               (label, preset, params_json, steps_run,
                final_avg_stress, final_avg_delegation_rate,
                final_total_labor_hours, final_social_efficiency)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (label, preset, params_json, model.current_step,
             final_stress, final_delegation, final_labor, final_efficiency),
        )
        run_id = cursor.lastrowid

        df_reset = df.reset_index()
        step_col = "Step" if "Step" in df_reset.columns else df_reset.columns[0]
        step_rows = []
        for _, row in df_reset.iterrows():
            step = int(row[step_col])
            metrics = {k: (float(v) if hasattr(v, "item") else v)
                       for k, v in row.items() if k != step_col}
            step_rows.append((run_id, step, json.dumps(metrics)))

        conn.executemany(
            "INSERT INTO run_steps (run_id, step, metrics_json) VALUES (?, ?, ?)",
            step_rows,
        )
        conn.commit()
        logger.info("Saved run %d (%d steps)", run_id, model.current_step)
        return run_id
    finally:
        conn.close()
