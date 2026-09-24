from __future__ import annotations

"""Regression checks for Altitude v8 context/routing hardening.

Run with:
    PYTHONPATH=app python scripts/test_context_routing_v8.py
"""

from core.conversation_context import build_contextual_query, is_contextual_follow_up
from core.request_guard import route_request_guard
from core.wifi_router import route_wifi_question


def check(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"FAIL: {name}: {detail}")
    print(f"PASS: {name}")


def guard_intent(question: str, expected: str, history=None) -> None:
    decision = route_request_guard(question, history or [])
    check(
        f"guard {expected}",
        decision.handled and decision.intent == expected,
        f"intent={decision.intent!r} answer={decision.answer[:120]!r}",
    )


def contextual_guard(question: str, history, expected: str) -> None:
    check(
        f"follow-up recognized for {expected}",
        is_contextual_follow_up(question, history),
        question,
    )
    contextual = build_contextual_query(question, history)
    decision = route_request_guard(contextual, history)
    check(
        f"contextual guard {expected}",
        decision.handled and decision.intent == expected,
        f"query={contextual!r} intent={decision.intent!r}",
    )



def run_assistant_bridge_checks() -> None:
    """Exercise prepare_answer without requiring Ollama/Chroma in this test."""

    import sys
    import types
    from dataclasses import dataclass

    fake_llm = types.ModuleType("core.llm")
    fake_llm.stream_model_response = lambda **kwargs: iter(())
    fake_llm.stream_web_model_response = lambda **kwargs: iter(())
    sys.modules["core.llm"] = fake_llm

    @dataclass(frozen=True)
    class FakeRagResult:
        context: str = ""
        sources: tuple[str, ...] = ()
        best_distance: float | None = None
        matched_chunks: int = 0

    fake_rag = types.ModuleType("core.rag")
    fake_rag.retrieve_public_knowledge = lambda **kwargs: FakeRagResult()
    sys.modules["core.rag"] = fake_rag

    @dataclass(frozen=True)
    class FakeWebSource:
        title: str
        url: str
        snippet: str = ""

    @dataclass(frozen=True)
    class FakeWebResult:
        context: str = ""
        sources: tuple[FakeWebSource, ...] = ()

    fake_web = types.ModuleType("core.web_support")
    fake_web.MICROSOFT_SUPPORT_ENABLED = False
    fake_web.WebSource = FakeWebSource
    fake_web.is_microsoft_question = lambda q: any(x in q.lower() for x in ("windows", "microsoft", "outlook", "teams"))
    fake_web.search_trusted_web = lambda q: FakeWebResult()
    fake_web.should_prefer_web_support = lambda q: False
    sys.modules["core.web_support"] = fake_web

    from core.assistant import prepare_answer

    cases = [
        (
            "I'm using a MacBook Air",
            [
                {"role": "user", "content": "There is no sound on my Zoom call"},
                {"role": "assistant", "content": "Check Zoom Audio settings."},
            ],
            "zoom_audio",
        ),
        (
            "Only on this website",
            [
                {"role": "user", "content": "Safari keeps crashing when I open the attendance system"},
                {"role": "assistant", "content": "Does it happen on every website?"},
            ],
            "safari_single_site_crash",
        ),
        (
            "Yes, the image is showing",
            [
                {"role": "user", "content": "The touch screen on the board isn't working"},
                {"role": "assistant", "content": "Check the USB touch/control cable."},
            ],
            "smartboard_touch",
        ),
        (
            "Students are saying they need permission to view it",
            [
                {"role": "user", "content": "I made a quiz in Google Forms"},
                {"role": "assistant", "content": "You can configure quiz settings in Google Forms."},
            ],
            "forms_responder_access",
        ),
        (
            "I'm on my iPhone",
            [
                {"role": "user", "content": "I can't connect to the internet"},
                {"role": "assistant", "content": "Are you on Student Wi-Fi or Guest Wi-Fi?"},
            ],
            "byod_wifi_profile",
        ),
    ]

    for question, history, expected in cases:
        plan = prepare_answer(question, history)
        check(
            f"assistant context bridge {expected}",
            plan.direct_answer is not None and plan.intent == expected,
            f"intent={plan.intent!r} answer={plan.direct_answer!r}",
        )


def main() -> None:
    guard_intent(
        "My Mac is connected to the Wi-Fi but Chrome keeps saying 'Your connection is not private'.",
        "certificate_privacy_warning",
    )
    wifi = route_wifi_question(
        "My Mac is connected to the Wi-Fi but Chrome keeps saying 'Your connection is not private'.",
        [],
    )
    check("certificate warning is not hijacked by Wi-Fi", not wifi.handled, wifi.answer)

    guard_intent(
        "The school Wi-Fi is down. Can I use my iPhone hotspot for my Mac?",
        "hotspot_policy_and_setup",
    )
    guard_intent(
        "My sub needs to take attendance. Can I just write my password on a sticky note for them?",
        "password_sharing_boundary",
    )
    guard_intent(
        "My Mac keeps nagging me to update to Sonoma, should I do it?",
        "major_os_upgrade_policy",
    )
    guard_intent(
        "Everything I print to the color printer comes out in black and white.",
        "printer_colour_output",
    )
    guard_intent(
        "I accidentally sent a 100-page document to the staff room printer! How do I stop it?",
        "printer_cancel_job",
    )
    guard_intent(
        "I sent a confidential IEP document to the staff printer but it didn't print.",
        "printer_secure_release",
    )
    guard_intent(
        "All my files on my desktop are gone!",
        "desktop_files_missing",
    )
    guard_intent("My camera is blurry", "camera_blurry")
    guard_intent(
        "The HR website won't let me view my paystub. It just flashes and does nothing.",
        "browser_popup_site",
    )
    guard_intent(
        "I want to see all 30 students at once on Google Meet but it only shows 16.",
        "meet_tiled_layout",
    )
    guard_intent(
        "I want my student teacher to be able to let kids in from the waiting room.",
        "meeting_cohost_access",
    )
    guard_intent(
        "Students are complaining they are stuck in a waiting room, but I didn't turn that on.",
        "meeting_waiting_room",
    )
    guard_intent(
        "I am retiring. How do I give my Google Classrooms to the new teacher?",
        "classroom_transfer_owner",
    )
    guard_intent(
        "A visually impaired student needs their Chromebook screen read to them.",
        "chromebook_chromevox",
    )
    guard_intent(
        "My webcam works in Photo Booth but Zoom says it can't detect a camera.",
        "zoom_camera_permission",
    )
    guard_intent(
        "I forgot my charger at home. Can I borrow a Mac charger from the library for 3rd period?",
        "inventory_charger_clarification",
    )
    guard_intent(
        "I plugged my Mac into the dock but my two external monitors are just mirroring each other.",
        "mac_dock_multi_display",
    )

    zoom_history = [
        {"role": "user", "content": "There is no sound on my Zoom call"},
        {"role": "assistant", "content": "Check Zoom Audio settings."},
    ]
    contextual_guard("I'm using a MacBook Air", zoom_history, "zoom_audio")

    safari_history = [
        {"role": "user", "content": "Safari keeps crashing when I open the attendance system"},
        {"role": "assistant", "content": "Does it happen on every website?"},
    ]
    contextual_guard("Only on this website", safari_history, "safari_single_site_crash")

    smartboard_history = [
        {"role": "user", "content": "The touch screen on the board isn't working"},
        {"role": "assistant", "content": "Check the USB touch/control cable."},
    ]
    contextual_guard("Yes, the image is showing", smartboard_history, "smartboard_touch")

    cable_history = [
        {"role": "user", "content": "Do you have USB-C cables?"},
        {"role": "assistant", "content": "Current live availability for USB-C Cable: 6"},
    ]
    contextual_guard("To connect my MacBook to the smartboard", cable_history, "smartboard_video_connection")

    forms_history = [
        {"role": "user", "content": "I made a quiz in Google Forms"},
        {"role": "assistant", "content": "You can configure quiz settings in Google Forms."},
    ]
    contextual_guard("Students are saying they need permission to view it", forms_history, "forms_responder_access")

    byod_history = [
        {"role": "user", "content": "I can't connect to the internet"},
        {"role": "assistant", "content": "Are you on Student Wi-Fi or Guest Wi-Fi?"},
    ]
    contextual_guard("I'm on my iPhone", byod_history, "byod_wifi_profile")

    run_assistant_bridge_checks()

    print("\nAll v8 context/routing checks passed.")


if __name__ == "__main__":
    main()
