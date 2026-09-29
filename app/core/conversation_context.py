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
    "it's ",
    "its ",
    "now ",
    "still ",
    "that ",
    "the same ",
    "this ",
)


# Short replies with one of these openings often depend on the previous turn,
# but only when there is already a recent support topic in the conversation.
HISTORY_AWARE_FOLLOW_UP_PREFIXES = (
    "no ",
    "yes ",
    "yeah ",
    "yep ",
    "i'm ",
    "im ",
    "i am ",
    "i already ",
    "i know ",
    "i just ",
    "the ",
    "there ",
    "they ",
    "how do i ",
    "can i ",
)


# Very short additions such as "and usb-c block" usually name another
# inventory item or a new device instead of describing the previous problem.
# Treating them as generic conversational follow-ups can accidentally attach
# an unrelated earlier account, calendar, or printer issue to the new noun.
SHORT_STANDALONE_SUBJECTS = (
    "usb-c block",
    "usb-c charging block",
    "usb c charging block",
    "usb c block",
    "usb-c charger",
    "usb c charger",
    "usb-c cable",
    "usb c cable",
    "usb-a block",
    "usb a block",
    "charger",
    "adapter",
    "cable",
    "mouse",
    "keyboard",
    "stylus",
    "ipad",
    "chromebook",
    "macbook",
)


SHORT_CONTINUATION_SIGNALS = (
    "still",
    "not working",
    "doesn't work",
    "does not work",
    "same issue",
    "no signal",
    "error",
    "problem",
    "issue",
)


SUPPORT_CONTEXT_MARKERS = (
    "printer",
    "print",
    "printing",
    "print queue",
    "library",
    "wifi",
    "wi-fi",
    "internet",
    "network",
    "mac",
    "macbook",
    "chromebook",
    "chrome",
    "safari",
    "google",
    "gmail",
    "drive",
    "classroom",
    "meet",
    "zoom",
    "adobe",
    "creative cloud",
    "acrobat",
    "photoshop",
    "projector",
    "classroom tv",
    "display",
    "screen",
    "touch screen",
    "monitor",
    "airplay",
    "apple tv",
    "camera",
    "microphone",
    "sound",
    "audio",
    "password",
    "account",
    "charger",
    "battery",
    "keyboard",
    "mouse",
    "inventory",
    "loaner",
    "usb-c",
    "smartboard",
    "smart board",
)


# A short message that names a clearly different support subject should be
# treated as a new issue rather than silently attached to the previous topic.
NEW_ISSUE_MARKERS = (
    "printer",
    "wifi",
    "wi-fi",
    "zoom",
    "google classroom",
    "google drive",
    "google meet",
    "gmail",
    "safari",
    "chrome",
    "adobe",
    "photoshop",
    "projector",
    "classroom tv",
    "monitor",
    "camera",
    "microphone",
    "mouse",
    "keyboard",
    "charger",
    "battery",
)


def recent_user_messages(
    history: list[dict[str, Any]],
    current_question: str,
    limit: int = 12,
) -> list[str]:
    """Return recent user messages, excluding the current message once."""

    normalized_current = normalize_text(current_question)
    skipped_current = False
    values: list[str] = []

    for message in reversed(history[-limit:]):
        if message.get("role") != "user":
            continue

        content = str(message.get("content", "")).strip()
        if not content:
            continue

        if (
            not skipped_current
            and normalize_text(content) == normalized_current
        ):
            skipped_current = True
            continue

        values.append(content)

    return values


def has_recent_support_context(
    history: list[dict[str, Any]] | None,
    current_question: str = "",
) -> bool:
    """Return whether recent user turns establish an active IT support topic."""

    if not history:
        return False

    current = normalize_text(current_question)
    for message in reversed(history[-12:]):
        if message.get("role") != "user":
            continue

        content = normalize_text(str(message.get("content", "")))
        if not content or content == current:
            continue

        if any(marker in content for marker in SUPPORT_CONTEXT_MARKERS):
            return True

    return False


def _looks_like_short_new_issue(text: str) -> bool:
    """Protect short but explicit new issues from being glued to old context."""

    normalized = normalize_text(text)
    if not normalized:
        return False

    # "My printer is offline" is a complete new issue even though it is short.
    if normalized.startswith(("my ", "a ", "an ")) and any(
        marker in normalized for marker in NEW_ISSUE_MARKERS
    ):
        return True

    return False


def is_contextual_follow_up(
    text: str,
    history: list[dict[str, Any]] | None = None,
) -> bool:
    """Return whether a message depends on a recent user issue.

    The history parameter is optional for backward compatibility. When history
    is supplied, short conversational replies such as "No, for the Library",
    "I'm using a MacBook Air", or "The light is flashing red" retain the
    existing support topic instead of being routed as unrelated new questions.
    """

    normalized = normalize_text(text)
    if not normalized:
        return False

    if is_platform_only_reply(text):
        return True

    if normalized in GENERIC_FOLLOW_UP_VALUES:
        return True

    if (
        len(normalized.split()) <= 6
        and normalized.startswith(("and ", "also "))
        and any(subject in normalized for subject in SHORT_STANDALONE_SUBJECTS)
        and not any(signal in normalized for signal in SHORT_CONTINUATION_SIGNALS)
    ):
        return False

    if (
        len(normalized.split()) <= 12
        and normalized.startswith(FOLLOW_UP_PREFIXES)
    ):
        return True

    if not history or not has_recent_support_context(history, text):
        return False

    if _looks_like_short_new_issue(text):
        return False

    word_count = len(normalized.split())
    if word_count > 12:
        return False

    # A device/platform clarification is context, even when written as a short
    # sentence rather than a bare "Mac"/"Chromebook" reply.
    if detect_platform(text) is not None and word_count <= 8:
        return True

    if normalized.startswith(HISTORY_AWARE_FOLLOW_UP_PREFIXES):
        return True

    # Pronoun/deictic references usually depend on the object already being
    # discussed. This catches replies such as "wiped the lens", "red light",
    # and "who did it" without forcing every short sentence into old context.
    reference_terms = (
        " it",
        " it ",
        " that",
        " this",
        " one",
        " them",
        " they",
        " who",
        " lens",
        " light",
        " cable",
        " port",
        " list",
        " settings",
    )
    padded = f" {normalized} "
    return any(term in padded for term in reference_terms)


def recent_issue_chain(
    history: list[dict[str, Any]],
    current_question: str,
    limit: int = 6,
) -> list[str]:
    """Return the active user issue plus its short follow-ups."""

    chain_reversed: list[str] = []
    for content in recent_user_messages(history, current_question, limit=18):
        normalized = normalize_text(content)
        if not normalized:
            continue

        chain_reversed.append(content)

        is_short_context = (
            is_platform_only_reply(content)
            or normalized in GENERIC_FOLLOW_UP_VALUES
            or is_contextual_follow_up(content, history)
        )
        if not is_short_context:
            break
        if len(chain_reversed) >= limit:
            break

    return list(reversed(chain_reversed))


def find_recent_user_issue(
    history: list[dict[str, Any]],
    current_question: str,
) -> str:
    """Find the root issue for the current short follow-up chain."""

    chain = recent_issue_chain(history, current_question)
    return chain[0] if chain else ""


def build_contextual_query(
    question: str,
    history: list[dict[str, Any]] | None,
) -> str:
    """Turn a short follow-up into a standalone retrieval query."""

    cleaned_question = question.strip()

    if (
        not history
        or not is_contextual_follow_up(cleaned_question, history)
    ):
        return cleaned_question

    chain = recent_issue_chain(history, cleaned_question)
    if not chain:
        return cleaned_question

    parts = [chain[0]]
    for follow_up in chain[1:]:
        parts.append(f"Follow-up: {follow_up}")

    # Always preserve the user's actual follow-up text.  Platform detection is
    # extra context, not a replacement for the message.  Dropping the text here
    # previously turned replies such as "To connect my MacBook to the smartboard"
    # into only "Operating system: Mac", which erased the user's new symptom/goal.
    parts.append(f"Follow-up: {cleaned_question}")

    platform = detect_platform(cleaned_question)
    if platform is not None and (
        is_platform_only_reply(cleaned_question)
        or len(normalize_text(cleaned_question).split()) <= 8
    ):
        parts.append(f"Operating system: {platform_display_name(platform)}")

    return "\n".join(parts)
