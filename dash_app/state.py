"""
Server-side simulation state management.

Holds the current simulation model instance, LLM audit log,
and model assignments. Provides thread-safe access for Dash callbacks.

Note:
    This module uses module-level state, suitable for single-user
    local deployment. For multi-user scenarios, a session-based or
    database-backed approach would be needed.
"""

import threading
import logging
from typing import Any

from api.llm_service import PRIMARY_MODEL, SECONDARY_MODEL

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_model = None
_run_id: str | None = None
_is_running: bool = False
_current_preset: str | None = None

# Session-level LLM audit log (list of call dicts, newest last)
_audit_log: list[dict[str, Any]] = []

# Per-role model assignments (live-switchable from the LLM Studio page)
_role_models: dict[str, str] = {
    "role_1": PRIMARY_MODEL,
    "role_2": SECONDARY_MODEL,
    "role_3": PRIMARY_MODEL,
    "role_4": PRIMARY_MODEL,
    "role_5": PRIMARY_MODEL,
}


# --- Simulation state ---

def get_model():
    """Return the current simulation model instance, or None."""
    return _model


def set_model(model) -> None:
    """Replace the current simulation model."""
    global _model
    with _lock:
        _model = model


def clear_model() -> None:
    """Remove the current simulation model (reset)."""
    global _model, _run_id, _is_running, _current_preset
    with _lock:
        _model = None
        _run_id = None
        _is_running = False
        _current_preset = None


def get_run_id() -> str | None:
    """Return the current run ID, if the run has been saved."""
    return _run_id


def set_run_id(rid: str | None) -> None:
    """Set the current run ID after saving to the database."""
    global _run_id
    with _lock:
        _run_id = rid


def is_running() -> bool:
    """Check if a simulation is currently advancing steps."""
    return _is_running


def set_running(running: bool) -> None:
    """Mark whether a simulation run is in progress."""
    global _is_running
    _is_running = running


def is_initialized() -> bool:
    """Check if a simulation model has been initialized."""
    return _model is not None


def get_status() -> dict[str, Any]:
    """Return a summary of the current simulation state."""
    m = _model
    return {
        "initialized": m is not None,
        "current_step": m.current_step if m else 0,
        "is_running": _is_running,
        "run_id": _run_id,
        "current_preset": _current_preset,
        "num_agents": m.num_agents if m else 0,
    }


def get_current_preset() -> str | None:
    """Return the active preset selection for the current simulation."""
    return _current_preset


def set_current_preset(preset: str | None) -> None:
    """Store the active preset selection used to initialize the model."""
    global _current_preset
    with _lock:
        _current_preset = preset


# --- LLM audit log ---

def append_audit_entry(entry: dict[str, Any]) -> None:
    """Add one LLM call record to the session audit log."""
    with _lock:
        _audit_log.append(entry)


def get_audit_log() -> list[dict[str, Any]]:
    """Return a copy of the full session audit log."""
    return list(_audit_log)


def clear_audit_log() -> None:
    """Clear the session audit log."""
    global _audit_log
    with _lock:
        _audit_log = []


# --- Per-role model assignments ---

def get_role_model(role: str) -> str:
    """Return the LLM model assigned to a role (e.g. 'role_1')."""
    return _role_models.get(role, PRIMARY_MODEL)


def set_role_model(role: str, model_name: str) -> None:
    """Assign an LLM model to a role."""
    with _lock:
        _role_models[role] = model_name


def get_all_role_models() -> dict[str, str]:
    """Return the current model assignments for all roles."""
    return dict(_role_models)
