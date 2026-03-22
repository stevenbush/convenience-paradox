"""conftest.py — pytest configuration for The Convenience Paradox project.

Registers custom marks so pytest does not emit PytestUnknownMarkWarning.
All marks are documented here with their intended usage.
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
