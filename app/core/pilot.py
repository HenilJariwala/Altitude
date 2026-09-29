"""Configuration and validation helpers for the faculty pilot."""

from __future__ import annotations

import os


def _environment_flag(name: str, default: bool = False) -> bool:
    """Return a predictable boolean value from an environment variable."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().casefold() in {"1", "true", "yes", "on"}


def is_pilot_mode_enabled() -> bool:
    """Return whether the faculty pilot experience is enabled."""
    return _environment_flag("ALTITUDE_PILOT_MODE", False)


def is_pilot_name_required() -> bool:
    """Return whether a participant must identify themselves before chat."""
    return _environment_flag("ALTITUDE_PILOT_REQUIRE_NAME", True)


def is_pilot_ticket_submission_disabled() -> bool:
    """Return whether pilot users are prevented from creating real tickets."""
    return _environment_flag("ALTITUDE_PILOT_DISABLE_TICKETS", True)


def get_pilot_label() -> str:
    """Return the short label displayed in the pilot interface."""
    configured = " ".join(
        os.getenv("ALTITUDE_PILOT_LABEL", "Faculty Pilot").split()
    )
    return configured[:80] or "Faculty Pilot"


def normalize_participant_name(value: str) -> str:
    """Normalize and validate a faculty pilot participant's display name."""
    normalized = " ".join(str(value).split()).strip()
    if len(normalized) < 2:
        raise ValueError("Enter your first and last name, or your staff display name.")
    if len(normalized) > 100:
        raise ValueError("The participant name must be 100 characters or fewer.")
    if sum(character.isalnum() for character in normalized) < 2:
        raise ValueError("Enter a valid participant name.")
    return normalized
