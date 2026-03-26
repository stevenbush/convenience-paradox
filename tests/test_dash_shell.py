"""Tests for Dash shell helpers and page callbacks."""

import sys
from types import SimpleNamespace

import pandas as pd
from dash import dcc, no_update

import dash_app.db as db
import dash_app.state as app_state
from dash_app.app import _resolve_sidebar_toggle, create_app
from dash_app.components.controls import simulation_controls
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
    nav = component.children[0]
    sidebar_controls = component.children[1]

    assert sidebar_controls.id == "sidebar-controls"
    assert sidebar_controls.children
    assert "cp-sidebar__nav" in nav.className


def test_simulation_actions_render_before_parameter_sections() -> None:
    """High-frequency simulation buttons should appear near the top of the sidebar."""
    controls = simulation_controls()

    section_titles = [
        child.children[0].children
        for child in controls.children
        if getattr(child, "children", None)
        and isinstance(child.children, list)
        and getattr(child.children[0], "className", "") == "cp-controls__section-title"
    ]

    assert section_titles[:2] == ["PRESET", "SIMULATION"]


def test_app_layout_exposes_memory_store_for_llm_studio() -> None:
    """LLM Studio state should live in root-level memory stores."""
    layout = create_app().layout
    llm_store = next(
        child for child in layout.children
        if isinstance(child, dcc.Store) and child.id == "llm-studio-store"
    )

    assert llm_store.storage_type == "memory"
    assert llm_store.data == {}
    scenario_queue = next(
        child for child in layout.children
        if isinstance(child, dcc.Store) and child.id == "scenario-parse-request-store"
    )
    assert scenario_queue.data is None
    chat_store = next(
        child for child in layout.children
        if isinstance(child, dcc.Store) and child.id == "chat-history-store"
    )
    assert chat_store.storage_type == "memory"
    assert chat_store.data == {}
    chat_queue = next(
        child for child in layout.children
        if isinstance(child, dcc.Store) and child.id == "chat-interpret-request-store"
    )
    assert chat_queue.data is None
    profile_store = next(
        child for child in layout.children
        if isinstance(child, dcc.Store) and child.id == "profile-history-store"
    )
    assert profile_store.storage_type == "memory"
    assert profile_store.data == {}
    profile_queue = next(
        child for child in layout.children
        if isinstance(child, dcc.Store) and child.id == "profile-generate-request-store"
    )
    assert profile_queue.data is None
    annotation_store = next(
        child for child in layout.children
        if isinstance(child, dcc.Store) and child.id == "annotation-history-store"
    )
    assert annotation_store.storage_type == "memory"
    assert annotation_store.data == {}
    annotation_queue = next(
        child for child in layout.children
        if isinstance(child, dcc.Store) and child.id == "annotation-annotate-request-store"
    )
    assert annotation_queue.data is None
    audit_snapshot = next(
        child for child in layout.children
        if isinstance(child, dcc.Store) and child.id == "audit-trigger-store"
    )
    assert audit_snapshot.data == []


def test_llm_studio_parser_input_uses_memory_persistence() -> None:
    """Scenario Parser textarea should preserve drafts during navigation only."""
    create_app()
    from dash_app.pages import llm_studio

    scenario_tab = llm_studio._tab_scenario()
    intro = scenario_tab.children[0]
    workspace_row = scenario_tab.children[1]
    conversation_col = workspace_row.children[0]
    conversation_card = conversation_col.children[0]
    card_body = conversation_card.children[1]
    textarea = card_body.children[1].children[0]
    actions = card_body.children[1].children[1]

    assert intro.className == "cp-scenario-guide"
    assert "cp-llm-workspace" in workspace_row.className
    assert "cp-llm-workspace__col" in conversation_col.className
    assert "cp-llm-workspace__card--conversation" in conversation_card.className
    assert textarea.id == "scenario-input"
    assert "Describe daily life" in textarea.placeholder
    assert textarea.persistence is True
    assert textarea.persistence_type == "memory"
    assert textarea.submit_on_enter is True
    assert card_body.children[0].id == "scenario-thread"
    assert actions.children[0].id == "btn-parse-scenario"
    assert actions.children[1].id == "btn-clear-scenario"
    assert actions.children[1].children[1] == "Clear Conversation"


def test_llm_studio_chat_tab_uses_conversation_layout() -> None:
    """Chat Interpreter should mirror the Scenario Parser conversation layout."""
    create_app()
    from dash_app.pages import llm_studio

    chat_tab = llm_studio._tab_chat()
    intro = chat_tab.children[0]
    workspace_row = chat_tab.children[1]
    conversation_col = workspace_row.children[0]
    conversation_card = conversation_col.children[0]
    card_body = conversation_card.children[1]
    textarea = card_body.children[1].children[0]
    actions = card_body.children[1].children[1]

    assert intro.className == "cp-scenario-guide"
    assert "cp-llm-workspace" in workspace_row.className
    assert "cp-llm-workspace__col" in conversation_col.className
    assert "cp-llm-workspace__card--conversation" in conversation_card.className
    assert card_body.children[0].id == "chat-thread"
    assert textarea.id == "chat-input"
    assert textarea.persistence is True
    assert textarea.persistence_type == "memory"
    assert textarea.submit_on_enter is True
    assert actions.children[0].id == "btn-chat-send"
    assert actions.children[1].id == "btn-clear-chat"


def test_llm_studio_profile_tab_uses_conversation_layout() -> None:
    """Profile Generator should mirror the Scenario Parser conversation layout."""
    create_app()
    from dash_app.pages import llm_studio

    profile_tab = llm_studio._tab_profile()
    intro = profile_tab.children[0]
    workspace_row = profile_tab.children[1]
    conversation_col = workspace_row.children[0]
    conversation_card = conversation_col.children[0]
    card_body = conversation_card.children[1]
    textarea = card_body.children[1].children[0]
    actions = card_body.children[1].children[1]
    prompt_strip = intro.children[2]
    prompt_row = prompt_strip.children[1]

    assert intro.className == "cp-scenario-guide"
    assert "cp-llm-workspace" in workspace_row.className
    assert "cp-llm-workspace__col" in conversation_col.className
    assert "cp-llm-workspace__card--conversation" in conversation_card.className
    assert prompt_strip.className == "cp-profile__prompt-strip"
    assert prompt_row.className == "cp-profile__prompt-row"
    assert prompt_row.children[0].id == "btn-profile-prompt-busy"
    assert prompt_row.children[1].id == "btn-profile-prompt-self-serve"
    assert prompt_row.children[2].id == "btn-profile-prompt-coordinator"
    assert card_body.children[0].id == "profile-thread"
    assert textarea.id == "profile-input"
    assert textarea.persistence is True
    assert textarea.persistence_type == "memory"
    assert textarea.submit_on_enter is True
    assert actions.children[0].id == "btn-generate-profile"
    assert actions.children[1].id == "btn-clear-profile"
    assert actions.children[1].children[1] == "Clear Conversation"


def test_llm_studio_annotations_tab_uses_guided_workspace_layout() -> None:
    """Annotations should expose a compact guide plus annotate and clear actions."""
    create_app()
    from dash_app.pages import llm_studio

    annotations_tab = llm_studio._tab_annotations()
    intro = annotations_tab.children[0]
    actions = annotations_tab.children[1]
    output = annotations_tab.children[2]

    assert intro.className == "cp-scenario-guide"
    assert intro.children[0].children == "How To Use Annotations"
    assert "Visualization Annotator" in intro.children[1].children
    assert "cp-scenario__composer-actions" in actions.className
    assert actions.children[0].id == "btn-annotate-charts"
    assert actions.children[1].id == "btn-clear-annotations"
    assert output.id == "annotations-output"


def test_llm_studio_audit_tab_uses_guided_workspace_layout() -> None:
    """Audit Log should expose guidance, actions, table slot, and detail inspector slot."""
    create_app()
    from dash_app.pages import llm_studio

    audit_tab = llm_studio._tab_audit()
    intro = audit_tab.children[0]
    actions = audit_tab.children[1]
    table_slot = audit_tab.children[2]
    detail_slot = audit_tab.children[3]

    assert intro.className == "cp-scenario-guide"
    assert intro.children[0].children == "How To Use Audit Log"
    assert "session-level trail" in intro.children[1].children
    assert "cp-scenario__composer-actions" in actions.className
    assert actions.children[0].id == "btn-refresh-audit"
    assert actions.children[1].id == "btn-clear-audit"
    assert table_slot.id == "audit-log-content"
    assert detail_slot.id == "audit-log-detail"


def test_model_configuration_is_collapsed_by_default() -> None:
    """Model Configuration should default to collapsed to save vertical space."""
    create_app()
    from dash_app.pages import llm_studio

    panel = llm_studio._model_config_panel()
    collapse = panel.children[1]

    assert collapse.id == "model-config-collapse"
    assert collapse.is_open is False


def test_llm_studio_layout_includes_remount_interval() -> None:
    """The page should include a mount interval that retriggers rehydration after navigation."""
    create_app()
    from dash_app.pages import llm_studio

    page_layout = llm_studio.layout()
    mount_interval = page_layout.children[0]

    assert mount_interval.id == "llm-studio-mount-interval"
    assert mount_interval.max_intervals == 1
    assert mount_interval.interval == 50


def test_llm_studio_refreshes_models_on_page_mount(monkeypatch) -> None:
    """Available Ollama models should populate role selectors on initial page load."""
    create_app()
    from dash_app.pages import llm_studio

    fake_models = SimpleNamespace(
        models=[
            SimpleNamespace(model="qwen3.5:4b"),
            SimpleNamespace(model="qwen3:1.7b"),
        ]
    )
    monkeypatch.setitem(sys.modules, "ollama", SimpleNamespace(list=lambda: fake_models))

    outputs = llm_studio.refresh_models({"mounted": True}, None)

    options = outputs[0]
    values = outputs[5:10]
    statuses = outputs[10:15]

    assert {"label": "qwen3.5:4b", "value": "qwen3.5:4b"} in options
    assert values[0] == "qwen3.5:4b"
    assert values[1] == "qwen3:1.7b"
    assert all(status == "cp-status-dot cp-status-dot--online" for status in statuses)


def test_model_config_summary_shows_role_model_chips() -> None:
    """Collapsed header should expose compact per-role model status chips."""
    create_app()
    from dash_app.pages import llm_studio

    summary = llm_studio._build_model_config_summary(
        {
            "role_1": "qwen3.5:4b",
            "role_2": "qwen3:1.7b",
            "role_3": "qwen3.5:4b",
            "role_4": "qwen3.5:4b",
            "role_5": "qwen3.5:4b",
        },
        {role: "cp-status-dot cp-status-dot--online" for role, *_ in llm_studio.ROLES},
    )

    assert summary.className == "cp-model-summary__list"
    first_chip = summary.children[0]
    assert first_chip.className == "cp-model-summary__chip"
    assert first_chip.children[1].children == "R1"
    assert first_chip.children[2].children == "qwen3.5:4b"


def test_model_config_summary_shows_neutral_state_when_no_models_available() -> None:
    """Collapsed header should make a lack of local models obvious."""
    create_app()
    from dash_app.pages import llm_studio

    summary = llm_studio._build_model_config_summary(
        {role: "" for role, *_ in llm_studio.ROLES},
        {role: "cp-status-dot cp-status-dot--offline" for role, *_ in llm_studio.ROLES},
    )

    assert summary.className == "cp-badge cp-badge--neutral"
    assert summary.children == "No local LLM model available"


def test_llm_studio_stages_pending_scenario_request() -> None:
    """Submitting a scenario should create a user turn and a pending assistant turn."""
    create_app()
    from dash_app.pages import llm_studio

    state = llm_studio._stage_scenario_request(
        {},
        "Independent households with occasional outsourcing.",
        "qwen3.5:4b",
        "req-1",
    )

    scenario_state = state["scenario"]
    assert scenario_state["status"] == "pending"
    assert scenario_state["request_id"] == "req-1"
    assert len(scenario_state["history"]) == 2
    assert scenario_state["history"][0]["role"] == "user"
    assert scenario_state["history"][1]["status"] == "pending"


def test_llm_studio_ignores_replayed_scenario_button_click(monkeypatch) -> None:
    """A remounted page should not treat the previous Parse click as a new request."""
    create_app()
    from dash_app.pages import llm_studio
    monkeypatch.setattr(llm_studio, "ctx", SimpleNamespace(triggered_id="btn-parse-scenario"))

    staged_state = llm_studio._stage_scenario_request(
        {},
        "Independent households with occasional outsourcing.",
        "qwen3.5:4b",
        "req-1",
    )
    staged_state["scenario"]["last_parse_clicks"] = 1

    result = llm_studio.stage_scenario_request(
        1,
        0,
        "Independent households with occasional outsourcing.",
        staged_state,
    )

    assert result == (no_update, no_update, no_update)


def test_llm_studio_clear_resets_scenario_conversation() -> None:
    """Clear should wipe the transcript and inspector so the user can start over."""
    create_app()
    from dash_app.pages import llm_studio

    pending_state = llm_studio._stage_scenario_request(
        {},
        "A busy society that outsources household tasks.",
        "qwen3.5:4b",
        "req-clear",
    )
    store_data = llm_studio._complete_scenario_request(
        pending_state,
        "req-clear",
        "qwen3.5:4b",
        1.1,
        result={
            "scenario_summary": "Residents delegate routine work when schedules become tight.",
            "reasoning": "Moderate delegation and workload pressure fit an outsourcing-heavy system.",
            "delegation_preference_mean": 0.65,
            "service_cost_factor": 0.35,
            "social_conformity_pressure": 0.4,
            "tasks_per_step_mean": 3.5,
            "num_agents": 100,
        },
        raw_response='{"scenario_summary":"Residents delegate routine work when schedules become tight."}',
    )

    cleared_state, cleared_input = llm_studio.clear_scenario_conversation(1, store_data)

    assert cleared_input == ""
    scenario_state = cleared_state["scenario"]
    assert scenario_state["status"] == "idle"
    assert scenario_state["history"] == []
    assert scenario_state["result"] is None
    assert scenario_state["raw_response"] is None
    assert scenario_state["last_clear_clicks"] == 1


def test_llm_studio_stages_pending_chat_request() -> None:
    """Submitting a chat question should create a user turn and pending interpreter turn."""
    create_app()
    from dash_app.pages import llm_studio

    context = {
        "initialized": True,
        "current_step": 24,
        "preset": "custom",
        "note": "This snapshot is injected into the interpreter prompt together with your question.",
        "latest_metrics": {"avg_stress": 0.21, "avg_delegation_rate": 0.58},
        "params": {"delegation_preference_mean": 0.55, "service_cost_factor": 0.4},
    }

    state = llm_studio._stage_chat_request(
        {},
        "Why is stress rising now?",
        "qwen3.5:4b",
        "chat-1",
        context,
    )

    chat_state = llm_studio._normalize_chat_state(state)
    assert chat_state["status"] == "pending"
    assert chat_state["request_id"] == "chat-1"
    assert chat_state["context"]["current_step"] == 24
    assert len(chat_state["history"]) == 2
    assert chat_state["history"][0]["role"] == "user"
    assert chat_state["history"][1]["status"] == "pending"


def test_llm_studio_ignores_replayed_chat_button_click(monkeypatch) -> None:
    """A remounted page should not treat the previous Ask click as a new request."""
    create_app()
    from dash_app.pages import llm_studio
    monkeypatch.setattr(llm_studio, "ctx", SimpleNamespace(triggered_id="btn-chat-send"))

    state = llm_studio._stage_chat_request(
        {"last_send_clicks": 1},
        "Why is stress rising now?",
        "qwen3.5:4b",
        "chat-1",
        {
            "initialized": True,
            "current_step": 24,
            "preset": "custom",
            "note": "This snapshot is injected into the interpreter prompt together with your question.",
            "latest_metrics": {"avg_stress": 0.21},
            "params": {"delegation_preference_mean": 0.55},
        },
    )

    result = llm_studio.stage_chat_request(1, 0, "Why is stress rising now?", state)

    assert result == (no_update, no_update, no_update)


def test_llm_studio_stages_pending_profile_request() -> None:
    """Submitting a profile description should create a user turn and pending generator turn."""
    create_app()
    from dash_app.pages import llm_studio

    state = llm_studio._stage_profile_request(
        {},
        "A busy dual-income household that outsources chores but handles paperwork well.",
        "qwen3.5:4b",
        "profile-1",
    )

    profile_state = llm_studio._normalize_profile_state(state)
    assert profile_state["status"] == "pending"
    assert profile_state["request_id"] == "profile-1"
    assert len(profile_state["history"]) == 2
    assert profile_state["history"][0]["role"] == "user"
    assert profile_state["history"][1]["status"] == "pending"


def test_llm_studio_ignores_replayed_profile_button_click(monkeypatch) -> None:
    """A remounted page should not treat the previous Generate click as a new request."""
    create_app()
    from dash_app.pages import llm_studio
    monkeypatch.setattr(llm_studio, "ctx", SimpleNamespace(triggered_id="btn-generate-profile"))

    state = llm_studio._stage_profile_request(
        {"last_generate_clicks": 1},
        "A busy dual-income household that outsources chores but handles paperwork well.",
        "qwen3.5:4b",
        "profile-1",
    )

    result = llm_studio.stage_profile_request(
        1,
        0,
        "A busy dual-income household that outsources chores but handles paperwork well.",
        state,
    )

    assert result == (no_update, no_update, no_update)


def test_llm_studio_profile_prompt_map_returns_expected_text() -> None:
    """Suggested prompt buttons should map to full profile descriptions."""
    create_app()
    from dash_app.pages import llm_studio

    assert "time-constrained professional" in llm_studio._profile_prompt_text("btn-profile-prompt-busy")
    assert "self-reliant resident" in llm_studio._profile_prompt_text("btn-profile-prompt-self-serve")
    assert "household coordinator" in llm_studio._profile_prompt_text("btn-profile-prompt-coordinator")
    assert llm_studio._profile_prompt_text("btn-profile-prompt-missing") is None


def test_llm_studio_chat_context_panel_shows_current_snapshot() -> None:
    """Chat Interpreter should show the grounded simulation snapshot being interpreted."""
    create_app()
    from dash_app.pages import llm_studio

    context = {
        "initialized": True,
        "current_step": 18,
        "preset": "type_b",
        "note": "This snapshot is injected into the interpreter prompt together with your question.",
        "latest_metrics": {
            "avg_stress": 0.18,
            "avg_delegation_rate": 0.74,
            "total_labor_hours": 411.2,
        },
        "params": {
            "delegation_preference_mean": 0.72,
            "service_cost_factor": 0.2,
            "social_conformity_pressure": 0.65,
            "tasks_per_step_mean": 3.5,
            "num_agents": 100,
            "network_type": "small_world",
        },
    }
    pending_state = llm_studio._stage_chat_request(
        {},
        "What does this run suggest?",
        "qwen3.5:4b",
        "chat-ctx",
        context,
    )
    store_data = llm_studio._complete_chat_request(
        pending_state,
        "chat-ctx",
        "qwen3.5:4b",
        1.4,
        context_snapshot=context,
        result={
            "answer": "The run suggests delegation is outpacing well-being gains.",
            "detailed_explanation": "Stress remains elevated while labor hours stay high, which points to coordination costs.",
            "hypothesis_connection": "H1",
            "confidence_note": "This is still an early-stage run.",
        },
    )

    chat_state = llm_studio._normalize_chat_state(store_data)
    thread = llm_studio._build_chat_thread(chat_state)
    context_panel = llm_studio._build_chat_context_panel(chat_state)

    assert thread.className == "cp-chat"
    assert "cp-card" in context_panel.className
    assert "cp-llm-workspace__card--inspector" in context_panel.className
    header = context_panel.children[0]
    title_wrap = header.children[0]
    assert title_wrap.children[0].children == "Current Interpretation Context"

    body = context_panel.children[1]
    summary_grid = body.children[1]
    assert summary_grid.className == "cp-chat-context__grid"
    assert summary_grid.children[0].children[0].children == "Current Step"
    assert summary_grid.children[0].children[1].children == "18"
    assert body.children[2].children.startswith("This snapshot is injected")
    metrics_grid = body.children[4]
    assert metrics_grid.className == "cp-chat-context__grid"
    assert metrics_grid.children[0].children[0].children == "Avg Stress"
    params_grid = body.children[6]
    assert params_grid.className == "cp-chat-context__grid"
    assert params_grid.children[0].children[0].children == "Delegation Mean"
    assert body.children[7].children == "Prompt Context"
    assert "context JSON" in body.children[8].children[0].children


def test_llm_studio_profile_output_shows_generated_agent_type() -> None:
    """Profile Generator inspector should show summary, skills, and parameter meanings."""
    create_app()
    from dash_app.pages import llm_studio

    pending_state = llm_studio._stage_profile_request(
        {},
        "A time-constrained professional who outsources chores but manages admin tasks well.",
        "qwen3.5:4b",
        "profile-ready",
    )
    store_data = llm_studio._complete_profile_request(
        pending_state,
        "profile-ready",
        "qwen3.5:4b",
        1.2,
        result={
            "profile_description": "A service-comfortable professional who saves time by outsourcing home tasks.",
            "delegation_preference": 0.72,
            "skill_domestic": 0.41,
            "skill_administrative": 0.78,
            "skill_errand": 0.65,
            "skill_maintenance": 0.38,
        },
        raw_response='{"profile_description":"A service-comfortable professional who saves time by outsourcing home tasks."}',
    )

    profile_state = llm_studio._normalize_profile_state(store_data)
    thread = llm_studio._build_profile_thread(profile_state)
    panel = llm_studio._build_profile_output(profile_state)

    assert thread.className == "cp-chat"
    assert "cp-card" in panel.className
    assert "cp-llm-workspace__card--inspector" in panel.className

    header = panel.children[0]
    title_wrap = header.children[0]
    assert title_wrap.children[0].children == "Generated Agent Type"
    assert title_wrap.children[1].children == "1.2s · qwen3.5:4b"

    body = panel.children[1]
    assert body.children[1].children == "Agent Type Summary"
    assert "service-comfortable professional" in body.children[2].children
    summary_grid = body.children[3]
    assert summary_grid.className == "cp-chat-context__grid"
    assert summary_grid.children[0].children[0].children == "Delegation Style"
    assert body.children[4].children == "Skill Profile"
    assert "Graph" in type(body.children[5].children[0].children).__name__
    assert body.children[6].children == "Parameter Breakdown"
    param_grid = body.children[7]
    assert param_grid.className == "cp-chat-context__grid"
    assert param_grid.children[0].children[0].children == "Delegation Preference"
    assert "outsource tasks" in param_grid.children[0].children[2].children
    assert body.children[8].children == "How To Use This Agent Type"
    assert "simulation-ready agent type" in body.children[9].children
    assert body.children[10].children == "Raw LLM Output"
    assert "raw profile JSON" in body.children[11].children[0].children


def test_llm_studio_stages_pending_annotation_cards(monkeypatch) -> None:
    """Annotate All Charts should immediately stage chart previews and pending states."""
    create_app()
    from dash_app.pages import llm_studio

    monkeypatch.setattr(
        llm_studio,
        "_build_annotation_snapshot",
        lambda: {
            "initialized": True,
            "current_step": 12,
            "preset": "custom",
            "model": "qwen3.5:4b",
            "note": "Injected chart summaries.",
            "items": [
                {
                    "chart_key": "total_labor_hours",
                    "chart_label": "Total Labor Hours (H1)",
                    "chart_subtitle": "System-wide labor demand over time",
                    "chart_description": "Shows whether delegation raises aggregate labor.",
                    "metrics": {"last": 42.0, "mean": 36.4, "trend": "rising", "steps": 12},
                    "summary_metrics": [
                        {"label": "Latest", "value": 42.0},
                        {"label": "Mean", "value": 36.4},
                        {"label": "Trend", "value": "Rising"},
                        {"label": "Steps", "value": 12},
                    ],
                    "preview": {
                        "kind": "line",
                        "steps": [0, 1, 2],
                        "traces": [
                            {"type": "line", "name": "Labor Hours", "values": [24.0, 31.0, 42.0], "color": "#2C8C99"}
                        ],
                    },
                    "status": "pending",
                    "caption": None,
                    "key_insight": None,
                    "chart_title": None,
                    "hypothesis_tag": None,
                    "elapsed": None,
                    "model": None,
                    "error": None,
                }
            ],
        },
    )

    state, request = llm_studio.annotate_charts_cb(1, {})

    assert state["status"] == "pending"
    assert state["current_step"] == 12
    assert state["items"][0]["status"] == "pending"
    assert request["request_id"] == state["request_id"]
    assert request["items"][0]["chart_key"] == "total_labor_hours"


def test_llm_studio_annotations_rehydrate_from_memory_state() -> None:
    """Annotations should rebuild the chart workspace from the in-memory store."""
    create_app()
    from dash_app.pages import llm_studio

    state = {
        "status": "success",
        "current_step": 18,
        "preset": "custom",
        "model": "qwen3.5:4b",
        "note": "Injected chart summaries.",
        "items": [
            {
                "chart_key": "total_labor_hours",
                "chart_label": "Total Labor Hours (H1)",
                "chart_subtitle": "System-wide labor demand over time",
                "chart_description": "Shows whether delegation raises aggregate labor.",
                "chart_title": "Labor Hours Keep Rising",
                "hypothesis_tag": "H1",
                "caption": "Labor demand keeps climbing as delegation expands.",
                "key_insight": "Service convenience increases total system work.",
                "metrics": {"last": 42.0, "mean": 36.4, "trend": "rising", "steps": 18},
                "summary_metrics": [
                    {"label": "Latest", "value": 42.0},
                    {"label": "Mean", "value": 36.4},
                    {"label": "Trend", "value": "Rising"},
                    {"label": "Steps", "value": 18},
                ],
                "preview": {
                    "kind": "line",
                    "steps": [0, 1, 2],
                    "traces": [
                        {"type": "line", "name": "Labor Hours", "values": [24.0, 31.0, 42.0], "color": "#2C8C99"}
                    ],
                },
                "elapsed": 1.4,
                "model": "qwen3.5:4b",
                "status": "success",
            }
        ],
    }

    rendered = llm_studio.render_annotations_output(state, 1)

    assert rendered.children[1].className == "cp-chat-context__grid"
    assert rendered.children[3].className == "cp-annotation__list"
    annotation_card = rendered.children[3].children[0]
    assert "cp-annotation__card" in annotation_card.className
    header = annotation_card.children[0]
    title_wrap = header.children[0]
    assert title_wrap.children[0].children == "Total Labor Hours (H1)"
    body = annotation_card.children[1].children
    assert body.className == "cp-annotation__body"
    analysis = body.children[1]
    assert analysis.children[1].children == "Labor Hours Keep Rising"
    assert "Labor demand keeps climbing" in analysis.children[2].children
    assert "Service convenience increases total system work." in analysis.children[3].children[1]


def test_llm_studio_ignores_replayed_annotation_click(monkeypatch) -> None:
    """A remounted page should not retrigger chart annotation for the same button click."""
    create_app()
    from dash_app.pages import llm_studio

    called = {"value": False}

    def fake_snapshot():
        called["value"] = True
        return {"initialized": True, "items": []}

    monkeypatch.setattr(llm_studio, "_build_annotation_snapshot", fake_snapshot)

    result = llm_studio.annotate_charts_cb(
        1,
        {"status": "success", "items": [], "last_annotate_clicks": 1},
    )

    assert result == (no_update, no_update)
    assert called["value"] is False


def test_llm_studio_ignores_annotation_click_while_request_is_pending(monkeypatch) -> None:
    """A second click should not queue a new annotation request while one is already running."""
    create_app()
    from dash_app.pages import llm_studio

    called = {"value": False}

    def fake_snapshot():
        called["value"] = True
        return {"initialized": True, "items": []}

    monkeypatch.setattr(llm_studio, "_build_annotation_snapshot", fake_snapshot)

    result = llm_studio.annotate_charts_cb(
        2,
        {"status": "pending", "request_id": "req-123", "items": [], "last_annotate_clicks": 1},
    )

    assert result == (no_update, no_update)
    assert called["value"] is False


def test_llm_studio_record_audit_keeps_raw_input_and_output() -> None:
    """Session audit entries should retain inspectable raw input/output payloads."""
    create_app()
    from dash_app.pages import llm_studio

    app_state.clear_audit_log()
    llm_studio._record_audit(
        "Role 1",
        "scenario_parser",
        "qwen3.5:4b",
        "Busy households rely on services.",
        {"delegation_preference_mean": 0.6},
        1.4,
        input_payload={"user_prompt": "Busy households rely on services."},
        output_payload={"raw_response": "{\"delegation_preference_mean\": 0.6}"},
    )

    entry = app_state.get_audit_log()[-1]

    assert entry["input_payload"]["user_prompt"] == "Busy households rely on services."
    assert entry["output_payload"]["raw_response"] == "{\"delegation_preference_mean\": 0.6}"


def test_llm_studio_audit_log_table_exposes_inspect_action() -> None:
    """Rendered audit rows should include an inspect button for opening raw payload details."""
    create_app()
    from dash_app.pages import llm_studio

    table = llm_studio._build_audit_log_table([
        {
            "timestamp": "15:32:06",
            "role": "Role 1",
            "call_kind": "scenario_parser",
            "model": "qwen3.5:4b",
            "elapsed": 7.8,
            "status": "success",
            "prompt_preview": "Busy households rely on services.",
        }
    ])

    row = table.children[1].children[0]
    inspect_button = row.children[7].children

    assert inspect_button.id == {"type": "audit-view-btn", "index": 0}
    assert inspect_button.children[1] == "Inspect"


def test_llm_studio_audit_detail_renders_original_input_and_output() -> None:
    """Selected audit entries should expose collapsible original input/output blocks."""
    create_app()
    from dash_app.pages import llm_studio

    detail = llm_studio._build_audit_detail(
        {
            "role": "Role 3",
            "call_kind": "result_interpreter",
            "model": "qwen3.5:4b",
            "timestamp": "15:32:06",
            "elapsed": 2.8,
            "status": "success",
            "prompt_preview": "Why is stress increasing?",
            "input_payload": {"user_prompt": "Why is stress increasing?"},
            "output_payload": {"raw_response": "{\"answer\": \"Stress rises with delegation.\"}"},
        }
    )

    body = detail.children[1]

    assert detail.children[0].children[0].children[0].children == "Interaction Details"
    assert "detail panel below exposes" in body.children[2].children
    assert body.children[3].children == "Original Input"
    assert body.children[4].children[0].children == "View Original Input"
    assert body.children[5].children == "Original Output"
    assert body.children[6].children[0].children == "View Original Output"


def test_llm_studio_audit_detail_handles_pattern_trigger_ids(monkeypatch) -> None:
    """Inspect buttons should work when Dash passes a dict-like triggered_id."""
    create_app()
    from dash_app.pages import llm_studio

    app_state.clear_audit_log()
    llm_studio._record_audit(
        "Role 1",
        "scenario_parser",
        "qwen3.5:4b",
        "Busy households rely on services.",
        {"delegation_preference_mean": 0.6},
        1.4,
        input_payload={"user_prompt": "Busy households rely on services."},
        output_payload={"raw_response": "{\"delegation_preference_mean\": 0.6}"},
    )
    monkeypatch.setattr(
        llm_studio,
        "ctx",
        SimpleNamespace(triggered_id={"type": "audit-view-btn", "index": 0}),
    )

    detail = llm_studio.update_audit_detail([1], 0, 0, 0, list(reversed(app_state.get_audit_log())))

    assert detail.children[0].children[0].children[0].children == "Interaction Details"
    assert "Busy households rely on services." in detail.children[0].children[0].children[1].children


def test_llm_studio_audit_detail_uses_rendered_table_snapshot(monkeypatch) -> None:
    """Inspect should stay aligned with the rows currently shown in the table."""
    create_app()
    from dash_app.pages import llm_studio

    rendered_entries = [
        {
            "role": "Role 1",
            "call_kind": "scenario_parser",
            "model": "qwen3.5:4b",
            "timestamp": "15:32:06",
            "elapsed": 1.4,
            "status": "success",
            "prompt_preview": "Older rendered row",
            "input_payload": {"user_prompt": "Older rendered row"},
            "output_payload": {"raw_response": "{\"delegation_preference_mean\": 0.6}"},
        }
    ]
    app_state.clear_audit_log()
    app_state.append_audit_entry(
        {
            "role": "Role 3",
            "call_kind": "result_interpreter",
            "model": "qwen3.5:4b",
            "timestamp": "15:33:10",
            "elapsed": 2.1,
            "status": "success",
            "prompt_preview": "Newer live row",
            "input_payload": {"user_prompt": "Newer live row"},
            "output_payload": {"raw_response": "{\"answer\": \"Newer result\"}"},
        }
    )
    monkeypatch.setattr(
        llm_studio,
        "ctx",
        SimpleNamespace(triggered_id={"type": "audit-view-btn", "index": 0}),
    )

    detail = llm_studio.update_audit_detail([1], 0, 0, 0, rendered_entries)

    assert "Older rendered row" in detail.children[0].children[0].children[1].children


def test_llm_studio_clearing_annotations_also_cancels_pending_request() -> None:
    """Clearing the workspace should reset both the history and queued request store."""
    create_app()
    from dash_app.pages import llm_studio

    cleared_state, cleared_request = llm_studio.clear_annotations_cb(
        1,
        {
            "status": "pending",
            "request_id": "req-123",
            "items": [{"chart_key": "total_labor_hours", "status": "pending"}],
            "last_annotate_clicks": 4,
        },
    )

    assert cleared_state["status"] == "idle"
    assert cleared_state["request_id"] is None
    assert cleared_state["items"] == []
    assert cleared_state["last_annotate_clicks"] == 4
    assert cleared_state["last_clear_clicks"] == 1
    assert cleared_request is None


def test_llm_studio_ignores_stale_annotation_request_after_clear() -> None:
    """A stale queued request should not repopulate the workspace after clearing."""
    create_app()
    from dash_app.pages import llm_studio

    result = llm_studio.resolve_annotation_request(
        {
            "request_id": "req-123",
            "model": "qwen3.5:4b",
            "items": [{"chart_key": "total_labor_hours", "chart_label": "Total Labor Hours (H1)", "metrics": {}}],
        },
        {
            "status": "idle",
            "request_id": None,
            "items": [],
        },
    )

    assert result == (no_update, no_update)


def test_llm_studio_annotation_snapshot_uses_dashboard_step_axis(monkeypatch) -> None:
    """Annotation previews should use the same zero-based step axis as the dashboard charts."""
    create_app()
    import pandas as pd
    from dash_app.pages import llm_studio

    class StubModel:
        current_step = 3

        @staticmethod
        def get_model_dataframe():
            return pd.DataFrame(
                {
                    "total_labor_hours": [24.0, 31.0, 42.0],
                    "avg_stress": [0.2, 0.3, 0.5],
                    "avg_delegation_rate": [0.4, 0.45, 0.5],
                    "social_efficiency": [1.1, 1.0, 0.9],
                    "unmatched_tasks": [0, 1, 2],
                    "tasks_delegated_frac": [0.25, 0.35, 0.45],
                }
            )

    monkeypatch.setattr(llm_studio.app_state, "get_model", lambda: StubModel())
    monkeypatch.setattr(llm_studio.app_state, "get_current_preset", lambda: "custom")
    monkeypatch.setattr(llm_studio.app_state, "get_role_model", lambda role: "qwen3.5:4b")

    snapshot = llm_studio._build_annotation_snapshot()

    assert snapshot["initialized"] is True
    assert snapshot["items"][0]["preview"]["steps"] == [0, 1, 2]


def test_llm_studio_rehydrates_active_tab_and_scenario_result() -> None:
    """Stored LLM Studio state should rebuild the active tab, transcript, and inspector."""
    create_app()
    from dash_app.pages import llm_studio

    pending_state = llm_studio._stage_scenario_request(
        {"active_tab": "tab-chat"},
        "Independent households with occasional outsourcing.",
        "qwen3.5:4b",
        "req-1",
    )
    store_data = llm_studio._complete_scenario_request(
        pending_state,
        "req-1",
        "qwen3.5:4b",
        1.23,
        result={
            "scenario_summary": "Residents mostly self-serve and delegate only when busy.",
            "reasoning": "Low delegation and low conformity imply an autonomy-oriented setting.",
            "delegation_preference_mean": 0.1,
            "service_cost_factor": 0.5,
            "social_conformity_pressure": 0.0,
            "tasks_per_step_mean": 3.0,
            "num_agents": 100,
        },
        raw_response='{"scenario_summary":"Residents mostly self-serve and delegate only when busy."}',
    )

    state = llm_studio._normalize_llm_studio_state(store_data)
    thread = llm_studio._build_scenario_thread(state["scenario"])
    panel = llm_studio._build_scenario_output(state["scenario"])

    assert llm_studio.restore_llm_studio_tab({"mounted": True}, store_data) == "tab-chat"
    assert thread.className == "cp-chat"
    assert "cp-card" in panel.className
    assert "cp-llm-workspace__card--inspector" in panel.className

    header = panel.children[0]
    title_wrap = header.children[0]
    assert title_wrap.children[0].children == "Latest Parsed Scenario"
    assert title_wrap.children[1].children == "1.2s · qwen3.5:4b"

    body = panel.children[1]
    assert body.children[1].children == (
        "Residents mostly self-serve and delegate only when busy."
    )
    param_grid = body.children[4]
    assert param_grid.className == "cp-chat-context__grid"
    first_chip = param_grid.children[0]
    assert first_chip.children[0].children[0].children == "Delegation Preference Mean"
    assert first_chip.children[0].children[1].children == "LLM-derived"
    assert first_chip.children[1].children == "0.1"
    assert body.children[6].children.startswith("These values map directly")
    assert "raw LLM JSON" in body.children[8].children[0].children


def test_llm_studio_uses_neutral_defaults_when_parser_returns_partial_result() -> None:
    """Missing parser fields should be replaced with neutral defaults and clearly marked."""
    create_app()
    from dash_app.pages import llm_studio

    pending_state = llm_studio._stage_scenario_request(
        {},
        "People are busy and sometimes outsource chores.",
        "qwen3.5:4b",
        "req-partial",
    )
    store_data = llm_studio._complete_scenario_request(
        pending_state,
        "req-partial",
        "qwen3.5:4b",
        0.9,
        result={
            "scenario_summary": "Residents sometimes outsource chores when busy.",
            "reasoning": "The prompt hints at mixed behaviour but leaves several dimensions underspecified.",
            "delegation_preference_mean": 0.55,
            "service_cost_factor": None,
            "social_conformity_pressure": None,
            "tasks_per_step_mean": None,
            "num_agents": None,
        },
        raw_response='{"scenario_summary":"Residents sometimes outsource chores when busy."}',
    )

    scenario_result = store_data["scenario"]["result"]
    assert scenario_result["delegation_preference_mean"] == 0.55
    assert scenario_result["service_cost_factor"] == 0.4
    assert scenario_result["social_conformity_pressure"] == 0.3
    assert scenario_result["tasks_per_step_mean"] == 2.5
    assert scenario_result["num_agents"] == 100
    assert scenario_result["parameter_sources"]["delegation_preference_mean"] == "llm"
    assert scenario_result["parameter_sources"]["service_cost_factor"] == "default"
    assert "Neutral defaults were used for" in scenario_result["coverage_warning"]
    assert "A mid-sized society" in scenario_result["example_description"]
    assert "Simulation Dashboard controls" in scenario_result["next_step_guidance"]


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
