"""
Page 4: Analysis

Research results presentation — hypothesis scoreboard, Type A vs Type B
comparison, and interactive sensitivity heatmap.

Callback architecture:
    - Hypothesis cards are static research findings from completed analysis.
    - "Run Both Presets" triggers server-side runs of Type A and Type B,
      then populates the comparison table and grouped bar chart.
    - The sensitivity heatmap runs a lightweight on-demand parameter sweep
      (5x5 grid) and renders a Plotly imshow heatmap.

Goals served: B (visual analytics for research results), C (advanced data visualization)
"""

from __future__ import annotations

import logging
import time

import dash
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go
from dash import html, dcc, callback, Input, Output, State, no_update

from dash_app.components.card import card
from dash_app.components.badges import hypothesis_badge
from dash_app.components.charts import CHART_COLORWAY
from dash_app.components.empty_states import empty_state
from model.model import ConvenienceParadoxModel
from model.params import (
    TYPE_A_PRESET, TYPE_B_PRESET, PARAMETER_DEFINITIONS,
)

logger = logging.getLogger(__name__)

dash.register_page(
    __name__,
    path="/analysis",
    name="Analysis",
    order=3,
)


# =========================================================================
# Hypothesis data (from completed research — README and analysis reports)
# =========================================================================

HYPOTHESES = [
    {
        "id": "H1",
        "title": "Delegation Increases Total Labor",
        "status": "confirmed",
        "finding": "+22% labor hours in Type B vs Type A (60-step runs)",
        "detail": (
            "Higher delegation rates lead to higher total systemic labor hours. "
            "The service economy creates overhead: when Agent A delegates a task "
            "to Agent B, the task still takes time — plus matching, coordination, "
            "and travel costs. Type B societies consistently generate ~22% more "
            "total labor hours across all tested parameter ranges."
        ),
        "icon": "fas fa-arrow-trend-up",
        "key_metric": "total_labor_hours",
    },
    {
        "id": "H2",
        "title": "Involution Threshold",
        "status": "supported",
        "finding": "Efficiency plateau visible; cascade requires 200+ steps",
        "detail": (
            "A critical delegation threshold exists beyond which social efficiency "
            "stops improving and may decline. The threshold manifests as an "
            "efficiency plateau in the sensitivity heatmap around delegation_mean "
            "= 0.55–0.65. Full involution cascades require extended runs (200+ "
            "steps) to become visible."
        ),
        "icon": "fas fa-chart-line",
        "key_metric": "social_efficiency",
    },
    {
        "id": "H3",
        "title": "Autonomy Improves Well-being",
        "status": "supported",
        "finding": "Long-run phenomenon — stress divergence at 100+ steps",
        "detail": (
            "Higher autonomy (lower delegation) leads to lower long-run stress "
            "and higher aggregate well-being. Crucially, this is a long-run "
            "emergent property: in short runs (<60 steps), Type B societies "
            "actually show LOWER stress because convenience works in the short "
            "term. The paradox becomes visible only at 100+ steps as service "
            "economy overhead compounds."
        ),
        "icon": "fas fa-heart-pulse",
        "key_metric": "avg_stress",
    },
    {
        "id": "H4",
        "title": "Mixed System Instability",
        "status": "partial",
        "finding": "Conformity-driven polarisation observed",
        "detail": (
            "Mixed-delegation societies (delegation_mean ~0.5) are unstable "
            "and tend to drift toward one extreme. This drift is driven by "
            "social conformity pressure: agents copy their neighbours' behaviour, "
            "creating positive feedback loops. The direction of drift depends on "
            "the initial distribution and random seed."
        ),
        "icon": "fas fa-arrows-left-right",
        "key_metric": "avg_delegation_rate",
    },
]


# =========================================================================
# Layout helpers
# =========================================================================

def _hypothesis_cards() -> dbc.Row:
    """Row of 4 hypothesis status cards with expandable details."""
    cols = []
    for h in HYPOTHESES:
        card_content = html.Div([
            html.Div([
                html.Span(
                    h["id"],
                    style={
                        "fontSize": "var(--cp-text-lg)",
                        "fontWeight": "var(--cp-weight-bold)",
                        "color": "var(--cp-text-primary)",
                    },
                ),
                hypothesis_badge(h["id"], h["status"]),
            ], className="d-flex justify-content-between align-items-center mb-2"),
            html.Div(
                h["title"],
                style={
                    "fontSize": "var(--cp-text-base)",
                    "fontWeight": "var(--cp-weight-semibold)",
                    "color": "var(--cp-text-primary)",
                    "marginBottom": "var(--cp-space-2)",
                },
            ),
            html.Div(
                h["finding"],
                style={
                    "fontSize": "var(--cp-text-sm)",
                    "color": "var(--cp-text-secondary)",
                    "marginBottom": "var(--cp-space-2)",
                },
            ),
            dbc.Collapse(
                html.Div(
                    h["detail"],
                    style={
                        "fontSize": "var(--cp-text-sm)",
                        "color": "var(--cp-text-secondary)",
                        "borderTop": "1px solid var(--cp-border)",
                        "paddingTop": "var(--cp-space-3)",
                        "marginTop": "var(--cp-space-2)",
                    },
                ),
                id=f"collapse-{h['id'].lower()}",
                is_open=False,
            ),
            html.Div(
                html.A(
                    "Details",
                    id=f"toggle-{h['id'].lower()}",
                    style={
                        "fontSize": "var(--cp-text-xs)",
                        "color": "var(--cp-accent)",
                        "cursor": "pointer",
                        "textDecoration": "none",
                    },
                ),
                className="text-end mt-1",
            ),
        ], className="cp-card", style={"padding": "var(--cp-space-5)"})

        cols.append(dbc.Col(card_content, lg=3, md=6, xs=12))

    return dbc.Row(cols, className="g-3 mb-4")


def _comparison_section() -> html.Div:
    """Type A vs Type B comparison panel with Run Both button."""
    return card(
        title="Type A vs Type B Comparison",
        subtitle="Autonomy-Oriented vs Convenience-Oriented society presets",
        children=[
            html.Div(id="comparison-status", className="mb-2"),
            dbc.Row([
                dbc.Col(
                    html.Div(
                        id="comparison-table-container",
                        children=empty_state(
                            icon="fas fa-table",
                            title="Run comparison to see results",
                            message="Click 'Run Both Presets' to generate a side-by-side comparison.",
                        ),
                    ),
                    lg=5, md=12,
                ),
                dbc.Col(
                    html.Div(
                        dcc.Graph(
                            id="chart-ab-comparison",
                            style={"width": "100%", "height": "100%"},
                            config={"displayModeBar": False, "responsive": True},
                        ),
                        style={"height": "380px"},
                    ),
                    lg=7, md=12,
                ),
            ], className="g-3"),
            html.Div(
                dbc.Row([
                    dbc.Col(
                        html.Label("Steps per run", className="cp-controls__slider-label"),
                        width="auto",
                    ),
                    dbc.Col(
                        dbc.Input(
                            id="comparison-steps-input",
                            type="number", value=60, min=10, max=500, step=10,
                            size="sm", style={"width": "100px"},
                        ),
                        width="auto",
                    ),
                    dbc.Col(
                        dbc.Button(
                            [html.I(className="fas fa-play me-2"), "Run Both Presets"],
                            id="btn-run-both",
                            className="cp-btn-primary",
                            size="sm",
                        ),
                        width="auto",
                    ),
                ], className="g-2 align-items-end justify-content-center"),
                className="text-center mt-3",
            ),
        ],
    )


def _sensitivity_section() -> html.Div:
    """Interactive sensitivity heatmap with parameter dropdowns."""
    param_options = [
        {"label": pdef.get("description", key)[:45], "value": key}
        for key, pdef in PARAMETER_DEFINITIONS.items()
        if pdef.get("type") != str
    ]

    outcome_options = [
        {"label": "Avg Stress", "value": "avg_stress"},
        {"label": "Total Labor Hours", "value": "total_labor_hours"},
        {"label": "Social Efficiency", "value": "social_efficiency"},
        {"label": "Income Gini", "value": "gini_income"},
        {"label": "Delegation Fraction", "value": "tasks_delegated_frac"},
        {"label": "Avg Income", "value": "avg_income"},
    ]

    return card(
        title="Sensitivity Explorer",
        subtitle="Interactive parameter space exploration (on-demand sweep)",
        children=[
            dbc.Row([
                dbc.Col([
                    html.Label("X-axis Parameter", className="cp-controls__slider-label"),
                    dcc.Dropdown(
                        id="sensitivity-x-param",
                        options=param_options,
                        value="delegation_preference_mean",
                        clearable=False,
                        style={"fontSize": "var(--cp-text-sm)"},
                    ),
                ], lg=3, md=6, xs=12),
                dbc.Col([
                    html.Label("Y-axis Parameter", className="cp-controls__slider-label"),
                    dcc.Dropdown(
                        id="sensitivity-y-param",
                        options=param_options,
                        value="social_conformity_pressure",
                        clearable=False,
                        style={"fontSize": "var(--cp-text-sm)"},
                    ),
                ], lg=3, md=6, xs=12),
                dbc.Col([
                    html.Label("Color Metric", className="cp-controls__slider-label"),
                    dcc.Dropdown(
                        id="sensitivity-outcome",
                        options=outcome_options,
                        value="avg_stress",
                        clearable=False,
                        style={"fontSize": "var(--cp-text-sm)"},
                    ),
                ], lg=3, md=6, xs=12),
                dbc.Col([
                    html.Label("Grid & Steps", className="cp-controls__slider-label"),
                    dbc.Row([
                        dbc.Col(
                            dbc.Input(
                                id="sensitivity-grid-size", type="number",
                                value=6, min=3, max=10, step=1, size="sm",
                                placeholder="Grid",
                            ),
                            width=6,
                        ),
                        dbc.Col(
                            dbc.Input(
                                id="sensitivity-steps", type="number",
                                value=40, min=10, max=200, step=10, size="sm",
                                placeholder="Steps",
                            ),
                            width=6,
                        ),
                    ], className="g-1"),
                ], lg=3, md=6, xs=12),
            ], className="g-3 mb-3"),
            html.Div(
                dbc.Button(
                    [html.I(className="fas fa-fire me-2"), "Run Sweep"],
                    id="btn-run-sweep",
                    className="cp-btn-primary",
                    size="sm",
                ),
                className="text-center mb-3",
            ),
            html.Div(id="sensitivity-status", className="mb-2"),
            html.Div(
                dcc.Graph(
                    id="chart-sensitivity-heatmap",
                    style={"width": "100%", "height": "100%"},
                    config={"displayModeBar": True, "displaylogo": False, "responsive": True},
                ),
                className="cp-chart-container",
                style={"height": "480px"},
            ),
        ],
    )


# =========================================================================
# Page layout
# =========================================================================

layout = html.Div([
    html.Div([
        html.H2("Analysis", className="cp-page-title"),
        html.P(
            "Research results, hypothesis evidence, and parameter sensitivity exploration.",
            className="cp-page-subtitle",
        ),
    ], className="cp-page-header"),

    html.Div("HYPOTHESIS SCOREBOARD", className="cp-section-label",
             style={"paddingLeft": "0"}),
    _hypothesis_cards(),

    _comparison_section(),
    html.Div(className="mb-4"),

    _sensitivity_section(),
])


# =========================================================================
# Callback 1: Hypothesis detail toggles
# =========================================================================

for h in HYPOTHESES:
    hid = h["id"].lower()

    @callback(
        Output(f"collapse-{hid}", "is_open"),
        Input(f"toggle-{hid}", "n_clicks"),
        State(f"collapse-{hid}", "is_open"),
        prevent_initial_call=True,
    )
    def _toggle_hypothesis(n_clicks, is_open, _hid=hid):
        return not is_open


# =========================================================================
# Callback 2: Run Both Presets — Type A vs Type B comparison
# =========================================================================

@callback(
    Output("comparison-table-container", "children"),
    Output("chart-ab-comparison", "figure"),
    Output("comparison-status", "children"),
    Input("btn-run-both", "n_clicks"),
    State("comparison-steps-input", "value"),
    prevent_initial_call=True,
)
def run_both_presets(n_clicks, n_steps):
    """Run Type A and Type B simulations and display comparison."""
    n_steps = int(n_steps or 60)

    status = dbc.Alert(
        [html.I(className="fas fa-spinner fa-spin me-2"), "Running simulations..."],
        color="info", className="py-2",
    )

    t0 = time.time()

    # --- Run Type A ---
    preset_a = {k: v for k, v in TYPE_A_PRESET.items()
                if k not in ("label", "description", "empirical_basis")}
    model_a = ConvenienceParadoxModel(**preset_a)
    for _ in range(n_steps):
        model_a.step()
    df_a = model_a.get_model_dataframe()

    # --- Run Type B ---
    preset_b = {k: v for k, v in TYPE_B_PRESET.items()
                if k not in ("label", "description", "empirical_basis")}
    model_b = ConvenienceParadoxModel(**preset_b)
    for _ in range(n_steps):
        model_b.step()
    df_b = model_b.get_model_dataframe()

    elapsed = time.time() - t0

    # --- Extract final metrics ---
    metrics_config = [
        ("avg_stress", "Avg Stress", ".3f"),
        ("total_labor_hours", "Labor Hours", ".1f"),
        ("social_efficiency", "Efficiency", ".3f"),
        ("gini_income", "Income Gini", ".3f"),
        ("avg_delegation_rate", "Delegation Rate", ".3f"),
        ("avg_income", "Avg Income", ".2f"),
    ]

    last_a = df_a.iloc[-1] if len(df_a) > 0 else {}
    last_b = df_b.iloc[-1] if len(df_b) > 0 else {}

    # --- Build comparison table ---
    table_rows = [
        html.Tr([
            html.Th("Metric", style={"width": "40%"}),
            html.Th("Type A", className="text-end"),
            html.Th("Type B", className="text-end"),
            html.Th("Delta", className="text-end"),
        ], className="table-light"),
    ]

    bar_labels = []
    bar_a_vals = []
    bar_b_vals = []

    for key, label, fmt in metrics_config:
        va = float(last_a.get(key, 0))
        vb = float(last_b.get(key, 0))
        if va != 0:
            delta_pct = (vb - va) / abs(va) * 100
            delta_str = f"{'+' if delta_pct >= 0 else ''}{delta_pct:.1f}%"
            delta_color = "var(--cp-danger)" if abs(delta_pct) > 15 else "var(--cp-text-secondary)"
        else:
            delta_str = "—"
            delta_color = "var(--cp-text-secondary)"

        table_rows.append(html.Tr([
            html.Td(label, style={"fontWeight": "var(--cp-weight-semibold)"}),
            html.Td(f"{va:{fmt}}", className="text-end"),
            html.Td(f"{vb:{fmt}}", className="text-end"),
            html.Td(delta_str, className="text-end",
                     style={"color": delta_color, "fontWeight": "var(--cp-weight-semibold)"}),
        ]))

        bar_labels.append(label)
        bar_a_vals.append(va)
        bar_b_vals.append(vb)

    # Add key parameter differences
    param_diffs = [
        ("delegation_preference_mean", "Delegation Mean", ".2f"),
        ("service_cost_factor", "Service Cost", ".2f"),
        ("social_conformity_pressure", "Conformity", ".2f"),
    ]

    table_rows.append(html.Tr([
        html.Td(html.Strong("Parameters"), colSpan=4,
                style={"backgroundColor": "var(--cp-bg-secondary)"}),
    ]))

    for key, label, fmt in param_diffs:
        va = TYPE_A_PRESET.get(key, 0)
        vb = TYPE_B_PRESET.get(key, 0)
        table_rows.append(html.Tr([
            html.Td(label),
            html.Td(f"{va:{fmt}}", className="text-end"),
            html.Td(f"{vb:{fmt}}", className="text-end"),
            html.Td("", className="text-end"),
        ], style={"color": "var(--cp-text-secondary)", "fontSize": "var(--cp-text-sm)"}))

    comparison_table = html.Table(
        [html.Tbody(table_rows)],
        className="table table-sm table-hover mb-0",
        style={"fontSize": "var(--cp-text-sm)"},
    )

    # --- Build grouped bar chart ---
    # Normalize for visual comparison (different scales)
    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="Type A (Autonomy)",
        x=bar_labels, y=bar_a_vals,
        marker_color=CHART_COLORWAY[0],
        text=[f"{v:.2f}" for v in bar_a_vals],
        textposition="outside",
        textfont_size=9,
    ))
    fig.add_trace(go.Bar(
        name="Type B (Convenience)",
        x=bar_labels, y=bar_b_vals,
        marker_color=CHART_COLORWAY[1],
        text=[f"{v:.2f}" for v in bar_b_vals],
        textposition="outside",
        textfont_size=9,
    ))

    fig.update_layout(
        barmode="group",
        margin=dict(t=30, b=50, l=56, r=16),
        height=380,
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
        yaxis_title="Value",
        xaxis_tickangle=-20,
    )

    status_msg = dbc.Alert(
        f"Completed: {n_steps} steps each, {elapsed:.1f}s total. "
        f"Type A final stress: {float(last_a.get('avg_stress', 0)):.3f}, "
        f"Type B final stress: {float(last_b.get('avg_stress', 0)):.3f}.",
        color="success", className="py-2",
    )

    return comparison_table, fig, status_msg


# =========================================================================
# Callback 3: Sensitivity heatmap sweep
# =========================================================================

@callback(
    Output("chart-sensitivity-heatmap", "figure"),
    Output("sensitivity-status", "children"),
    Input("btn-run-sweep", "n_clicks"),
    State("sensitivity-x-param", "value"),
    State("sensitivity-y-param", "value"),
    State("sensitivity-outcome", "value"),
    State("sensitivity-grid-size", "value"),
    State("sensitivity-steps", "value"),
    prevent_initial_call=True,
)
def run_sensitivity_sweep(n_clicks, x_param, y_param, outcome,
                          grid_size, n_steps):
    """Run a lightweight on-demand parameter sweep and render a heatmap."""
    grid_size = int(grid_size or 6)
    n_steps = int(n_steps or 40)

    if x_param == y_param:
        return no_update, dbc.Alert(
            "X and Y parameters must be different.", color="warning", className="py-2",
        )

    x_def = PARAMETER_DEFINITIONS.get(x_param, {})
    y_def = PARAMETER_DEFINITIONS.get(y_param, {})

    x_min, x_max = x_def.get("min", 0), x_def.get("max", 1)
    y_min, y_max = y_def.get("min", 0), y_def.get("max", 1)

    x_vals = np.linspace(x_min, x_max, grid_size)
    y_vals = np.linspace(y_min, y_max, grid_size)

    base_params = {k: v["default"] for k, v in PARAMETER_DEFINITIONS.items()
                   if "default" in v and k != "network_type"}
    base_params["network_type"] = "small_world"
    base_params["seed"] = 42

    t0 = time.time()
    results = np.zeros((grid_size, grid_size))

    total_runs = grid_size * grid_size
    for i, yv in enumerate(y_vals):
        for j, xv in enumerate(x_vals):
            params = {**base_params, x_param: float(xv), y_param: float(yv)}

            # Ensure integer params stay integer
            if x_def.get("type") == int:
                params[x_param] = int(round(xv))
            if y_def.get("type") == int:
                params[y_param] = int(round(yv))

            try:
                model = ConvenienceParadoxModel(**params)
                for _ in range(n_steps):
                    model.step()
                df = model.get_model_dataframe()
                if len(df) > 0:
                    # Average over last 20% of steps for equilibrium
                    tail = max(1, len(df) // 5)
                    results[i, j] = float(df[outcome].iloc[-tail:].mean())
                else:
                    results[i, j] = float("nan")
            except Exception as e:
                logger.warning("Sweep run failed for %s=%s, %s=%s: %s",
                               x_param, xv, y_param, yv, e)
                results[i, j] = float("nan")

    elapsed = time.time() - t0

    # Format axis labels
    x_fmt = ".0f" if x_def.get("type") == int else ".2f"
    y_fmt = ".0f" if y_def.get("type") == int else ".2f"

    x_labels = [f"{v:{x_fmt}}" for v in x_vals]
    y_labels = [f"{v:{y_fmt}}" for v in y_vals]

    outcome_label = outcome.replace("_", " ").title()
    cmap = "RdYlGn_r" if "stress" in outcome else "Viridis"

    fig = go.Figure(data=go.Heatmap(
        z=results,
        x=x_labels,
        y=y_labels,
        colorscale=cmap,
        colorbar=dict(title=outcome_label),
        hovertemplate=(
            f"{x_param}: %{{x}}<br>"
            f"{y_param}: %{{y}}<br>"
            f"{outcome_label}: %{{z:.3f}}<extra></extra>"
        ),
    ))

    # Add cell annotations for small grids
    if grid_size <= 8:
        for i in range(grid_size):
            for j in range(grid_size):
                val = results[i, j]
                if not np.isnan(val):
                    fig.add_annotation(
                        x=x_labels[j], y=y_labels[i],
                        text=f"{val:.2f}",
                        showarrow=False,
                        font=dict(
                            size=10,
                            color="white" if val > np.nanmean(results) else "black",
                        ),
                    )

    fig.update_layout(
        xaxis_title=x_param.replace("_", " ").title(),
        yaxis_title=y_param.replace("_", " ").title(),
        margin=dict(t=30, b=60, l=80, r=20),
        height=480,
    )

    status = dbc.Alert(
        f"Sweep complete: {total_runs} runs x {n_steps} steps in {elapsed:.1f}s. "
        f"Range: {np.nanmin(results):.3f} – {np.nanmax(results):.3f}.",
        color="success", className="py-2",
    )

    return fig, status
