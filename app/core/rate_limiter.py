"""Per-session rolling-window limits for public chat messages."""

from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from typing import Iterable


DEFAULT_MESSAGE_LIMIT = 12
DEFAULT_WINDOW_SECONDS = 60


@dataclass(frozen=True)
class RateLimitDecision:
    """Result of checking one message against the current session window."""

    allowed: bool
    timestamps: tuple[float, ...]
    remaining: int
    retry_after_seconds: int


def _positive_environment_integer(name: str, default: int) -> int:
    """Read a positive integer setting, falling back safely when invalid."""
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    return value if value > 0 else default


def configured_message_limit() -> int:
    """Return the configured maximum accepted messages per window."""
    return _positive_environment_integer(
        "ALTITUDE_RATE_LIMIT_MESSAGES",
        DEFAULT_MESSAGE_LIMIT,
    )


def configured_window_seconds() -> int:
    """Return the configured rolling-window length in seconds."""
    return _positive_environment_integer(
        "ALTITUDE_RATE_LIMIT_WINDOW_SECONDS",
        DEFAULT_WINDOW_SECONDS,
    )


def evaluate_message_rate(
    timestamps: Iterable[object],
    *,
    now: float | None = None,
    message_limit: int | None = None,
    window_seconds: int | None = None,
) -> RateLimitDecision:
    """Evaluate and, when allowed, record one session message.

    Only accepted messages are recorded. Invalid, expired, and future values
    are discarded so stale Streamlit state cannot lock a user out.
    """
    current_time = time.monotonic() if now is None else float(now)
    limit = (
        configured_message_limit()
        if message_limit is None
        else message_limit
    )
    window = (
        configured_window_seconds()
        if window_seconds is None
        else window_seconds
    )

    if limit <= 0 or window <= 0:
        raise ValueError("Rate-limit values must be positive integers.")

    cutoff = current_time - window
    recent: list[float] = []

    for value in timestamps:
        if isinstance(value, bool):
            continue
        try:
            timestamp = float(value)
        except (TypeError, ValueError):
            continue
        if cutoff < timestamp <= current_time:
            recent.append(timestamp)

    recent.sort()

    if len(recent) >= limit:
        retry_after = max(
            1,
            math.ceil(recent[0] + window - current_time),
        )
        return RateLimitDecision(
            allowed=False,
            timestamps=tuple(recent),
            remaining=0,
            retry_after_seconds=retry_after,
        )

    recent.append(current_time)
    return RateLimitDecision(
        allowed=True,
        timestamps=tuple(recent),
        remaining=max(0, limit - len(recent)),
        retry_after_seconds=0,
    )
