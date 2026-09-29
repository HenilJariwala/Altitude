#!/usr/bin/env python3
from __future__ import annotations

import sys
import types
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

# The production environment installs rapidfuzz. The isolated release-build
# workspace may not, and these checks only need exact phrase matching.
try:
    import rapidfuzz  # noqa: F401
except ModuleNotFoundError:
    fallback_fuzz = types.SimpleNamespace(
        partial_ratio=lambda _left, _right: 0.0,
        token_set_ratio=lambda _left, _right: 0.0,
    )
    fallback_module = types.ModuleType("rapidfuzz")
    fallback_module.fuzz = fallback_fuzz
    sys.modules["rapidfuzz"] = fallback_module

from core.contextual_support_router import route_contextual_support  # noqa: E402


def history(*messages: tuple[str, str]) -> list[dict[str, str]]:
    return [{"role": role, "content": content} for role, content in messages]


def require(name: str, condition: bool, answer: str) -> None:
    if not condition:
        raise AssertionError(f"FAIL: {name}\nAnswer: {answer}")
    print(f"PASS: {name}")


def direct(question: str, chat_history: list[dict[str, str]]) -> tuple[str, str]:
    decision = route_contextual_support(question, chat_history)
    return decision.answer, decision.intent


def main() -> None:
    answer, intent = direct(
        "My keyboard keeps typing the same letter.",
        history(("user", "My keyboard keeps typing the same letter.")),
    )
    require(
        "repeating key is not treated as a layout problem",
        intent == "keyboard_repeating_key" and "stuck or repeating key" in answer.lower(),
        answer,
    )

    keyboard_history = history(
        ("user", "My keyboard keeps typing the same letter."),
        ("assistant", "Check the keyboard layout and input language."),
        ("user", "No, it types the same."),
    )
    answer, intent = direct("No, it types the same.", keyboard_history)
    require(
        "keyboard correction changes the answer",
        intent == "keyboard_repeating_key" and "language problem" in answer.lower(),
        answer,
    )

    answer, intent = direct(
        "My trackpad is not clicking.",
        history(("user", "My trackpad is not clicking.")),
    )
    require(
        "unknown trackpad platform asks for clarification",
        intent == "trackpad_platform_clarification" and "windows" in answer.lower(),
        answer,
    )

    trackpad_history = history(
        ("user", "My trackpad is not clicking."),
        ("assistant", "Which device are you using?"),
        ("user", "I am on Windows."),
    )
    answer, intent = direct("I am on Windows.", trackpad_history)
    require(
        "Windows correction produces Windows touchpad steps",
        intent == "windows_touchpad_not_clicking"
        and "bluetooth & devices" in answer.lower()
        and "mac" not in answer.lower(),
        answer,
    )

    answer, intent = direct("I on Windows.", trackpad_history[:-1] + history(("user", "I on Windows.")))
    require(
        "short Windows reply retains the trackpad issue",
        intent == "windows_touchpad_not_clicking" and "touchpad" in answer.lower(),
        answer,
    )

    answer, intent = direct(
        "Google Docs says Working offline even though Wi-Fi is connected.",
        history(("user", "Google Docs says Working offline even though Wi-Fi is connected.")),
    )
    require(
        "unexpected Docs offline state is diagnosed",
        intent == "docs_unexpected_offline" and "should not stay" in answer.lower(),
        answer,
    )

    answer, intent = direct(
        "Other people cannot see my changes in a shared Google Doc.",
        history(("user", "Other people cannot see my changes in a shared Google Doc.")),
    )
    require(
        "Docs collaboration issue is not routed to version restoration",
        intent == "docs_realtime_collaboration"
        and "synchronization" in answer.lower()
        and "restore" not in answer.lower(),
        answer,
    )

    answer, intent = direct(
        "My Google Docs is not getting updated realtime.",
        history(("user", "My Google Docs is not getting updated realtime.")),
    )
    require(
        "natural realtime wording routes to collaboration troubleshooting",
        intent == "docs_realtime_collaboration",
        answer,
    )

    wifi_history = history(
        ("user", "I want to know the SJK Wi-Fi password."),
        ("assistant", "Which approved network do you need: Student Wi-Fi or Guest Wi-Fi?"),
        ("user", "SJK"),
    )
    answer, intent = direct("SJK", wifi_history)
    require(
        "ambiguous school Wi-Fi follow-up asks for the approved network",
        intent == "wifi_network_clarification"
        and "student wi-fi" in answer.lower()
        and "guest wi-fi" in answer.lower(),
        answer,
    )

    meet_history = history(
        ("user", "My Google Meet microphone is not working."),
        ("assistant", "Check Meet audio settings and test the microphone in another app."),
        ("user", "It works in Voice Memos."),
    )
    answer, intent = direct("It works in Voice Memos.", meet_history)
    require(
        "working Voice Memos test narrows the problem to Meet",
        intent == "meet_microphone_app_specific"
        and "hardware is working" in answer.lower()
        and "meet" in answer.lower(),
        answer,
    )

    answer, intent = direct(
        "I need to fix my computer.",
        history(("user", "I need to fix my computer.")),
    )
    require(
        "vague computer request asks for device and symptom",
        intent == "computer_issue_clarification"
        and "what is happening" in answer.lower(),
        answer,
    )

    print("All 11 v15 pilot context checks passed.")


if __name__ == "__main__":
    main()
