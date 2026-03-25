"""
Sidebar navigation component.

Fixed left sidebar with vertical page navigation, built dynamically
from dash.page_registry. Includes the simulation controls section
that is visible only on the Simulation Dashboard page.
"""

from dash import html, dcc, page_registry

from dash_app.components.controls import simulation_controls


PAGE_ICONS = {
    "/": "fas fa-chart-area",
    "/llm-studio": "fas fa-brain",
    "/run-manager": "fas fa-database",
    "/analysis": "fas fa-flask",
}

PAGE_ORDER = ["/", "/llm-studio", "/run-manager", "/analysis"]


def sidebar() -> html.Div:
    """Build the sidebar navigation component.

    The sidebar has three sections:
    1. Navigation links (always visible)
    2. Simulation controls placeholder (toggled by callback based on URL)
    3. Footer with version and LLM status
    """
    nav_items = []
    for path in PAGE_ORDER:
        page = None
        for p in page_registry.values():
            if p["path"] == path:
                page = p
                break
        if page is None:
            continue

        icon_class = PAGE_ICONS.get(path, "fas fa-circle")
        nav_items.append(
            dcc.Link(
                [
                    html.Span(className=f"{icon_class} cp-nav-item__icon"),
                    html.Span(page["name"], className="cp-nav-item__label"),
                ],
                href=path,
                className="cp-nav-item",
                id=f"nav-{path.strip('/') or 'home'}",
            )
        )

    return html.Div(
        [
            # Navigation section
            html.Nav(nav_items, className="cp-sidebar__nav"),

            # Simulation controls remain mounted so navigation does not recreate
            # the action buttons and accidentally retrigger simulation callbacks.
            html.Div(
                simulation_controls(),
                id="sidebar-controls",
                className="cp-sidebar__controls",
            ),

            # Footer
            html.Div(
                [
                    html.Span(
                        [
                            html.Span("v1.0", style={"opacity": "0.5"}),
                            html.Span(" · ", style={"opacity": "0.3"}),
                            html.Span("Ollama "),
                            html.Span(id="sidebar-llm-dot"),
                        ],
                        style={
                            "fontSize": "var(--cp-text-xs)",
                            "color": "var(--cp-text-tertiary)",
                        },
                    ),
                ],
                className="cp-sidebar__footer",
            ),
        ],
        className="cp-sidebar",
        id="sidebar",
    )
