"""
Page 3: Run Manager

Experiment database management with query, filtering, comparison, and
deletion capabilities. Uses Dash AG Grid for the interactive data table.

Callback architecture:
    - On page load and after mutations, the runs-grid is repopulated from SQLite.
    - Filter controls (search, preset, date range) feed into the query.
    - Delete operations cascade to both runs and run_steps tables.
    - The comparison panel exposes explicit controls: choose runs in the grid,
      pick one metric, then click Compare to render the average-value summary
      and the aligned trend chart.

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
from dash_app.components.badges import status_badge
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

RUN_COMPARISON_METRICS = [
    {
        "key": "avg_stress",
        "label": "Avg Stress",
        "format": ".3f",
        "yaxis": "Stress",
        "description": "Average time pressure carried by agents during the run. Higher values indicate more overload.",
    },
    {
        "key": "total_labor_hours",
        "label": "Labor Hours",
        "format": ".1f",
        "yaxis": "Hours",
        "description": "Total system-wide labor performed at each step, including service provision for others.",
    },
    {
        "key": "social_efficiency",
        "label": "Social Efficiency",
        "format": ".3f",
        "yaxis": "Tasks / Hour",
        "description": "How many tasks the society completes per unit of labor. Higher values indicate better coordination.",
    },
    {
        "key": "avg_delegation_rate",
        "label": "Delegation Rate",
        "format": ".3f",
        "yaxis": "Delegation Share",
        "description": "Share of tasks that agents delegate instead of handling themselves.",
    },
    {
        "key": "unmatched_tasks",
        "label": "Unmatched Tasks",
        "format": ".1f",
        "yaxis": "Tasks",
        "description": "Delegated tasks that the system fails to match with a provider. Higher values suggest market strain.",
    },
    {
        "key": "avg_income",
        "label": "Avg Income",
        "format": ".2f",
        "yaxis": "Income",
        "description": "Average net income across agents over time, combining earnings and service spending.",
    },
]

MAX_COMPARISON_RUNS = 6



# =========================================================================
# Layout
# =========================================================================

def _filter_bar() -> html.Div:
    """Search and filter controls above the data table."""
    return card(
        children=[
            dbc.Row([
                dbc.Col([
                    html.Label("Search", className="cp-controls__slider-label"),
                    dbc.Input(
                        id="run-search-input",
                        placeholder="Search by run name or preset...",
                        type="text", size="sm", debounce=True,
                    ),
                ], lg=4, md=12, xs=12),
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
                ], lg=3, md=6, xs=12),
                dbc.Col([
                    html.Label("Date Range", className="cp-controls__slider-label"),
                    dcc.DatePickerRange(
                        id="run-date-range",
                        display_format="YYYY-MM-DD",
                        style={"fontSize": "var(--cp-text-sm)"},
                    ),
                ], lg=5, md=6, xs=12),
            ], className="g-3"),
            html.Div(className="mb-3"),
            dbc.Row([
                dbc.Col([
                    html.Label("Run Name", className="cp-run-manager__field-label"),
                    dbc.Input(
                        id="run-save-name-input",
                        placeholder="Optional name for current run...",
                        type="text", size="sm", maxLength=120,
                        className="cp-run-manager__name-input",
                    ),
                    html.Div(
                        "Used when you click Save Current. Saved runs can still be renamed in the table below.",
                        className="cp-run-manager__field-hint",
                    ),
                ], lg=5, md=12, xs=12),
                dbc.Col([
                    html.Div("Run Actions", className="cp-run-manager__field-label"),
                    html.Div([
                        dbc.Button(
                            [html.I(className="fas fa-rotate-right me-1"), "Refresh"],
                            id="btn-refresh-runs",
                            className="cp-btn-outline cp-run-manager__action-btn cp-run-manager__action-btn--refresh",
                            size="sm",
                        ),
                        dbc.Button(
                            [html.I(className="fas fa-save me-1"), "Save Current"],
                            id="btn-save-run",
                            className="cp-btn-primary cp-run-manager__action-btn cp-run-manager__action-btn--save",
                            size="sm",
                        ),
                        dbc.Button(
                            [html.I(className="fas fa-pen me-1"), "Update"],
                            id="btn-update-run-names",
                            className="cp-btn-outline cp-run-manager__action-btn cp-run-manager__action-btn--update",
                            size="sm",
                        ),
                        dbc.Button(
                            [html.I(className="fas fa-trash-alt me-1"), "Delete Selected"],
                            id="btn-delete-selected",
                            className="cp-btn-danger cp-run-manager__action-btn cp-run-manager__action-btn--delete",
                            size="sm",
                        ),
                    ], className="cp-run-manager__action-bar"),
                ], lg=7, md=12, xs=12),
            ], className="g-3 align-items-end"),
        ],
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
        {"field": "created_at", "headerName": "Date", "width": 160, "sortable": True,
         "editable": False},
        {"field": "run_name", "headerName": "Run Name", "flex": 1, "sortable": True,
         "filter": True, "editable": True},
        {"field": "preset", "headerName": "Preset", "width": 100, "sortable": True,
         "editable": False},
        {"field": "steps_run", "headerName": "Steps", "width": 80, "sortable": True,
         "type": "numericColumn", "editable": False},
        {"field": "final_avg_stress", "headerName": "Stress", "width": 90,
         "sortable": True, "type": "numericColumn", "editable": False,
         "valueFormatter": {"function": "params.value != null ? d3.format('.3f')(params.value) : '—'"}},
        {"field": "final_total_labor_hours", "headerName": "Labor", "width": 90,
         "sortable": True, "type": "numericColumn", "editable": False,
         "valueFormatter": {"function": "params.value != null ? d3.format('.1f')(params.value) : '—'"}},
        {"field": "final_social_efficiency", "headerName": "Efficiency", "width": 100,
         "sortable": True, "type": "numericColumn", "editable": False,
         "valueFormatter": {"function": "params.value != null ? d3.format('.3f')(params.value) : '—'"}},
        {"field": "final_avg_delegation_rate", "headerName": "Deleg Rate", "width": 100,
         "sortable": True, "type": "numericColumn", "editable": False,
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


def _comparison_metric_options() -> list[dict[str, str]]:
    """Return dropdown options for the one-metric-at-a-time comparison control."""
    return [
        {"label": metric["label"], "value": metric["key"]}
        for metric in RUN_COMPARISON_METRICS
    ]


def _comparison_metric_map() -> dict[str, dict[str, str]]:
    """Lookup table for comparison metric metadata."""
    return {metric["key"]: metric for metric in RUN_COMPARISON_METRICS}


def _comparison_empty_card(title: str, message: str) -> html.Div:
    """Return a consistent empty-state card for the comparison results area."""
    return card(
        title=title,
        subtitle="Compare one metric across selected runs",
        children=empty_state(
            icon="fas fa-code-compare",
            title=title,
            message=message,
        ),
        class_name="cp-run-manager__comparison-card",
    )


def _comparison_panel() -> html.Div:
    """Comparison workspace — explicit controls plus results area."""
    return html.Div(
        id="run-comparison-panel",
        children=card(
            title="Comparison",
            subtitle="Select runs, choose one metric, then click Compare",
            children=[
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div("Selected Runs", className="cp-run-manager__field-label"),
                                html.Div(
                                    id="run-comparison-selection-summary",
                                    className="cp-run-manager__selection-summary",
                                ),
                            ],
                            lg=5,
                            md=12,
                        ),
                        dbc.Col(
                            [
                                html.Label("Comparison Metric", className="cp-run-manager__field-label"),
                                dcc.Dropdown(
                                    id="run-compare-metric",
                                    options=_comparison_metric_options(),
                                    placeholder="Choose one metric to compare...",
                                    clearable=True,
                                    style={"fontSize": "var(--cp-text-sm)"},
                                ),
                                html.Div(
                                    id="run-compare-metric-help",
                                    className="cp-run-manager__compare-help",
                                ),
                            ],
                            lg=4,
                            md=12,
                        ),
                        dbc.Col(
                            [
                                html.Div("Compare Actions", className="cp-run-manager__field-label"),
                                html.Div(
                                    [
                                        dbc.Button(
                                            [html.I(className="fas fa-code-compare me-1"), "Compare"],
                                            id="btn-run-compare",
                                            className="cp-btn-primary cp-run-manager__action-btn cp-run-manager__action-btn--compare",
                                            size="sm",
                                        ),
                                        dbc.Button(
                                            [html.I(className="fas fa-eraser me-1"), "Clear"],
                                            id="btn-clear-comparison",
                                            className="cp-btn-outline cp-run-manager__action-btn cp-run-manager__action-btn--clear",
                                            size="sm",
                                        ),
                                    ],
                                    className="cp-run-manager__action-bar cp-run-manager__action-bar--compare",
                                ),
                            ],
                            lg=3,
                            md=12,
                        ),
                    ],
                    className="g-3 align-items-start",
                ),
                html.Div(id="run-comparison-results", className="mt-3"),
            ],
            card_id="comparison-card",
        ),
    )


def _comparison_metric_help(metric_key: str | None) -> str:
    """Return helper text explaining the currently selected comparison metric."""
    if not metric_key:
        labels = ", ".join(metric["label"] for metric in RUN_COMPARISON_METRICS)
        return f"Available metrics: {labels}. Choose one metric, then click Compare."
    metric = _comparison_metric_map().get(metric_key)
    if not metric:
        return "Choose one metric, then click Compare."
    return f"{metric['label']}: {metric['description']}"


def _selected_run_summary(selected: list[dict] | None):
    """Render compact chips summarising which runs are currently selected."""
    selected = selected or []
    if not selected:
        return html.Div(
            "No runs selected yet. Choose at least 2 runs from the table above.",
            className="cp-run-manager__compare-help",
        )

    chips = []
    visible_rows = selected[:MAX_COMPARISON_RUNS]
    for row in visible_rows:
        label = format_run_label(row)
        chips.append(
            html.Div(
                [
                    html.Span(f"#{row['id']}", className="cp-chat-context__label"),
                    html.Div(label, className="cp-chat-context__value"),
                ],
                className="cp-chat-context__chip",
            )
        )

    children = [html.Div(chips, className="cp-chat-context__grid")]
    hidden_count = len(selected) - len(visible_rows)
    if hidden_count > 0:
        children.append(
            html.Div(
                f"Showing the first {MAX_COMPARISON_RUNS} of {len(selected)} selected runs. Narrow the selection before comparing.",
                className="cp-run-manager__compare-help",
            )
        )
    return html.Div(children)


def _build_comparison_trend_figure(compare_state: dict[str, object]) -> go.Figure:
    """Build the comparison trend figure for the current comparison state."""
    metric = compare_state["metric"]
    runs = compare_state["runs"]
    fmt = metric["format"]

    x_field = compare_state["x_field"]
    trend_fig = go.Figure()
    for run in runs:
        trend_fig.add_trace(go.Scatter(
            x=[point[x_field] for point in run["series"]],
            y=[point["value"] for point in run["series"]],
            mode="lines",
            name=run["label"],
            line=dict(color=run["color"], width=2),
            hovertemplate=(
                "Run: %{fullData.name}<br>"
                + ("Progress: %{x:.0f}%<br>" if x_field == "progress" else "Step: %{x}<br>")
                + f"{metric['label']}: %{{y:{fmt}}}<extra></extra>"
            ),
        ))

    trend_fig.update_layout(
        xaxis_title="Normalized Progress (%)" if x_field == "progress" else "Step",
        yaxis_title=metric["yaxis"],
        margin=dict(t=10, b=40, l=56, r=16),
        height=320,
        legend=dict(orientation="h", y=1.12, x=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    if x_field == "progress":
        trend_fig.update_xaxes(range=[0, 100])

    return trend_fig


def _build_comparison_results(compare_state: dict | None):
    """Render the comparison result area from the last explicit Compare action."""
    if not isinstance(compare_state, dict):
        return _comparison_empty_card(
            "Compare Selected Runs",
            "Choose at least 2 runs, pick one metric, then click Compare to generate the side-by-side view.",
        )

    status = compare_state.get("status")
    if status == "error":
        return _comparison_empty_card(
            "Comparison Not Ready",
            str(compare_state.get("error") or "Choose at least 2 runs and one metric before comparing."),
        )

    metric = compare_state["metric"]
    runs = compare_state["runs"]
    trend_fig = _build_comparison_trend_figure(compare_state)
    avg_cards = [
        dbc.Col(
            kpi_card(
                run["label"],
                format(run["mean_value"], metric["format"]),
                delta=f"Steps: {run['step_count']}",
                delta_direction="neutral",
            ),
            xl=3,
            lg=4,
            md=6,
            xs=12,
        )
        for run in runs
    ]

    note_variant = "info" if compare_state.get("x_field") == "progress" else "neutral"
    note_text = compare_state.get("comparison_note") or (
        "All selected runs share the same step span, so the trend chart uses the native simulation step axis."
    )

    return card(
        title=f"{metric['label']} Comparison",
        subtitle="Explicit comparison generated from the selected runs",
        children=[
            html.Div(
                [
                    html.Span(note_text, className="cp-run-manager__compare-help"),
                    status_badge(
                        "Normalized for unequal step counts" if compare_state.get("x_field") == "progress" else "Native step axis",
                        note_variant,
                    ),
                ],
                className="cp-run-manager__compare-note",
            ),
            html.Div("Average Value By Run", className="cp-run-manager__field-label"),
            dbc.Row(avg_cards, className="g-2 mb-2"),
            html.Div("Metric Trend Over Time", className="cp-run-manager__field-label mt-2"),
            html.Div(
                dcc.Graph(
                    figure=trend_fig,
                    config={"displayModeBar": True, "displaylogo": False, "responsive": True},
                    style={"width": "100%", "height": "320px"},
                ),
                className="cp-chart-container",
                style={"height": "320px"},
            ),
        ],
        class_name="cp-run-manager__comparison-card",
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
    dcc.Store(id="run-comparison-store", data=None),

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


@callback(
    Output("runs-refresh-trigger", "data", allow_duplicate=True),
    Input("btn-refresh-runs", "n_clicks"),
    State("runs-refresh-trigger", "data"),
    prevent_initial_call=True,
)
def refresh_runs(n_clicks, current_trigger):
    """Manually refresh the runs grid to pick up the latest database state."""
    if not n_clicks:
        return no_update
    return int(current_trigger or 0) + 1


# =========================================================================
# Callback 2: Save current simulation run
# =========================================================================

@callback(
    Output("runs-refresh-trigger", "data", allow_duplicate=True),
    Output("save-toast", "is_open"),
    Output("save-toast", "children"),
    Output("run-save-name-input", "value"),
    Input("btn-save-run", "n_clicks"),
    State("run-save-name-input", "value"),
    prevent_initial_call=True,
)
def save_current_run(n_clicks, custom_run_name):
    model = app_state.get_model()
    if model is None or model.current_step == 0:
        return no_update, True, "No simulation to save. Initialize and run first.", no_update

    run_name = (custom_run_name or "").strip()
    if not run_name:
        run_name = f"Dashboard run (step {model.current_step})"

    try:
        run_id = db.save_run(
            model,
            label=run_name,
            preset=app_state.get_current_preset() or "custom",
        )
        app_state.set_run_id(str(run_id))
        return run_id, True, f"Run saved as ID {run_id} ({run_name}).", ""
    except Exception as e:
        return no_update, True, f"Save failed: {e}", no_update


@callback(
    Output("runs-refresh-trigger", "data", allow_duplicate=True),
    Output("save-toast", "is_open", allow_duplicate=True),
    Output("save-toast", "children", allow_duplicate=True),
    Input("btn-update-run-names", "n_clicks"),
    State("runs-grid", "rowData"),
    prevent_initial_call=True,
)
def update_run_names(n_clicks, rows):
    """Persist edited Run Name values after the user confirms with Update."""
    if not rows:
        return no_update, True, "No runs available to update."

    label_updates: list[tuple[int, str | None]] = []
    for row in rows:
        edited_name = str(row.get("run_name") or "").strip()
        current_label = str(row.get("label") or "").strip()
        current_name = current_label or f"Run {row['id']}"
        if edited_name != current_name:
            label_updates.append((int(row["id"]), edited_name or None))

    if not label_updates:
        return no_update, True, "No Run Name changes to update."

    updated = db.update_run_labels(label_updates)
    import time
    return int(time.time()), True, f"Updated {updated} run name(s)."


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
# Callback 5: Comparison controls
# =========================================================================

@callback(
    Output("run-comparison-selection-summary", "children"),
    Output("run-compare-metric-help", "children"),
    Output("btn-run-compare", "disabled"),
    Output("btn-clear-comparison", "disabled"),
    Input("runs-grid", "selectedRows"),
    Input("run-compare-metric", "value"),
)
def update_comparison_controls(selected, metric_key):
    """Keep the comparison guidance and action buttons in sync with current selection."""
    selected = selected or []
    can_compare = 2 <= len(selected) <= MAX_COMPARISON_RUNS and bool(metric_key)
    can_clear = len(selected) > 0 or bool(metric_key)
    return (
        _selected_run_summary(selected),
        _comparison_metric_help(metric_key),
        not can_compare,
        not can_clear,
    )


@callback(
    Output("run-comparison-store", "data", allow_duplicate=True),
    Input("runs-grid", "selectedRows"),
    Input("runs-grid", "rowData"),
    Input("run-compare-metric", "value"),
    Input("runs-refresh-trigger", "data"),
    Input("run-search-input", "value"),
    Input("run-preset-filter", "value"),
    Input("run-date-range", "start_date"),
    Input("run-date-range", "end_date"),
    prevent_initial_call=True,
)
def invalidate_run_comparison(
    selected,
    row_data,
    metric_key,
    refresh_token,
    search,
    preset_filter,
    start_date,
    end_date,
):
    """Discard the last comparison whenever the grid inputs change."""
    return None


@callback(
    Output("run-comparison-store", "data"),
    Output("runs-grid", "selectedRows", allow_duplicate=True),
    Output("run-compare-metric", "value", allow_duplicate=True),
    Input("btn-run-compare", "n_clicks"),
    Input("btn-clear-comparison", "n_clicks"),
    State("runs-grid", "selectedRows"),
    State("run-compare-metric", "value"),
    prevent_initial_call=True,
)
def manage_run_comparison(compare_clicks, clear_clicks, selected, metric_key):
    """Only compare after an explicit click, and clear on demand."""
    triggered = ctx.triggered_id
    if triggered == "btn-clear-comparison":
        return None, [], None

    selected = selected or []
    if len(selected) < 2 or not metric_key:
        return {
            "status": "error",
            "error": "Select at least 2 runs and choose one metric before clicking Compare.",
        }, no_update, no_update
    if len(selected) > MAX_COMPARISON_RUNS:
        return {
            "status": "error",
            "error": f"Select no more than {MAX_COMPARISON_RUNS} runs for one comparison to keep the charts readable.",
        }, no_update, no_update

    metric = _comparison_metric_map().get(metric_key)
    if metric is None:
        return {
            "status": "error",
            "error": "Choose a valid comparison metric before clicking Compare.",
        }, no_update, no_update

    run_payloads = []
    for index, run_row in enumerate(selected):
        run_detail = db.get_run_detail(int(run_row["id"]))
        if not run_detail or not run_detail.get("steps"):
            continue

        series = []
        for step in run_detail["steps"]:
            value = step.get(metric_key)
            if value is None:
                continue
            series.append({
                "step": int(step.get("step", len(series))),
                "value": float(value),
            })

        if not series:
            continue

        max_step = max(point["step"] for point in series) or 1
        for point in series:
            point["progress"] = round((point["step"] / max_step) * 100, 2)

        run_payloads.append({
            "id": int(run_row["id"]),
            "label": f"#{run_row['id']} {format_run_label(run_row)}",
            "step_count": len(series),
            "max_step": max_step,
            "mean_value": sum(point["value"] for point in series) / len(series),
            "series": series,
            "color": CHART_COLORWAY[index % len(CHART_COLORWAY)],
        })

    if len(run_payloads) < 2:
        return {
            "status": "error",
            "error": "At least 2 selected runs must contain step-level data for the chosen metric.",
        }, no_update, no_update

    max_steps = {run["max_step"] for run in run_payloads}
    use_progress_axis = len(max_steps) > 1
    comparison_note = (
        "Selected runs have different total step counts, so the trend chart aligns them by normalized progress (%) to keep the trajectories comparable."
        if use_progress_axis
        else "Selected runs share the same step span, so the trend chart uses the native simulation step axis."
    )

    return {
        "status": "success",
        "metric": metric,
        "runs": run_payloads,
        "x_field": "progress" if use_progress_axis else "step",
        "comparison_note": comparison_note,
    }, no_update, no_update


@callback(
    Output("run-comparison-results", "children"),
    Input("run-comparison-store", "data"),
)
def render_comparison_results(compare_state):
    """Render the comparison result card from the last explicit compare request."""
    return _build_comparison_results(compare_state)
