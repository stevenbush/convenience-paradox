"""
Page 2: LLM Studio

Unified interface for all 5 LLM roles: scenario parser, result interpreter,
profile generator, visualization annotator, and agent forums.
Includes per-role model selection and a session audit log viewer.

Callback architecture:
    - Model config panel queries Ollama for available models and populates
      per-role dropdowns. Selections are stored in dash_app.state.
    - Each role tab has its own input/output UI and callback.
    - All LLM calls go through api/llm_service.py (Roles 1-4) or
      model/forums.py (Role 5), with audit entries accumulated in state.
    - The audit log tab reads from state.get_audit_log().

Goals served: A (interactive UI), C (LLM-enhanced interface)
"""

from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime
from typing import Any

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import html, dcc, callback, Input, Output, State, ctx, no_update

from dash_app.components.card import card
from dash_app.components.badges import status_badge
from dash_app.components.charts import CHART_COLORWAY
import dash_app.state as app_state

logger = logging.getLogger(__name__)

dash.register_page(
    __name__,
    path="/llm-studio",
    name="LLM Studio",
    order=1,
)

# Role definitions for building the model config and tabs
ROLES = [
    ("role_1", "Role 1", "Scenario Parser", "fas fa-wand-magic-sparkles"),
    ("role_2", "Role 2", "Profile Generator", "fas fa-user-gear"),
    ("role_3", "Role 3", "Result Interpreter", "fas fa-comments"),
    ("role_4", "Role 4", "Viz Annotator", "fas fa-pen-fancy"),
    ("role_5", "Role 5", "Agent Forums", "fas fa-people-group"),
]


# =========================================================================
# Layout helpers
# =========================================================================

def _model_config_panel() -> html.Div:
    """Collapsible panel for per-role LLM model selection."""
    rows = []
    for role_key, role_id, role_name, _ in ROLES:
        rows.append(
            dbc.Row([
                dbc.Col(
                    html.Span(
                        [html.Strong(role_id), f" — {role_name}"],
                        style={"fontSize": "var(--cp-text-sm)"},
                    ),
                    width=5, className="d-flex align-items-center",
                ),
                dbc.Col(
                    dcc.Dropdown(
                        id=f"{role_key}-model",
                        options=[],
                        placeholder="Click Refresh...",
                        clearable=False,
                        style={"fontSize": "var(--cp-text-sm)"},
                    ),
                    width=5,
                ),
                dbc.Col(
                    html.Span(
                        id=f"{role_key}-model-status",
                        className="cp-status-dot cp-status-dot--unknown",
                    ),
                    width=2,
                    className="d-flex align-items-center justify-content-center",
                ),
            ], className="mb-2 align-items-center")
        )

    rows.append(
        dbc.Row(
            dbc.Col(
                dbc.Button(
                    [html.I(className="fas fa-sync-alt me-1"), "Refresh Models"],
                    id="btn-refresh-models",
                    className="cp-btn-outline",
                    size="sm",
                ),
                width="auto", className="mt-2",
            ),
            justify="end",
        )
    )

    return html.Div([
        html.Div([
            html.I(className="fas fa-cog me-2"),
            html.Span("Model Configuration",
                       style={"fontWeight": "var(--cp-weight-semibold)"}),
            dbc.Button(
                html.I(className="fas fa-chevron-down"),
                id="btn-toggle-model-config",
                className="cp-btn-outline ms-auto",
                size="sm", n_clicks=0,
            ),
        ], className="d-flex align-items-center mb-3",
           style={"cursor": "pointer"}),
        dbc.Collapse(
            card(children=rows),
            id="model-config-collapse",
            is_open=True,
        ),
    ])


def _tab_scenario() -> html.Div:
    """Role 1: Scenario Parser — NL description to model parameters."""
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Textarea(
                    id="scenario-input",
                    placeholder="Describe a social scenario (e.g., 'A society where everyone uses delivery apps and nobody cooks')...",
                    style={"height": "100px", "fontSize": "var(--cp-text-sm)"},
                    maxLength=500,
                ),
                html.Div([
                    dbc.Button(
                        [html.I(className="fas fa-wand-magic-sparkles me-1"), "Parse Scenario"],
                        id="btn-parse-scenario",
                        className="cp-btn-primary mt-2",
                        size="sm",
                    ),
                    dbc.Spinner(
                        html.Span(id="scenario-spinner"),
                        size="sm", color="primary",
                        spinner_class_name="ms-2",
                    ),
                ], className="d-flex align-items-center"),
            ], md=6),
            dbc.Col(
                html.Div(id="scenario-output"),
                md=6,
            ),
        ]),
    ], className="p-3")


def _tab_chat() -> html.Div:
    """Role 3: Result Interpreter — chat interface for asking about simulation."""
    return html.Div([
        html.Div(
            id="chat-messages",
            style={
                "height": "350px", "overflowY": "auto",
                "border": "1px solid var(--cp-border)",
                "borderRadius": "var(--cp-radius-lg)",
                "padding": "var(--cp-space-3)",
                "marginBottom": "var(--cp-space-3)",
                "background": "var(--cp-bg)",
            },
            children=html.Div(
                "Ask a question about your simulation results. "
                "The AI will interpret the data with hypothesis connections.",
                style={"color": "var(--cp-text-tertiary)",
                       "fontSize": "var(--cp-text-sm)",
                       "textAlign": "center", "marginTop": "140px"},
            ),
        ),
        dbc.InputGroup([
            dbc.Input(
                id="chat-input",
                placeholder="Ask about your simulation (e.g., 'Why is stress rising?')...",
                type="text",
            ),
            dbc.Button(
                [html.I(className="fas fa-paper-plane")],
                id="btn-chat-send",
                className="cp-btn-primary",
            ),
        ]),
        html.Div(
            "Context: current simulation metrics are auto-injected.",
            style={"fontSize": "var(--cp-text-xs)",
                   "color": "var(--cp-text-tertiary)",
                   "marginTop": "var(--cp-space-2)"},
        ),
    ], className="p-3")


def _tab_profile() -> html.Div:
    """Role 2: Profile Generator — demographic description to agent attributes."""
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Input(
                    id="profile-input",
                    placeholder="Describe an agent type (e.g., 'An elderly retiree who values self-sufficiency')...",
                    type="text",
                ),
                html.Div([
                    dbc.Button(
                        [html.I(className="fas fa-user-gear me-1"), "Generate Profile"],
                        id="btn-generate-profile",
                        className="cp-btn-primary mt-2",
                        size="sm",
                    ),
                    dbc.Spinner(
                        html.Span(id="profile-spinner"),
                        size="sm", color="primary",
                        spinner_class_name="ms-2",
                    ),
                ], className="d-flex align-items-center"),
            ], md=5),
            dbc.Col(
                html.Div(id="profile-output"),
                md=7,
            ),
        ]),
    ], className="p-3")


def _tab_annotations() -> html.Div:
    """Role 4: Visualization Annotator — auto-generate chart captions."""
    return html.Div([
        html.Div([
            dbc.Button(
                [html.I(className="fas fa-pen-fancy me-1"), "Annotate All Charts"],
                id="btn-annotate-charts",
                className="cp-btn-primary",
                size="sm",
            ),
            dbc.Spinner(
                html.Span(id="annotate-spinner"),
                size="sm", color="primary",
                spinner_class_name="ms-2",
            ),
        ], className="d-flex align-items-center mb-3"),
        html.Div(id="annotations-output"),
    ], className="p-3")


def _tab_forums() -> html.Div:
    """Role 5: Agent Forums — experimental LLM-powered group discussions."""
    return html.Div([
        html.Div([
            status_badge("Experimental Mode", "warning"),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                html.Label("Forum Fraction", className="cp-controls__slider-label"),
                dcc.Slider(
                    id="forum-fraction-slider",
                    min=0.05, max=0.5, step=0.05, value=0.20,
                    marks=None,
                    tooltip={"placement": "bottom"},
                ),
            ], md=4),
            dbc.Col([
                html.Label("Group Size", className="cp-controls__slider-label"),
                dbc.RadioItems(
                    id="forum-group-size",
                    options=[{"label": str(i), "value": i} for i in [2, 3, 4]],
                    value=2, inline=True,
                ),
            ], md=3),
            dbc.Col([
                html.Label("Dialogue Turns", className="cp-controls__slider-label"),
                dbc.RadioItems(
                    id="forum-num-turns",
                    options=[{"label": str(i), "value": i} for i in [1, 2, 3]],
                    value=2, inline=True,
                ),
            ], md=3),
            dbc.Col([
                dbc.Button(
                    [html.I(className="fas fa-people-group me-1"), "Run Forum"],
                    id="btn-run-forum",
                    className="cp-btn-primary mt-3",
                    size="sm",
                ),
            ], md=2),
        ], className="mb-3"),
        dbc.Spinner(
            html.Div(id="forum-output"),
            color="primary",
        ),
    ], className="p-3")


def _tab_audit() -> html.Div:
    """Audit log viewer for all LLM interactions during this session."""
    return html.Div([
        html.Div([
            dbc.Button(
                [html.I(className="fas fa-sync-alt me-1"), "Refresh Log"],
                id="btn-refresh-audit",
                className="cp-btn-outline me-2",
                size="sm",
            ),
            dbc.Button(
                [html.I(className="fas fa-trash me-1"), "Clear Log"],
                id="btn-clear-audit",
                className="cp-btn-outline",
                size="sm",
            ),
        ], className="d-flex mb-3"),
        html.Div(id="audit-log-content"),
    ], className="p-3")


def _tab_content() -> dbc.Tabs:
    """Horizontal tab bar for the 6 LLM role interfaces."""
    return dbc.Tabs([
        dbc.Tab(_tab_scenario(), label="Scenario Parser", tab_id="tab-scenario"),
        dbc.Tab(_tab_chat(), label="Chat Interpreter", tab_id="tab-chat"),
        dbc.Tab(_tab_profile(), label="Profile Generator", tab_id="tab-profile"),
        dbc.Tab(_tab_annotations(), label="Annotations", tab_id="tab-annotations"),
        dbc.Tab(_tab_forums(), label="Agent Forums", tab_id="tab-forums"),
        dbc.Tab(_tab_audit(), label="Audit Log", tab_id="tab-audit"),
    ], id="llm-tabs", active_tab="tab-scenario", className="cp-tabs")


layout = html.Div([
    html.Div([
        html.H2("LLM Studio", className="cp-page-title"),
        html.P(
            "AI-powered research assistant — 5 peripheral LLM roles for analysis and interpretation.",
            className="cp-page-subtitle",
        ),
    ], className="cp-page-header"),
    _model_config_panel(),
    html.Div(className="mb-4"),
    _tab_content(),
])


# =========================================================================
# Shared helper: record an LLM call to the session audit log
# =========================================================================

def _record_audit(role: str, call_kind: str, model: str,
                  prompt_preview: str, result: Any,
                  elapsed: float, error: str | None = None) -> None:
    """Add a lightweight audit entry to the session log."""
    app_state.append_audit_entry({
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "role": role,
        "call_kind": call_kind,
        "model": model,
        "prompt_preview": prompt_preview[:120],
        "result_preview": str(result)[:200] if result else "",
        "elapsed": round(elapsed, 2),
        "status": "error" if error else "success",
        "error": error,
    })


# =========================================================================
# Callback 1: Toggle model config panel
# =========================================================================

@callback(
    Output("model-config-collapse", "is_open"),
    Input("btn-toggle-model-config", "n_clicks"),
    State("model-config-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_model_config(n_clicks, is_open):
    return not is_open


# =========================================================================
# Callback 2: Refresh available models from Ollama
# =========================================================================

@callback(
    [Output(f"{rk}-model", "options") for rk, _, _, _ in ROLES]
    + [Output(f"{rk}-model", "value") for rk, _, _, _ in ROLES]
    + [Output(f"{rk}-model-status", "className") for rk, _, _, _ in ROLES],
    Input("btn-refresh-models", "n_clicks"),
    prevent_initial_call=True,
)
def refresh_models(n_clicks):
    """Query Ollama for available models and populate all role dropdowns."""
    try:
        import ollama as _ollama
        models_resp = _ollama.list()
        model_names = [m.model for m in models_resp.models]
    except Exception:
        model_names = []

    options = [{"label": m, "value": m} for m in model_names]
    if not options:
        options = [{"label": "(no models found)", "value": ""}]

    current = app_state.get_all_role_models()
    values = []
    statuses = []
    for rk, _, _, _ in ROLES:
        assigned = current.get(rk, "")
        if assigned in model_names:
            values.append(assigned)
            statuses.append("cp-status-dot cp-status-dot--online")
        elif model_names:
            values.append(model_names[0])
            app_state.set_role_model(rk, model_names[0])
            statuses.append("cp-status-dot cp-status-dot--online")
        else:
            values.append("")
            statuses.append("cp-status-dot cp-status-dot--offline")

    return [options] * 5 + values + statuses


# =========================================================================
# Callback 3: Save model selections to state
# =========================================================================

for _rk, _, _, _ in ROLES:
    @callback(
        Output(f"{_rk}-model-status", "className", allow_duplicate=True),
        Input(f"{_rk}-model", "value"),
        prevent_initial_call=True,
    )
    def _save_model_selection(value, role_key=_rk):
        if value:
            app_state.set_role_model(role_key, value)
            return "cp-status-dot cp-status-dot--online"
        return "cp-status-dot cp-status-dot--unknown"


# =========================================================================
# Callback 4: Scenario Parser (Role 1)
# =========================================================================

@callback(
    Output("scenario-output", "children"),
    Input("btn-parse-scenario", "n_clicks"),
    State("scenario-input", "value"),
    prevent_initial_call=True,
)
def parse_scenario_cb(n_clicks, description):
    if not description or not description.strip():
        return html.Div("Please enter a scenario description.",
                        style={"color": "var(--cp-danger)", "fontSize": "var(--cp-text-sm)"})

    import time
    model_name = app_state.get_role_model("role_1")
    t0 = time.perf_counter()
    try:
        from api.llm_service import parse_scenario
        result = parse_scenario(description, model=model_name)
        elapsed = time.perf_counter() - t0
        _record_audit("Role 1", "scenario_parser", model_name,
                      description, result, elapsed)

        params_rows = []
        param_keys = ["delegation_preference_mean", "service_cost_factor",
                      "social_conformity_pressure", "tasks_per_step_mean", "num_agents"]
        for pk in param_keys:
            val = result.get(pk)
            params_rows.append(
                html.Tr([
                    html.Td(pk.replace("_", " ").title(),
                            style={"fontSize": "var(--cp-text-sm)"}),
                    html.Td(
                        f"{val}" if val is not None else "—",
                        style={"fontFamily": "var(--cp-font-mono)",
                               "fontSize": "var(--cp-text-sm)"},
                    ),
                ])
            )

        return card(
            title="Parsed Parameters",
            subtitle=f"{elapsed:.1f}s · {model_name}",
            children=[
                html.P(result.get("scenario_summary", ""),
                       style={"fontWeight": "var(--cp-weight-semibold)",
                              "fontSize": "var(--cp-text-sm)"}),
                html.P(result.get("reasoning", ""),
                       style={"fontSize": "var(--cp-text-sm)",
                              "color": "var(--cp-text-secondary)"}),
                dbc.Table(
                    html.Tbody(params_rows),
                    bordered=True, size="sm", className="mt-2",
                ),
            ],
        )
    except Exception as e:
        elapsed = time.perf_counter() - t0
        _record_audit("Role 1", "scenario_parser", model_name,
                      description, None, elapsed, str(e))
        return html.Div(
            f"Error: {e}",
            style={"color": "var(--cp-danger)", "fontSize": "var(--cp-text-sm)"},
        )


# =========================================================================
# Callback 5: Chat Interpreter (Role 3)
# =========================================================================

@callback(
    Output("chat-messages", "children"),
    Output("chat-history-store", "data"),
    Output("chat-input", "value"),
    Input("btn-chat-send", "n_clicks"),
    State("chat-input", "value"),
    State("chat-history-store", "data"),
    prevent_initial_call=True,
)
def chat_send_cb(n_clicks, question, history):
    if not question or not question.strip():
        return no_update, no_update, no_update

    history = history or []
    history.append({"role": "user", "content": question})

    # Build simulation context
    sim_model = app_state.get_model()
    if sim_model is not None and sim_model.current_step > 0:
        df = sim_model.get_model_dataframe()
        latest = df.iloc[-1].to_dict()
        context = {
            "current_step": sim_model.current_step,
            "latest_metrics": {k: round(v, 4) if isinstance(v, float) else v
                               for k, v in latest.items()},
            "params": sim_model.get_params(),
        }
    else:
        context = {"current_step": 0, "note": "No simulation running."}

    import time
    model_name = app_state.get_role_model("role_3")
    t0 = time.perf_counter()
    try:
        from api.llm_service import interpret_results
        result = interpret_results(question, context, history=history, model=model_name)
        elapsed = time.perf_counter() - t0
        _record_audit("Role 3", "result_interpreter", model_name,
                      question, result, elapsed)

        answer_text = result.get("answer", "No answer generated.")
        hypo = result.get("hypothesis_connection", "")
        confidence = result.get("confidence_note", "")

        response_parts = [answer_text]
        if hypo:
            response_parts.append(f"[{hypo}]")
        if confidence:
            response_parts.append(f"Note: {confidence}")

        history.append({"role": "assistant", "content": " ".join(response_parts)})

    except Exception as e:
        elapsed = time.perf_counter() - t0
        _record_audit("Role 3", "result_interpreter", model_name,
                      question, None, elapsed, str(e))
        history.append({"role": "assistant", "content": f"Error: {e}"})

    # Build chat bubble display
    bubbles = []
    for msg in history:
        if msg["role"] == "user":
            bubbles.append(html.Div([
                html.Div("You", className="cp-chat__sender"),
                html.Div(msg["content"]),
            ], className="cp-chat__message cp-chat__message--user"))
        else:
            bubbles.append(html.Div([
                html.Div("AI Interpreter", className="cp-chat__sender"),
                html.Div(msg["content"]),
            ], className="cp-chat__message cp-chat__message--ai"))

    return html.Div(bubbles, className="cp-chat"), history, ""


# =========================================================================
# Callback 6: Profile Generator (Role 2)
# =========================================================================

@callback(
    Output("profile-output", "children"),
    Input("btn-generate-profile", "n_clicks"),
    State("profile-input", "value"),
    prevent_initial_call=True,
)
def generate_profile_cb(n_clicks, description):
    if not description or not description.strip():
        return html.Div("Please enter a demographic description.",
                        style={"color": "var(--cp-danger)", "fontSize": "var(--cp-text-sm)"})

    import time
    model_name = app_state.get_role_model("role_2")
    t0 = time.perf_counter()
    try:
        from api.llm_service import generate_agent_profile
        result = generate_agent_profile(description, model=model_name)
        elapsed = time.perf_counter() - t0
        _record_audit("Role 2", "profile_generator", model_name,
                      description, result, elapsed)

        # Radar chart of 4 skills
        skills = ["domestic", "administrative", "errand", "maintenance"]
        skill_vals = [result.get(f"skill_{s}", 0.5) for s in skills]
        skill_vals.append(skill_vals[0])  # close the polygon
        labels = [s.title() for s in skills] + [skills[0].title()]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=skill_vals, theta=labels,
            fill="toself",
            fillcolor="rgba(44,140,153,0.15)",
            line=dict(color=CHART_COLORWAY[0], width=2),
            name="Skills",
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 1]),
            ),
            showlegend=False,
            margin=dict(t=30, b=30, l=60, r=60),
            height=250,
        )

        return card(
            title="Generated Profile",
            subtitle=f"{elapsed:.1f}s · {model_name}",
            children=[
                html.P(
                    result.get("profile_description", ""),
                    style={"fontStyle": "italic", "fontSize": "var(--cp-text-sm)"},
                ),
                dbc.Row([
                    dbc.Col([
                        html.Div(
                            f"Delegation: {result.get('delegation_preference', 0):.2f}",
                            style={"fontSize": "var(--cp-text-lg)",
                                   "fontWeight": "var(--cp-weight-bold)",
                                   "color": "var(--cp-primary)"},
                        ),
                        html.Div("delegation_preference",
                                 style={"fontSize": "var(--cp-text-xs)",
                                        "color": "var(--cp-text-tertiary)"}),
                    ], md=4, className="d-flex flex-column justify-content-center"),
                    dbc.Col(
                        dcc.Graph(figure=fig, config={"displayModeBar": False},
                                  style={"height": "250px"}),
                        md=8,
                    ),
                ]),
            ],
        )
    except Exception as e:
        elapsed = time.perf_counter() - t0
        _record_audit("Role 2", "profile_generator", model_name,
                      description, None, elapsed, str(e))
        return html.Div(
            f"Error: {e}",
            style={"color": "var(--cp-danger)", "fontSize": "var(--cp-text-sm)"},
        )


# =========================================================================
# Callback 7: Annotations (Role 4)
# =========================================================================

ANNOTATABLE_CHARTS = [
    ("total_labor_hours", "Total Labor Hours (H1)"),
    ("stress_delegation", "Stress & Delegation (H2/H3)"),
    ("social_efficiency", "Social Efficiency (H2)"),
    ("market_health", "Market Health"),
]


@callback(
    Output("annotations-output", "children"),
    Input("btn-annotate-charts", "n_clicks"),
    prevent_initial_call=True,
)
def annotate_charts_cb(n_clicks):
    sim_model = app_state.get_model()
    if sim_model is None or sim_model.current_step == 0:
        return html.Div("Initialize and run a simulation first.",
                        style={"color": "var(--cp-text-tertiary)",
                               "fontSize": "var(--cp-text-sm)"})

    import time
    from api.llm_service import annotate_visualization
    model_name = app_state.get_role_model("role_4")
    df = sim_model.get_model_dataframe()

    annotation_cards = []
    for chart_key, chart_label in ANNOTATABLE_CHARTS:
        col_map = {
            "total_labor_hours": "total_labor_hours",
            "stress_delegation": "avg_stress",
            "social_efficiency": "social_efficiency",
            "market_health": "unmatched_tasks",
        }
        col = col_map.get(chart_key, chart_key)
        if col in df.columns:
            series = df[col]
            metrics = {
                "min": round(float(series.min()), 4),
                "max": round(float(series.max()), 4),
                "mean": round(float(series.mean()), 4),
                "last": round(float(series.iloc[-1]), 4),
                "trend": "rising" if series.iloc[-1] > series.iloc[0] else "falling",
                "steps": len(series),
            }
        else:
            metrics = {"note": "Column not found"}

        t0 = time.perf_counter()
        try:
            result = annotate_visualization(
                chart_label, metrics, model=model_name,
            )
            elapsed = time.perf_counter() - t0
            _record_audit("Role 4", "visualization_annotator", model_name,
                          chart_label, result, elapsed)

            annotation_cards.append(card(
                title=result.get("chart_title", chart_label),
                subtitle=result.get("hypothesis_tag", ""),
                children=[
                    html.P(result.get("caption", ""),
                           style={"fontSize": "var(--cp-text-sm)"}),
                    html.Div(
                        [html.I(className="fas fa-lightbulb me-1"),
                         result.get("key_insight", "")],
                        style={"fontSize": "var(--cp-text-sm)",
                               "color": "var(--cp-primary)",
                               "fontWeight": "var(--cp-weight-semibold)"},
                    ),
                ],
                footer=html.Span(f"{elapsed:.1f}s · {model_name}",
                                 style={"fontSize": "var(--cp-text-xs)",
                                        "color": "var(--cp-text-tertiary)"}),
            ))
        except Exception as e:
            elapsed = time.perf_counter() - t0
            _record_audit("Role 4", "visualization_annotator", model_name,
                          chart_label, None, elapsed, str(e))
            annotation_cards.append(card(
                title=chart_label,
                children=html.Div(f"Error: {e}",
                                  style={"color": "var(--cp-danger)",
                                         "fontSize": "var(--cp-text-sm)"}),
            ))

    return html.Div(annotation_cards)


# =========================================================================
# Callback 8: Agent Forums (Role 5)
# =========================================================================

@callback(
    Output("forum-output", "children"),
    Input("btn-run-forum", "n_clicks"),
    State("forum-fraction-slider", "value"),
    State("forum-group-size", "value"),
    State("forum-num-turns", "value"),
    prevent_initial_call=True,
)
def run_forum_cb(n_clicks, fraction, group_size, num_turns):
    sim_model = app_state.get_model()
    if sim_model is None:
        return html.Div("Initialize a simulation first.",
                        style={"color": "var(--cp-danger)",
                               "fontSize": "var(--cp-text-sm)"})

    import time
    from model.forums import run_forum_step, format_session_for_api

    model_name = app_state.get_role_model("role_5")
    t0 = time.perf_counter()
    try:
        session = run_forum_step(
            sim_model,
            forum_fraction=fraction or 0.20,
            group_size=group_size or 2,
            num_turns=num_turns or 2,
            llm_model=model_name,
        )
        elapsed = time.perf_counter() - t0
        session_data = format_session_for_api(session)
        _record_audit("Role 5", "agent_forums", model_name,
                      f"fraction={fraction}, groups={group_size}",
                      f"{len(session_data.get('groups', []))} groups",
                      elapsed)

        group_cards = []
        for gi, group in enumerate(session_data.get("groups", [])):
            # Build dialogue bubbles
            bubbles = []
            for turn in group.get("turns", []):
                bubbles.append(html.Div([
                    html.Div(
                        turn.get("speaker_label", "Agent"),
                        className="cp-chat__sender",
                    ),
                    html.Div(turn.get("content", "")),
                ], className="cp-chat__message cp-chat__message--ai"))

            outcome = group.get("outcome", {}) or {}
            norm_signal = outcome.get("norm_signal", 0)
            confidence = outcome.get("confidence", 0)
            summary = outcome.get("summary", "No consensus extracted")

            norm_color = CHART_COLORWAY[2] if norm_signal < 0 else CHART_COLORWAY[1]
            norm_label = f"{'→ Autonomy' if norm_signal < 0 else '→ Delegation'}"

            group_cards.append(card(
                title=f"Group {gi + 1}",
                subtitle=f"Agents {group.get('agent_ids', [])}",
                children=[
                    html.Div(bubbles, className="cp-chat",
                             style={"maxHeight": "200px", "overflowY": "auto"}),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col([
                            html.Div("Norm Signal", style={"fontSize": "var(--cp-text-xs)",
                                                           "color": "var(--cp-text-tertiary)"}),
                            html.Div(
                                f"{norm_signal:+.2f} {norm_label}",
                                style={"fontWeight": "var(--cp-weight-bold)",
                                       "color": norm_color},
                            ),
                        ], md=3),
                        dbc.Col([
                            html.Div("Confidence", style={"fontSize": "var(--cp-text-xs)",
                                                          "color": "var(--cp-text-tertiary)"}),
                            html.Div(f"{confidence:.2f}",
                                     style={"fontWeight": "var(--cp-weight-bold)"}),
                        ], md=3),
                        dbc.Col([
                            html.Div("Delta Applied",
                                     style={"fontSize": "var(--cp-text-xs)",
                                            "color": "var(--cp-text-tertiary)"}),
                            html.Div(f"{group.get('delta_applied', 0):+.4f}",
                                     style={"fontFamily": "var(--cp-font-mono)"}),
                        ], md=3),
                        dbc.Col([
                            html.Div("Summary", style={"fontSize": "var(--cp-text-xs)",
                                                       "color": "var(--cp-text-tertiary)"}),
                            html.Div(summary, style={"fontSize": "var(--cp-text-sm)"}),
                        ], md=3),
                    ]),
                ],
            ))

        return html.Div([
            html.Div([
                html.Span(f"Completed in {elapsed:.1f}s · {model_name} · ",
                          style={"fontSize": "var(--cp-text-sm)",
                                 "color": "var(--cp-text-secondary)"}),
                html.Span(
                    f"{session_data.get('n_agents_participating', 0)} agents, "
                    f"{len(session_data.get('groups', []))} groups",
                    style={"fontSize": "var(--cp-text-sm)",
                           "fontWeight": "var(--cp-weight-semibold)"},
                ),
            ], className="mb-3"),
            *group_cards,
        ])
    except Exception as e:
        elapsed = time.perf_counter() - t0
        _record_audit("Role 5", "agent_forums", model_name,
                      f"fraction={fraction}", None, elapsed, str(e))
        return html.Div(
            f"Error: {e}",
            style={"color": "var(--cp-danger)", "fontSize": "var(--cp-text-sm)"},
        )


# =========================================================================
# Callback 9: Audit Log Viewer
# =========================================================================

@callback(
    Output("audit-log-content", "children"),
    Input("btn-refresh-audit", "n_clicks"),
    Input("btn-clear-audit", "n_clicks"),
    prevent_initial_call=True,
)
def update_audit_log(n_refresh, n_clear):
    triggered = ctx.triggered_id
    if triggered == "btn-clear-audit":
        app_state.clear_audit_log()
        return html.Div(
            "Audit log cleared.",
            style={"color": "var(--cp-text-tertiary)",
                   "fontSize": "var(--cp-text-sm)", "textAlign": "center",
                   "padding": "var(--cp-space-8)"},
        )

    log = app_state.get_audit_log()
    if not log:
        return html.Div(
            "No LLM calls recorded in this session. Use any role above to generate entries.",
            style={"color": "var(--cp-text-tertiary)",
                   "fontSize": "var(--cp-text-sm)", "textAlign": "center",
                   "padding": "var(--cp-space-8)"},
        )

    rows = []
    for entry in reversed(log):
        status_class = "cp-badge cp-badge--success" if entry.get("status") == "success" \
            else "cp-badge cp-badge--danger"
        rows.append(
            html.Tr([
                html.Td(entry.get("timestamp", ""),
                        style={"fontFamily": "var(--cp-font-mono)",
                               "fontSize": "var(--cp-text-xs)"}),
                html.Td(entry.get("role", ""),
                        style={"fontSize": "var(--cp-text-sm)",
                               "fontWeight": "var(--cp-weight-semibold)"}),
                html.Td(entry.get("call_kind", ""),
                        style={"fontSize": "var(--cp-text-xs)"}),
                html.Td(entry.get("model", ""),
                        style={"fontSize": "var(--cp-text-xs)",
                               "fontFamily": "var(--cp-font-mono)"}),
                html.Td(f"{entry.get('elapsed', 0):.1f}s",
                        style={"fontSize": "var(--cp-text-xs)",
                               "fontFamily": "var(--cp-font-mono)"}),
                html.Td(html.Span(
                    entry.get("status", ""),
                    className=status_class,
                )),
                html.Td(entry.get("prompt_preview", ""),
                        style={"fontSize": "var(--cp-text-xs)",
                               "maxWidth": "200px", "overflow": "hidden",
                               "textOverflow": "ellipsis", "whiteSpace": "nowrap"}),
            ])
        )

    return dbc.Table(
        [
            html.Thead(html.Tr([
                html.Th("Time"), html.Th("Role"), html.Th("Kind"),
                html.Th("Model"), html.Th("Time"), html.Th("Status"),
                html.Th("Prompt"),
            ])),
            html.Tbody(rows),
        ],
        bordered=True, hover=True, responsive=True, size="sm",
        style={"fontSize": "var(--cp-text-sm)"},
    )
