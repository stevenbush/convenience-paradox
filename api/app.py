"""api/app.py — Flask Application Factory

Architecture role:
    This module creates and configures the Flask application. It uses the
    application factory pattern (create_app()) as required by CLAUDE.md §8.3.
    The factory pattern allows the app to be instantiated with different
    configurations (e.g., for testing) without running in global scope.

    The app serves two purposes:
      1. REST API backend: JSON endpoints for simulation control and data
         retrieval (consumed by the Plotly.js dashboard via fetch()).
      2. Static page server: serves `templates/index.html` (the dashboard)
         and static assets (CSS, JS) via Flask's built-in static file handling.

    Simulation state is stored in the application context (`app.config`)
    and protected by a threading.Lock to handle potential concurrent requests
    from the browser (though the dashboard is single-user by design).

SQLite database:
    Run persistence is handled via SQLite (Python's built-in `sqlite3`).
    The database file is created at `data/results/runs.db` on first startup.
    It stores run metadata and per-step metric snapshots for the run
    history comparison panel on the dashboard.

See also:
    - api/routes.py     — all REST endpoint implementations
    - api/schemas.py    — Pydantic schemas for request validation
    - templates/index.html — the single-page dashboard served by this app
"""

import logging
import os
import sqlite3
import threading
from pathlib import Path

from flask import Flask

logger = logging.getLogger(__name__)

# Project root: one level above api/
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_app(config: dict | None = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        config: Optional dict of Flask configuration overrides.
            Useful for testing (e.g., DATABASE_PATH pointing to a temp file).

    Returns:
        Configured Flask application instance.
    """
    app = Flask(
        __name__,
        # Flask looks for templates/ and static/ relative to the project root.
        template_folder=str(PROJECT_ROOT / "templates"),
        static_folder=str(PROJECT_ROOT / "static"),
    )

    # --- Default configuration ---
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "convenience-paradox-dev-key"),
        # Path to the SQLite database for run persistence.
        DATABASE_PATH=str(PROJECT_ROOT / "data" / "results" / "runs.db"),
        # Maximum steps per /api/simulation/run call (safety limit).
        MAX_RUN_STEPS=1000,
        # Default number of steps for the "Run" button.
        DEFAULT_RUN_STEPS=50,
    )

    # Apply any user-provided overrides.
    if config:
        app.config.update(config)

    # --- Simulation state store ---
    # The active model instance and its run metadata are stored here.
    # A threading.Lock prevents race conditions if the browser sends
    # overlapping requests (unlikely but possible with rapid clicking).
    app.config["SIMULATION"] = {
        "model": None,        # Active ConvenienceParadoxModel instance
        "run_id": None,       # SQLite run ID of the current session
        "params": {},         # Parameters used to initialise the current model
        "is_running": False,  # True while a background run is in progress
    }
    app.config["SIMULATION_LOCK"] = threading.Lock()

    # --- Initialise SQLite database ---
    _init_database(app.config["DATABASE_PATH"])

    # --- Register blueprints ---
    from api.routes import simulation_bp
    app.register_blueprint(simulation_bp)

    # LLM endpoints (Phase 4: Roles 1–4 + health check)
    from api.llm_routes import llm_bp
    app.register_blueprint(llm_bp)

    logger.info(
        "Flask app created. Database: %s", app.config["DATABASE_PATH"]
    )
    return app


def _init_database(db_path: str) -> None:
    """Create the SQLite database schema if it does not already exist.

    Schema:
        runs: One row per simulation run. Stores the parameter configuration
              and final-step summary metrics.
        run_steps: One row per (run, step). Stores the full metric snapshot
                   at each step for the run history comparison feature.

    Args:
        db_path: Filesystem path to the SQLite database file.

    Note:
        Uses `IF NOT EXISTS` so this is idempotent — safe to call on every
        app startup without wiping existing run history.
    """
    # Ensure the parent directory exists (data/results/ may not exist yet).
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                label       TEXT,
                preset      TEXT,
                params_json TEXT    NOT NULL,
                steps_run   INTEGER NOT NULL DEFAULT 0,
                -- Summary metrics at final step (for quick comparison without
                -- loading all step data from run_steps).
                final_avg_stress          REAL,
                final_avg_delegation_rate REAL,
                final_total_labor_hours   REAL,
                final_social_efficiency   REAL
            );

            CREATE TABLE IF NOT EXISTS run_steps (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id     INTEGER NOT NULL REFERENCES runs(id),
                step       INTEGER NOT NULL,
                -- All model-level metrics stored as a JSON string for flexibility.
                -- Parsed in Python when retrieved; avoids wide schema migrations.
                metrics_json TEXT   NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_run_steps_run_id
                ON run_steps (run_id, step);
        """)
        conn.commit()
        logger.debug("SQLite database initialised at %s", db_path)
    finally:
        conn.close()


def get_db(app: Flask) -> sqlite3.Connection:
    """Open a new SQLite connection for the current request context.

    Callers are responsible for closing the connection. This is a thin
    helper used by api/routes.py for run persistence operations.

    Args:
        app: The Flask application instance.

    Returns:
        An open sqlite3.Connection with row_factory set to sqlite3.Row
        (enables column access by name, e.g., row["label"]).
    """
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row
    return conn
