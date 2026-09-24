from __future__ import annotations

import re
from typing import Literal

from core.text_matching import contains_phrase, normalize_text


Platform = Literal["macos", "chromebook", "windows"]


PLATFORM_ALIASES: dict[Platform, tuple[str, ...]] = {
    "macos": (
        "apple computer",
        "apple laptop",
        "mac book",
        "macbook",
        "mac os",
        "macos",
        "os x",
        "mac",
    ),
    "chromebook": (
        "chromebook",
        "chrome book",
        "chromeos",
        "chrome os",
    ),
    "windows": (
        "windows laptop",
        "windows computer",
        "windows pc",
        "windows 11",
        "windows 10",
        "dell laptop",
        "hp laptop",
        "windows",
        "pc",
    ),
}


PLATFORM_DISPLAY_NAMES: dict[Platform, str] = {
    "macos": "Mac",
    "chromebook": "Chromebook",
    "windows": "Windows",
}


_CONTEXT_FILLER_WORDS = {
    "a",
    "actually",
    "am",
    "an",
    "computer",
    "currently",
    "device",
    "have",
    "i",
    "im",
    "i'm",
    "is",
    "it",
    "it's",
    "laptop",
    "machine",
    "meant",
    "my",
    "on",
    "operating",
    "os",
    "please",
    "running",
    "sorry",
    "system",
    "the",
    "this",
    "use",
    "using",
}


def detect_platform(text: str) -> Platform | None:
    """Detect one unambiguous desktop operating system."""

    matches: set[Platform] = set()

    for platform, aliases in PLATFORM_ALIASES.items():
        if any(
            contains_phrase(text, alias)
            for alias in aliases
        ):
            matches.add(platform)

    if len(matches) != 1:
        return None

    return next(iter(matches))


def platform_display_name(
    platform: Platform,
) -> str:
    return PLATFORM_DISPLAY_NAMES[platform]


def is_platform_only_reply(text: str) -> bool:
    """Recognize natural platform-only replies.

    Examples include ``Mac``, ``I am using a Mac``, and
    ``Actually, this is a Chromebook``. A message that also contains an
    issue, such as ``my Mac is frozen``, is not considered platform-only.
    """

    platform = detect_platform(text)

    if platform is None:
        return False

    remainder = normalize_text(text)

    for alias in sorted(
        PLATFORM_ALIASES[platform],
        key=len,
        reverse=True,
    ):
        normalized_alias = normalize_text(alias)
        remainder = re.sub(
            rf"(?<![a-z0-9]){re.escape(normalized_alias)}(?![a-z0-9])",
            " ",
            remainder,
        )

    tokens = re.findall(
        r"[a-z0-9']+",
        remainder,
    )

    return all(
        token in _CONTEXT_FILLER_WORDS
        or token.isdigit()
        for token in tokens
    )
