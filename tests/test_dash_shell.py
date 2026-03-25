"""Tests for Dash shell helpers and page callbacks."""

from types import SimpleNamespace

import pandas as pd
from dash import dcc, no_update

import dash_app.db as db
import dash_app.state as app_state
from dash_app.app import _resolve_sidebar_toggle, create_app
from dash_app.components.sidebar import sidebar
from dash_app.utils import format_run_label


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


def test_sidebar_keeps_simulation_controls_mounted() -> None:
    """Navigation should hide sidebar controls rather than recreating them."""
    component = sidebar()
    sidebar_controls = component.children[1]

    assert sidebar_controls.id == "sidebar-controls"
    assert sidebar_controls.children


def test_app_layout_exposes_session_store_for_llm_studio() -> None:
    """LLM Studio state should live in a root-level session store."""
    layout = create_app().layout
    llm_store = next(
        child for child in layout.children
        if isinstance(child, dcc.Store) and child.id == "llm-studio-store"
    )

    assert llm_store.storage_type == "session"
    assert llm_store.data == {}


def test_llm_studio_parser_input_uses_session_persistence() -> None:
    """Scenario Parser textarea should preserve draft text across page remounts."""
    create_app()
    from dash_app.pages import llm_studio

    scenario_tab = llm_studio._tab_scenario()
    textarea = scenario_tab.children[0].children[0].children[0]

    assert textarea.id == "scenario-input"
    assert textarea.persistence is True
    assert textarea.persistence_type == "session"


def test_llm_studio_rehydrates_active_tab_and_scenario_result() -> None:
    """Stored LLM Studio state should rebuild the active tab and parser result card."""
    create_app()
    from dash_app.pages import llm_studio

    store_data = {
        "active_tab": "tab-chat",
        "scenario": {
            "description": "Independent households with occasional outsourcing.",
            "status": "success",
            "error": None,
            "elapsed": 1.23,
            "model": "qwen3.5:4b",
            "result": {
                "scenario_summary": "Residents mostly self-serve and delegate only when busy.",
                "reasoning": "Low delegation and low conformity imply an autonomy-oriented setting.",
                "delegation_preference_mean": 0.1,
                "service_cost_factor": 0.5,
                "social_conformity_pressure": 0.0,
                "tasks_per_step_mean": 3.0,
                "num_agents": 100,
            },
        },
    }

    state = llm_studio._normalize_llm_studio_state(store_data)
    panel = llm_studio._build_scenario_output(state["scenario"])

    assert llm_studio.restore_llm_studio_tab({"mounted": True}, store_data) == "tab-chat"
    assert panel.className == "cp-card"

    header = panel.children[0]
    title_wrap = header.children[0]
    assert title_wrap.children[0].children == "Parsed Parameters"
    assert title_wrap.children[1].children == "1.2s · qwen3.5:4b"

    body = panel.children[1]
    assert body.children[0].children == (
        "Residents mostly self-serve and delegate only when busy."
    )
    table = body.children[2]
    first_row = table.children.children[0]
    assert first_row.children[0].children == "Delegation Preference Mean"
    assert first_row.children[1].children == "0.1"


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

    refresh_value, toast_open, toast_text, input_value = save_current_run(1, "Policy Stress Test")

    assert refresh_value == 17
    assert toast_open is True
    assert "Run saved as ID 17" in toast_text
    assert "Policy Stress Test" in toast_text
    assert input_value == ""
    assert saved_call["label"] == "Policy Stress Test"
    assert saved_call["preset"] == "type_b"
    assert saved_call["run_id"] == "17"


def test_save_current_run_rejects_empty_models(monkeypatch) -> None:
    """Saving without a simulated step should leave the grid untouched."""
    create_app()
    from dash_app.pages.run_manager import save_current_run

    monkeypatch.setattr(app_state, "get_model", lambda: SimpleNamespace(current_step=0))

    refresh_value, toast_open, toast_text, input_value = save_current_run(1, "Ignored")

    assert refresh_value is no_update
    assert toast_open is True
    assert "No simulation to save" in toast_text
    assert input_value is no_update


def test_save_current_run_falls_back_to_default_name(monkeypatch) -> None:
    """Blank custom names should fall back to the default dashboard label."""
    create_app()
    from dash_app.pages.run_manager import save_current_run

    saved_call: dict[str, object] = {}

    def fake_save_run(model, label=None, preset=None):
        saved_call["label"] = label
        saved_call["preset"] = preset
        return 23

    monkeypatch.setattr(app_state, "get_model", lambda: SimpleNamespace(current_step=8))
    monkeypatch.setattr(app_state, "get_current_preset", lambda: "custom")
    monkeypatch.setattr(app_state, "set_run_id", lambda rid: saved_call.setdefault("run_id", rid))
    monkeypatch.setattr(db, "save_run", fake_save_run)

    _, _, _, input_value = save_current_run(1, "   ")

    assert saved_call["label"] == "Dashboard run (step 8)"
    assert input_value == ""


def test_update_run_names_persists_only_changed_rows(monkeypatch) -> None:
    """Only edited Run Name values should be written on Update."""
    create_app()
    from dash_app.pages.run_manager import update_run_names

    captured_updates: list[tuple[int, str | None]] = []

    monkeypatch.setattr(
        db,
        "update_run_labels",
        lambda updates: captured_updates.extend(updates) or len(updates),
    )

    rows = [
        {"id": 11, "label": "Saved Run", "run_name": "Saved Run"},
        {"id": 12, "label": None, "run_name": "Experiment B"},
        {
            "id": 13,
            "label": "Long descriptive run label for charting",
            "run_name": "Long descriptive run label for charting",
        },
    ]

    refresh_value, toast_open, toast_text = update_run_names(1, rows)

    assert refresh_value is not no_update
    assert toast_open is True
    assert toast_text == "Updated 1 run name(s)."
    assert captured_updates == [(12, "Experiment B")]


def test_list_runs_keeps_full_editable_names_for_long_labels(monkeypatch, tmp_path) -> None:
    """Editable grid rows should keep full labels instead of truncated display text."""
    tmp_db = tmp_path / "runs.db"
    original_init_db = db.init_db
    original_get_conn = db._get_conn

    monkeypatch.setattr(db, "init_db", lambda db_path=db.DEFAULT_DB_PATH: original_init_db(str(tmp_db)))
    monkeypatch.setattr(db, "_get_conn", lambda db_path=db.DEFAULT_DB_PATH: original_get_conn(str(tmp_db)))

    db.init_db()
    conn = db._get_conn()
    try:
        conn.execute(
            """
            INSERT INTO runs (
                label, preset, params_json, steps_run,
                final_avg_stress, final_avg_delegation_rate,
                final_total_labor_hours, final_social_efficiency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Long descriptive run label for charting",
                "custom",
                "{}",
                50,
                0.01,
                0.5,
                400.0,
                0.55,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    rows = db.list_runs()

    assert rows[0]["run_name"] == "Long descriptive run label for charting"
    assert rows[0]["run_name_display"] == format_run_label(rows[0])


def test_update_run_names_ignores_unchanged_grid_rows() -> None:
    """Update should no-op when the editable column has not changed."""
    create_app()
    from dash_app.pages.run_manager import update_run_names

    rows = [
        {"id": 14, "label": None, "run_name": "Run 14"},
        {"id": 15, "label": "Named run", "run_name": "Named run"},
    ]

    refresh_value, toast_open, toast_text = update_run_names(1, rows)

    assert refresh_value is no_update
    assert toast_open is True
    assert toast_text == "No Run Name changes to update."


def test_simulation_page_rehydrates_dashboard_from_server_state(monkeypatch) -> None:
    """Returning to the dashboard page should redraw figures from the live model."""
    create_app()
    from dash_app.pages.simulation import update_kpis, update_time_series

    model_df = pd.DataFrame(
        [
            {
                "avg_stress": 0.012,
                "total_labor_hours": 424.7,
                "social_efficiency": 0.565,
                "gini_income": 0.201,
                "avg_delegation_rate": 0.514,
                "unmatched_tasks": 3,
                "tasks_delegated_frac": 0.51,
            }
        ]
    )
    fake_model = SimpleNamespace(
        current_step=100,
        get_model_dataframe=lambda: model_df,
    )
    monkeypatch.setattr(app_state, "get_model", lambda: fake_model)

    stress, labor, efficiency, gini = update_kpis(None, {"mounted": True})
    labor_fig, stress_deleg_fig, efficiency_fig, market_fig = update_time_series(
        None,
        {"mounted": True},
    )

    assert (stress, labor, efficiency, gini) == ("0.012", "424.7", "0.565", "0.201")
    assert list(labor_fig.data[0].y) == [424.7]
    assert labor_fig.layout.xaxis.title.text == "Step"
    assert list(stress_deleg_fig.data[0].y) == [0.012]
    assert list(stress_deleg_fig.data[1].y) == [0.514]
    assert list(efficiency_fig.data[0].y) == [0.565]
    assert list(market_fig.data[0].y) == [3]
    assert list(market_fig.data[1].y) == [0.51]
