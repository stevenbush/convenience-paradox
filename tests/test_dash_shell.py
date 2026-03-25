"""Tests for Dash shell helpers and page callbacks."""

from types import SimpleNamespace

from dash import no_update

import dash_app.db as db
import dash_app.state as app_state
from dash_app.app import _resolve_sidebar_toggle, create_app


def test_resolve_sidebar_toggle_opens_sidebar_from_hamburger() -> None:
    """Hamburger clicks should open the mobile sidebar and backdrop."""
    sidebar_class, backdrop_class = _resolve_sidebar_toggle("sidebar-toggle", "cp-sidebar")

    assert sidebar_class == "cp-sidebar cp-sidebar--open"
    assert backdrop_class == "cp-sidebar-backdrop"


def test_resolve_sidebar_toggle_closes_sidebar_on_backdrop_or_navigation() -> None:
    """Backdrop clicks and page navigation should close the mobile sidebar."""
    assert _resolve_sidebar_toggle(
        "sidebar-backdrop",
        "cp-sidebar cp-sidebar--open",
    ) == ("cp-sidebar", "")
    assert _resolve_sidebar_toggle(
        "url",
        "cp-sidebar cp-sidebar--open",
    ) == ("cp-sidebar", "")


def test_save_current_run_persists_active_preset(monkeypatch) -> None:
    """Saved dashboard runs should keep the active preset for filtering."""
    create_app()
    from dash_app.pages.run_manager import save_current_run

    saved_call: dict[str, object] = {}

    def fake_save_run(model, label=None, preset=None):
        saved_call["label"] = label
        saved_call["preset"] = preset
        return 17

    monkeypatch.setattr(app_state, "get_model", lambda: SimpleNamespace(current_step=12))
    monkeypatch.setattr(app_state, "get_current_preset", lambda: "type_b")
    monkeypatch.setattr(app_state, "set_run_id", lambda rid: saved_call.setdefault("run_id", rid))
    monkeypatch.setattr(db, "save_run", fake_save_run)

    refresh_value, toast_open, toast_text = save_current_run(1)

    assert refresh_value == 17
    assert toast_open is True
    assert "Run saved as ID 17" in toast_text
    assert saved_call["preset"] == "type_b"
    assert saved_call["run_id"] == "17"


def test_save_current_run_rejects_empty_models(monkeypatch) -> None:
    """Saving without a simulated step should leave the grid untouched."""
    create_app()
    from dash_app.pages.run_manager import save_current_run

    monkeypatch.setattr(app_state, "get_model", lambda: SimpleNamespace(current_step=0))

    refresh_value, toast_open, toast_text = save_current_run(1)

    assert refresh_value is no_update
    assert toast_open is True
    assert "No simulation to save" in toast_text
