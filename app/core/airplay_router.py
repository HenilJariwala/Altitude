from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.platform_context import detect_platform
from core.text_matching import normalize_text
from core.topic_context import build_topic_context


@dataclass(frozen=True)
class AirPlayDecision:
    """Result returned by the AirPlay router."""

    handled: bool
    answer: str = ""


MAC_TERMS = (
    "mac",
    "macbook",
    "mac book",
    "macos",
    "apple laptop",
)


WINDOWS_TERMS = (
    "windows",
    "windows pc",
    "windows laptop",
    "pc",
    "dell laptop",
    "hp laptop",
)


AIRPLAY_TERMS = (
    "airplay",
    "air play",
    "apple tv",
    "screen mirroring",
    "screen mirror",
    "mirror my screen",
)


AIRPLAY_ACTION_TERMS = (
    "connect",
    "mirror",
    "airplay",
    "air play",
    "cast",
    "display",
    "show my screen",
    "share my screen",
    "present",
    "project",
)


TROUBLESHOOTING_TERMS = (
    "not working",
    "does not work",
    "doesn't work",
    "doesnt work",
    "not connecting",
    "cannot connect",
    "can't connect",
    "cant connect",
    "not showing",
    "does not appear",
    "doesn't appear",
    "not appearing",
    "cannot find",
    "can't find",
    "cant find",
    "not listed",
    "disconnecting",
    "keeps disconnecting",
    "black screen",
    "no picture",
    "error",
    "problem",
    "issue",
)


def get_last_assistant_message(
    history: list[dict[str, Any]],
) -> str:
    """Return the most recent assistant message."""

    for message in reversed(history):
        if message.get("role") != "assistant":
            continue

        content = message.get("content")

        if isinstance(content, str):
            return content

    return ""

def get_recent_messages(
    history: list[dict[str, Any]],
    limit: int = 6,
) -> list[str]:
    """Return recent valid conversation messages."""

    messages: list[str] = []

    for message in history[-limit:]:
        content = message.get("content")

        if isinstance(content, str) and content.strip():
            messages.append(
                normalize_text(content)
            )

    return messages


def has_recent_airplay_context(
    history: list[dict[str, Any]],
) -> bool:
    """
    Detect whether the recent conversation is about
    AirPlay, Apple TV, or screen mirroring.
    """

    recent_messages = get_recent_messages(
        history,
        limit=6,
    )

    airplay_context_terms = (
        "airplay",
        "air play",
        "apple tv",
        "screen mirroring",
        "screen mirror",
        "mirror my screen",
        "wireless display",
    )

    return any(
        any(
            term in message
            for term in airplay_context_terms
        )
        for message in recent_messages
    )


def is_computer_type_follow_up(
    question: str,
) -> bool:
    """
    Detect short corrections or answers such as:
    - Mac
    - I have a Mac
    - Actually it is Windows
    - I meant MacBook
    """

    normalized = normalize_text(question)

    if not detect_computer_type(question):
        return False

    follow_up_phrases = (
        "mac",
        "macbook",
        "mac book",
        "windows",
        "windows pc",
        "pc",
        "i have mac",
        "i have a mac",
        "i have macbook",
        "i have a macbook",
        "i have windows",
        "i have a windows pc",
        "actually mac",
        "actually a mac",
        "actually windows",
        "it is mac",
        "it is a mac",
        "it's mac",
        "it's a mac",
        "i meant mac",
        "i meant macbook",
        "i meant windows",
        "sorry mac",
        "sorry windows",
    )

    return (
        normalized in follow_up_phrases
        or len(normalized.split()) <= 5
    )

def waiting_for_airplay_device(
    history: list[dict[str, Any]],
) -> bool:
    """
    Detect whether the recent conversation is waiting for
    or discussing the computer type for Apple TV mirroring.
    """

    last_message = normalize_text(
        get_last_assistant_message(history)
    )

    assistant_asked_for_device = (
        "apple tv" in last_message
        and "mac" in last_message
        and "windows" in last_message
    )

    return (
        assistant_asked_for_device
        or has_recent_airplay_context(history)
    )

def detect_computer_type(
    text: str,
) -> str | None:
    """Detect whether the user has a Mac or Windows PC."""

    platform = detect_platform(text)

    if platform == "macos":
        return "mac"

    if platform == "windows":
        return "windows"

    return None


def is_airplay_request(
    question: str,
    history: list[dict[str, Any]],
) -> bool:
    """Return True for Apple TV screen-sharing requests."""

    normalized = normalize_text(question)

    if not normalized:
        return False

    # Handle short follow-ups or corrections:
    # "Mac", "I have a Mac", "Actually Windows", etc.
    if (
        is_computer_type_follow_up(question)
        and has_recent_airplay_context(history)
    ):
        return True

    has_airplay_term = any(
        term in normalized
        for term in AIRPLAY_TERMS
    )

    has_action_term = any(
        term in normalized
        for term in AIRPLAY_ACTION_TERMS
    )

    if (
        "airplay" in normalized
        or "air play" in normalized
    ):
        return True

    return (
        has_airplay_term
        and has_action_term
    )

def is_airplay_troubleshooting(
    question: str,
) -> bool:
    normalized = normalize_text(question)

    return any(
        term in normalized
        for term in TROUBLESHOOTING_TERMS
    )


def build_mac_airplay_answer() -> str:
    return (
        "To mirror your **MacBook to the Apple TV**:\n\n"
        "1. Turn on the TV and select the input connected "
        "to the Apple TV.\n"
        "2. Confirm that the MacBook and Apple TV are on "
        "the same approved school network.\n"
        "3. On the MacBook, open **Control Center** from "
        "the menu bar.\n"
        "4. Select **Screen Mirroring**.\n"
        "5. Select the correct classroom Apple TV.\n"
        "6. If a code appears on the TV, enter that code "
        "on the MacBook.\n"
        "7. Choose whether to mirror the MacBook display "
        "or use the TV as another display when prompted.\n\n"
        "To disconnect, open **Control Center → Screen "
        "Mirroring**, then select the Apple TV again or "
        "choose **Stop Mirroring**.\n\n"
        "Do not share the AirPlay code with people who are "
        "not in the room."
    )


def build_mac_airplay_troubleshooting_answer() -> str:
    return (
        "If the Apple TV is not appearing on the MacBook:\n\n"
        "1. Confirm that the TV is showing the Apple TV "
        "input and that the Apple TV is awake.\n"
        "2. Confirm that the MacBook and Apple TV are on "
        "the same approved school network.\n"
        "3. Open **Control Center → Screen Mirroring** again.\n"
        "4. Turn Wi-Fi off and back on from the MacBook.\n"
        "5. Restart the MacBook.\n"
        "6. Restart the Apple TV only if you are authorized "
        "to control the classroom equipment.\n"
        "7. Ask the IT Helpdesk to confirm that AirPlay is "
        "enabled and that the Apple TV allows connections "
        "from the school network.\n\n"
        "If the Apple TV still does not appear, contact the "
        "IT Helpdesk with the classroom name and Apple TV name."
    )


def build_windows_apple_tv_answer() -> str:
    return (
        "A **Windows PC cannot natively AirPlay its full "
        "screen to an Apple TV**.\n\n"
        "Windows' built-in wireless-display feature uses "
        "Miracast, while Apple TV receives AirPlay.\n\n"
        "Use one of the school's approved alternatives:\n\n"
        "1. Connect the Windows PC to the TV using an "
        "approved HDMI cable and adapter.\n"
        "2. Use the classroom's approved wireless "
        "presentation system, if one is installed.\n"
        "3. Ask the IT Helpdesk whether an approved "
        "AirPlay-compatible Windows application is available.\n\n"
        "Do not install random third-party AirPlay or "
        "screen-mirroring software on a school device."
    )


def route_airplay_question(
    question: str,
    history: list[dict[str, Any]],
) -> AirPlayDecision:
    """Handle AirPlay and Apple TV screen-sharing requests."""

    topic_context = build_topic_context(question, history)
    if not topic_context.allows("airplay"):
        return AirPlayDecision(handled=False)

    if not is_airplay_request(
        question,
        history,
    ):
        return AirPlayDecision(
            handled=False,
        )

    computer_type = detect_computer_type(
        question
    )

    if computer_type == "windows":
        return AirPlayDecision(
            handled=True,
            answer=build_windows_apple_tv_answer(),
        )

    if computer_type == "mac":
        if is_airplay_troubleshooting(question):
            answer = (
                build_mac_airplay_troubleshooting_answer()
            )
        else:
            answer = build_mac_airplay_answer()

        return AirPlayDecision(
            handled=True,
            answer=answer,
        )

    return AirPlayDecision(
        handled=True,
        answer=(
            "Are you connecting to the Apple TV from a "
            "**MacBook/Mac** or a **Windows PC**?"
        ),
    )