from __future__ import annotations

"""Regression checks for Altitude v7 routing/retrieval hardening.

Run with:
    PYTHONPATH=app python scripts/test_architecture_hardening_v7.py
"""

from core.conversation_context import build_contextual_query, is_contextual_follow_up
from core.inventory_router import has_hardware_term, is_possible_item_request
from core.printer_router import get_expected_printer_step, route_printer_question
from core.request_guard import route_request_guard
from core.support_router import route_security_or_account_question
from core.wifi_router import contains_wifi_topic


def check(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"FAIL: {name}: {detail}")
    print(f"PASS: {name}")


def guard_intent(question: str, expected: str, history=None) -> None:
    decision = route_request_guard(question, history or [])
    check(
        f"guard {expected}",
        decision.handled and decision.intent == expected,
        f"intent={decision.intent!r} answer={decision.answer[:100]!r}",
    )


def main() -> None:
    check(
        "blocked does not match inventory block",
        not has_hardware_term("The website is blocked by the school firewall"),
    )
    check(
        "wireless mouse is not Wi-Fi",
        not contains_wifi_topic("My wireless mouse stopped working"),
    )
    check(
        "half-class Wi-Fi is Wi-Fi",
        contains_wifi_topic("Half my class got kicked off the school Wi-Fi"),
    )
    check(
        "MacBook mirroring is not inventory",
        not is_possible_item_request(
            "My MacBook screen is mirroring to the projector, but I want to see my notes",
            [],
        ),
    )
    check(
        "short cable request remains inventory",
        is_possible_item_request("I need a USB-C cable", []),
    )

    printer_history = [
        {"role": "user", "content": "I need to print my syllabus"},
        {
            "role": "assistant",
            "content": "Which printer are you trying to use? Learning Commons / Library printer or another school printer?",
        },
    ]
    printer = route_printer_question("No, for the Library", printer_history)
    check("library printer short follow-up", printer.handled, printer.answer)

    zoom_history = [
        {"role": "user", "content": "There is no sound on my Zoom call"},
        {"role": "assistant", "content": "Are you using a Mac or a Chromebook?"},
    ]
    check(
        "generic device clarification is not a printer workflow",
        get_expected_printer_step(zoom_history) is None,
        str(get_expected_printer_step(zoom_history)),
    )
    check(
        "MacBook Air reply preserves Zoom context",
        is_contextual_follow_up("I'm using a MacBook Air", zoom_history),
        build_contextual_query("I'm using a MacBook Air", zoom_history),
    )

    guard_intent(
        "My MacBook screen is mirroring to the projector, but I want to see my notes on my laptop and the slides on the board.",
        "mac_extended_presentation",
    )
    guard_intent(
        "I created a Google Classroom but the substitute teacher can't post assignments. How do I fix this?",
        "classroom_coteacher",
    )
    guard_intent(
        "I found a great math game but it's blocked by the school firewall. Can you give me the bypass code just for today?",
        "security_bypass",
    )
    guard_intent(
        "A student spilled juice on their Chromebook and the keyboard is sticky.",
        "liquid_damage",
    )
    guard_intent(
        "Creative Cloud is logging me out every time I open Photoshop for yearbook.",
        "adobe_signin_loop",
    )
    guard_intent("There is no sound on my Zoom call", "zoom_audio")
    guard_intent(
        "The state testing website isn't loading right in Safari, the buttons are missing.",
        "safari_site_compatibility",
    )
    guard_intent(
        "I can't find the quiz I made yesterday. I think Google deleted it.",
        "drive_find_form",
    )
    guard_intent(
        "I'm trying to share my screen on Zoom but the students just see a grey box. I'm on a Mac.",
        "zoom_screen_share_permission",
    )
    guard_intent(
        "A student is going on a field trip and needs to work on their Google Doc on the bus without Wi-Fi.",
        "drive_offline",
    )
    guard_intent("The touch screen on the board isn't working", "smartboard_touch")
    guard_intent(
        "My screen has a huge red pop-up saying the FBI locked my computer and to call a number!",
        "browser_scam",
    )
    guard_intent(
        "A kid thought it would be funny to flip their Chromebook screen upside down and I don't know how to fix it.",
        "chromebook_screen_rotation",
    )
    guard_intent("I need Audacity installed for my music class by tomorrow.", "software_install_approval")
    guard_intent("My laptop sounds like a jet engine during my Zoom classes.", "mac_fan_load")
    guard_intent("I can't connect to the StaffShare drive on my Mac anymore.", "mac_network_share")
    guard_intent("The spinning beach ball of death has been on my screen for 10 minutes.", "mac_force_quit")
    guard_intent(
        "I got an email saying my Google Drive is 95% full. I thought schools had unlimited storage.",
        "drive_storage_cleanup",
    )
    guard_intent(
        "How do I take a picture of just one part of my screen to put in a slideshow?",
        "mac_partial_screenshot",
    )
    guard_intent("I can't create a new Jamboard anymore. What's going on?", "jamboard_retired")
    guard_intent(
        "I snapped off my headphone plug inside the Mac audio jack. Can I use tweezers?",
        "audio_jack_damage",
    )
    guard_intent("Premiere Pro says 'Scratch Disk is Full' and won't open my video project.", "premiere_scratch_disk")
    guard_intent("My students can't log into Adobe Express (Spark), it says 'Access Denied'.", "adobe_express_access")
    guard_intent("My wireless mouse stopped working. The red light on the bottom is still on.", "wireless_mouse")

    security = route_security_or_account_question(
        "I need to install this font, but it's asking for an administrator name and password."
    )
    check("admin name+password install prompt", security.handled, security.answer)

    projector_history = [
        {"role": "user", "content": "My projector won't turn on"},
        {"role": "assistant", "content": "Check the projector power and status light."},
    ]
    projector = route_request_guard("The light is flashing red", projector_history)
    check(
        "projector red-light follow-up",
        projector.handled and projector.intent == "projector_hardware_fault",
        projector.intent,
    )

    password_history = [
        {"role": "user", "content": "I need to change my password"},
        {"role": "assistant", "content": "Use the approved password-change process."},
    ]
    password = route_request_guard("I know my current one", password_history)
    check(
        "password change follow-up",
        password.handled and password.intent == "password_change",
        password.intent,
    )

    print("\nAll v7 architecture-hardening checks passed.")


if __name__ == "__main__":
    main()
