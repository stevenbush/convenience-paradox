"""Tests for reusable Dash UI components."""

from dash import html

from dash_app.components.card import kpi_card
from dash_app.utils import format_run_label


def test_kpi_card_without_card_id_omits_child_ids() -> None:
    """kpi_card should not pass id=None to Dash child components."""
    component = kpi_card("Avg Stress", "0.123", delta="Spread: 0.010")

    assert isinstance(component, html.Div)
    assert getattr(component, "id", None) is None

    label, value, delta = component.children
    assert getattr(value, "id", None) is None
    assert getattr(delta, "id", None) is None


def test_kpi_card_with_card_id_sets_child_ids() -> None:
    """kpi_card should generate stable child ids when card_id is provided."""
    component = kpi_card("Avg Stress", "0.123", delta="Spread: 0.010", card_id="stress-kpi")

    assert component.id == "stress-kpi"

    label, value, delta = component.children
    assert value.id == "stress-kpi-value"
    assert delta.id == "stress-kpi-delta"


def test_format_run_label_falls_back_when_database_label_is_missing() -> None:
    """Run Manager comparison should survive NULL or blank labels."""
    assert format_run_label({"id": 32, "label": None}) == "Run 32"
    assert format_run_label({"id": 33, "label": "   "}) == "Run 33"


def test_format_run_label_truncates_long_labels() -> None:
    """Long labels should be shortened to keep the comparison legend compact."""
    label = format_run_label({"id": 99, "label": "A very long dashboard experiment label"})
    assert label == "A very long dashboard ..."
