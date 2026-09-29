from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from core.conversation_context import build_contextual_query
from core.conversation_router import looks_like_it_question
from core.inventory_router import InventoryItem, InventoryPayload, route_inventory_question
from core.printer_router import route_printer_question
from core.request_guard import route_request_guard
from core.retrieval_profile import (
    build_document_profile,
    build_retrieval_profile,
    profiles_are_compatible,
)
from core.support_router import is_google_password_request
from core.web_support import _candidate_domains, DEFAULT_TRUSTED_DOMAINS, _official_article_url


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print(f"[PASS] {name}")


def main() -> int:
    cases = {
        "Mac screenshot": "How do I take a screenshot on Mac?",
        "Safari websites": "Safari won't open any websites",
        "Safari cookies": "How do I clear cookies in Safari?",
        "Chrome Aw Snap": "I'm getting 'Aw, Snap!' error in Chrome",
        "Gmail send": "My Gmail isn't sending emails",
        "Classroom loading": "Google Classroom isn't loading assignments",
        "Projector video": "Projector isn't showing my laptop screen",
        "Zoom audio": "Zoom audio isn't working",
        "Zoom sign-in": "I can't sign into Zoom with my school account",
        "Zoom share": "Zoom screen sharing isn't working",
        "Python install": "I need to install Python, why is it asking for a password?",
        "Webcam managed": "Can you just enable the webcam for me, it's grayed out",
        "Chrome extension admin": "I need admin rights to install a Chrome extension for my class",
        "Whitelist": "Can you whitelist this website for my room only?",
        "Chromebook local admin": "Can you give my student's Chromebook local admin so they can install a font?",
        "Drive sharing": "My co-teacher needs access to my Google Drive folder, can you set that up?",
        "Policy": "Can students print more than 20 pages a day?",
        "Vague": "My computer is being weird",
        "Freeze vague": "It's doing that thing where it freezes",
        "Compound display": "My Mac won't connect to the projector AND the sound isn't working",
        "Compound services": "Students can't print and also can't log into Drive",
        "Compound Zoom": "My Mac is slow and now Zoom keeps crashing too",
        "Testing": "We're doing a standardized test right now and Chromebooks are locking up",
        "Mid-test power": "A student's Chromebook died mid-test, what do I do?",
        "Workspace session": "macOS says 'Your session has expired' when signing into Workspace",
        "Meet host": "Google Meet says 'You can't join this meeting' as the host",
        "DOCX": "How do I open a .docx file a parent sent me?",
        "Permissions escalation": "This has been broken for three weeks, can you just fix the permissions yourself since IT is slow?",
        "Teacher admin": "I'm the teacher, so I should have admin access to my own classroom computer, right?",
    }
    for name, question in cases.items():
        decision = route_request_guard(question, [])
        check(f"guard handles {name}", decision.handled and bool(decision.answer))

    for question in (
        "Safari won't open any websites",
        "Adobe Acrobat won't open PDF files",
        "Photoshop keeps crashing on my Mac",
        "Can you just enable the webcam for me, it's grayed out",
    ):
        check(f"supported IT recognized: {question}", looks_like_it_question(question))

    check(
        "Zoom school-account sign-in is not misclassified as Google password reset",
        not is_google_password_request("I can't sign into Zoom with my school account"),
    )
    check(
        "Google password problem is still recognized",
        is_google_password_request("I forgot my school Google password"),
    )

    inventory = InventoryPayload(
        types=[
            InventoryItem(typeId=1, typeName="USB-C Block", totalCount=8, availableCount=4, loanedCount=4),
            InventoryItem(typeId=2, typeName="USB-C Cable", totalCount=10, availableCount=6, loanedCount=4),
            InventoryItem(typeId=3, typeName="HP Chromebook", totalCount=12, availableCount=5, loanedCount=7),
            InventoryItem(typeId=4, typeName="Macbook", totalCount=4, availableCount=2, loanedCount=2),
        ]
    )
    inventory_history = [
        {"role": "user", "content": "Do you have USB-C cables available?"},
        {"role": "assistant", "content": "Current live availability for USB-C Cable: 6 available."},
    ]
    with patch("core.inventory_router.fetch_inventory", return_value=inventory):
        block = route_inventory_question("and a USB-C charging block", inventory_history)
        loaner = route_inventory_question("I need a loaner Mac for the week, mine is being repaired", [])
    check("USB-C charging block follow-up stays inventory", block.handled and "USB-C Block" in block.answer)
    check("loaner Mac request stays inventory despite repair wording", loaner.handled and "Macbook" in loaner.answer)

    hold = route_inventory_question("Can you hold 5 Chromebooks for my class tomorrow?", [])
    check("future Chromebook hold is not promised", hold.handled and "cannot reserve or hold" in hold.answer.lower())
    cart = route_inventory_question("Do you have a cart of laptops available for a field trip?", [])
    check("cart request uses request process", cart.handled and "entire cart" in cart.answer.lower())

    printer_history = [
        {"role": "user", "content": "I want to print in the library"},
        {"role": "assistant", "content": "Are you using a Mac or a Chromebook?"},
        {"role": "user", "content": "Mac"},
        {"role": "assistant", "content": "Make sure your Mac is connected to SJK Wi-Fi. Add the Learning Commons printer."},
    ]
    offline = route_printer_question("it says offline", printer_history)
    check("printer offline follow-up stays printer context", offline.handled and "offline access" not in offline.answer.lower())

    chain_history = [
        {"role": "user", "content": "Printer issue"},
        {"role": "assistant", "content": "Which printer are you trying to use? Learning Commons / Library printer or another school printer?"},
        {"role": "user", "content": "It's the library one"},
        {"role": "assistant", "content": "Try printer checks."},
        {"role": "user", "content": "Mac"},
        {"role": "assistant", "content": "On your Mac, open Printers & Scanners."},
    ]
    missing = route_printer_question("won't even show up in the list", chain_history)
    check("missing library printer follow-up stays setup flow", missing.handled and "192.168.1.205" in missing.answer)

    display_history = [
        {"role": "user", "content": "My display isn't working"},
        {"role": "assistant", "content": "External monitor checks"},
        {"role": "user", "content": "It's the classroom TV, not a monitor"},
        {"role": "assistant", "content": "Classroom TV checks"},
    ]
    display = route_request_guard("still black even after restart", display_history)
    check("classroom TV correction persists", display.handled and "classroom tv" in display.answer.lower())

    contextual = build_contextual_query("it says offline", printer_history)
    check("contextual query preserves printer root and Mac", "print in the library" in contextual.lower() and "mac" in contextual.lower())

    adobe_domains = _candidate_domains("Photoshop keeps crashing on my Mac", DEFAULT_TRUSTED_DOMAINS)
    check("Photoshop searches Adobe only", adobe_domains == ("helpx.adobe.com",))
    check("Google community threads are rejected", not _official_article_url("https://support.google.com/chrome/thread/123/test"))
    check("Google help articles are allowed", _official_article_url("https://support.google.com/chrome/answer/6098869"))

    # Regression checks for retrieval mismatches exposed by the acceptance run.
    projector_query = build_retrieval_profile("Projector isn't showing my laptop screen")
    slides_notes_doc = build_document_profile(
        SimpleNamespace(
            metadata={
                "source": "google_workspace_education_support.md",
                "document_title": "Google Workspace for Education Support",
                "section_title": "Use speaker notes in Google Slides",
                "intent_keywords": "google slides speaker notes presenter view",
            }
        )
    )
    check(
        "projector failure rejects Google Slides speaker-notes article",
        not profiles_are_compatible(projector_query, slides_notes_doc),
    )

    screenshot_query = build_retrieval_profile("How do I take a screenshot on Mac?")
    printer_doc = build_document_profile(
        SimpleNamespace(
            metadata={
                "source": "printer_support.md",
                "document_title": "Printer Support",
                "section_title": "Clear a stuck print queue",
                "intent_keywords": "printer printing print queue paused job",
            }
        )
    )
    check(
        "Mac screenshot rejects printer article",
        not profiles_are_compatible(screenshot_query, printer_doc),
    )

    testing_query = build_retrieval_profile(
        "We're doing a standardized test right now and Chromebooks are locking up"
    )
    zoom_chromebook_doc = build_document_profile(
        SimpleNamespace(
            metadata={
                "source": "zoom_workplace_school_support.md",
                "document_title": "Zoom Workplace School Support",
                "section_title": "Use Zoom on a Chromebook",
                "intent_keywords": "zoom web app chromebook browser meeting",
            }
        )
    )
    check(
        "assessment Chromebook failure rejects generic Zoom Chromebook article",
        not profiles_are_compatible(testing_query, zoom_chromebook_doc),
    )

    zoom_crash_query = build_retrieval_profile("My Mac is slow and now Zoom keeps crashing too")
    zoom_mic_doc = build_document_profile(
        SimpleNamespace(
            metadata={
                "source": "zoom_workplace_school_support.md",
                "document_title": "Zoom Workplace School Support",
                "section_title": "Troubleshoot microphone input",
                "intent_keywords": "zoom microphone audio input not picking up",
            }
        )
    )
    check(
        "Zoom crash/performance issue rejects microphone article",
        not profiles_are_compatible(zoom_crash_query, zoom_mic_doc),
    )

    print("\nAll acceptance hardening checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
