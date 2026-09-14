#!/usr/bin/env python3
"""Run 96 additional school IT support questions through Altitude.

This catalog is separate from ``test_real_world_questions.py`` because it uses a
new set of questions provided for broader validation. It sends each prompt
through the real Altitude chatbot response pipeline and writes TXT, JSON, and
HTML reports with the exact answer, route, sources, latency, and feedback-button
eligibility.

Safety guarantees:
* No helpdesk ticket is submitted.
* Inventory requests are read-only.
* Environment secrets are never printed.
* Knowledge Queue admin workflow is not tested.

Examples:
    python scripts/test_school_it_questions.py
    python scripts/test_school_it_questions.py --category "Wi-Fi & Internet"
    python scripts/test_school_it_questions.py --case SQ-WIFI-01
    python scripts/test_school_it_questions.py --limit 10
    python scripts/test_school_it_questions.py --list
    python scripts/test_school_it_questions.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import test_bot_responses as base  # noqa: E402


CATEGORY_TERMS: dict[str, tuple[str, ...]] = {
    "Wi-Fi & Internet": (
        "wi-fi", "wifi", "wireless", "network", "internet", "connection",
        "outage", "browser", "website", "signal",
    ),
    "Printers & Print Queues": (
        "print", "printer", "copier", "queue", "toner", "paper", "offline",
    ),
    "Passwords, Accounts, Gmail, Drive, Classroom": (
        "password", "account", "google", "gmail", "drive", "classroom",
        "email", "calendar", "2fa", "verify", "shared",
    ),
    "MacBooks, Chromebooks, Displays, AirPlay": (
        "macbook", "mac", "chromebook", "display", "screen", "airplay",
        "projector", "battery", "trackpad", "charger", "hdmi",
    ),
    "Approved Software & Device Troubleshooting": (
        "software", "app", "application", "approved", "chrome", "zoom",
        "extension", "update", "security", "admin", "patch",
    ),
    "Loaner Devices & Inventory": (
        "loaner", "borrow", "inventory", "available", "charger", "ipad",
        "laptop", "chromebook", "return", "damaged", "lost",
    ),
    "Escalating to Helpdesk / Ticketing": (
        "ticket", "helpdesk", "support", "it", "status", "priority",
        "screenshot", "response", "reopen", "assigned",
    ),
}

CATEGORY_FORBIDDEN: dict[str, tuple[str, ...]] = {
    "Wi-Fi & Internet": (
        "print queue", "paper jam", "google classroom class code",
        "external drive", "powerpoint",
    ),
    "Printers & Print Queues": (
        "google classroom class code", "airplay code", "external drive",
        "password reset", "lost or stolen device",
    ),
    "Passwords, Accounts, Gmail, Drive, Classroom": (
        "paper jam", "printer queue", "airplay", "projector", "external drive",
    ),
    "MacBooks, Chromebooks, Displays, AirPlay": (
        "gmail spam", "print queue", "class code", "drive folder",
    ),
    "Approved Software & Device Troubleshooting": (
        "paper jam", "loaner inventory count", "classroom display input",
    ),
    "Loaner Devices & Inventory": (
        "paper jam", "class code", "gmail filter", "powerpoint slide",
    ),
    "Escalating to Helpdesk / Ticketing": (
        "paper jam", "class code", "airplay code", "drive trash",
    ),
}


def g(*phrases: str) -> tuple[str, ...]:
    return tuple(phrases)


def sq(
    case_id: str,
    category: str,
    question: str,
    purpose: str,
    *concept_groups: Sequence[str],
    forbidden: Sequence[str] = (),
    feedback: base.FeedbackExpectation = "auto",
    kind: base.ResponseKind = "answer",
    required: bool = True,
) -> base.TestCase:
    required_groups: list[tuple[str, ...]] = [CATEGORY_TERMS[category]]
    required_groups.extend(tuple(group) for group in concept_groups)
    return base.TestCase(
        case_id=case_id,
        category=category,
        question=question,
        purpose=purpose,
        required_groups=tuple(required_groups),
        forbidden_phrases=tuple(CATEGORY_FORBIDDEN.get(category, ())) + tuple(forbidden),
        feedback=feedback,
        kind=kind,
        required=required,
    )


CASES: tuple[base.TestCase, ...] = (
    # Wi-Fi & Internet (1-15)
    sq("SQ-WIFI-01", "Wi-Fi & Internet", "Why does the Wi-Fi keep dropping in the library?", "Troubleshoot location-specific Wi-Fi drops", g("dropping", "disconnect", "library", "signal", "reconnect", "helpdesk"), feedback="show"),
    sq("SQ-WIFI-02", "Wi-Fi & Internet", "My laptop won't connect to the school network, what do I do?", "Troubleshoot device Wi-Fi connection", g("laptop", "connect", "school network", "forget", "reconnect", "restart"), feedback="show"),
    sq("SQ-WIFI-03", "Wi-Fi & Internet", "Is the internet down for everyone or just my room?", "Clarify local versus wider outage", g("everyone", "room", "others", "outage", "multiple", "helpdesk"), feedback="show"),
    sq("SQ-WIFI-04", "Wi-Fi & Internet", "Why is the Wi-Fi so slow during testing week?", "Handle slow Wi-Fi during testing period", g("slow", "testing", "multiple users", "signal", "helpdesk", "outage"), feedback="show"),
    sq("SQ-WIFI-05", "Wi-Fi & Internet", "How do I connect a personal device to the guest network?", "Give guest-network guidance", g("guest", "personal device", "qr code", "connect"), feedback="show"),
    sq("SQ-WIFI-06", "Wi-Fi & Internet", "Can I get the Wi-Fi password for my classroom?", "Avoid exposing Wi-Fi password and give approved access method", g("password", "not provided", "plain text", "qr code", "classroom"), forbidden=("the password is",), feedback="show"),
    sq("SQ-WIFI-07", "Wi-Fi & Internet", 'Why does my Chromebook say "no internet, open network"?', "Troubleshoot Chromebook no-internet state", g("chromebook", "no internet", "open network", "reconnect", "restart"), feedback="show"),
    sq("SQ-WIFI-08", "Wi-Fi & Internet", "Is there an outage affecting the whole building?", "Handle whole-building outage check", g("outage", "building", "multiple", "everyone", "helpdesk"), feedback="show"),
    sq("SQ-WIFI-09", "Wi-Fi & Internet", "How do I reset my network settings on a school laptop?", "Explain safe network reset guidance", g("reset", "network settings", "school laptop", "forget", "reconnect", "helpdesk"), forbidden=("terminal", "registry"), feedback="show"),
    sq("SQ-WIFI-10", "Wi-Fi & Internet", "Why can't I access certain websites from the classroom Wi-Fi?", "Explain website access/filter troubleshooting", g("website", "blocked", "classroom", "filter", "approved", "ticket"), forbidden=("vpn", "proxy", "bypass"), feedback="show"),
    sq("SQ-WIFI-11", "Wi-Fi & Internet", "My video call keeps freezing, is it the network?", "Troubleshoot video call freezing and network impact", g("video call", "freezing", "network", "wi-fi", "others", "restart"), feedback="show"),
    sq("SQ-WIFI-12", "Wi-Fi & Internet", "Do we have Wi-Fi issues in the gym or only in classrooms?", "Compare location-specific Wi-Fi reports", g("gym", "classrooms", "location", "others", "signal", "helpdesk"), feedback="show"),
    sq("SQ-WIFI-13", "Wi-Fi & Internet", "Why does the internet cut out every day around the same time?", "Handle recurring time-based internet issue", g("same time", "recurring", "cut out", "record", "location", "helpdesk"), feedback="show"),
    sq("SQ-WIFI-14", "Wi-Fi & Internet", "Can students connect their phones to school Wi-Fi?", "Explain student phone Wi-Fi policy", g("students", "phones", "school wi-fi", "policy", "approved"), feedback="show"),
    sq("SQ-WIFI-15", "Wi-Fi & Internet", "How do I check if it's my device or the network causing the problem?", "Guide device-vs-network isolation", g("device", "network", "other users", "another device", "location", "helpdesk"), feedback="show"),

    # Printers & Print Queues (16-28)
    sq("SQ-PRN-16", "Printers & Print Queues", "Why won't the printer in the front office respond?", "Troubleshoot front-office printer not responding", g("front office", "respond", "offline", "power", "queue", "helpdesk"), feedback="show"),
    sq("SQ-PRN-17", "Printers & Print Queues", "My print job has been stuck in the queue for 20 minutes, what's wrong?", "Troubleshoot stuck queue", g("queue", "20 minutes", "stuck", "cancel", "resume", "restart"), feedback="show"),
    sq("SQ-PRN-18", "Printers & Print Queues", "How do I clear a stuck print job myself?", "Clear stuck print job safely", g("clear", "stuck", "print job", "queue", "cancel", "delete"), feedback="show"),
    sq("SQ-PRN-19", "Printers & Print Queues", 'Why is the printer showing "offline" even though it\'s on?', "Troubleshoot offline printer", g("offline", "on", "selected", "queue", "wi-fi", "restart"), feedback="show"),
    sq("SQ-PRN-20", "Printers & Print Queues", "Can I print from my personal laptop to the school printer?", "Explain personal-laptop printing policy", g("personal laptop", "school printer", "policy", "approved", "helpdesk"), feedback="show"),
    sq("SQ-PRN-21", "Printers & Print Queues", "Why does the printer keep jamming on double-sided prints?", "Handle duplex paper jams", g("jamming", "double-sided", "duplex", "paper", "tray", "helpdesk"), feedback="show"),
    sq("SQ-PRN-22", "Printers & Print Queues", "How do I find out which printer my document went to?", "Find selected printer destination", g("which printer", "document", "selected", "print dialog", "queue"), feedback="show"),
    sq("SQ-PRN-23", "Printers & Print Queues", "Is there a way to see how many jobs are ahead of mine in the queue?", "Explain queue position visibility", g("jobs", "ahead", "queue", "printer", "status"), feedback="show"),
    sq("SQ-PRN-24", "Printers & Print Queues", "Why did my print job come out blank?", "Troubleshoot blank print output", g("blank", "toner", "file", "preview", "print settings", "helpdesk"), feedback="show"),
    sq("SQ-PRN-25", "Printers & Print Queues", "Who do I contact if the copier in the teacher's lounge is out of toner?", "Route copier toner issue", g("copier", "teacher", "lounge", "toner", "helpdesk", "contact"), feedback="show"),
    sq("SQ-PRN-26", "Printers & Print Queues", "Can I cancel a print job I sent by mistake?", "Cancel mistaken print job", g("cancel", "mistake", "print job", "queue", "delete", "printer"), feedback="show"),
    sq("SQ-PRN-27", "Printers & Print Queues", "Why does the printer disconnect from the network overnight?", "Handle recurring printer network disconnect", g("disconnect", "network", "overnight", "printer", "power", "helpdesk"), feedback="show"),
    sq("SQ-PRN-28", "Printers & Print Queues", "How do I add a new printer to my laptop?", "Add school printer", g("add", "new printer", "laptop", "settings", "printer"), feedback="show"),

    # Passwords, Accounts, Gmail, Drive, Classroom (29-45)
    sq("SQ-ACC-29", "Passwords, Accounts, Gmail, Drive, Classroom", "I forgot my school password, how do I reset it?", "Reset forgotten password", g("forgot", "password", "reset", "helpdesk", "identity"), forbidden=("type your password",), feedback="show"),
    sq("SQ-ACC-30", "Passwords, Accounts, Gmail, Drive, Classroom", "Why does it say my account is locked?", "Handle locked account", g("account", "locked", "sign in", "wait", "helpdesk", "verify"), feedback="show"),
    sq("SQ-ACC-31", "Passwords, Accounts, Gmail, Drive, Classroom", "How do I recover a Google Doc I accidentally deleted?", "Recover deleted Google Doc", g("google doc", "deleted", "trash", "restore", "drive"), feedback="show"),
    sq("SQ-ACC-32", "Passwords, Accounts, Gmail, Drive, Classroom", "Can I change my student email password myself?", "Explain student password-change policy", g("student", "email", "password", "change", "helpdesk", "policy"), feedback="show"),
    sq("SQ-ACC-33", "Passwords, Accounts, Gmail, Drive, Classroom", "Why isn't my Google Classroom showing my new class?", "Troubleshoot missing Classroom class", g("google classroom", "new class", "account", "invitation", "teacher", "refresh"), feedback="show"),
    sq("SQ-ACC-34", "Passwords, Accounts, Gmail, Drive, Classroom", "How do I share a Drive folder with another teacher?", "Share Drive folder", g("drive folder", "share", "teacher", "permission", "school account"), feedback="show"),
    sq("SQ-ACC-35", "Passwords, Accounts, Gmail, Drive, Classroom", "Why can't I log into Gmail on my phone?", "Troubleshoot Gmail phone sign-in", g("gmail", "phone", "sign in", "account", "password", "verification"), feedback="show"),
    sq("SQ-ACC-36", "Passwords, Accounts, Gmail, Drive, Classroom", "My Classroom assignment isn't loading, is that a known issue?", "Troubleshoot Classroom loading", g("classroom", "assignment", "loading", "browser", "known issue", "teacher"), feedback="show"),
    sq("SQ-ACC-37", "Passwords, Accounts, Gmail, Drive, Classroom", "How do I merge two Google accounts I accidentally created?", "Explain account merge limitation", g("merge", "two google accounts", "cannot", "school account", "helpdesk"), feedback="show"),
    sq("SQ-ACC-38", "Passwords, Accounts, Gmail, Drive, Classroom", "Why does it keep asking me to verify my identity when I log in?", "Handle identity-verification prompts", g("verify", "identity", "login", "2fa", "do not share", "helpdesk"), feedback="show"),
    sq("SQ-ACC-39", "Passwords, Accounts, Gmail, Drive, Classroom", "Can I get access to a shared Drive folder from last year?", "Request access to older shared folder", g("shared drive", "folder", "last year", "access", "owner", "permission"), feedback="show"),
    sq("SQ-ACC-40", "Passwords, Accounts, Gmail, Drive, Classroom", "How long does a password reset usually take?", "Explain password-reset timing", g("password reset", "time", "usually", "helpdesk", "identity"), feedback="show"),
    sq("SQ-ACC-41", "Passwords, Accounts, Gmail, Drive, Classroom", "Why did my Classroom invite go to the wrong student?", "Handle wrong Classroom invite", g("classroom", "invite", "wrong student", "teacher", "email", "privacy"), feedback="show"),
    sq("SQ-ACC-42", "Passwords, Accounts, Gmail, Drive, Classroom", "Is there a way to recover files after my Drive storage got full?", "Recover files after storage issue", g("drive", "storage", "full", "recover", "trash", "helpdesk"), feedback="show"),
    sq("SQ-ACC-43", "Passwords, Accounts, Gmail, Drive, Classroom", 'Why does my account say "access denied" for the shared calendar?', "Troubleshoot shared Calendar access", g("access denied", "shared calendar", "account", "permission", "owner"), feedback="show"),
    sq("SQ-ACC-44", "Passwords, Accounts, Gmail, Drive, Classroom", "How do I set up two-factor authentication for my school account?", "Set up 2FA safely", g("two-factor", "2fa", "school account", "verification", "do not share"), feedback="show"),
    sq("SQ-ACC-45", "Passwords, Accounts, Gmail, Drive, Classroom", "Can a parent get access to their child's Classroom account?", "Explain parent Classroom access/privacy", g("parent", "child", "classroom", "access", "privacy", "teacher"), feedback="show"),

    # MacBooks, Chromebooks, Displays, AirPlay (46-61)
    sq("SQ-DEV-46", "MacBooks, Chromebooks, Displays, AirPlay", "Why won't my MacBook turn on after the update?", "MacBook will not turn on after update", g("macbook", "turn on", "update", "power", "charger", "helpdesk"), feedback="show"),
    sq("SQ-DEV-47", "MacBooks, Chromebooks, Displays, AirPlay", "My Chromebook screen is frozen, what should I do?", "Restart frozen Chromebook", g("chromebook", "screen", "frozen", "power", "refresh", "restart"), feedback="show"),
    sq("SQ-DEV-48", "MacBooks, Chromebooks, Displays, AirPlay", "How do I connect my laptop to the classroom display?", "Connect laptop to display", g("laptop", "classroom display", "input", "cable", "airplay", "hdmi"), feedback="show"),
    sq("SQ-DEV-49", "MacBooks, Chromebooks, Displays, AirPlay", "Why does AirPlay keep disconnecting mid-lesson?", "Troubleshoot AirPlay disconnects", g("airplay", "disconnect", "mid-lesson", "network", "restart", "display"), feedback="show"),
    sq("SQ-DEV-50", "MacBooks, Chromebooks, Displays, AirPlay", "Can I mirror my iPad to the projector wirelessly?", "Explain iPad wireless mirroring", g("ipad", "mirror", "projector", "wireless", "airplay", "code"), feedback="show"),
    sq("SQ-DEV-51", "MacBooks, Chromebooks, Displays, AirPlay", 'Why is the classroom display showing "no signal"?', "Troubleshoot display no signal", g("classroom display", "no signal", "input", "source", "cable", "power"), feedback="show"),
    sq("SQ-DEV-52", "MacBooks, Chromebooks, Displays, AirPlay", "How do I fix a Chromebook stuck on the login screen?", "Fix Chromebook login screen issue", g("chromebook", "login screen", "restart", "account", "helpdesk"), feedback="show"),
    sq("SQ-DEV-53", "MacBooks, Chromebooks, Displays, AirPlay", "My MacBook trackpad stopped responding, is that a hardware issue?", "Handle MacBook trackpad issue", g("macbook", "trackpad", "responding", "hardware", "battery", "helpdesk"), feedback="show"),
    sq("SQ-DEV-54", "MacBooks, Chromebooks, Displays, AirPlay", "Why won't AirPlay show up as an option on my device?", "Restore missing AirPlay option", g("airplay", "option", "device", "screen mirroring", "network", "restart"), feedback="show"),
    sq("SQ-DEV-55", "MacBooks, Chromebooks, Displays, AirPlay", "How do I reset a Chromebook to factory settings?", "Block unauthorized factory reset and escalate", g("chromebook", "factory", "reset", "managed", "helpdesk", "not"), forbidden=("powerwash it yourself",), feedback="show"),
    sq("SQ-DEV-56", "MacBooks, Chromebooks, Displays, AirPlay", "Can I use HDMI instead of AirPlay if the wireless isn't working?", "Offer HDMI fallback", g("hdmi", "airplay", "wireless", "cable", "input", "adapter"), feedback="show"),
    sq("SQ-DEV-57", "MacBooks, Chromebooks, Displays, AirPlay", "Why does my MacBook battery drain so fast during the school day?", "Troubleshoot MacBook battery drain", g("macbook", "battery", "drain", "brightness", "applications", "battery health"), feedback="show"),
    sq("SQ-DEV-58", "MacBooks, Chromebooks, Displays, AirPlay", "How do I fix a flickering classroom display?", "Troubleshoot flickering display", g("flickering", "classroom display", "cable", "input", "restart", "helpdesk"), feedback="show"),
    sq("SQ-DEV-59", "MacBooks, Chromebooks, Displays, AirPlay", "Why is my Chromebook keyboard typing the wrong characters?", "Troubleshoot Chromebook keyboard layout", g("chromebook", "keyboard", "wrong characters", "layout", "restart", "settings"), feedback="show"),
    sq("SQ-DEV-60", "MacBooks, Chromebooks, Displays, AirPlay", "Can I get a replacement charger for my school-issued MacBook?", "Route replacement charger request", g("replacement charger", "school-issued", "macbook", "borrow", "helpdesk", "inventory"), feedback="show"),
    sq("SQ-DEV-61", "MacBooks, Chromebooks, Displays, AirPlay", "Why does the display lag a few seconds behind my screen?", "Troubleshoot display lag", g("display", "lag", "screen", "airplay", "network", "resolution"), feedback="show"),

    # Approved Software & Device Troubleshooting (62-74)
    sq("SQ-SW-62", "Approved Software & Device Troubleshooting", "Is Zoom approved for use on school devices?", "Explain Zoom approval", g("zoom", "approved", "school devices", "software", "helpdesk"), feedback="show"),
    sq("SQ-SW-63", "Approved Software & Device Troubleshooting", "Can I install a coding app that's not on the approved list?", "Explain unapproved app process", g("coding app", "approved list", "install", "request", "approval"), forbidden=("bypass", "admin password"), feedback="show"),
    sq("SQ-SW-64", "Approved Software & Device Troubleshooting", "Why does the school block certain extensions in Chrome?", "Explain blocked Chrome extensions", g("chrome", "extensions", "blocked", "security", "approved"), feedback="show"),
    sq("SQ-SW-65", "Approved Software & Device Troubleshooting", "How do I request approval for new classroom software?", "Request new classroom software", g("request", "approval", "classroom software", "ticket", "purpose"), feedback="show"),
    sq("SQ-SW-66", "Approved Software & Device Troubleshooting", "My laptop is running really slow, what's causing that?", "Troubleshoot slow laptop", g("laptop", "slow", "restart", "storage", "applications", "updates"), feedback="show"),
    sq("SQ-SW-67", "Approved Software & Device Troubleshooting", "Why does an app keep crashing on my Chromebook?", "Troubleshoot Chromebook app crash", g("app", "crashing", "chromebook", "restart", "update", "storage"), feedback="show"),
    sq("SQ-SW-68", "Approved Software & Device Troubleshooting", "Is there a list of software already approved for teachers?", "Explain approved software list", g("list", "approved", "software", "teachers", "helpdesk"), feedback="show"),
    sq("SQ-SW-69", "Approved Software & Device Troubleshooting", "Can I use my own antivirus software on a school laptop?", "Explain managed antivirus policy", g("antivirus", "school laptop", "managed", "security", "not install"), feedback="show"),
    sq("SQ-SW-70", "Approved Software & Device Troubleshooting", "Why does the school block me from installing updates myself?", "Explain managed update restrictions", g("updates", "installing", "managed", "administrator", "security"), feedback="show"),
    sq("SQ-SW-71", "Approved Software & Device Troubleshooting", "How do I check if my device has the latest security patch?", "Check security patch status", g("security patch", "device", "update", "settings", "managed"), feedback="show"),
    sq("SQ-SW-72", "Approved Software & Device Troubleshooting", "Why does my laptop keep restarting on its own?", "Troubleshoot repeated restarts", g("laptop", "restarting", "updates", "crash", "error", "helpdesk"), feedback="show"),
    sq("SQ-SW-73", "Approved Software & Device Troubleshooting", "Is there an approved video editing tool for student projects?", "Explain approved video editing tools", g("approved", "video editing", "student projects", "software", "teacher", "helpdesk"), feedback="show"),
    sq("SQ-SW-74", "Approved Software & Device Troubleshooting", "Can I get admin access temporarily to install a plugin?", "Refuse temporary admin access and offer approval path", g("admin access", "plugin", "cannot", "approval", "helpdesk"), forbidden=("password is", "make you admin"), feedback="hide", kind="refusal"),

    # Loaner Devices & Inventory (75-84)
    sq("SQ-INV-75", "Loaner Devices & Inventory", "Is there a loaner Chromebook available for today?", "Check Chromebook availability", g("loaner chromebook", "available", "today", "inventory", "count"), feedback="show"),
    sq("SQ-INV-76", "Loaner Devices & Inventory", "How long can a student keep a loaner laptop?", "Explain loan duration", g("how long", "student", "loaner laptop", "return", "policy"), feedback="show"),
    sq("SQ-INV-77", "Loaner Devices & Inventory", "What do I do if a loaner device gets damaged?", "Handle damaged loaner", g("loaner", "damaged", "report", "helpdesk", "do not keep using"), feedback="show"),
    sq("SQ-INV-78", "Loaner Devices & Inventory", "Can I check how many loaner devices are currently available?", "Check live inventory counts", g("how many", "loaner devices", "currently available", "inventory"), feedback="show"),
    sq("SQ-INV-79", "Loaner Devices & Inventory", "Do I need to sign anything to borrow a laptop?", "Explain sign-out requirement", g("sign", "borrow", "laptop", "agreement", "helpdesk"), feedback="show"),
    sq("SQ-INV-80", "Loaner Devices & Inventory", "What happens if a loaner isn't returned by the deadline?", "Explain overdue loaner handling", g("deadline", "returned", "overdue", "loaner", "helpdesk"), feedback="show"),
    sq("SQ-INV-81", "Loaner Devices & Inventory", "Is there a charger included with the loaner device?", "Explain loaner accessories", g("charger", "included", "loaner", "device", "confirm"), feedback="show"),
    sq("SQ-INV-82", "Loaner Devices & Inventory", "Can teachers request a loaner projector for an event?", "Explain teacher loaner projector request", g("teachers", "loaner projector", "event", "request", "helpdesk"), feedback="show"),
    sq("SQ-INV-83", "Loaner Devices & Inventory", "How do I report a loaner device as lost?", "Report lost loaner", g("lost", "loaner device", "report", "helpdesk", "asset"), feedback="show"),
    sq("SQ-INV-84", "Loaner Devices & Inventory", "Are there loaner iPads available for testing week?", "Check iPad availability", g("loaner ipad", "available", "testing week", "inventory", "count"), feedback="show"),

    # Escalating to Helpdesk / Ticketing (85-96)
    sq("SQ-TKT-85", "Escalating to Helpdesk / Ticketing", "How do I submit a ticket for a problem that's not urgent?", "Explain non-urgent ticket submission", g("submit", "ticket", "not urgent", "low priority", "helpdesk"), feedback="show"),
    sq("SQ-TKT-86", "Escalating to Helpdesk / Ticketing", "Why hasn't anyone responded to my helpdesk ticket yet?", "Follow up on delayed ticket", g("responded", "helpdesk ticket", "status", "follow up", "response time"), feedback="show"),
    sq("SQ-TKT-87", "Escalating to Helpdesk / Ticketing", "Can I check the status of a ticket I submitted last week?", "Check ticket status", g("status", "ticket", "last week", "submitted", "updates"), feedback="show"),
    sq("SQ-TKT-88", "Escalating to Helpdesk / Ticketing", "Who do I escalate to if the issue keeps happening?", "Escalate recurring issue", g("escalate", "keeps happening", "ticket", "helpdesk", "details"), feedback="show"),
    sq("SQ-TKT-89", "Escalating to Helpdesk / Ticketing", "How do I attach a screenshot to my support ticket?", "Attach screenshot to ticket", g("attach", "screenshot", "support ticket", "privacy", "file"), feedback="show"),
    sq("SQ-TKT-90", "Escalating to Helpdesk / Ticketing", "What's the typical response time for IT tickets?", "Explain ticket response time", g("response time", "it tickets", "priority", "urgent", "helpdesk"), feedback="show"),
    sq("SQ-TKT-91", "Escalating to Helpdesk / Ticketing", "Can I reopen a ticket that was marked as resolved?", "Reopen resolved ticket", g("reopen", "resolved", "ticket", "reply", "not fixed"), feedback="show"),
    sq("SQ-TKT-92", "Escalating to Helpdesk / Ticketing", "How do I flag a ticket as high priority?", "Flag high-priority ticket", g("high priority", "ticket", "impact", "urgent", "classroom"), feedback="show"),
    sq("SQ-TKT-93", "Escalating to Helpdesk / Ticketing", "Is there a way to call IT directly for an urgent issue?", "Explain urgent IT contact", g("call", "directly", "urgent", "it", "helpdesk", "emergency"), feedback="show"),
    sq("SQ-TKT-94", "Escalating to Helpdesk / Ticketing", "Why did my ticket get closed without a fix?", "Handle closed-without-fix ticket", g("closed", "without a fix", "ticket", "reply", "reopen"), feedback="show"),
    sq("SQ-TKT-95", "Escalating to Helpdesk / Ticketing", "Can I submit a ticket on behalf of a whole classroom?", "Submit classroom-wide ticket", g("ticket", "whole classroom", "behalf", "multiple users", "room"), feedback="show"),
    sq("SQ-TKT-96", "Escalating to Helpdesk / Ticketing", "How do I know if my ticket was assigned to someone?", "Check ticket assignment", g("assigned", "ticket", "someone", "status", "updates"), feedback="show"),
)


def selected_cases(args: argparse.Namespace) -> list[base.TestCase]:
    cases = list(CASES)
    if args.category:
        wanted = args.category.casefold().strip()
        cases = [case for case in cases if case.category.casefold() == wanted]
    if args.case:
        wanted_case = args.case.casefold().strip()
        cases = [case for case in cases if case.case_id.casefold() == wanted_case]
    if args.limit is not None:
        cases = cases[: args.limit]
    return cases


def run_self_test() -> int:
    problems: list[str] = []
    if len(CASES) != 96:
        problems.append(f"Expected 96 cases, found {len(CASES)}.")
    seen: set[str] = set()
    for case in CASES:
        if case.case_id in seen:
            problems.append(f"Duplicate case id: {case.case_id}")
        seen.add(case.case_id)
        if not case.question.strip():
            problems.append(f"{case.case_id} has an empty question.")
        if not case.required_groups:
            problems.append(f"{case.case_id} has no required concept groups.")
        if case.category not in CATEGORY_TERMS:
            problems.append(f"{case.case_id} uses unknown category {case.category!r}.")
    if problems:
        print("Self-test failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("Self-test passed.")
    print("Total questions: 96")
    print("Categories:")
    for category in CATEGORY_TERMS:
        print(f"- {category}: {sum(case.category == category for case in CASES)}")
    return 0


def list_cases(cases: Sequence[base.TestCase]) -> None:
    for case in cases:
        print(f"{case.case_id}\t{case.category}\t{case.question}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 96 additional Altitude school IT questions.")
    parser.add_argument("--category", help="Run one exact category name only.")
    parser.add_argument("--case", help="Run one exact case id, such as SQ-WIFI-01.")
    parser.add_argument("--limit", type=int, help="Run only the first N selected cases.")
    parser.add_argument("--list", action="store_true", help="List selected cases without running the bot.")
    parser.add_argument("--self-test", action="store_true", help="Validate this question catalog and exit.")
    parser.add_argument("--timeout", type=float, default=base.DEFAULT_TIMEOUT_SECONDS, help="Per-question timeout in seconds.")
    parser.add_argument("--strict-latency", action="store_true", help="Fail instead of warn when latency is above target.")
    parser.add_argument("--stop-on-failure", action="store_true", help="Stop after the first required failure.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return run_self_test()

    cases = selected_cases(args)
    if not cases:
        print("No test cases matched your filters.", file=sys.stderr)
        return 2
    if args.list:
        list_cases(cases)
        return 0

    runner = base.ResponseTestRunner(
        timeout_seconds=args.timeout,
        strict_latency=args.strict_latency,
        stop_on_failure=args.stop_on_failure,
    )
    for case in cases:
        runner.run_case(case)

    text_path, json_path, html_path = runner.write_reports(
        base_name_prefix="altitude-school-it-96-question-test",
        report_title="Altitude School IT 96-Question Test Report",
        scope=(
            "96 additional realistic school IT questions covering Wi-Fi, printing, "
            "accounts, devices, software, inventory, ticketing, feedback, and latency"
        ),
    )

    summary = runner.summary()
    print("\nReport files:")
    print(f"- {text_path}")
    print(f"- {json_path}")
    print(f"- {html_path}")
    print("\nSummary:")
    print("  ".join(f"{key}: {value}" for key, value in summary.items()))
    return 1 if runner.has_required_failures() else 0


if __name__ == "__main__":
    raise SystemExit(main())
