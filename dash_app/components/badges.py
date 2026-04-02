"""
Badge and status indicator components.

Small pill-shaped elements for hypothesis status, LLM status, etc.
"""

from dash import html


def status_badge(text: str, variant: str = "neutral") -> html.Span:
    """Create a status badge pill.

    Args:
        text: Badge text content.
        variant: One of "success", "warning", "danger", "info", "neutral", "primary".
    """
    return html.Span(text, className=f"cp-badge cp-badge--{variant}")


def hypothesis_badge(hypothesis_id: str, status: str) -> html.Span:
    """Create a hypothesis status badge.

    Args:
        hypothesis_id: e.g. "H1", "H2".
        status: One of "confirmed", "supported", "partial", "pending".
    """
    variant_map = {
        "confirmed": "success",
        "supported": "warning",
        "partial": "neutral",
        "pending": "info",
    }
    label_map = {
        "confirmed": "Confirmed",
        "supported": "Supported",
        "partial": "Partial",
        "pending": "Pending",
    }
    variant = variant_map.get(status, "neutral")
    label = label_map.get(status, status.capitalize())

    return html.Span(
        [html.Strong(f"{hypothesis_id} "), label],
        className=f"cp-badge cp-badge--{variant}",
    )


def llm_status_dot(is_online: bool | None = None) -> html.Span:
    """Small colored dot indicating LLM service status.

    Args:
        is_online: True=green, False=red, None=gray.
    """
    if is_online is True:
        state = "online"
    elif is_online is False:
        state = "offline"
    else:
        state = "unknown"

    return html.Span(className=f"cp-status-dot cp-status-dot--{state}")
