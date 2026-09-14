from __future__ import annotations

import os
from datetime import datetime, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_TIMEZONE_NAME = "America/Toronto"


def get_local_timezone() -> tzinfo:
    """Return Altitude's configured timezone with a reliable fallback."""
    configured_name = (
        os.getenv("ALTITUDE_TIMEZONE", DEFAULT_TIMEZONE_NAME).strip()
        or DEFAULT_TIMEZONE_NAME
    )

    try:
        return ZoneInfo(configured_name)
    except (ZoneInfoNotFoundError, ValueError):
        try:
            return ZoneInfo(DEFAULT_TIMEZONE_NAME)
        except ZoneInfoNotFoundError:
            return timezone.utc


def local_now() -> datetime:
    """Return the current time in Altitude's configured timezone."""
    return datetime.now(get_local_timezone())
