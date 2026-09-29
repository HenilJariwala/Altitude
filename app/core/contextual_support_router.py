from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.conversation_context import build_contextual_query, find_recent_user_issue
from core.platform_context import detect_platform
from core.text_matching import contains_any_phrase, normalize_text


@dataclass(frozen=True)
class ContextualSupportDecision:
    """A high-confidence answer that may depend on earlier user messages."""

    handled: bool
    answer: str = ""
    intent: str = ""


def _has(text: str, *phrases: str) -> bool:
    return contains_any_phrase(text, phrases)


def route_contextual_support(
    question: str,
    history: list[dict[str, Any]],
) -> ContextualSupportDecision:
    """Handle support cases where corrections must change the next answer.

    The combined query keeps the original issue and the user's latest
    correction together. This prevents replies such as "I'm on Windows" or
    "it works in Voice Memos" from being treated as unrelated questions.
    """

    current = normalize_text(question).strip(" .")
    combined = normalize_text(build_contextual_query(question, history)).strip(" .")
    if not current:
        return ContextualSupportDecision(False)

    # A school abbreviation is meaningful only beside the preceding Wi-Fi
    # question, but it does not contain a normal pronoun/prefix follow-up cue.
    if current == "sjk" and combined == current:
        prior_issue = find_recent_user_issue(history, question)
        if prior_issue:
            combined = normalize_text(f"{prior_issue} Follow-up: {question}")

    if current in {
        "i need to fix my computer",
        "help me fix my computer",
        "my computer is not working",
        "my computer doesn't work",
        "my computer does not work",
    }:
        return ContextualSupportDecision(
            True,
            (
                "What kind of computer are you using—**Windows, Mac, or Chromebook**? "
                "Also tell me what is happening, including any error message and what you were trying to do."
            ),
            "computer_issue_clarification",
        )

    if (
        current in {"sjk", "school wifi", "school wi-fi", "the school wifi"}
        and _has(combined, "wifi", "wi-fi", "wireless network")
        and _has(combined, "password", "student wifi", "guest wifi")
    ):
        return ContextualSupportDecision(
            True,
            (
                "SJK identifies the school network, but I still need to know which approved option you mean: "
                "**Student Wi-Fi** or **Guest Wi-Fi**? Altitude will provide the approved connection method rather than displaying a private network password."
            ),
            "wifi_network_clarification",
        )

    keyboard_issue = _has(combined, "keyboard", "key")
    repeating_key = _has(
        combined,
        "same letter",
        "same character",
        "key keeps repeating",
        "keeps repeating",
        "repeating key",
        "types repeatedly",
        "typing repeatedly",
    )
    if keyboard_issue and repeating_key:
        return ContextualSupportDecision(
            True,
            (
                "This sounds like a **stuck or repeating key**, not a keyboard-language problem. "
                "Test the key in another app, restart the device, and check around the key for visible debris without removing the keycap. "
                "If available, use an approved external keyboard temporarily. If the same key continues repeating after restart, contact IT because the built-in keyboard may need service."
            ),
            "keyboard_repeating_key",
        )

    trackpad_issue = _has(combined, "trackpad", "touchpad") and _has(
        combined,
        "not clicking",
        "won't click",
        "wont click",
        "can't click",
        "cant click",
        "frozen",
        "not responding",
    )
    if trackpad_issue:
        platform = detect_platform(combined)
        if platform is None:
            return ContextualSupportDecision(
                True,
                (
                    "Which device are you using: **Windows, Mac, or Chromebook**? "
                    "The touchpad/trackpad troubleshooting steps are different for each one."
                ),
                "trackpad_platform_clarification",
            )

        if platform == "windows":
            return ContextualSupportDecision(
                True,
                (
                    "Since this is Windows, connect an approved USB mouse if available and save your work. "
                    "Restart the computer, then open **Settings → Bluetooth & devices → Touchpad** and confirm the touchpad is enabled. "
                    "If the touchpad still will not click, or the case looks raised or swollen, stop using the laptop and contact IT for hardware service."
                ),
                "windows_touchpad_not_clicking",
            )

        if platform == "chromebook":
            return ContextualSupportDecision(
                True,
                (
                    "Since this is a Chromebook, connect an approved USB mouse if available and save your work. "
                    "Restart the Chromebook and test the touchpad again. Do not Powerwash it or remove managed settings. "
                    "If it still will not click, or the case looks raised or swollen, stop using it and contact IT for hardware service."
                ),
                "chromebook_touchpad_not_clicking",
            )

        return ContextualSupportDecision(
            True,
            (
                "Since this is a Mac, connect an approved USB/Bluetooth mouse if available and save your work. "
                "Restart the Mac and test the trackpad again. If it still will not click, or the trackpad looks raised or swollen, "
                "stop using the Mac and contact IT for hardware service."
            ),
            "mac_trackpad_not_clicking",
        )

    docs_offline_problem = _has(combined, "google docs", "google doc", "docs") and _has(
        combined,
        "working offline",
        "says offline",
        "shows offline",
        "offline even though",
        "offline but",
    )
    if docs_offline_problem:
        return ContextualSupportDecision(
            True,
            (
                "Google Docs should not stay in **Working offline** while the connection is available. "
                "First confirm another website loads, then verify Docs is open in the correct school account. Wait for any unsaved changes, reload the document once, and reopen it from Google Drive. "
                "If it remains offline, try an approved private/incognito window or another supported browser. Do not disable offline access until you have confirmed that pending work is saved. "
                "Contact IT if the problem affects multiple Docs or the school account remains offline."
            ),
            "docs_unexpected_offline",
        )

    docs_collaboration_problem = _has(combined, "google docs", "google doc", "docs") and _has(
        combined,
        "cannot see my changes",
        "can't see my changes",
        "cant see my changes",
        "changes are not showing",
        "changes aren't showing",
        "not getting updated in realtime",
        "not getting updated in real time",
        "not updating in realtime",
        "not updating in real time",
        "not getting updated realtime",
        "not getting updated real time",
        "changes are not syncing",
        "changes aren't syncing",
    )
    if docs_collaboration_problem:
        return ContextualSupportDecision(
            True,
            (
                "This is a **Google Docs synchronization or collaboration issue**, not a version-history task. "
                "Check the status near the document title and confirm it says the changes are saved to Drive. Verify that you are online, using the correct school account, and editing the same shared file—not a copy. "
                "Ask one collaborator to reload the document, then reload it yourself in an approved browser. If the status stays offline or saving never completes, stop making duplicate copies and contact IT with the document link and affected accounts."
            ),
            "docs_realtime_collaboration",
        )

    meet_microphone_issue = _has(combined, "google meet", "meet") and _has(
        combined,
        "microphone",
        "mic",
    )
    hardware_test_passed = _has(
        combined,
        "works in voice memos",
        "works in voice memo",
        "works in another app",
        "microphone works elsewhere",
        "mic works elsewhere",
    )
    if meet_microphone_issue and hardware_test_passed:
        return ContextualSupportDecision(
            True,
            (
                "Because the microphone works in Voice Memos, the microphone hardware is working. Focus on Google Meet and the browser: select the correct microphone in **Meet → Settings → Audio**, confirm the browser is allowed to use the microphone, and reload or rejoin the meeting. "
                "Close other tabs or meeting apps that may be using the microphone. If Meet still cannot hear you, try Meet in an approved private/incognito window and contact IT with the browser and device type."
            ),
            "meet_microphone_app_specific",
        )

    return ContextualSupportDecision(False)
