"""
Card components — the fundamental UI container.

Provides card(), kpi_card(), and chart_card() functions returning
Dash component trees styled via the cp-card design tokens.
"""

from dash import html, dcc


def card(
    title: str | None = None,
    subtitle: str | None = None,
    children=None,
    card_id: str | None = None,
    flush: bool = False,
    highlight: bool = False,
    footer=None,
    header_right=None,
    class_name: str = "",
    reserve_subtitle_space: bool = False,
) -> html.Div:
    """Create a standard card container.

    Args:
        title: Card header title text.
        subtitle: Smaller subtitle below the title.
        children: Card body content.
        card_id: HTML id attribute.
        flush: If True, removes body padding (for full-bleed charts).
        highlight: If True, adds left accent border.
        footer: Optional footer content.
        header_right: Optional content on the right side of the header.
        class_name: Additional CSS classes.
        reserve_subtitle_space: If True, keep a subtitle row even when empty.
    """
    classes = ["cp-card"]
    if flush:
        classes.append("cp-card--flush")
    if highlight:
        classes.append("cp-card--highlight")
    if class_name:
        classes.append(class_name)

    parts = []

    if title:
        subtitle_node = None
        if subtitle:
            subtitle_node = html.P(subtitle, className="cp-card__subtitle")
        elif reserve_subtitle_space:
            subtitle_node = html.P(
                "\u00A0",
                className="cp-card__subtitle cp-card__subtitle--placeholder",
                **{"aria-hidden": "true"},
            )
        header_children = [
            html.Div([
                html.H3(title, className="cp-card__title"),
                subtitle_node,
            ]),
        ]
        if header_right:
            header_children.append(html.Div(header_right))
        parts.append(html.Div(header_children, className="cp-card__header"))

    if children is not None:
        parts.append(html.Div(children, className="cp-card__body"))

    if footer is not None:
        parts.append(html.Div(footer, className="cp-card__footer"))

    props = {"className": " ".join(classes)}
    if card_id:
        props["id"] = card_id

    return html.Div(parts, **props)


def kpi_card(
    label: str,
    value: str = "—",
    delta: str | None = None,
    delta_direction: str = "neutral",
    card_id: str | None = None,
) -> html.Div:
    """Create a compact KPI metric card.

    Args:
        label: Metric name (e.g. "Avg Stress").
        value: Current value to display prominently.
        delta: Optional change indicator text (e.g. "+3.2%").
        delta_direction: One of "up", "down", "neutral".
        card_id: HTML id for dynamic updates.
    """
    value_props = {"className": "cp-kpi__value"}
    if card_id:
        value_props["id"] = f"{card_id}-value"

    children = [
        html.Div(label, className="cp-kpi__label"),
        html.Div(value, **value_props),
    ]

    if delta is not None:
        arrow = {"up": "▲ ", "down": "▼ ", "neutral": ""}
        delta_props = {
            "className": f"cp-kpi__delta cp-kpi__delta--{delta_direction}",
        }
        if card_id:
            delta_props["id"] = f"{card_id}-delta"
        children.append(
            html.Span(
                f"{arrow.get(delta_direction, '')}{delta}",
                **delta_props,
            )
        )

    props = {"className": "cp-kpi"}
    if card_id:
        props["id"] = card_id

    return html.Div(children, **props)


def chart_card(
    title: str,
    graph_id: str,
    subtitle: str | None = None,
    aspect: str = "16x9",
    header_right=None,
    height: str | None = None,
) -> html.Div:
    """Create a card wrapping a Plotly dcc.Graph with consistent sizing.

    Args:
        title: Chart title in the card header.
        graph_id: The id for the dcc.Graph component.
        subtitle: Optional subtitle / hypothesis tag.
        aspect: Aspect ratio class: "16x9", "4x3", "square", "wide".
        header_right: Optional header-right content (badges, etc.).
        height: Fixed height override (e.g. "350px"). If set, ignores aspect.
    """
    container_class = f"cp-chart-container cp-chart-container--{aspect}"
    style = {}
    if height:
        container_class = "cp-chart-container"
        style = {"height": height}

    graph = html.Div(
        dcc.Graph(
            id=graph_id,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToRemove": [
                    "select2d", "lasso2d", "autoScale2d", "toggleSpikelines",
                ],
                "responsive": True,
            },
            style={"width": "100%", "height": "100%"},
        ),
        className=container_class,
        style=style if style else None,
    )

    return card(
        title=title,
        subtitle=subtitle,
        children=graph,
        flush=True,
        header_right=header_right,
        class_name="cp-card--chart",
        reserve_subtitle_space=True,
    )
