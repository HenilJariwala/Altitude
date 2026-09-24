from __future__ import annotations

from pathlib import Path

from core.general_fallback_router import route_general_fallback
from core.inventory_router import is_inventory_request
from core.printer_router import route_printer_question
from core.request_guard import route_request_guard
from core.web_support import is_microsoft_question
from core.wifi_router import route_wifi_question


FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"PASS: {name}")
        return
    FAILURES.append(name)
    print(f"FAIL: {name} {detail}".rstrip())


def guard_case(question: str, expected_intent: str) -> None:
    result = route_request_guard(question, [])
    check(
        f"guard {expected_intent}",
        result.handled and result.intent == expected_intent,
        f"got handled={result.handled} intent={result.intent!r}",
    )


def fallback_case(question: str, expected_intent: str) -> None:
    result = route_general_fallback(question, [])
    check(
        f"fallback {expected_intent}",
        result.handled and result.intent == expected_intent,
        f"got handled={result.handled} intent={result.intent!r}",
    )


def main() -> None:
    rag_source = (Path(__file__).resolve().parents[1] / "app" / "core" / "rag.py").read_text()
    check("RAG hard ceiling is code-enforced", "RAG_HARD_DISTANCE_CEILING = 0.66" in rag_source and "min(_configured_max_distance, RAG_HARD_DISTANCE_CEILING)" in rag_source)
    check(
        "two browser windows is not Microsoft Windows",
        not is_microsoft_question("I have 45 Chrome tabs open across two windows and Chrome froze"),
    )

    guard_case("The back of a student Chromebook looks slightly puffed up near the trackpad.", "battery_swelling")
    guard_case("Three MacBook keys stopped working after I spilled tea on it.", "liquid_damage")
    guard_case("Can you just fix it?", "clarification")
    guard_case("It worked five minutes ago and now it doesn't.", "clarification")
    guard_case("The internet is down again.", "clarification")
    guard_case("Can I use a personal VPN to access a blocked research site?", "security_bypass")
    guard_case("Can you remote into my computer and fix it?", "capability_remote_access")
    guard_case("Can you email my principal for me?", "capability_send_email")
    guard_case("Can you enable Developer Mode in Chrome for me?", "managed_permission")
    guard_case("My phone with the authenticator app broke and I can't get the 2-step verification code.", "mfa_recovery")
    guard_case("My loaner Chromebook says it needs to be re-enrolled.", "loaner_reenrollment")
    guard_case("I lost the charger that came with my loaner MacBook.", "loaner_missing_accessory")
    guard_case("Do I need to wipe my loaner Mac before returning it?", "loaner_return")
    guard_case("Can I use my personal phone as a hotspot for the school laptop while we're on a trip?", "hotspot_policy_and_setup")

    check(
        "hotspot question is not inventory",
        not is_inventory_request("Can I use my personal phone as a hotspot for the school laptop while we're on a trip?", []),
    )
    check(
        "charging cart problem is not inventory reservation",
        not is_inventory_request("None of the Chromebooks in the charging cart seem to be charging even though it's plugged in.", []),
    )
    check(
        "loaner re-enrollment is not inventory",
        not is_inventory_request("The Chromebook I borrowed is saying it needs to be re-enrolled.", []),
    )
    check(
        "Apple Pencil borrow remains inventory",
        is_inventory_request("Is there a spare Apple Pencil I can borrow?", []),
    )

    wifi = route_wifi_question("Every classroom on the second floor lost Wi-Fi at the exact same time.", [])
    check("widespread Wi-Fi outage", wifi.handled and "multiple people" in wifi.answer.lower())
    wifi = route_wifi_question("We're on a field trip and none of our Chromebooks will connect to the museum guest Wi-Fi.", [])
    check("off-site Wi-Fi does not return SJK QR flow", not wifi.handled)
    wifi = route_wifi_question("My phone connects to school Wi-Fi but my laptop won't even see the network.", [])
    check("device-specific Wi-Fi", wifi.handled and "focus on the laptop" in wifi.answer.lower())

    printer = route_printer_question("I sent the same worksheet to print five times because nothing happened.", [])
    check("printer duplicate queue", printer.handled and "print queue" in printer.answer.lower())
    printer = route_printer_question("Everything I print has a faint grey line down the page.", [])
    check("printer quality", printer.handled and "physical" in printer.answer.lower())
    printer = route_printer_question("Can I print directly from my phone to the classroom printer?", [])
    check("printer mobile", printer.handled and "mobile" in printer.answer.lower())
    printer = route_printer_question("Can I print in color from the Library printer?", [])
    check("printer color", printer.handled and "colour" in printer.answer.lower())

    fallback_case("The projector shows No Signal but the light is on.", "display_no_signal")
    fallback_case("Colors on the projected image look washed out and pink.", "display_colour_fault")
    fallback_case("My slides look zoomed in on the classroom screen.", "display_resolution")
    fallback_case("Chrome takes forever to open every morning.", "chrome_startup_performance")
    fallback_case("My Chrome extension disappeared from the toolbar.", "chrome_extension_missing")
    fallback_case("Safari says the network connection was lost but Chrome works fine.", "safari_specific_network_error")
    fallback_case("I scheduled a Google Classroom assignment for 8am but it never posted.", "classroom_scheduled_post")
    fallback_case("Classroom says Missing even though the student attached the file.", "classroom_submission_status")
    fallback_case("I shared a Google Drive folder with anyone with the link by accident.", "drive_revoke_public_link")
    fallback_case("I need to see what a Google Doc looked like one week ago before a student's edit.", "drive_version_history")
    fallback_case("Does Google Meet automatically take attendance for me?", "meet_attendance")
    fallback_case("I set a Gmail filter to auto-archive parent emails and now I'm missing messages.", "gmail_filter_archive")
    fallback_case("A parent is stuck in the Zoom waiting room and I can't find Admit.", "zoom_waiting_room_admit")
    fallback_case("My Zoom account got downgraded to Basic and cuts off at 40 minutes.", "zoom_license_tier")
    fallback_case("I can't type into a fillable PDF in Adobe Acrobat.", "pdf_fillable_form")
    fallback_case("I have 40 GB of System Data on my Mac.", "mac_system_data")
    fallback_case("My Chromebook local storage is full.", "chromebook_storage")
    fallback_case("A Chromebook has been stuck on Updating for 20 minutes.", "chromebook_update_stuck")

    if FAILURES:
        raise SystemExit(f"\n{len(FAILURES)} v9 checks failed: {', '.join(FAILURES)}")

    print("\nAll v9 generalization hardening checks passed.")


if __name__ == "__main__":
    main()
