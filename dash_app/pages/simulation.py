"""
Page 1: Simulation Dashboard

The primary dashboard page for controlling and visualizing ABM simulations.
Combines parameter configuration (in the sidebar), simulation controls,
and live time-series / distribution / flow visualizations.

Callback architecture:
    - Sidebar controls (preset, sliders, buttons) are defined in
      components/controls.py and rendered into the sidebar by app.py.
    - A single sim-trigger-store (dcc.Store in app layout) acts as the
      signal bus: sim action callbacks write to it, chart callbacks read it.
    - Chart callbacks access the model via dash_app.state (server-side),
      avoiding large DataFrame serialization through the browser.

Goals served: A (interactive controls), B (visual analytics), C (computational model)
"""

from __future__ import annotations

import logging
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
import networkx as nx
import numpy as np
import plotly.graph_objects as go
from dash import html, dcc, callback, Input, Output, State, ctx, no_update

from dash_app.components.card import kpi_card, chart_card
from dash_app.components.charts import CHART_COLORWAY
import dash_app.state as sim_state
from model.model import ConvenienceParadoxModel
from model.params import (
    PARAMETER_DEFINITIONS, TYPE_A_PRESET, TYPE_B_PRESET,
    get_preset, TASK_TYPES,
)

logger = logging.getLogger(__name__)

dash.register_page(
    __name__,
    path="/",
    name="Simulation Dashboard",
    order=0,
)

# --- Parameter keys used by sidebar sliders (must match controls.py) ---

_ALL_SLIDER_PARAMS = [
    "delegation_preference_mean", "service_cost_factor",
    "social_conformity_pressure", "tasks_per_step_mean",
    "initial_available_time", "num_agents",
    "delegation_preference_std", "tasks_per_step_std",
    "stress_threshold", "stress_recovery_rate", "adaptation_rate",
]


# =========================================================================
# Layout
# =========================================================================

def _kpi_row() -> dbc.Row:
    """Top row of KPI summary cards."""
    return dbc.Row(
        [
            dbc.Col(kpi_card("Avg Stress", "—", card_id="kpi-stress"), lg=3, md=6, xs=6),
            dbc.Col(kpi_card("Total Labor Hours", "—", card_id="kpi-labor"), lg=3, md=6, xs=6),
            dbc.Col(kpi_card("Social Efficiency", "—", card_id="kpi-efficiency"), lg=3, md=6, xs=6),
            dbc.Col(kpi_card("Income Gini", "—", card_id="kpi-gini"), lg=3, md=6, xs=6),
        ],
        className="g-3 mb-3",
    )


def _charts_row_1() -> dbc.Row:
    return dbc.Row(
        [
            dbc.Col(
                chart_card("Total Labor Hours", "chart-labor-hours",
                           subtitle="H1 — Delegation paradox", height="320px"),
                lg=8, md=12,
            ),
            dbc.Col(
                chart_card("Stress Distribution", "chart-stress-dist", height="320px"),
                lg=4, md=12,
            ),
        ],
        className="g-3 mb-3",
    )


def _charts_row_2() -> dbc.Row:
    return dbc.Row(
        [
            dbc.Col(
                chart_card("Stress & Delegation", "chart-stress-delegation",
                           subtitle="H2, H3 — Dual axis", height="320px"),
                lg=8, md=12,
            ),
            dbc.Col(
                chart_card("Delegation Preferences", "chart-delegation-dist", height="320px"),
                lg=4, md=12,
            ),
        ],
        className="g-3 mb-3",
    )


def _charts_row_3() -> dbc.Row:
    return dbc.Row(
        [
            dbc.Col(
                chart_card("Social Efficiency", "chart-efficiency",
                           subtitle="H2 — Involution threshold", height="300px"),
                lg=4, md=6, xs=12,
            ),
            dbc.Col(
                chart_card("Market Health", "chart-market-health",
                           subtitle="Unmatched tasks", height="300px"),
                lg=4, md=6, xs=12,
            ),
            dbc.Col(
                chart_card("Provider vs Consumer", "chart-provider-consumer", height="300px"),
                lg=4, md=12,
            ),
        ],
        className="g-3 mb-3",
    )


def _advanced_viz_row() -> dbc.Row:
    return dbc.Row(
        [
            dbc.Col(
                chart_card("Task Flow", "chart-sankey",
                           subtitle="Service pipeline", height="350px"),
                lg=4, md=6, xs=12,
            ),
            dbc.Col(
                chart_card("Fee Flow", "chart-waterfall",
                           subtitle="Economic transfer", height="350px"),
                lg=4, md=6, xs=12,
            ),
            dbc.Col(
                chart_card("Network Topology", "chart-network",
                           subtitle="Agent connections", height="350px"),
                lg=4, md=12,
            ),
        ],
        className="g-3 mb-3",
    )


layout = html.Div(
    [
        dcc.Store(id="simulation-page-store", data={"mounted": True}),
        html.Div(
            [
                html.H2("Simulation Dashboard", className="cp-page-title"),
                html.P(
                    "Initialize a simulation and run steps to see live results.",
                    className="cp-page-subtitle",
                ),
            ],
            className="cp-page-header",
        ),
        _kpi_row(),
        _charts_row_1(),
        _charts_row_2(),
        _charts_row_3(),
        _advanced_viz_row(),
    ]
)


# =========================================================================
# Helper: empty Plotly figure
# =========================================================================

def _empty_fig(msg: str = "Initialize a simulation to see data") -> go.Figure:
    """Return a blank figure with a centered annotation."""
    fig = go.Figure()
    fig.add_annotation(
        text=msg, xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=14, color="#94A3B8"),
    )
    fig.update_layout(
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(t=10, b=10, l=10, r=10),
    )
    return fig


# =========================================================================
# Callback 1: Preset selector → update all sliders
# =========================================================================

@callback(
    [Output(f"slider-{p}", "value") for p in _ALL_SLIDER_PARAMS]
    + [Output("radio-network-type", "value")],
    Input("preset-selector", "value"),
    prevent_initial_call=True,
)
def apply_preset(preset_name: str):
    """When a preset is selected, update all parameter sliders to match."""
    if preset_name == "custom":
        return [no_update] * (len(_ALL_SLIDER_PARAMS) + 1)
    preset = get_preset(preset_name)
    values = [preset.get(p, PARAMETER_DEFINITIONS[p]["default"]) for p in _ALL_SLIDER_PARAMS]
    values.append(preset.get("network_type", "small_world"))
    return values


# =========================================================================
# Callback 2: Toggle advanced parameters collapse
# =========================================================================

@callback(
    Output("advanced-collapse", "is_open"),
    Input("btn-toggle-advanced", "n_clicks"),
    State("advanced-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_advanced(n_clicks, is_open):
    return not is_open


# =========================================================================
# Callback 3: Bidirectional slider ↔ number input sync
#
# When the slider moves  → format and push value into the number input.
# When the input changes → clamp to [min, max] and push value into slider.
# Using allow_duplicate=True so both outputs can be targeted by other
# callbacks (e.g. apply_preset still writes to slider-{p}.value).
# =========================================================================

for _pk in _ALL_SLIDER_PARAMS:
    @callback(
        Output(f"slider-{_pk}", "value", allow_duplicate=True),
        Output(f"input-{_pk}", "value"),
        Input(f"slider-{_pk}", "value"),
        Input(f"input-{_pk}", "value"),
        prevent_initial_call=True,
    )
    def _sync_slider_input(slider_val, input_val, key=_pk):
        """Keep slider and number input in sync when either changes."""
        triggered = ctx.triggered_id
        pdef = PARAMETER_DEFINITIONS[key]
        p_min, p_max = pdef["min"], pdef["max"]

        if triggered == f"slider-{key}":
            # Slider moved — update the number input display value
            if slider_val is None:
                return no_update, no_update
            if pdef["type"] is int:
                display = int(slider_val)
            else:
                display = round(float(slider_val), 4)
            return no_update, display
        else:
            # Number input edited — clamp to valid range and update slider
            if input_val is None:
                return no_update, no_update
            try:
                clamped = float(input_val)
            except (TypeError, ValueError):
                return no_update, no_update
            clamped = max(p_min, min(p_max, clamped))
            if pdef["type"] is int:
                clamped = int(clamped)
            return clamped, no_update


# =========================================================================
# Callback 4: Simulation actions (Init / Step / Run / Reset)
# =========================================================================

@callback(
    Output("sim-trigger-store", "data"),
    Output("sim-status-display", "children"),
    Input("btn-init", "n_clicks"),
    Input("btn-step", "n_clicks"),
    Input("btn-run", "n_clicks"),
    Input("btn-reset", "n_clicks"),
    [State(f"slider-{p}", "value") for p in _ALL_SLIDER_PARAMS]
    + [State("radio-network-type", "value"),
       State("input-run-steps", "value"),
       State("preset-selector", "value")],
    prevent_initial_call=True,
)
def handle_sim_action(n_init, n_step, n_run, n_reset, *state_values):
    """Handle all simulation control button clicks."""
    triggered = ctx.triggered_id
    if triggered is None:
        return no_update, no_update

    # Unpack state values
    slider_vals = list(state_values[:len(_ALL_SLIDER_PARAMS)])
    network_type = state_values[len(_ALL_SLIDER_PARAMS)]
    run_steps = state_values[len(_ALL_SLIDER_PARAMS) + 1] or 50
    preset_name = state_values[len(_ALL_SLIDER_PARAMS) + 2]

    now = datetime.now().isoformat()

    if triggered == "btn-init":
        params = {p: slider_vals[i] for i, p in enumerate(_ALL_SLIDER_PARAMS)}
        params["network_type"] = network_type or "small_world"
        params["seed"] = 42
        # Ensure integer type for num_agents
        params["num_agents"] = int(params["num_agents"])

        model = ConvenienceParadoxModel(**params)
        sim_state.set_model(model)
        sim_state.set_run_id(None)
        sim_state.set_current_preset(preset_name or "custom")
        logger.info("Simulation initialized with %d agents", params["num_agents"])

        status = html.Span(
            [html.I(className="fas fa-check-circle me-1"),
             f"Initialized — {params['num_agents']} agents"],
            style={"fontSize": "var(--cp-text-xs)", "color": "var(--cp-success)"},
        )
        return {"step": 0, "action": "init", "ts": now}, status

    elif triggered == "btn-step":
        model = sim_state.get_model()
        if model is None:
            status = html.Span(
                "Initialize first",
                style={"fontSize": "var(--cp-text-xs)", "color": "var(--cp-danger)"},
            )
            return no_update, status
        model.step()
        step = model.current_step
        status = html.Span(
            f"Step {step}",
            style={"fontSize": "var(--cp-text-xs)", "color": "var(--cp-text-secondary)"},
        )
        return {"step": step, "action": "step", "ts": now}, status

    elif triggered == "btn-run":
        model = sim_state.get_model()
        if model is None:
            status = html.Span(
                "Initialize first",
                style={"fontSize": "var(--cp-text-xs)", "color": "var(--cp-danger)"},
            )
            return no_update, status
        n = int(run_steps)
        for _ in range(n):
            model.step()
        step = model.current_step
        status = html.Span(
            f"Step {step} (ran {n})",
            style={"fontSize": "var(--cp-text-xs)", "color": "var(--cp-text-secondary)"},
        )
        return {"step": step, "action": "run", "ts": now}, status

    elif triggered == "btn-reset":
        sim_state.clear_model()
        status = html.Span(
            "Not initialized",
            style={"fontSize": "var(--cp-text-xs)", "color": "var(--cp-text-tertiary)"},
        )
        return {"step": 0, "action": "reset", "ts": now}, status

    return no_update, no_update


# =========================================================================
# Callback 5: KPI card updates
# =========================================================================

@callback(
    Output("kpi-stress-value", "children"),
    Output("kpi-labor-value", "children"),
    Output("kpi-efficiency-value", "children"),
    Output("kpi-gini-value", "children"),
    Input("sim-trigger-store", "data"),
    Input("simulation-page-store", "data"),
)
def update_kpis(trigger, page_state):
    model = sim_state.get_model()
    if model is None or model.current_step == 0:
        return "—", "—", "—", "—"

    df = model.get_model_dataframe()
    if df.empty:
        return "—", "—", "—", "—"

    latest = df.iloc[-1]
    stress = f"{latest['avg_stress']:.3f}"
    labor = f"{latest['total_labor_hours']:.1f}"
    efficiency = f"{latest['social_efficiency']:.3f}"
    gini = f"{latest['gini_income']:.3f}"
    return stress, labor, efficiency, gini


# =========================================================================
# Callback 6: Time series charts
# =========================================================================

@callback(
    Output("chart-labor-hours", "figure"),
    Output("chart-stress-delegation", "figure"),
    Output("chart-efficiency", "figure"),
    Output("chart-market-health", "figure"),
    Input("sim-trigger-store", "data"),
    Input("simulation-page-store", "data"),
)
def update_time_series(trigger, page_state):
    model = sim_state.get_model()
    if model is None:
        return _empty_fig(), _empty_fig(), _empty_fig(), _empty_fig()

    df = model.get_model_dataframe()
    if df.empty:
        return _empty_fig("Run at least one step"), _empty_fig("Run at least one step"), \
               _empty_fig("Run at least one step"), _empty_fig("Run at least one step")

    steps = list(range(len(df)))

    # Chart 1: Total Labor Hours (H1)
    fig_labor = go.Figure()
    fig_labor.add_trace(go.Scatter(
        x=steps, y=df["total_labor_hours"],
        mode="lines", name="Total Labor Hours",
        line=dict(color=CHART_COLORWAY[0], width=2),
        fill="tozeroy", fillcolor="rgba(44,140,153,0.1)",
    ))
    fig_labor.update_layout(
        xaxis_title="Step", yaxis_title="Hours",
        margin=dict(t=10, b=40, l=56, r=16),
    )

    # Chart 2: Stress & Delegation (dual axis)
    fig_sd = go.Figure()
    fig_sd.add_trace(go.Scatter(
        x=steps, y=df["avg_stress"],
        mode="lines", name="Avg Stress",
        line=dict(color=CHART_COLORWAY[4], width=2),
    ))
    fig_sd.add_trace(go.Scatter(
        x=steps, y=df["avg_delegation_rate"],
        mode="lines", name="Avg Delegation",
        line=dict(color=CHART_COLORWAY[1], width=2),
        yaxis="y2",
    ))
    fig_sd.update_layout(
        xaxis_title="Step",
        yaxis=dict(title="Stress", side="left"),
        yaxis2=dict(
            title="Delegation Preference", side="right",
            overlaying="y", showgrid=False,
            range=[0, 1],
        ),
        margin=dict(t=10, b=40, l=56, r=56),
    )

    # Chart 3: Social Efficiency (H2)
    fig_eff = go.Figure()
    fig_eff.add_trace(go.Scatter(
        x=steps, y=df["social_efficiency"],
        mode="lines", name="Social Efficiency",
        line=dict(color=CHART_COLORWAY[2], width=2),
        fill="tozeroy", fillcolor="rgba(39,174,96,0.1)",
    ))
    fig_eff.update_layout(
        xaxis_title="Step", yaxis_title="Tasks / Hour",
        margin=dict(t=10, b=40, l=56, r=16),
    )

    # Chart 4: Market Health (unmatched tasks + delegation fraction)
    fig_mh = go.Figure()
    fig_mh.add_trace(go.Bar(
        x=steps, y=df["unmatched_tasks"],
        name="Unmatched Tasks",
        marker_color=CHART_COLORWAY[4],
        opacity=0.7,
    ))
    fig_mh.add_trace(go.Scatter(
        x=steps, y=df["tasks_delegated_frac"],
        mode="lines", name="Delegation Fraction",
        line=dict(color=CHART_COLORWAY[1], width=2),
        yaxis="y2",
    ))
    fig_mh.update_layout(
        xaxis_title="Step",
        yaxis=dict(title="Unmatched Count", side="left"),
        yaxis2=dict(
            title="Fraction Delegated", side="right",
            overlaying="y", showgrid=False,
            range=[0, 1],
        ),
        margin=dict(t=10, b=40, l=56, r=56),
        barmode="overlay",
    )

    return fig_labor, fig_sd, fig_eff, fig_mh


# =========================================================================
# Callback 7: Distribution charts
# =========================================================================

@callback(
    Output("chart-stress-dist", "figure"),
    Output("chart-delegation-dist", "figure"),
    Output("chart-provider-consumer", "figure"),
    Input("sim-trigger-store", "data"),
    Input("simulation-page-store", "data"),
)
def update_distributions(trigger, page_state):
    model = sim_state.get_model()
    if model is None:
        return _empty_fig(), _empty_fig(), _empty_fig()

    agents = model.get_agent_states()
    if not agents:
        return _empty_fig(), _empty_fig(), _empty_fig()

    stress_vals = [a["stress_level"] for a in agents]
    deleg_vals = [a["delegation_preference"] for a in agents]
    time_providing = [a["time_spent_providing"] for a in agents]
    tasks_delegated = [a["tasks_delegated"] for a in agents]

    # Stress distribution histogram
    fig_stress = go.Figure()
    fig_stress.add_trace(go.Histogram(
        x=stress_vals, nbinsx=20,
        marker_color=CHART_COLORWAY[4],
        opacity=0.8,
        name="Agents",
    ))
    fig_stress.update_layout(
        xaxis_title="Stress Level",
        yaxis_title="Count",
        margin=dict(t=10, b=40, l=48, r=16),
        bargap=0.05,
    )

    # Delegation preference distribution
    fig_deleg = go.Figure()
    fig_deleg.add_trace(go.Histogram(
        x=deleg_vals, nbinsx=20,
        marker_color=CHART_COLORWAY[1],
        opacity=0.8,
        name="Agents",
    ))
    fig_deleg.update_layout(
        xaxis_title="Delegation Preference",
        yaxis_title="Count",
        margin=dict(t=10, b=40, l=48, r=16),
        bargap=0.05,
    )

    # Provider vs Consumer scatter
    fig_pc = go.Figure()
    fig_pc.add_trace(go.Scatter(
        x=tasks_delegated,
        y=time_providing,
        mode="markers",
        marker=dict(
            color=stress_vals,
            colorscale="RdYlGn_r",
            size=8,
            opacity=0.7,
            colorbar=dict(title="Stress", thickness=12, len=0.7),
            line=dict(width=0.5, color="white"),
        ),
        name="Agents",
        hovertemplate=(
            "Delegated: %{x}<br>"
            "Providing: %{y:.1f}h<br>"
            "Stress: %{marker.color:.3f}<extra></extra>"
        ),
    ))
    fig_pc.update_layout(
        xaxis_title="Tasks Delegated (cumul.)",
        yaxis_title="Hours Providing (cumul.)",
        margin=dict(t=10, b=40, l=56, r=16),
    )

    return fig_stress, fig_deleg, fig_pc


# =========================================================================
# Callback 8: Flow diagrams (Sankey + Waterfall)
# =========================================================================

@callback(
    Output("chart-sankey", "figure"),
    Output("chart-waterfall", "figure"),
    Input("sim-trigger-store", "data"),
    Input("simulation-page-store", "data"),
)
def update_flow_diagrams(trigger, page_state):
    model = sim_state.get_model()
    if model is None:
        return _empty_fig(), _empty_fig()

    total = model._step_tasks_total
    delegated = model._step_tasks_delegated
    matched = model._step_tasks_matched
    self_served = total - delegated
    unmatched = delegated - matched

    if total == 0:
        return _empty_fig("Run at least one step"), _empty_fig("Run at least one step")

    # --- Sankey: task flow pipeline ---
    fig_sankey = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20,
            thickness=20,
            label=["Generated", "Self-Served", "Delegated", "Matched", "Unmatched"],
            color=[
                "#94A3B8",           # Generated — neutral
                CHART_COLORWAY[0],   # Self-Served — teal
                CHART_COLORWAY[1],   # Delegated — orange
                CHART_COLORWAY[2],   # Matched — green
                CHART_COLORWAY[4],   # Unmatched — red
            ],
        ),
        link=dict(
            source=[0, 0, 2, 2],
            target=[1, 2, 3, 4],
            value=[
                max(self_served, 0),
                max(delegated, 0),
                max(matched, 0),
                max(unmatched, 0),
            ],
            color=[
                "rgba(44,140,153,0.25)",
                "rgba(230,126,34,0.25)",
                "rgba(39,174,96,0.25)",
                "rgba(231,76,60,0.25)",
            ],
        ),
    ))
    fig_sankey.update_layout(margin=dict(t=10, b=10, l=10, r=10))

    # --- Waterfall: economic fee flow ---
    agents = model.get_agent_states()
    provider_earnings = sum(a["income"] for a in agents if a["income"] > 0)
    delegator_costs = sum(a["income"] for a in agents if a["income"] < 0)
    net_balance = provider_earnings + delegator_costs

    fig_waterfall = go.Figure(go.Waterfall(
        orientation="v",
        x=["Provider<br>Earnings", "Delegator<br>Fees", "Net<br>Balance"],
        y=[provider_earnings, delegator_costs, net_balance],
        measure=["relative", "relative", "total"],
        textposition="outside",
        text=[f"+{provider_earnings:.1f}", f"{delegator_costs:.1f}", f"{net_balance:.1f}"],
        connector=dict(line=dict(color="#CBD5E1", width=1)),
        increasing=dict(marker_color=CHART_COLORWAY[2]),
        decreasing=dict(marker_color=CHART_COLORWAY[4]),
        totals=dict(marker_color=CHART_COLORWAY[5]),
    ))
    fig_waterfall.update_layout(
        yaxis_title="Cumulative Income",
        margin=dict(t=10, b=40, l=56, r=16),
        showlegend=False,
    )

    return fig_sankey, fig_waterfall


# =========================================================================
# Callback 9: Network topology graph
# =========================================================================

@callback(
    Output("chart-network", "figure"),
    Input("sim-trigger-store", "data"),
    Input("simulation-page-store", "data"),
)
def update_network(trigger, page_state):
    model = sim_state.get_model()
    if model is None:
        return _empty_fig()

    G = model.grid.G
    pos = nx.spring_layout(G, seed=42, k=1.5 / np.sqrt(len(G)), iterations=50)

    agents_dict = {a["id"]: a for a in model.get_agent_states()}

    # Edge traces
    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    # Node traces
    node_x = [pos[n][0] for n in G.nodes()]
    node_y = [pos[n][1] for n in G.nodes()]
    node_stress = [agents_dict.get(n, {}).get("stress_level", 0) for n in G.nodes()]
    node_deleg = [agents_dict.get(n, {}).get("delegation_preference", 0.5) for n in G.nodes()]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(width=0.4, color="#CBD5E1"),
        hoverinfo="none",
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode="markers",
        marker=dict(
            size=7,
            color=node_stress,
            colorscale="RdYlGn_r",
            cmin=0, cmax=1,
            colorbar=dict(title="Stress", thickness=10, len=0.6),
            line=dict(width=0.5, color="white"),
        ),
        text=[f"Agent {n}<br>Stress: {node_stress[i]:.3f}<br>Deleg: {node_deleg[i]:.3f}"
              for i, n in enumerate(G.nodes())],
        hoverinfo="text",
        showlegend=False,
    ))
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(t=5, b=5, l=5, r=5),
        hovermode="closest",
    )
    return fig
