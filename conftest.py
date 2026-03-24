"""conftest.py — pytest configuration for The Convenience Paradox project.

Registers custom marks so pytest does not emit PytestUnknownMarkWarning and
keeps live-Ollama tests out of the default offline test run.
"""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom pytest marks."""
    config.addinivalue_line(
        "markers",
        "ollama: marks tests that require a running Ollama instance with the "
        "qwen3.5:4b or qwen3:1.7b model available. Skip with "
        "'pytest -k \"not ollama\"' in CI or offline environments.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip live Ollama tests unless they were explicitly requested.

    The project keeps a small set of end-to-end LLM tests for manual
    verification, but the default `pytest` invocation should remain green in
    offline environments. Users can still run them explicitly with
    `pytest -m ollama`.
    """
    markexpr = (config.option.markexpr or "").strip()
    if "ollama" in markexpr:
        return

    skip_ollama = pytest.mark.skip(
        reason="requires explicit selection via `pytest -m ollama` and a running Ollama instance",
    )
    for item in items:
        if "ollama" in item.keywords:
            item.add_marker(skip_ollama)
