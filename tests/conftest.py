"""Keep native Isaac off during unit tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_isaac(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOCIAL_NAV_ISAAC_PATH", "/nonexistent/isaac/python.sh")
