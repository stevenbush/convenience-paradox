"""
Simulation parameter control panel for the sidebar.

Provides sliders for the 6 primary model parameters, a collapsible
Advanced section for the remaining 5, preset selector, network type
toggle, and simulation action buttons (Init, Step, Run, Reset).
"""

import dash_bootstrap_components as dbc
from dash import html, dcc

from model.params import PARAMETER_DEFINITIONS, TYPE_A_PRESET, TYPE_B_PRESET


# --- Slider definitions (primary = always visible) ---

PRIMARY_PARAMS = [
    "delegation_preference_mean",
    "service_cost_factor",
    "social_conformity_pressure",
    "tasks_per_step_mean",
    "initial_available_time",
    "num_agents",
]

ADVANCED_PARAMS = [
    "delegation_preference_std",
    "tasks_per_step_std",
    "stress_threshold",
    "stress_recovery_rate",
    "adaptation_rate",
]

# Short display labels
PARAM_LABELS = {
    "delegation_preference_mean": "Delegation Mean",
    "delegation_preference_std": "Delegation Std",
    "service_cost_factor": "Service Cost",
    "social_conformity_pressure": "Conformity",
    "tasks_per_step_mean": "Tasks / Step",
    "tasks_per_step_std": "Tasks Std",
    "initial_available_time": "Available Time",
    "stress_threshold": "Stress Threshold",
    "stress_recovery_rate": "Stress Recovery",
    "adaptation_rate": "Adaptation Rate",
    "num_agents": "Num Agents",
}


def _make_slider(param_key: str) -> html.Div:
    """Create a labeled slider + direct number input for one simulation parameter.

    The slider and number input are bidirectionally synced via callbacks in
    simulation.py — changing either one updates the other.
    """
    pdef = PARAMETER_DEFINITIONS[param_key]
    label = PARAM_LABELS.get(param_key, param_key)
    default = pdef["default"]
    p_min = pdef["min"]
    p_max = pdef["max"]

    if pdef["type"] is int:
        slider_step = max(1, (p_max - p_min) // 20)
        input_step = 1
        fmt_default = str(int(default))
    else:
        slider_step = round((p_max - p_min) / 40, 4)
        input_step = slider_step
        fmt_default = f"{default:.2f}"

    slider = dcc.Slider(
        id=f"slider-{param_key}",
        min=p_min, max=p_max, step=slider_step,
        value=default,
        marks=None,
        tooltip={"placement": "bottom", "always_visible": False},
    )

    # Compact inline number input — allows precise value entry alongside the slider
    number_input = dbc.Input(
        id=f"input-{param_key}",
        type="number",
        value=default,
        min=p_min,
        max=p_max,
        step=input_step,
        debounce=True,
        className="cp-slider-input",
    )

    return html.Div(
        [
            html.Div(
                [
                    html.Span(label),
                    number_input,
                ],
                className="cp-controls__slider-label",
            ),
            slider,
        ],
        className="mb-2",
    )


def simulation_controls() -> html.Div:
    """Build the full simulation control panel for the sidebar."""

    preset_selector = html.Div([
        html.Div("PRESET", className="cp-controls__section-title"),
        dcc.Dropdown(
            id="preset-selector",
            options=[
                {"label": "Type A (Autonomy)", "value": "type_a"},
                {"label": "Type B (Convenience)", "value": "type_b"},
                {"label": "Custom", "value": "custom"},
            ],
            value="custom",
            clearable=False,
            style={"fontSize": "var(--cp-text-sm)"},
        ),
    ], className="mb-3")

    primary_sliders = html.Div([
        html.Div("PARAMETERS", className="cp-controls__section-title"),
        *[_make_slider(p) for p in PRIMARY_PARAMS],
    ])

    advanced_section = html.Div([
        dbc.Button(
            [html.I(className="fas fa-chevron-right me-2", id="advanced-chevron"),
             "Advanced"],
            id="btn-toggle-advanced",
            className="cp-btn-outline w-100 mb-2",
            size="sm",
            n_clicks=0,
        ),
        dbc.Collapse(
            html.Div([_make_slider(p) for p in ADVANCED_PARAMS]),
            id="advanced-collapse",
            is_open=False,
        ),
    ], className="mb-3")

    network_selector = html.Div([
        html.Div("NETWORK", className="cp-controls__section-title"),
        dbc.RadioItems(
            id="radio-network-type",
            options=[
                {"label": " Small World", "value": "small_world"},
                {"label": " Random", "value": "random"},
            ],
            value="small_world",
            inline=True,
            style={"fontSize": "var(--cp-text-sm)"},
        ),
    ], className="mb-3")

    step_input = html.Div([
        html.Div(
            [
                html.Span("Run Steps"),
                html.Span(className="cp-controls__slider-value"),
            ],
            className="cp-controls__slider-label",
        ),
        dbc.Input(
            id="input-run-steps",
            type="number",
            value=50,
            min=1, max=500,
            size="sm",
        ),
    ], className="mb-3")

    action_buttons = html.Div([
        html.Div("SIMULATION", className="cp-controls__section-title"),
        html.Div([
            dbc.Button("Initialize", id="btn-init", className="cp-btn-primary", size="sm"),
            dbc.Button("Step", id="btn-step", className="cp-btn-outline", size="sm"),
        ], className="cp-controls__actions"),
        html.Div([
            dbc.Button("Run", id="btn-run", className="cp-btn-primary", size="sm"),
            dbc.Button("Reset", id="btn-reset", className="cp-btn-outline", size="sm"),
        ], className="cp-controls__actions"),
        step_input,
    ])

    status_display = html.Div(
        id="sim-status-display",
        children=html.Span(
            "Not initialized",
            style={
                "fontSize": "var(--cp-text-xs)",
                "color": "var(--cp-text-tertiary)",
            },
        ),
        className="mt-2",
    )

    return html.Div([
        preset_selector,
        action_buttons,
        status_display,
        primary_sliders,
        advanced_section,
        network_selector,
    ])
