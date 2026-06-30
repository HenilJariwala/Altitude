from __future__ import annotations

from typing import Any

from core.platform_context import (
    detect_platform,
    is_platform_only_reply,
    platform_display_name,
)
from core.text_matching import normalize_text


GENERIC_FOLLOW_UP_VALUES = {
    "guest",
    "no",
    "nope",
    "student",
    "yes",
    "yeah",
    "yep",
    "still not working",
    "that did not work",
    "that didn't work",
    "it did not work",
    "it didn't work",
    "same issue",
    "problem continues",
    "issue continues",
}


FOLLOW_UP_PREFIXES = (
    "also ",
    "and ",
    "but ",
    "it ",
    "now ",
    "still ",
    "that ",
    "the same ",
    "this ",
)


def recent_user_messages(
    history: list[dict[str, Any]],
    current_question: str,
    limit: int = 12,
) -> list[str]:
    """Return recent user messages, excluding the current message once."""

    normalized_current = normalize_text(
        current_question
    )
    skipped_current = False
    values: list[str] = []

    for message in reversed(history[-limit:]):
        if message.get("role") != "user":
            continue

        content = str(
            message.get("content", "")
        ).strip()

        if not content:
            continue

        if (
            not skipped_current
            and normalize_text(content)
            == normalized_current
        ):
            skipped_current = True
            continue

        values.append(content)

    return values


def is_contextual_follow_up(text: str) -> bool:
    """Return whether a message depends on a recent user issue."""

    normalized = normalize_text(text)

    if not normalized:
        return False

    if is_platform_only_reply(text):
        return True

    if normalized in GENERIC_FOLLOW_UP_VALUES:
        return True

    return (
        len(normalized.split()) <= 12
        and normalized.startswith(FOLLOW_UP_PREFIXES)
    )


def find_recent_user_issue(
    history: list[dict[str, Any]],
    current_question: str,
) -> str:
    """Find the most recent substantive user issue."""

    for content in recent_user_messages(
        history,
        current_question,
    ):
        if is_platform_only_reply(content):
            continue

        normalized = normalize_text(content)

        if normalized in GENERIC_FOLLOW_UP_VALUES:
            continue

        return content

    return ""


def build_contextual_query(
    question: str,
    history: list[dict[str, Any]] | None,
) -> str:
    """Turn a short follow-up into a standalone retrieval query."""

    cleaned_question = question.strip()

    if (
        not history
        or not is_contextual_follow_up(cleaned_question)
    ):
        return cleaned_question

    previous_issue = find_recent_user_issue(
        history,
        cleaned_question,
    )

    if not previous_issue:
        return cleaned_question

    platform = detect_platform(cleaned_question)

    if (
        platform is not None
        and is_platform_only_reply(cleaned_question)
    ):
        return (
            f"{previous_issue}\n"
            f"Operating system: "
            f"{platform_display_name(platform)}"
        )

    return (
        f"{previous_issue}\n"
        f"Follow-up: {cleaned_question}"
    )
