from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.compound_router import route_compound_question
from core.conversation_router import looks_like_it_question
from core.general_fallback_router import route_general_fallback
from core.printer_router import route_printer_question
from core.retrieval_profile import (
    build_document_profile,
    build_retrieval_profile,
    profiles_are_compatible,
)


FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"PASS: {name}")
        return
    FAILURES.append(name)
    print(f"FAIL: {name} {detail}".rstrip())


def fallback_case(question: str, expected_intent: str) -> None:
    result = route_general_fallback(question, [])
    check(
        f"fallback {expected_intent}",
        result.handled and result.intent == expected_intent,
        f"got handled={result.handled} intent={result.intent!r}",
    )


def incompatible_case(question: str, metadata: dict[str, str], name: str) -> None:
    query_profile = build_retrieval_profile(question)
    document = SimpleNamespace(page_content="", metadata=metadata)
    document_profile = build_document_profile(document)
    check(
        name,
        not profiles_are_compatible(query_profile, document_profile),
        f"query={query_profile} document={document_profile}",
    )


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    rag_source = (project_root / "app" / "core" / "rag.py").read_text()
    assistant_source = (project_root / "app" / "core" / "assistant.py").read_text()

    check(
        "distance-less KB answers disabled",
        "ALLOW_DISTANCELESS_KB_ANSWERS = False" in rag_source,
    )
    check(
        "lexical candidates require explicit opt-in",
        "if ALLOW_DISTANCELESS_KB_ANSWERS:" in rag_source,
    )
    check(
        "semantic validation gate installed",
        "def semantic_match_is_acceptable" in rag_source,
    )
    check(
        "compound router runs before request guard",
        assistant_source.index("route_compound_question(question, history)")
        < assistant_source.index("route_request_guard(question, history)"),
    )

    mouse_profile = build_retrieval_profile(
        "My wireless mouse works on every other Mac except mine."
    )
    check("wireless mouse is not Wi-Fi", "wifi" not in mouse_profile.domains)

    meet_profile = build_retrieval_profile(
        "My breakout rooms in Meet are not letting students back into the main room."
    )
    check("Meet shorthand resolves to Google Meet", "google_meet" in meet_profile.products)

    chromebook_profile = build_retrieval_profile(
        "Our school Chromebooks will not connect to museum Wi-Fi."
    )
    check("Chromebooks plural detected", "chromebook" in chromebook_profile.platforms)

    incompatible_case(
        "My wireless mouse works on every other Mac except mine.",
        {
            "source": "mac_basic_troubleshooting.md",
            "platform": "macos",
            "section_title": "Mac Wi-Fi Connection Problems",
            "intent_keywords": "wifi, wireless network, cannot connect",
        },
        "mouse cannot use Wi-Fi article",
    )
    incompatible_case(
        "A Chrome extension I use for grading disappeared from my toolbar.",
        {
            "source": "google_workspace_education_support.md",
            "section_title": "Chrome Keyboard Navigation and Accessibility",
            "intent_keywords": "chrome, keyboard navigation, accessibility",
        },
        "Chrome extension cannot use accessibility article",
    )
    incompatible_case(
        "My breakout rooms in Meet are not letting students back into the main room.",
        {
            "source": "zoom_workplace_school_support.md",
            "section_title": "Zoom Breakout Rooms",
            "intent_keywords": "breakout rooms, main room",
        },
        "Google Meet cannot use Zoom article",
    )
    incompatible_case(
        "Events on my school Calendar are not showing on my phone calendar app.",
        {
            "source": "google_workspace_education_support.md",
            "section_title": "Delegated Calendar Events",
            "intent_keywords": "calendar, delegated calendar, create event",
        },
        "Calendar sync cannot use generic delegated-calendar article",
    )
    incompatible_case(
        "I set a Gmail filter to auto-archive parent emails.",
        {
            "source": "day_to_day_troubleshooting.md",
            "section_title": "External Vendor Email Missing",
            "intent_keywords": "email, spam, junk, vendor",
        },
        "Gmail filter cannot use generic spam article",
    )
    incompatible_case(
        "Our school Chromebooks will not connect to the museum guest Wi-Fi.",
        {
            "source": "mac_basic_troubleshooting.md",
            "platform": "macos",
            "section_title": "Mac Wi-Fi Connection Problems",
            "intent_keywords": "wifi, guest network, cannot connect",
        },
        "Chromebook cannot use Mac Wi-Fi article",
    )

    fallback_case(
        "I have a MacBook Air and the room only has an old VGA projector, what adapter do I need?",
        "display_vga_adapter",
    )
    fallback_case(
        "None of the Chromebooks in the charging cart seem to be charging even though it is plugged in.",
        "charging_cart_power",
    )
    fallback_case(
        "I scheduled an assignment for 8am but it never posted to the class.",
        "classroom_scheduled_post",
    )
    fallback_case(
        "I shared a folder with anyone with the link by accident, can you undo that for me?",
        "drive_revoke_public_link",
    )
    fallback_case(
        "Files I edit on my Mac in the Drive folder are not showing changes on my Chromebook.",
        "drive_desktop_sync",
    )
    fallback_case(
        "My Zoom account got downgraded to Basic and cuts off at 40 minutes.",
        "zoom_license_tier",
    )
    fallback_case(
        "My USB microphone is not appearing in my Mac sound settings.",
        "usb_microphone_detection",
    )
    fallback_case(
        "My Downloads folder has 15000 files in it.",
        "downloads_cleanup",
    )
    fallback_case(
        "Can I plug in a personal USB flash drive to back up files from my school Mac?",
        "external_storage_policy",
    )
    fallback_case(
        "I am logged into my school account on my home computer from over the summer.",
        "account_session_review",
    )
    fallback_case(
        "My gradebook export to CSV is missing three students who submitted work.",
        "assessment_export_missing",
    )
    fallback_case(
        "The timer on our online quiz platform is showing a different time than the classroom clock.",
        "assessment_time_mismatch",
    )
    fallback_case(
        "Chrome shows ERR_SSL_PROTOCOL_ERROR when I open our grading site.",
        "chrome_ssl_error",
    )
    fallback_case(
        "We're on a field trip and our school Chromebooks will not connect to the museum Wi-Fi.",
        "wifi_offsite_managed_device",
    )

    compound = route_compound_question(
        "My Mac won't connect to Wi-Fi, and even when I use my phone hotspot, Zoom still won't load.",
        [],
    )
    check(
        "compound Wi-Fi plus Zoom",
        compound.handled
        and compound.intent == "compound_it_issues"
        and "two separate IT issues" in compound.answer,
    )
    compound = route_compound_question(
        "The projector has no signal AND my MacBook keyboard backlight won't turn on, weird timing.",
        [],
    )
    check(
        "compound projector plus keyboard",
        compound.handled
        and "display" in compound.answer.lower()
        and "keyboard" in compound.answer.lower(),
    )

    for question in (
        "I scheduled an assignment for 8am but it never posted.",
        "My Drive version history is missing.",
        "None of the Chromebooks in the charging cart are charging.",
        "My Bluetooth keyboard keeps disconnecting.",
        "The assessment platform timer is wrong.",
    ):
        check(f"supported IT classifier: {question}", looks_like_it_question(question))

    printer = route_printer_question(
        "The print preview in Chrome shows blank pages even though the document has content.",
        [],
    )
    check(
        "blank Chrome print preview is diagnosed before printer selection",
        printer.handled and "browser-specific" in printer.answer,
    )

    if FAILURES:
        raise SystemExit(
            f"\n{len(FAILURES)} v10 checks failed: {', '.join(FAILURES)}"
        )

    print("\nAll v10 retrieval/generalization checks passed.")


if __name__ == "__main__":
    main()
