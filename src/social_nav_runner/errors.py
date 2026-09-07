"""Stable failure categories for social-nav run --execute."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class HopError(Exception):
    def __init__(self, category: str, message: str) -> None:
        self.category = category
        super().__init__(message)


def as_hop(category: str, fn: Callable[..., T], *args, **kwargs) -> T:
    try:
        return fn(*args, **kwargs)
    except TimeoutError as exc:
        raise HopError(category, str(exc)) from exc
