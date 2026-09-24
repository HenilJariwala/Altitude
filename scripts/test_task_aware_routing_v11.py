from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.compound_router import route_compound_question
from core.general_fallback_router import (
    route_general_fallback,
    should_preempt_knowledge,
)
from core.inventory_router import is_inventory_request
from core.request_guard import route_request_guard
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
    decision = route_general_fallback(question, [])
    check(
        f"fallback {expected_intent}",
        decision.handled
        and decision.intent == expected_intent
        and should_preempt_knowledge(decision),
        f"got handled={decision.handled} intent={decision.intent!r}",
    )


def guard_case(question: str, expected_intent: str) -> None:
    decision = route_request_guard(question, [])
    check(
        f"guard {expected_intent}",
        decision.handled and decision.intent == expected_intent,
        f"got handled={decision.handled} intent={decision.intent!r}",
    )


def incompatible_case(
    question: str,
    metadata: dict[str, str],
    name: str,
) -> None:
    query = build_retrieval_profile(question)
    document = SimpleNamespace(page_content="", metadata=metadata)
    document_profile = build_document_profile(document)
    check(
        name,
        not profiles_are_compatible(query, document_profile),
        f"query={query} document={document_profile}",
    )


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    assistant_source = (project_root / "app" / "core" / "assistant.py").read_text()

    check(
        "task fallback runs before common support and RAG",
        assistant_source.index("priority_fallback = route_general_fallback")
        < assistant_source.index("common_support = route_common_support_question")
        < assistant_source.index("rag_result = retrieve_public_knowledge"),
    )
    check(
        "generic scope refusals are deferred",
        "generic_scope_answer = conversation.answer in" in assistant_source,
    )
    check(
        "vendor errors run before broad support",
        assistant_source.index("should_prefer_web_support(vendor_error_question)")
        < assistant_source.index("common_support = route_common_support_question"),
    )

    fallback_cases = (
        ("Safari uses way more battery than Chrome on my MacBook, is that expected?", "safari_energy_use"),
        ("Can Google Meet record my class automatically every day without me clicking anything?", "meet_recording_automation"),
        ("Can my assistant have access to send emails as me from my school Gmail?", "gmail_delegation"),
        ("It says I have 0 Adobe licenses left for my department.", "adobe_license_admin"),
        ("My dock charges my MacBook but not when I also have my phone plugged into it.", "dock_power_budget"),
        ("My USB microphone isn't appearing anywhere in my Mac's sound settings.", "usb_microphone_detection"),
        ("Can I plug in a personal USB flash drive to back up files from my school Mac?", "external_storage_policy"),
        ("My computer clock is 10 minutes off from my Calendar reminders.", "system_clock_sync"),
        ("I closed my browser without saving. Is my essay draft in Google Docs gone forever?", "docs_autosave_recovery"),
        ("My cursor turned into a rainbow pinwheel and won't go back to normal.", "mac_spinning_beachball"),
        ("I typed my password wrong twice. Am I about to get locked out permanently?", "account_failed_attempts"),
        ("Is it bad that I have 200 unread emails in my school Gmail?", "gmail_unread_count"),
        ("The Epson projector keeps shutting off after about 10 minutes.", "projector_repeated_shutdown"),
        ("The Promethean board cursor is way off and needs calibration.", "interactive_board_calibration"),
        ("My MacBook fan sounds like it is grinding.", "mac_fan_mechanical_fault"),
        ("I just started. How do I set up my school email on my personal phone?", "school_email_personal_phone"),
        ("Why does the school use Chromebooks? They were better at my old district.", "device_choice_feedback"),
        ("Can you text me when the Wi-Fi is fixed?", "capability_follow_up_notification"),
        ("Can you put in a ticket for me automatically?", "capability_ticket_creation"),
        ("I graded 30 essays and now the grades disappeared from the gradebook overnight.", "classroom_gradebook_missing"),
        ("A teacher who left the school owns files my department still needs.", "drive_departed_owner"),
        ("I need to see what a document looked like one week ago before a student's edit.", "drive_version_history"),
        ("Streaming a YouTube video keeps buffering. Is our network too slow?", "wifi_bandwidth"),
        ("My monitor says input not supported.", "display_resolution"),
        ("My headset works for listening but nobody can hear me on Meet.", "headset_microphone_input"),
        ("I need a new math app installed on all 30 classroom Chromebooks.", "managed_bulk_deployment"),
        ("My Gmail isn't loading, Calendar isn't loading, but Drive and Classroom work fine.", "google_partial_service_issue"),
        ("Students should submit in Classroom but emailed the file instead.", "classroom_submission_method"),
        ("I've submitted five tickets about my slow Mac and nothing has changed.", "ticket_repeat_escalation"),
        ("Google Classroom shows Error 400 when I try grading an assignment.", "classroom_error_400"),
        ("Testing week is starting and my Mac wants to install a huge system update.", "testing_update_deferral"),
        ("Did the school's Google account get hacked or is my personal Gmail broken?", "account_scope_clarification"),
        ("My PDF exported from Google Docs looks different in Adobe.", "pdf_docs_rendering"),
        ("Safari tabs from my phone are missing under Tabs from iPhone.", "safari_icloud_tabs"),
        ("Half my class can join Meet but the other half don't have permission.", "meet_split_account_permission"),
    )
    for question, expected_intent in fallback_cases:
        fallback_case(question, expected_intent)

    guard_cases = (
        ("My Gmail filter auto-archives parent emails and now messages are missing.", "gmail_filter_archive"),
        ("My Google Drive is at 100% storage and I can't save.", "drive_storage_cleanup"),
        ("My mic isn't working for the virtual student.", "urgent_microphone"),
        ("Can I get a standing desk converter?", "facilities_furniture_request"),
        ("Google Classroom shows Error 400 when I grade.", "classroom_error_400"),
        ("Drive for desktop shows Error 1223 syncing files.", "drive_desktop_error_1223"),
        ("Zoom gives me Error Code 104101 when I join.", "zoom_error_104101"),
        ("How do I install Grammarly on student Chromebooks?", "managed_extension_deployment"),
        ("One row of Chromebooks can't connect to Wi-Fi.", "wifi_localized_subset"),
        ("My Mac asks for a password to change the desktop wallpaper.", "wallpaper_permission_prompt"),
        ("My department wants a new Shared Drive. How do we get one set up?", "shared_drive_creation_request"),
        ("Where do I find the login for the shared printer?", "printer_login_clarification"),
        ("Is this a me problem or an IT problem? My screen just went black.", "black_screen_triage"),
        ("This is the third time my projector died mid-class.", "projector_repeat_failure"),
    )
    for question, expected_intent in guard_cases:
        guard_case(question, expected_intent)

    guard = route_request_guard(
        "Can you reset my password and unlock the classroom door?",
        [],
    )
    check(
        "password plus physical access boundary",
        guard.handled and guard.intent == "mixed_password_physical_access",
    )

    notification_guard = route_request_guard(
        "Can you text me when the Wi-Fi in my room is fixed?",
        [],
    )
    check(
        "notification capability wins before Wi-Fi routing",
        notification_guard.handled
        and notification_guard.intent == "capability_follow_up_notification",
    )

    check(
        "document scanners are recognized as inventory",
        is_inventory_request(
            "Do you have any document scanners we can check out for the front office?",
            [],
        ),
    )
    check(
        "document cameras are recognized as inventory",
        is_inventory_request(
            "Do you have document cameras available to borrow?",
            [],
        ),
    )

    compound = route_compound_question(
        "My projector's broken, my Mac's slow, and also can you approve my field trip form?",
        [],
    )
    check(
        "mixed IT and administrative compound request",
        compound.handled and compound.intent == "compound_it_and_admin",
    )

    incompatible_case(
        "Can my assistant send emails as me from Gmail?",
        {
            "source": "google_workspace_education_support.md",
            "section_title": "Report a Lost or Stolen Device",
            "intent_keywords": "lost device, stolen laptop, secure account",
        },
        "Gmail delegation cannot use lost-device article",
    )
    incompatible_case(
        "I have 0 Adobe licenses left for my department.",
        {
            "source": "zoom_workplace_school_support.md",
            "section_title": "Zoom Plan and Licence Features",
            "intent_keywords": "zoom licence, basic account, meeting limit",
        },
        "Adobe licensing cannot use Zoom licensing article",
    )
    incompatible_case(
        "My USB microphone is not appearing in Mac sound settings.",
        {
            "source": "zoom_workplace_school_support.md",
            "section_title": "Select and Test Zoom Speaker and Microphone",
            "intent_keywords": "select mic zoom, audio settings zoom",
        },
        "OS-level USB microphone cannot use Zoom article",
    )
    incompatible_case(
        "A teacher who left the school owns files we need.",
        {
            "source": "google_workspace_education_support.md",
            "section_title": "Organize Files with Folders and Shortcuts",
            "intent_keywords": "move file, add shortcut, organize drive",
        },
        "departed ownership cannot use organization article",
    )

    if FAILURES:
        raise SystemExit(f"{len(FAILURES)} v11 task-aware routing check(s) failed")

    print(f"All {3 + len(fallback_cases) + len(guard_cases) + 5 + 4} v11 task-aware routing checks passed.")


if __name__ == "__main__":
    main()
