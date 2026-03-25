"""
Page 3: Run Manager

Experiment database management with query, filtering, comparison, and
deletion capabilities. Uses Dash AG Grid for the interactive data table.

Callback architecture:
    - On page load and after mutations, the runs-grid is repopulated from SQLite.
    - Filter controls (search, preset, date range) feed into the query.
    - Delete operations cascade to both runs and run_steps tables.
    - The comparison panel activates when 2+ runs are selected in the grid,
      showing metric deltas and overlaid time series.

Goals served: A (interactive application), B (data management front-end)
"""

from __future__ import annotations

import logging

import dash
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import plotly.graph_objects as go
from dash import html, dcc, callback, Input, Output, State, ctx, no_update

from dash_app.components.card import card, kpi_card
from dash_app.components.charts import CHART_COLORWAY
from dash_app.components.empty_states import empty_state
import dash_app.db as db
import dash_app.state as app_state
from dash_app.utils import format_run_label

logger = logging.getLogger(__name__)

dash.register_page(
    __name__,
    path="/run-manager",
    name="Run Manager",
    order=2,
)



# =========================================================================
# Layout
# =========================================================================

def _filter_bar() -> html.Div:
    """Search and filter controls above the data table."""
    return card(
        children=dbc.Row([
            dbc.Col([
                html.Label("Search", className="cp-controls__slider-label"),
                dbc.Input(
                    id="run-search-input",
                    placeholder="Search by run name or preset...",
                    type="text", size="sm", debounce=True,
                ),
            ], lg=3, md=6, xs=12),
            dbc.Col([
                html.Label("Preset Filter", className="cp-controls__slider-label"),
                dcc.Dropdown(
                    id="run-preset-filter",
                    options=[
                        {"label": "All Presets", "value": "all"},
                        {"label": "Type A", "value": "type_a"},
                        {"label": "Type B", "value": "type_b"},
                        {"label": "Custom", "value": "custom"},
                    ],
                    value="all", clearable=False,
                    style={"fontSize": "var(--cp-text-sm)"},
                ),
            ], lg=2, md=6, xs=12),
            dbc.Col([
                html.Label("Date Range", className="cp-controls__slider-label"),
                dcc.DatePickerRange(
                    id="run-date-range",
                    display_format="YYYY-MM-DD",
                    style={"fontSize": "var(--cp-text-sm)"},
                ),
            ], lg=3, md=6, xs=12),
            dbc.Col([
                html.Div([
                    dbc.Button(
                        [html.I(className="fas fa-save me-1"), "Save Current"],
                        id="btn-save-run",
                        className="cp-btn-primary me-2",
                        size="sm",
                    ),
                    dbc.Button(
                        [html.I(className="fas fa-trash-alt me-1"), "Delete Selected"],
                        id="btn-delete-selected",
                        className="cp-btn-danger",
                        size="sm",
                    ),
                ], className="d-flex align-items-end h-100"),
            ], lg=4, md=6, xs=12),
        ], className="g-3 align-items-end"),
    )


def _runs_table() -> html.Div:
    """Dash AG Grid table for experiment run history."""
    column_defs = [
        {
            "headerName": "", "checkboxSelection": True,
            "headerCheckboxSelection": True, "width": 54, "pinned": "left",
            "sortable": False, "filter": False, "resizable": False,
            "suppressSizeToFit": True, "suppressMenu": True,
        },
        {"field": "id", "headerName": "ID", "width": 70, "sortable": True},
        {"field": "created_at", "headerName": "Date", "width": 160, "sortable": True},
        {"field": "run_name", "headerName": "Run Name", "flex": 1, "sortable": True,
         "filter": True, "editable": False},
        {"field": "preset", "headerName": "Preset", "width": 100, "sortable": True},
        {"field": "steps_run", "headerName": "Steps", "width": 80, "sortable": True,
         "type": "numericColumn"},
        {"field": "final_avg_stress", "headerName": "Stress", "width": 90,
         "sortable": True, "type": "numericColumn",
         "valueFormatter": {"function": "params.value != null ? d3.format('.3f')(params.value) : '—'"}},
        {"field": "final_total_labor_hours", "headerName": "Labor", "width": 90,
         "sortable": True, "type": "numericColumn",
         "valueFormatter": {"function": "params.value != null ? d3.format('.1f')(params.value) : '—'"}},
        {"field": "final_social_efficiency", "headerName": "Efficiency", "width": 100,
         "sortable": True, "type": "numericColumn",
         "valueFormatter": {"function": "params.value != null ? d3.format('.3f')(params.value) : '—'"}},
        {"field": "final_avg_delegation_rate", "headerName": "Deleg Rate", "width": 100,
         "sortable": True, "type": "numericColumn",
         "valueFormatter": {"function": "params.value != null ? d3.format('.3f')(params.value) : '—'"}},
    ]

    return html.Div(
        dag.AgGrid(
            id="runs-grid",
            columnDefs=column_defs,
            rowData=[],
            defaultColDef={"resizable": True, "sortable": True},
            dashGridOptions={
                "rowSelection": {"mode": "multiRow"},
                "pagination": True,
                "paginationPageSize": 15,
                "domLayout": "autoHeight",
                "animateRows": True,
            },
            style={"width": "100%"},
            className="ag-theme-alpine",
        ),
        className="cp-card",
    )


def _comparison_panel() -> html.Div:
    """Comparison panel — shown when 2+ runs are selected."""
    return html.Div(
        id="run-comparison-panel",
        children=card(
            title="Comparison",
            subtitle="Select 2 or more runs to compare",
            children=empty_state(
                icon="fas fa-code-compare",
                title="No runs selected",
                message="Check the boxes next to runs in the table above to compare their metrics.",
            ),
            card_id="comparison-card",
        ),
    )


_delete_modal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Confirm Deletion")),
    dbc.ModalBody(id="delete-modal-body",
                  children="Are you sure you want to delete the selected runs?"),
    dbc.ModalFooter([
        dbc.Button("Cancel", id="btn-cancel-delete",
                   className="cp-btn-outline", size="sm"),
        dbc.Button("Delete", id="btn-confirm-delete",
                   className="cp-btn-danger", size="sm"),
    ]),
], id="delete-modal", is_open=False, centered=True)

_save_toast = dbc.Toast(
    id="save-toast",
    header="Run Saved",
    is_open=False,
    dismissable=True,
    duration=4000,
    icon="success",
    style={"position": "fixed", "top": 70, "right": 20, "width": 300, "zIndex": 9999},
)


layout = html.Div([
    # Hidden store to trigger grid refresh after mutations
    dcc.Store(id="runs-refresh-trigger", data=0),

    html.Div([
        html.H2("Run Manager", className="cp-page-title"),
        html.P(
            "Browse, compare, and manage saved experiment runs.",
            className="cp-page-subtitle",
        ),
    ], className="cp-page-header"),

    _filter_bar(),
    _runs_table(),
    html.Div(className="mb-3"),
    _comparison_panel(),
    _delete_modal,
    _save_toast,
])


# =========================================================================
# Callback 1: Load / refresh runs grid
# =========================================================================

@callback(
    Output("runs-grid", "rowData"),
    Input("runs-refresh-trigger", "data"),
    Input("run-search-input", "value"),
    Input("run-preset-filter", "value"),
    Input("run-date-range", "start_date"),
    Input("run-date-range", "end_date"),
)
def load_runs(trigger, search, preset_filter, start_date, end_date):
    """Query the database with current filters and populate the grid."""
    rows = db.list_runs(
        search=search,
        preset_filter=preset_filter,
        start_date=start_date,
        end_date=end_date,
    )
    return rows


# =========================================================================
# Callback 2: Save current simulation run
# =========================================================================

@callback(
    Output("runs-refresh-trigger", "data", allow_duplicate=True),
    Output("save-toast", "is_open"),
    Output("save-toast", "children"),
    Input("btn-save-run", "n_clicks"),
    prevent_initial_call=True,
)
def save_current_run(n_clicks):
    model = app_state.get_model()
    if model is None or model.current_step == 0:
        return no_update, True, "No simulation to save. Initialize and run first."

    try:
        run_id = db.save_run(
            model,
            label=f"Dashboard run (step {model.current_step})",
            preset=app_state.get_current_preset() or "custom",
        )
        app_state.set_run_id(str(run_id))
        return run_id, True, f"Run saved as ID {run_id} ({model.current_step} steps)."
    except Exception as e:
        return no_update, True, f"Save failed: {e}"


# =========================================================================
# Callback 3: Open delete confirmation modal
# =========================================================================

@callback(
    Output("delete-modal", "is_open"),
    Output("delete-modal-body", "children"),
    Input("btn-delete-selected", "n_clicks"),
    Input("btn-cancel-delete", "n_clicks"),
    Input("btn-confirm-delete", "n_clicks"),
    State("runs-grid", "selectedRows"),
    State("delete-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_delete_modal(n_del, n_cancel, n_confirm, selected, is_open):
    triggered = ctx.triggered_id

    if triggered == "btn-delete-selected":
        if not selected:
            return False, "No runs selected."
        ids = [r["id"] for r in selected]
        return True, f"Delete {len(ids)} run(s)? IDs: {ids}. This cannot be undone."

    if triggered in ("btn-cancel-delete", "btn-confirm-delete"):
        return False, ""

    return is_open, no_update


# =========================================================================
# Callback 4: Execute deletion
# =========================================================================

@callback(
    Output("runs-refresh-trigger", "data", allow_duplicate=True),
    Input("btn-confirm-delete", "n_clicks"),
    State("runs-grid", "selectedRows"),
    prevent_initial_call=True,
)
def execute_delete(n_clicks, selected):
    if not selected:
        return no_update
    ids = [r["id"] for r in selected]
    deleted = db.delete_runs(ids)
    logger.info("Deleted %d runs via Run Manager", deleted)
    import time
    return int(time.time())


# =========================================================================
# Callback 5: Comparison panel
# =========================================================================

@callback(
    Output("run-comparison-panel", "children"),
    Input("runs-grid", "selectedRows"),
)
def update_comparison(selected):
    if not selected or len(selected) < 2:
        return card(
            title="Comparison",
            subtitle="Select 2 or more runs to compare",
            children=empty_state(
                icon="fas fa-code-compare",
                title="No runs selected" if not selected else "Select at least 2 runs",
                message="Check the boxes next to runs in the table above to compare their metrics.",
            ),
            card_id="comparison-card",
        )

    metrics = [
        ("final_avg_stress", "Avg Stress", ".3f"),
        ("final_total_labor_hours", "Labor Hours", ".1f"),
        ("final_social_efficiency", "Efficiency", ".3f"),
        ("final_avg_delegation_rate", "Delegation Rate", ".3f"),
    ]

    # Build metric comparison cards
    metric_cols = []
    for key, label, fmt in metrics:
        values = [r.get(key) for r in selected if r.get(key) is not None]
        if values:
            min_v, max_v = min(values), max(values)
            spread = max_v - min_v
            display = f"{min_v:{fmt}} – {max_v:{fmt}}"
            delta_str = f"Spread: {spread:{fmt}}"
        else:
            display = "—"
            delta_str = None
        metric_cols.append(
            dbc.Col(
                kpi_card(label, display, delta=delta_str, delta_direction="neutral"),
                md=3, xs=6,
            )
        )

    # Build overlay time series for selected runs
    overlay_fig = go.Figure()
    chart_metrics_to_plot = [
        ("avg_stress", "Stress"),
        ("total_labor_hours", "Labor Hours"),
    ]

    for i, run_row in enumerate(selected[:6]):
        run_detail = db.get_run_detail(run_row["id"])
        if run_detail and run_detail.get("steps"):
            steps_data = run_detail["steps"]
            step_nums = [s.get("step", j) for j, s in enumerate(steps_data)]

            color = CHART_COLORWAY[i % len(CHART_COLORWAY)]
            run_label = format_run_label(run_row)

            stress_vals = [s.get("avg_stress", 0) for s in steps_data]
            overlay_fig.add_trace(go.Scatter(
                x=step_nums, y=stress_vals,
                mode="lines",
                name=f"#{run_row['id']} {run_label}",
                line=dict(color=color, width=2),
            ))

    overlay_fig.update_layout(
        xaxis_title="Step",
        yaxis_title="Avg Stress",
        margin=dict(t=10, b=40, l=56, r=16),
        height=300,
        legend=dict(orientation="h", y=1.15),
    )

    return card(
        title=f"Comparing {len(selected)} Runs",
        subtitle="Metric ranges and time series overlay",
        children=[
            dbc.Row(metric_cols, className="g-3 mb-3"),
            html.Div(
                dcc.Graph(
                    figure=overlay_fig,
                    config={"displayModeBar": True, "displaylogo": False,
                            "responsive": True},
                    style={"width": "100%", "height": "300px"},
                ),
                className="cp-chart-container",
                style={"height": "300px"},
            ),
        ],
        card_id="comparison-card",
    )
