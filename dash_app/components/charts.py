"""
Plotly chart theme and helper functions.

Defines a unified Plotly template (CP_PLOTLY_TEMPLATE) applied to all charts
for visual consistency across the dashboard. The template matches the design
tokens defined in assets/tokens.css.
"""

import plotly.graph_objects as go
import plotly.io as pio


CHART_COLORWAY = [
    "#2C8C99",  # Primary teal
    "#E67E22",  # Warm orange
    "#27AE60",  # Green
    "#8E44AD",  # Purple
    "#E74C3C",  # Red
    "#3498DB",  # Blue
    "#F39C12",  # Gold
    "#1ABC9C",  # Mint
]

_FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
_GRID_COLOR = "#E2E8F0"
_TEXT_COLOR = "#64748B"
_TITLE_COLOR = "#1E293B"

CP_PLOTLY_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        font=dict(family=_FONT_FAMILY, color=_TEXT_COLOR, size=12),
        title=dict(
            font=dict(family=_FONT_FAMILY, color=_TITLE_COLOR, size=15),
            x=0,
            xanchor="left",
            pad=dict(l=4, t=4),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=CHART_COLORWAY,
        margin=dict(t=40, b=40, l=56, r=16),
        xaxis=dict(
            gridcolor=_GRID_COLOR,
            linecolor=_GRID_COLOR,
            zerolinecolor=_GRID_COLOR,
            showgrid=True,
            gridwidth=1,
        ),
        yaxis=dict(
            gridcolor=_GRID_COLOR,
            linecolor=_GRID_COLOR,
            zerolinecolor=_GRID_COLOR,
            showgrid=True,
            gridwidth=1,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11),
        ),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor=_GRID_COLOR,
            font=dict(family=_FONT_FAMILY, size=12, color=_TITLE_COLOR),
        ),
        hovermode="x unified",
    )
)


def apply_chart_theme() -> None:
    """Register and activate the project's Plotly template globally."""
    pio.templates["convenience_paradox"] = CP_PLOTLY_TEMPLATE
    pio.templates.default = "convenience_paradox"


CHART_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "select2d", "lasso2d", "autoScale2d", "toggleSpikelines",
    ],
    "responsive": True,
}
