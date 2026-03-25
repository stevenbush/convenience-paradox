"""
Reusable Dash component library.

All components use CSS classes from the design system (assets/*.css)
and reference design tokens — never hardcoded visual values.
"""

from dash_app.components.card import card, kpi_card, chart_card
from dash_app.components.badges import status_badge, hypothesis_badge, llm_status_dot
from dash_app.components.charts import CP_PLOTLY_TEMPLATE, apply_chart_theme
from dash_app.components.sidebar import sidebar
from dash_app.components.topbar import topbar
from dash_app.components.empty_states import empty_state
from dash_app.components.controls import simulation_controls

__all__ = [
    "card",
    "kpi_card",
    "chart_card",
    "status_badge",
    "hypothesis_badge",
    "llm_status_dot",
    "CP_PLOTLY_TEMPLATE",
    "apply_chart_theme",
    "sidebar",
    "topbar",
    "empty_state",
    "simulation_controls",
]
