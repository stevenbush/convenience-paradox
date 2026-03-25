"""Small utility helpers shared across Dash pages."""

from __future__ import annotations


def format_run_label(run_row: dict, max_length: int = 25) -> str:
    """Return a safe display label for a saved run.

    Falls back to the run id when the database label is NULL/empty and
    truncates long labels for compact legends in the comparison panel.
    """
    run_id = run_row.get("id", "?")
    raw_label = run_row.get("label")
    label = str(raw_label).strip() if raw_label is not None else ""
    if not label:
        label = f"Run {run_id}"
    if len(label) > max_length:
        label = label[:max_length - 3] + "..."
    return label
