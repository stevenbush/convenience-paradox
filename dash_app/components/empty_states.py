"""
Empty state placeholder components.

Shown when a page or section has no data to display yet
(e.g. simulation not initialized, no run history).
"""

from dash import html


def empty_state(
    icon: str = "fas fa-chart-line",
    title: str = "No data yet",
    message: str = "",
) -> html.Div:
    """Create a centered empty-state placeholder.

    Args:
        icon: Font Awesome icon class string.
        title: Short heading.
        message: Longer description text.
    """
    return html.Div(
        [
            html.I(className=f"{icon} cp-empty-state__icon"),
            html.Div(title, className="cp-empty-state__title"),
            html.Div(message, className="cp-empty-state__text") if message else None,
        ],
        className="cp-empty-state",
    )
