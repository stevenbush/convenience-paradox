"""api/routes.py — Flask REST API Endpoints

Architecture role:
    This module defines all REST API endpoints for the simulation dashboard.
    All endpoints are grouped in a Flask Blueprint (`simulation_bp`) and
    registered on the app in `api/app.py`.

    The endpoints provide a clean separation between the Mesa simulation
    engine and the Plotly.js frontend: the frontend calls these endpoints
    via fetch(), the endpoints manipulate the model and return JSON data,
    and the frontend renders the results as interactive charts.

Endpoint summary:
    GET  /                         — serve the dashboard HTML page
    POST /api/simulation/init      — create a new model with given parameters
    POST /api/simulation/step      — advance model by N steps
    POST /api/simulation/run       — run model to max_steps
    POST /api/simulation/reset     — clear current model (return to uninitialized)
    GET  /api/simulation/data      — current model DataFrame + agent states
    GET  /api/simulation/status    — step count, params, running flag
    GET  /api/presets              — Type A/B preset definitions
    GET  /api/parameters           — parameter metadata (for slider generation)
    GET  /api/runs                 — list of saved simulation runs
    GET  /api/runs/<run_id>        — full data for a specific saved run

State management:
    The active ConvenienceParadoxModel is stored in app.config["SIMULATION"].
    All access is protected by app.config["SIMULATION_LOCK"] (threading.Lock).
    The frontend is entirely stateless — it renders whatever the API returns.

Error handling:
    All endpoints return {error: message} with appropriate HTTP status codes.
    400: invalid input; 404: resource not found; 409: model not initialised;
    500: unexpected server error.

See also:
    - api/app.py     — application factory and database initialisation
    - api/schemas.py — Pydantic schemas for request validation
    - model/model.py — ConvenienceParadoxModel (the engine)
    - model/params.py — PARAMETER_DEFINITIONS, presets
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template, request
from pydantic import ValidationError

from api.app import get_db
from api.schemas import RunRequest, SimulationParams, StepRequest
from model.model import ConvenienceParadoxModel
from model.params import PARAMETER_DEFINITIONS, TYPE_A_PRESET, TYPE_B_PRESET, get_preset

logger = logging.getLogger(__name__)

# All routes are registered on this Blueprint.
# URL prefix is / (no prefix) so GET / serves the dashboard root.
simulation_bp = Blueprint("simulation", __name__)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _get_sim() -> dict:
    """Return the simulation state dict from the app config."""
    return current_app.config["SIMULATION"]


def _get_lock():
    """Return the threading.Lock protecting simulation state."""
    return current_app.config["SIMULATION_LOCK"]


def _model_required(func):
    """Decorator: return 409 if no model is currently initialised."""
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        sim = _get_sim()
        if sim["model"] is None:
            return jsonify({
                "error": "No simulation initialised. Call POST /api/simulation/init first."
            }), 409
        return func(*args, **kwargs)
    return wrapper


def _save_run_to_db(
    model: ConvenienceParadoxModel,
    label: str | None,
    preset: str | None = None,
) -> int:
    """Persist the completed simulation run to SQLite and return the run ID.

    Args:
        model: The completed ConvenienceParadoxModel.
        label: Optional user-provided label for this run.
        preset: Preset name ('type_a', 'type_b', 'custom', or None).
            Stored in its own column so the run history UI can display it
            without parsing params_json.

    Returns:
        The integer ID of the newly created `runs` row.
    """
    db = get_db(current_app)
    try:
        params_json = json.dumps(model.get_params())
        df = model.get_model_dataframe()

        # Extract final-step summary metrics for the runs table.
        if len(df) > 0:
            last = df.iloc[-1]
            final_stress = float(last.get("avg_stress", 0))
            final_delegation = float(last.get("avg_delegation_rate", 0))
            final_labor = float(last.get("total_labor_hours", 0))
            final_efficiency = float(last.get("social_efficiency", 0))
        else:
            final_stress = final_delegation = final_labor = final_efficiency = 0.0

        cursor = db.execute(
            """INSERT INTO runs
               (label, preset, params_json, steps_run,
                final_avg_stress, final_avg_delegation_rate,
                final_total_labor_hours, final_social_efficiency)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (label, preset, params_json, model.current_step,
             final_stress, final_delegation, final_labor, final_efficiency),
        )
        run_id = cursor.lastrowid

        # Save per-step metric snapshots to run_steps.
        # Reset index so Step is a column (Mesa DataCollector uses Step as index).
        df_reset = df.reset_index()
        step_col = "Step" if "Step" in df_reset.columns else df_reset.columns[0]

        step_rows = []
        for _, row in df_reset.iterrows():
            step = int(row[step_col])
            # Convert row to plain dict, handling numpy types.
            metrics = {k: (float(v) if hasattr(v, "item") else v)
                       for k, v in row.items() if k != step_col}
            step_rows.append((run_id, step, json.dumps(metrics)))

        db.executemany(
            "INSERT INTO run_steps (run_id, step, metrics_json) VALUES (?, ?, ?)",
            step_rows,
        )
        db.commit()
        logger.info("Run %d saved to database (%d steps).", run_id, model.current_step)
        return run_id
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@simulation_bp.route("/")
def index():
    """Serve the main dashboard HTML page.

    The dashboard is a single-page application: `templates/index.html` contains
    the full layout. All dynamic content is loaded via JavaScript fetch() calls
    to the API endpoints below.
    """
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Simulation control endpoints
# ---------------------------------------------------------------------------

@simulation_bp.route("/api/simulation/init", methods=["POST"])
def init_simulation():
    """Initialise a new simulation model with the given parameters.

    Request body (JSON):
        Any field from SimulationParams schema. If 'preset' is provided,
        those preset values override all other fields.

    Response (JSON):
        {status, params, agent_count, message}

    Example:
        POST /api/simulation/init
        {"preset": "type_a"}

        POST /api/simulation/init
        {"delegation_preference_mean": 0.6, "service_cost_factor": 0.3,
         "social_conformity_pressure": 0.5, "num_agents": 100}
    """
    try:
        body = request.get_json(force=True) or {}

        # If a preset is named, load it and merge with any explicit overrides.
        preset_name = body.get("preset")
        if preset_name:
            preset_data = get_preset(preset_name)
            # User-provided fields take priority over preset defaults.
            merged = {**preset_data, **{k: v for k, v in body.items() if k != "preset"}}
            merged["preset"] = preset_name
            body = merged

        params = SimulationParams(**body)

    except ValidationError as e:
        return jsonify({"error": "Invalid parameters.", "details": e.errors()}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Acquire lock and create the new model.
    lock = _get_lock()
    sim = _get_sim()

    with lock:
        sim["model"] = ConvenienceParadoxModel(**params.to_model_kwargs())
        sim["params"] = params.model_dump()
        sim["run_id"] = None
        sim["is_running"] = False

    logger.info(
        "Simulation initialised: %d agents, preset=%s, delegation_mean=%.2f",
        params.num_agents, params.preset, params.delegation_preference_mean,
    )
    return jsonify({
        "status": "ok",
        "message": "Simulation initialised.",
        "params": sim["params"],
        "agent_count": params.num_agents,
        "current_step": 0,
    })


@simulation_bp.route("/api/simulation/step", methods=["POST"])
@_model_required
def step_simulation():
    """Advance the simulation by N steps.

    Request body (JSON):
        {"steps": 1}  (default: 1, max: 200)

    Response (JSON):
        {status, current_step, model_data: [{step, metrics...}, ...]}
    """
    try:
        body = request.get_json(force=True) or {}
        req = StepRequest(**body)
    except ValidationError as e:
        return jsonify({"error": "Invalid request.", "details": e.errors()}), 400

    lock = _get_lock()
    sim = _get_sim()

    with lock:
        model: ConvenienceParadoxModel = sim["model"]
        for _ in range(req.steps):
            model.step()

        current_step = model.current_step
        # Return the most recent N+1 steps of data (including initial state).
        df = model.get_model_dataframe()
        # Send only the last `steps + 1` rows to avoid growing payload sizes.
        recent_df = df.tail(req.steps + 1).reset_index()
        step_col = recent_df.columns[0]
        model_data = recent_df.rename(columns={step_col: "step"}).to_dict(orient="records")

    return jsonify({
        "status": "ok",
        "current_step": current_step,
        "steps_advanced": req.steps,
        "model_data": model_data,
    })


@simulation_bp.route("/api/simulation/run", methods=["POST"])
@_model_required
def run_simulation():
    """Run the simulation to max_steps and optionally save to database.

    Request body (JSON):
        {"max_steps": 50, "save_run": true, "run_label": "My experiment"}

    Response (JSON):
        {status, current_step, run_id, model_data: [{step, metrics...}]}

    Note:
        This runs synchronously (all steps in one request). For large step
        counts on slow machines this may be slow. The dashboard's "Run" button
        uses a moderate max_steps (50–100) by default.
    """
    try:
        body = request.get_json(force=True) or {}
        req = RunRequest(**body)
    except ValidationError as e:
        return jsonify({"error": "Invalid request.", "details": e.errors()}), 400

    lock = _get_lock()
    sim = _get_sim()

    with lock:
        model: ConvenienceParadoxModel = sim["model"]
        sim["is_running"] = True

    try:
        # Run steps. Lock released during execution to allow status queries.
        for _ in range(req.max_steps):
            with lock:
                model.step()
    finally:
        with lock:
            sim["is_running"] = False

    run_id = None
    if req.save_run:
        # Pass the active preset name so it is stored in its own column.
        active_preset = sim["params"].get("preset")
        run_id = _save_run_to_db(model, req.run_label, preset=active_preset)
        with lock:
            sim["run_id"] = run_id

    df = model.get_model_dataframe().reset_index()
    step_col = df.columns[0]
    model_data = df.rename(columns={step_col: "step"}).to_dict(orient="records")

    return jsonify({
        "status": "ok",
        "current_step": model.current_step,
        "run_id": run_id,
        "model_data": model_data,
    })


@simulation_bp.route("/api/simulation/reset", methods=["POST"])
def reset_simulation():
    """Clear the current simulation model.

    Resets the server-side state to uninitialised. The frontend should
    clear its charts and re-enable the Init button.

    Response (JSON):
        {status, message}
    """
    lock = _get_lock()
    sim = _get_sim()

    with lock:
        sim["model"] = None
        sim["run_id"] = None
        sim["params"] = {}
        sim["is_running"] = False

    return jsonify({"status": "ok", "message": "Simulation reset."})


# ---------------------------------------------------------------------------
# Data retrieval endpoints
# ---------------------------------------------------------------------------

@simulation_bp.route("/api/simulation/data")
@_model_required
def get_simulation_data():
    """Return simulation data: model time-series + current agent states.

    Query parameters:
        last_n (int, optional): If provided, return only the last N rows of
            model_data. Used by the LLM chat widget (chat.js) to retrieve a
            compact data context for the result interpreter without sending the
            full history. If omitted or 0, all steps are returned.

    Response (JSON):
        {
          current_step,
          model_data: [{step, avg_stress, total_labor_hours, ...}],
          agent_states: [{id, stress_level, delegation_preference, ...}]
        }

    Used by the dashboard on page load or after a run completes to
    refresh all charts at once.
    """
    # Optional last_n query parameter for compact LLM context retrieval.
    try:
        last_n = int(request.args.get("last_n", 0))
    except (ValueError, TypeError):
        last_n = 0

    lock = _get_lock()
    sim = _get_sim()

    with lock:
        model: ConvenienceParadoxModel = sim["model"]
        df = model.get_model_dataframe().reset_index()
        step_col = df.columns[0]
        if last_n > 0:
            df = df.tail(last_n)
        model_data = df.rename(columns={step_col: "step"}).to_dict(orient="records")
        agent_states = model.get_agent_states()
        current_step = model.current_step

    return jsonify({
        "current_step": current_step,
        "model_data": model_data,
        "agent_states": agent_states,
    })


@simulation_bp.route("/api/simulation/status")
def get_status():
    """Return current simulation status without sending full data.

    Response (JSON):
        {initialised, current_step, is_running, params, run_id}

    Polled by the dashboard to update the status bar and button states.
    """
    sim = _get_sim()
    model = sim["model"]
    return jsonify({
        "initialised": model is not None,
        "current_step": model.current_step if model else 0,
        "is_running": sim["is_running"],
        "params": sim["params"],
        "run_id": sim["run_id"],
    })


# ---------------------------------------------------------------------------
# Configuration endpoints
# ---------------------------------------------------------------------------

@simulation_bp.route("/api/presets")
def get_presets():
    """Return the two society preset definitions.

    Response (JSON):
        {type_a: {label, description, params...}, type_b: {...}}

    Used by the dashboard to populate the Preset selector buttons and
    display preset descriptions to the user.
    """
    return jsonify({
        "type_a": {
            "label": TYPE_A_PRESET["label"],
            "description": TYPE_A_PRESET["description"],
            "empirical_basis": TYPE_A_PRESET["empirical_basis"],
            "params": {k: TYPE_A_PRESET[k] for k in TYPE_A_PRESET
                       if k not in {"label", "description", "empirical_basis"}},
        },
        "type_b": {
            "label": TYPE_B_PRESET["label"],
            "description": TYPE_B_PRESET["description"],
            "empirical_basis": TYPE_B_PRESET["empirical_basis"],
            "params": {k: TYPE_B_PRESET[k] for k in TYPE_B_PRESET
                       if k not in {"label", "description", "empirical_basis"}},
        },
    })


@simulation_bp.route("/api/parameters")
def get_parameters():
    """Return parameter metadata for dynamic slider generation.

    Response (JSON):
        {param_name: {type, min, max, default, description, unit}, ...}

    The dashboard uses this to build the parameter control panel sliders
    dynamically — any new parameter added to params.py appears automatically
    in the UI without HTML changes.
    """
    # Serialise type objects to strings (JSON can't encode Python types).
    serialisable = {}
    for name, defn in PARAMETER_DEFINITIONS.items():
        entry = dict(defn)
        entry["type"] = defn["type"].__name__ if isinstance(defn.get("type"), type) else str(defn.get("type", ""))
        serialisable[name] = entry
    return jsonify(serialisable)


# ---------------------------------------------------------------------------
# Run history endpoints
# ---------------------------------------------------------------------------

@simulation_bp.route("/api/runs")
def list_runs():
    """Return a list of all saved simulation runs (summary only).

    Response (JSON):
        [{id, created_at, label, preset, steps_run, final_avg_stress, ...}]

    Used by the dashboard's run history panel to let users select and
    overlay past runs on the charts.
    """
    db = get_db(current_app)
    try:
        rows = db.execute(
            """SELECT id, created_at, label, preset, steps_run,
                      final_avg_stress, final_avg_delegation_rate,
                      final_total_labor_hours, final_social_efficiency
               FROM runs ORDER BY id DESC LIMIT 50"""
        ).fetchall()
        return jsonify([dict(row) for row in rows])
    finally:
        db.close()


@simulation_bp.route("/api/runs/<int:run_id>")
def get_run(run_id: int):
    """Return full time-series data for a specific saved run.

    Args:
        run_id: Integer primary key of the run in the SQLite `runs` table.

    Response (JSON):
        {run: {id, label, ...}, steps: [{step, metrics...}]}

    Used by the dashboard to overlay a past run on the current charts.
    """
    db = get_db(current_app)
    try:
        run_row = db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not run_row:
            return jsonify({"error": f"Run {run_id} not found."}), 404

        step_rows = db.execute(
            "SELECT step, metrics_json FROM run_steps WHERE run_id = ? ORDER BY step",
            (run_id,),
        ).fetchall()

        steps = []
        for row in step_rows:
            metrics = json.loads(row["metrics_json"])
            metrics["step"] = row["step"]
            steps.append(metrics)

        return jsonify({
            "run": dict(run_row),
            "steps": steps,
        })
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Phase 5: Agent Forum endpoints
# ---------------------------------------------------------------------------

@simulation_bp.route("/api/simulation/forum_step", methods=["POST"])
@_model_required
def run_forum_step():
    """Run one Agent Communication Forum event (Phase 5 experimental mode).

    A subset of agents participates in LLM-driven dialogues about delegation
    norms. The forum's norm signal applies a small bounded update to each
    participating agent's delegation_preference.

    Request body (JSON):
        {
          "forum_fraction": 0.20,  (fraction of agents to invite, default 0.20)
          "group_size": 2,         (agents per dialogue group, default 2)
          "num_turns": 2           (dialogue turns per agent, default 2)
        }

    Response (JSON):
        {
          status, current_step,
          forum_session: {step, groups, n_agents_participating, elapsed_seconds, ...}
        }

    Warning: This endpoint is slow — each forum group requires 3–5 LLM calls.
    With 100 agents at forum_fraction=0.20, expect ~30–60 seconds (M4 Pro).
    Use small forum_fraction (0.10–0.20) for interactive demos.
    """
    from model.forums import run_forum_step as _run_forum, format_session_for_api

    body = request.get_json(force=True) or {}
    forum_fraction = float(body.get("forum_fraction", 0.20))
    group_size = int(body.get("group_size", 2))
    num_turns = int(body.get("num_turns", 2))

    # Clamp inputs to safe ranges.
    forum_fraction = max(0.05, min(0.50, forum_fraction))
    group_size = max(2, min(4, group_size))
    num_turns = max(1, min(3, num_turns))

    lock = _get_lock()
    sim = _get_sim()

    with lock:
        model = sim["model"]
        current_step = model.current_step

    # Forum runs outside the lock (it's slow and we don't mutate DataCollector).
    # Norm updates are applied directly to agent attributes, which is safe here
    # since the dashboard is single-user and no stepping happens concurrently.
    try:
        session = _run_forum(model, forum_fraction=forum_fraction,
                             group_size=group_size, num_turns=num_turns)
    except RuntimeError as e:
        return jsonify({"error": f"Forum error: {e}"}), 503

    # Store session in model for the forum_log endpoint.
    if not hasattr(model, "forum_log"):
        model.forum_log = []
    model.forum_log.append(session)

    return jsonify({
        "status": "ok",
        "current_step": current_step,
        "forum_session": format_session_for_api(session),
    })


@simulation_bp.route("/api/simulation/forum_log")
@_model_required
def get_forum_log():
    """Return the log of all forum sessions for the current simulation run.

    Response (JSON):
        {forum_sessions: [{step, groups, n_agents_participating, ...}]}

    Used by the dashboard's "Agent Forums" tab to show the audit trail.
    Each session shows the full dialogue and norm updates.
    """
    from model.forums import format_session_for_api

    sim = _get_sim()
    model = sim["model"]
    log = getattr(model, "forum_log", [])

    return jsonify({
        "forum_sessions": [format_session_for_api(s) for s in log],
        "total_sessions": len(log),
    })
