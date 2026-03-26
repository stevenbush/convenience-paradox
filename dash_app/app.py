"""
Dash application factory for The Convenience Paradox dashboard.

Creates a multi-page Dash app with:
- Bootswatch LITERA theme via dash-bootstrap-components
- Dash Pages for automatic page routing
- Fixed sidebar + top bar shell layout
- Global Plotly chart template
- dcc.Store components for simulation state signalling
"""

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ctx

from dash_app.components.charts import apply_chart_theme
from dash_app.components.topbar import topbar
from dash_app.components.sidebar import sidebar


def create_app(debug: bool = False) -> dash.Dash:
    """Create and configure the Dash application.

    Args:
        debug: Enable Dash dev tools and hot-reloading.

    Returns:
        Configured Dash app instance ready to run.
    """
    app = dash.Dash(
        __name__,
        use_pages=True,
        pages_folder="pages",
        external_stylesheets=[
            dbc.themes.LITERA,
            dbc.icons.FONT_AWESOME,
            "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
        ],
        meta_tags=[
            {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        ],
        suppress_callback_exceptions=True,
        title="The Convenience Paradox",
        update_title="Loading...",
    )

    apply_chart_theme()

    app.layout = _build_layout()
    _register_shell_callbacks(app)

    return app


def _build_layout() -> html.Div:
    """Construct the app shell: top bar + sidebar + page container + stores."""
    return html.Div(
        [
            dcc.Location(id="url", refresh=False),

            # Simulation state trigger — chart callbacks watch this store.
            dcc.Store(id="sim-trigger-store", data={"step": 0, "action": "none"}),

            # LLM Studio UI state — kept in browser memory so it survives in-app navigation
            # but resets on full reload, tab close, or server restart.
            dcc.Store(id="llm-studio-store", data={}, storage_type="memory"),

            # Scenario Parser request queue — used to show a pending state before LLM returns.
            dcc.Store(id="scenario-parse-request-store", data=None),

            # Result Interpreter request queue — used to stage the chat turn before the LLM returns.
            dcc.Store(id="chat-interpret-request-store", data=None),

            # Result Interpreter UI state — survives in-app navigation only.
            dcc.Store(id="chat-history-store", data={}, storage_type="memory"),

            # Profile Generator request queue — used to show a pending state before the LLM returns.
            dcc.Store(id="profile-generate-request-store", data=None),

            # Profile Generator UI state — survives in-app navigation only.
            dcc.Store(id="profile-history-store", data={}, storage_type="memory"),

            # Visualization Annotator UI state — survives in-app navigation only.
            dcc.Store(id="annotation-history-store", data={}, storage_type="memory"),

            # LLM audit log trigger — updated after each LLM call
            dcc.Store(id="audit-trigger-store", data=0),

            topbar(),

            html.Div(
                [
                    sidebar(),
                    html.Main(
                        dash.page_container,
                        className="cp-content",
                        id="page-content",
                    ),
                ],
                className="cp-shell",
            ),
            html.Div(id="sidebar-backdrop", n_clicks=0),
        ],
        id="app-root",
    )


def _sidebar_classes(is_open: bool) -> tuple[str, str]:
    """Return shell class names for the mobile sidebar and its backdrop."""
    sidebar_class = "cp-sidebar cp-sidebar--open" if is_open else "cp-sidebar"
    backdrop_class = "cp-sidebar-backdrop" if is_open else ""
    return sidebar_class, backdrop_class


def _resolve_sidebar_toggle(triggered_id: str | None,
                            current_class: str | None) -> tuple[str, str]:
    """Resolve whether the mobile sidebar should be open after a shell event."""
    is_open = "cp-sidebar--open" in (current_class or "")

    if triggered_id == "sidebar-toggle":
        return _sidebar_classes(not is_open)
    if triggered_id in {"sidebar-backdrop", "url"}:
        return _sidebar_classes(False)
    return _sidebar_classes(is_open)


def _register_shell_callbacks(app: dash.Dash) -> None:
    """Register callbacks for the app shell (navigation highlighting, sidebar controls)."""

    @app.callback(
        [Output(f"nav-{pid}", "className") for pid in ["home", "llm-studio", "run-manager", "analysis"]],
        Input("url", "pathname"),
    )
    def update_nav_active(pathname: str):
        """Highlight the active navigation item based on current URL."""
        paths = ["/", "/llm-studio", "/run-manager", "/analysis"]
        results = []
        for p in paths:
            if pathname == p or (p != "/" and pathname and pathname.startswith(p)):
                results.append("cp-nav-item cp-nav-item--active")
            else:
                results.append("cp-nav-item")
        return results

    @app.callback(
        Output("sidebar-controls", "style"),
        Input("url", "pathname"),
    )
    def toggle_sidebar_controls(pathname: str):
        """Show simulation controls only on the dashboard page."""
        if pathname == "/":
            return {"display": "block"}
        return {"display": "none"}

    @app.callback(
        Output("sidebar", "className"),
        Output("sidebar-backdrop", "className"),
        Input("sidebar-toggle", "n_clicks"),
        Input("sidebar-backdrop", "n_clicks"),
        Input("url", "pathname"),
        State("sidebar", "className"),
        prevent_initial_call=True,
    )
    def toggle_mobile_sidebar(n_toggle, n_backdrop, pathname, current_class):
        """Open and close the off-canvas sidebar on phone-sized layouts."""
        return _resolve_sidebar_toggle(ctx.triggered_id, current_class)
