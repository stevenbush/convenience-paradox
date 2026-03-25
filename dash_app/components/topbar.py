"""
Top bar component.

Fixed horizontal bar at the top of the viewport containing the
project title and right-side status indicators.
"""

from dash import html


def topbar() -> html.Div:
    """Build the top navigation bar.

    Contains:
    - Left: project title and subtitle
    - Right: LLM status indicator and optional controls
    """
    return html.Div(
        [
            # Left: brand / title
            html.Div(
                [
                    html.Span(
                        "◆",
                        style={
                            "color": "var(--cp-primary)",
                            "fontSize": "var(--cp-text-xl)",
                            "fontWeight": "700",
                        },
                    ),
                    html.H1("The Convenience Paradox", className="cp-topbar__title"),
                    html.Span("ABM Dashboard", className="cp-topbar__subtitle"),
                ],
                className="cp-topbar__brand",
            ),

            # Mobile hamburger toggle
            html.Button(
                html.I(className="fas fa-bars"),
                id="sidebar-toggle",
                className="cp-topbar__hamburger btn btn-sm",
                n_clicks=0,
                style={"border": "none", "background": "transparent"},
            ),

            # Right: status indicators
            html.Div(
                [
                    html.Div(
                        id="topbar-llm-status",
                        style={
                            "fontSize": "var(--cp-text-xs)",
                            "color": "var(--cp-text-tertiary)",
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "var(--cp-space-2)",
                        },
                    ),
                ],
                className="cp-topbar__right",
            ),
        ],
        className="cp-topbar",
    )
