#!/usr/bin/env python3
"""Run 118 realistic Altitude support questions and save detailed reports.

The catalog contains 90 structured school IT questions and 28 naturally typed,
stressed, or misspelled questions. Every question goes through the same routing,
RAG, inventory, and response pipeline used by the Streamlit chatbot.

The evaluator checks:
* topic relevance and question-specific concepts;
* obvious cross-topic retrieval mistakes;
* secret leakage and runtime failures;
* response latency;
* feedback-button behavior (show after a complete answer, hide while clarifying).

No helpdesk ticket is submitted. Inventory requests are read-only.

Examples:
    python scripts/test_real_world_questions.py
    python scripts/test_real_world_questions.py --set formal
    python scripts/test_real_world_questions.py --set natural
    python scripts/test_real_world_questions.py --category "Wi-Fi and Internet"
    python scripts/test_real_world_questions.py --case RW-WIFI-01
    python scripts/test_real_world_questions.py --limit 10
    python scripts/test_real_world_questions.py --list
    python scripts/test_real_world_questions.py --self-test
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
    "Wi-Fi and Internet": (
        "wi-fi", "wifi", "wireless", "network", "internet", "dns", "hotspot",
    ),
    "Printers and Print Queues": (
        "print", "printer", "copier", "queue", "toner", "paper",
    ),
    "Accounts and Google Workspace": (
        "password", "account", "google", "gmail", "drive", "classroom",
        "email", "form", "2fa", "authentication",
    ),
    "Devices, Displays, and AirPlay": (
        "mac", "macbook", "chromebook", "display", "screen", "airplay",
        "projector", "apple tv", "battery", "trackpad", "device",
    ),
    "Approved Software and Troubleshooting": (
        "software", "app", "application", "browser", "chrome", "zoom", "meet",
        "webcam", "camera", "microphone", "cache", "virus", "pdf", "extension",
        "text-to-speech", "lockdown", "respondus", "canva", "python",
    ),
    "Live Loaner Inventory": (
        "loaner", "loner", "inventory", "borrow", "charger", "ipad", "tablet",
        "pickup", "return", "available",
    ),
    "Helpdesk Tickets and Escalation": (
        "ticket", "helpdesk", "it desk", "tech desk", "support", "escalat",
        "priority", "status", "comment", "reopen",
    ),
}

CATEGORY_FORBIDDEN: dict[str, tuple[str, ...]] = {
    "Wi-Fi and Internet": (
        "external drive", "printer queue", "lost or stolen device",
        "create a class", "class code",
    ),
    "Printers and Print Queues": (
        "external drive", "airplay code", "google password reset",
        "lost or stolen device",
    ),
    "Accounts and Google Workspace": (
        "paper jam", "external drive", "airplay display", "no signal message",
    ),
    "Devices, Displays, and AirPlay": (
        "gmail filter", "class code", "print quota", "printer queue",
    ),
    "Approved Software and Troubleshooting": (
        "paper jam", "external drive", "loaner inventory count",
    ),
    "Live Loaner Inventory": (
        "paper jam", "external drive", "google classroom assignment",
    ),
    "Helpdesk Tickets and Escalation": (
        "paper jam", "external drive", "google classroom class code",
    ),
}


def g(*phrases: str) -> tuple[str, ...]:
    return tuple(phrases)


def rw(
    case_id: str,
    set_name: str,
    category: str,
    question: str,
    purpose: str,
    *concept_groups: Sequence[str],
    forbidden: Sequence[str] = (),
    kind: base.ResponseKind = "answer",
    feedback: base.FeedbackExpectation = "auto",
) -> base.TestCase:
    required_groups = [CATEGORY_TERMS[category]]
    required_groups.extend(tuple(group) for group in concept_groups)
    merged_forbidden = tuple(CATEGORY_FORBIDDEN.get(category, ())) + tuple(forbidden)
    return base.TestCase(
        case_id=case_id,
        category=category,
        question=question,
        purpose=f"{set_name}: {purpose}",
        required_groups=tuple(required_groups),
        forbidden_phrases=merged_forbidden,
        feedback=feedback,
        kind=kind,
        required=True,
    )


FORMAL_CASES: tuple[base.TestCase, ...] = (
    # Wi-Fi and Internet Connection Problems (1-13)
    rw("RW-WIFI-01", "Formal", "Wi-Fi and Internet", "Why won't my school device connect to the student/staff Wi-Fi network?", "Troubleshoot school Wi-Fi connection", g("connect", "connection", "student", "staff", "forget", "reconnect")),
    rw("RW-WIFI-02", "Formal", "Wi-Fi and Internet", 'How do I "forget" and reconnect to the school wireless network?', "Explain forgetting and reconnecting", g("forget", "remove", "reconnect", "join again")),
    rw("RW-WIFI-03", "Formal", "Wi-Fi and Internet", "Why is the internet loading so slowly on my Chromebook today?", "Troubleshoot slow Chromebook internet", g("slow", "speed", "signal", "restart", "tabs", "chromebook")),
    rw("RW-WIFI-04", "Formal", "Wi-Fi and Internet", "What should I do if my MacBook keeps randomly dropping its Wi-Fi connection?", "Troubleshoot intermittent Mac Wi-Fi", g("disconnect", "dropping", "forget", "reconnect", "restart", "macbook")),
    rw("RW-WIFI-05", "Formal", "Wi-Fi and Internet", "How do I connect a guest speaker’s personal device to the guest Wi-Fi?", "Give approved guest Wi-Fi guidance", g("guest", "personal device", "qr code", "connect", "speaker")),
    rw("RW-WIFI-06", "Formal", "Wi-Fi and Internet", 'Why am I getting a "No Internet Connection" error even though I have full Wi-Fi bars?', "Address connected-without-internet symptoms", g("no internet", "full bars", "connected", "reconnect", "browser")),
    rw("RW-WIFI-07", "Formal", "Wi-Fi and Internet", "Is there a known network outage on campus right now?", "Handle a possible campus outage", g("outage", "campus", "multiple users", "status", "helpdesk")),
    rw("RW-WIFI-08", "Formal", "Wi-Fi and Internet", 'Why does my browser say "Your connection is not private" when trying to load a school site?', "Handle a certificate/privacy warning safely", g("not private", "certificate", "date", "time", "do not proceed", "school site")),
    rw("RW-WIFI-09", "Formal", "Wi-Fi and Internet", 'How do I troubleshoot a "DNS server not responding" error?', "Troubleshoot DNS failure", g("dns", "restart", "reconnect", "network", "helpdesk")),
    rw("RW-WIFI-10", "Formal", "Wi-Fi and Internet", "Am I allowed to use a personal cellular hotspot instead of the school Wi-Fi?", "Explain hotspot policy safely", g("hotspot", "policy", "allowed", "approved", "school wi-fi")),
    rw("RW-WIFI-11", "Formal", "Wi-Fi and Internet", "Why does the Wi-Fi keep asking for a password when it never did before?", "Handle Wi-Fi credential prompts", g("password", "forget", "network", "qr code", "helpdesk")),
    rw("RW-WIFI-12", "Formal", "Wi-Fi and Internet", "How do I check my Wi-Fi signal strength and network speeds on a Mac?", "Explain Mac signal and speed checks", g("signal", "speed", "mac", "option", "wi-fi menu", "speed test")),
    rw("RW-WIFI-13", "Formal", "Wi-Fi and Internet", "Why is my Chromebook showing a Wi-Fi icon with a small exclamation mark?", "Explain Chromebook limited connectivity", g("exclamation", "chromebook", "no internet", "reconnect", "restart")),

    # Printers and Print Queues (14-26)
    rw("RW-PRN-14", "Formal", "Printers and Print Queues", "How do I add a specific classroom or library printer to my MacBook?", "Add an approved Mac printer", g("add", "macbook", "classroom", "library", "printers & scanners")),
    rw("RW-PRN-15", "Formal", "Printers and Print Queues", "Why is my print job stuck in the queue and not printing?", "Clear a stuck print queue", g("queue", "stuck", "cancel", "delete", "resume", "restart")),
    rw("RW-PRN-16", "Formal", "Printers and Print Queues", "How do I cancel a document that is currently trying to print?", "Cancel a print job", g("cancel", "delete", "remove", "print job", "queue")),
    rw("RW-PRN-17", "Formal", "Printers and Print Queues", 'What do I do if the printer status says "Offline" on my computer?', "Troubleshoot printer offline status", g("offline", "selected", "queue", "wi-fi", "restart")),
    rw("RW-PRN-18", "Formal", "Printers and Print Queues", "Why is the staff copier asking for a PIN or department ID code?", "Explain copier authentication", g("pin", "department id", "code", "staff", "helpdesk")),
    rw("RW-PRN-19", "Formal", "Printers and Print Queues", "How do I force my document to print double-sided (duplex) on a Chromebook?", "Enable duplex printing", g("double-sided", "duplex", "chromebook", "print settings")),
    rw("RW-PRN-20", "Formal", "Printers and Print Queues", "Why is my document printing with black streaks or faded text?", "Handle print-quality problems", g("streak", "faded", "toner", "cartridge", "maintenance", "helpdesk")),
    rw("RW-PRN-21", "Formal", "Printers and Print Queues", "What is the proper way to clear a paper jam in the staff room printer?", "Give safe paper-jam guidance", g("paper jam", "power", "tray", "do not force", "helpdesk")),
    rw("RW-PRN-22", "Formal", "Printers and Print Queues", "Where can I check if I have enough student print quota left for the semester?", "Explain print-quota checking", g("quota", "balance", "semester", "student", "portal", "helpdesk")),
    rw("RW-PRN-23", "Formal", "Printers and Print Queues", 'Why am I getting an "Access Denied" error when trying to send a print job?', "Troubleshoot printer access denial", g("access denied", "permission", "account", "authorized", "helpdesk")),
    rw("RW-PRN-24", "Formal", "Printers and Print Queues", "Why won't the network printer wake up from sleep mode?", "Troubleshoot a sleeping printer", g("sleep", "wake", "power", "screen", "network", "helpdesk")),
    rw("RW-PRN-25", "Formal", "Printers and Print Queues", "How do I print a PDF directly from Google Drive to the school copier?", "Print a Drive PDF", g("pdf", "google drive", "download", "print", "copier")),
    rw("RW-PRN-26", "Formal", "Printers and Print Queues", "Can I print to a school printer from my personal smartphone or tablet?", "Explain mobile printing policy", g("smartphone", "tablet", "mobile", "personal", "supported", "policy")),

    # School Passwords, Accounts, Gmail, Drive, and Classroom (27-43)
    rw("RW-ACC-27", "Formal", "Accounts and Google Workspace", "How do I reset my school portal password if I completely forgot it?", "Provide approved password-reset process", g("reset", "forgot", "identity", "helpdesk", "do not share")),
    rw("RW-ACC-28", "Formal", "Accounts and Google Workspace", "Why does the system say my school Google account is locked or disabled?", "Handle a locked school account", g("locked", "disabled", "stop repeated", "verify", "helpdesk")),
    rw("RW-ACC-29", "Formal", "Accounts and Google Workspace", "How do I change my password before the 90-day expiration policy kicks in?", "Explain proactive password change", g("change", "90-day", "expiration", "security", "approved")),
    rw("RW-ACC-30", "Formal", "Accounts and Google Workspace", "Why am I not receiving external emails in my school Gmail account?", "Troubleshoot missing external Gmail", g("external", "spam", "filter", "blocked", "bounce", "gmail")),
    rw("RW-ACC-31", "Formal", "Accounts and Google Workspace", "How do I recover a deleted assignment file in Google Drive?", "Recover a deleted Drive file", g("deleted", "trash", "restore", "assignment", "drive")),
    rw("RW-ACC-32", "Formal", "Accounts and Google Workspace", "Why can't I access a Google Drive folder that a teacher shared with me?", "Troubleshoot shared-folder access", g("shared", "teacher", "permission", "request access", "correct account")),
    rw("RW-ACC-33", "Formal", "Accounts and Google Workspace", "How do I join a new Google Classroom using a specific class code?", "Join Classroom with a code", g("join", "class code", "classroom", "school account")),
    rw("RW-ACC-34", "Formal", "Accounts and Google Workspace", "Why did my submitted Google Classroom assignment suddenly disappear?", "Investigate a missing submitted assignment", g("submitted", "assignment", "disappear", "classwork", "teacher", "classroom")),
    rw("RW-ACC-35", "Formal", "Accounts and Google Workspace", "How do I set up two-factor authentication (2FA) for my staff account?", "Set up approved 2FA", g("2fa", "two-factor", "verification", "staff", "authenticator", "security")),
    rw("RW-ACC-36", "Formal", "Accounts and Google Workspace", 'Why is my Google Drive giving me a "Storage Full" warning?', "Address Drive storage limits", g("storage", "full", "quota", "delete", "trash", "drive")),
    rw("RW-ACC-37", "Formal", "Accounts and Google Workspace", "How do I securely sign out of my Google account on a shared library computer?", "Securely sign out on a shared computer", g("sign out", "shared", "library", "remove account", "browser")),
    rw("RW-ACC-38", "Formal", "Accounts and Google Workspace", "Why do my emails bounce back when I try to send a message outside of the school domain?", "Troubleshoot external email bounces", g("bounce", "outside", "domain", "error", "blocked", "recipient")),
    rw("RW-ACC-39", "Formal", "Accounts and Google Workspace", "How do I transfer ownership of a collaborative Google Doc to my teacher?", "Explain Google Doc ownership transfer", g("transfer", "ownership", "teacher", "google doc", "permission")),
    rw("RW-ACC-40", "Formal", "Accounts and Google Workspace", 'Why am I getting a "You need permission" error when trying to open a Google Form quiz?', "Troubleshoot Form permissions", g("permission", "form", "quiz", "correct account", "request access")),
    rw("RW-ACC-41", "Formal", "Accounts and Google Workspace", "How do I sync my school Gmail with the native Mail app on my MacBook?", "Explain approved Mail-app setup", g("mail app", "macbook", "gmail", "sync", "account", "approved")),
    rw("RW-ACC-42", "Formal", "Accounts and Google Workspace", "What immediate steps should I take if I suspect my school account was hacked?", "Respond to a suspected account compromise", g("hacked", "compromised", "change password", "sign out", "helpdesk", "2fa")),
    rw("RW-ACC-43", "Formal", "Accounts and Google Workspace", "How do I configure Google Docs and Classroom for offline access?", "Configure offline Google access", g("offline", "docs", "classroom", "chrome", "enable")),

    # MacBooks, Chromebooks, Classroom Displays, and AirPlay (44-60)
    rw("RW-DEV-44", "Formal", "Devices, Displays, and AirPlay", "How do I perform a hard reset on a Chromebook that is completely frozen?", "Restart a frozen Chromebook", g("hard reset", "frozen", "refresh", "power", "chromebook")),
    rw("RW-DEV-45", "Formal", "Devices, Displays, and AirPlay", "What should I do if my school-issued MacBook won't turn on at all?", "Troubleshoot MacBook power", g("won't turn on", "power", "charger", "hold", "macbook")),
    rw("RW-DEV-46", "Formal", "Devices, Displays, and AirPlay", "How do I connect my MacBook to the interactive classroom display board?", "Connect a MacBook to a classroom display", g("connect", "interactive", "classroom display", "airplay", "cable", "input")),
    rw("RW-DEV-47", "Formal", "Devices, Displays, and AirPlay", "Why is the AirPlay icon completely missing from my Mac's menu bar?", "Restore missing AirPlay controls", g("airplay", "missing", "control center", "screen mirroring", "mac")),
    rw("RW-DEV-48", "Formal", "Devices, Displays, and AirPlay", "How do I fix a Chromebook where the screen is completely black but the power light is on?", "Troubleshoot black Chromebook screen", g("black", "power light", "brightness", "restart", "chromebook")),
    rw("RW-DEV-49", "Formal", "Devices, Displays, and AirPlay", 'Why is the classroom projector displaying a blue "No Signal" message?', "Troubleshoot projector no-signal", g("no signal", "projector", "input", "source", "cable")),
    rw("RW-DEV-50", "Formal", "Devices, Displays, and AirPlay", "How do I connect to a classroom Apple TV or AirPlay display without the onscreen code?", "Enforce approved AirPlay-code use", g("code", "apple tv", "airplay", "onscreen", "helpdesk", "required"), forbidden=("bypass the code", "disable the code")),
    rw("RW-DEV-51", "Formal", "Devices, Displays, and AirPlay", "Why is the video playing on the display but the audio is still coming from my laptop?", "Route audio to the classroom display", g("audio", "sound", "output", "display", "laptop")),
    rw("RW-DEV-52", "Formal", "Devices, Displays, and AirPlay", "How do I adjust the display mirroring resolution on my MacBook?", "Adjust Mac display resolution", g("resolution", "display settings", "mirror", "scaled", "macbook")),
    rw("RW-DEV-53", "Formal", "Devices, Displays, and AirPlay", "Why is the touchscreen feature on my Chromebook suddenly not responding?", "Troubleshoot Chromebook touchscreen", g("touchscreen", "not responding", "restart", "chromebook", "hardware")),
    rw("RW-DEV-54", "Formal", "Devices, Displays, and AirPlay", "How do I force an OS update on my managed school MacBook?", "Explain approved managed updates", g("update", "managed", "macbook", "software update", "approved"), forbidden=("remove management", "bypass management")),
    rw("RW-DEV-55", "Formal", "Devices, Displays, and AirPlay", "Why is my device battery draining incredibly fast during normal use?", "Troubleshoot rapid battery drain", g("battery", "drain", "brightness", "apps", "health", "service")),
    rw("RW-DEV-56", "Formal", "Devices, Displays, and AirPlay", "How do I fix severe lag or stuttering video while using AirPlay?", "Troubleshoot AirPlay lag", g("lag", "stutter", "airplay", "network", "restart", "resolution")),
    rw("RW-DEV-57", "Formal", "Devices, Displays, and AirPlay", "What is the approved method for safely cleaning my device screen?", "Give safe screen-cleaning guidance", g("clean", "screen", "cloth", "power off", "liquid"), forbidden=("spray directly", "bleach")),
    rw("RW-DEV-58", "Formal", "Devices, Displays, and AirPlay", "Why does my MacBook trackpad feel stiff and unresponsive to clicks?", "Treat possible trackpad/battery damage safely", g("trackpad", "stiff", "battery", "swelling", "stop using", "helpdesk")),
    rw("RW-DEV-59", "Formal", "Devices, Displays, and AirPlay", 'How do I "freeze" or blank the image on the classroom display while I work on my laptop?', "Explain display freeze/blank controls", g("freeze", "blank", "display", "remote", "projector", "input")),
    rw("RW-DEV-60", "Formal", "Devices, Displays, and AirPlay", "Why is my Mac showing a flashing folder with a question mark when I turn it on?", "Handle a Mac startup-disk error", g("flashing folder", "question mark", "startup disk", "mac", "helpdesk")),

    # Approved Software and Device Troubleshooting (61-73)
    rw("RW-SW-61", "Formal", "Approved Software and Troubleshooting", "What is the process for requesting a new software program to be approved for classroom use?", "Explain software approval requests", g("request", "approval", "classroom", "software", "ticket", "purpose")),
    rw("RW-SW-62", "Formal", "Approved Software and Troubleshooting", "Why is the school web filter blocking a legitimate website I need for a research project?", "Explain legitimate filter-review process", g("web filter", "blocked", "legitimate", "research", "review", "ticket"), forbidden=("use a vpn", "use a proxy")),
    rw("RW-SW-63", "Formal", "Approved Software and Troubleshooting", "How do I install school-approved applications from Self Service or the school's approved app catalogue?", "Install approved software", g("self service", "approved", "install", "app catalogue", "sign in")),
    rw("RW-SW-64", "Formal", "Approved Software and Troubleshooting", "Why does an approved app crash immediately every time I try to open it?", "Troubleshoot a crashing app", g("crash", "restart", "update", "reinstall", "error")),
    rw("RW-SW-65", "Formal", "Approved Software and Troubleshooting", "How do I manually update Google Chrome if it says it is managed by my organization?", "Update managed Chrome safely", g("chrome", "managed", "update", "restart", "administrator"), forbidden=("remove management",)),
    rw("RW-SW-66", "Formal", "Approved Software and Troubleshooting", "Why isn't my device's webcam or microphone working during a Zoom/Google Meet call?", "Troubleshoot meeting camera and microphone", g("webcam", "camera", "microphone", "zoom", "meet", "permission")),
    rw("RW-SW-67", "Formal", "Approved Software and Troubleshooting", "How do I clear my browser cache and cookies to fix website loading errors?", "Clear browser data safely", g("cache", "cookies", "browser", "clear", "reload")),
    rw("RW-SW-68", "Formal", "Approved Software and Troubleshooting", "What should I do if I accidentally clicked a link and got a virus warning popup?", "Respond to a possible phishing/malware event", g("virus", "popup", "close", "do not click", "disconnect", "helpdesk")),
    rw("RW-SW-69", "Formal", "Approved Software and Troubleshooting", "Why is the network preventing me from downloading this specific PDF file?", "Troubleshoot a blocked PDF download", g("pdf", "download", "blocked", "browser", "filter", "safe")),
    rw("RW-SW-70", "Formal", "Approved Software and Troubleshooting", "How do I enable accessibility browser extensions that are approved by the school?", "Enable approved accessibility extensions", g("accessibility", "extension", "approved", "chrome", "enable")),
    rw("RW-SW-71", "Formal", "Approved Software and Troubleshooting", "Why is the text-to-speech software failing to read my specific document?", "Troubleshoot text-to-speech", g("text-to-speech", "read", "document", "format", "permission")),
    rw("RW-SW-72", "Formal", "Approved Software and Troubleshooting", "How do I safely uninstall an app that is taking up too much space on my MacBook?", "Uninstall software safely", g("uninstall", "remove", "storage", "macbook", "approved")),
    rw("RW-SW-73", "Formal", "Approved Software and Troubleshooting", "Why is the required secure testing browser (e.g., Respondus/LockDown) failing to launch?", "Troubleshoot secure testing browser", g("respondus", "lockdown", "testing browser", "launch", "restart", "update")),

    # Live Loaner Inventory Checks (74-81)
    rw("RW-INV-74", "Formal", "Live Loaner Inventory", "How do I check the live inventory to see if there are any loaner Chromebooks currently available?", "Return live Chromebook availability", g("chromebook", "available", "count", "currently")),
    rw("RW-INV-75", "Formal", "Live Loaner Inventory", "Where is the designated pickup desk for securing a loaner device?", "Explain loaner pickup location", g("pickup", "desk", "helpdesk", "location")),
    rw("RW-INV-76", "Formal", "Live Loaner Inventory", "How long am I allowed to keep a loaner MacBook or Chromebook?", "Explain loan duration policy", g("how long", "duration", "return", "due", "policy")),
    rw("RW-INV-77", "Formal", "Live Loaner Inventory", "Can I reserve a loaner laptop through the online portal before I walk down to the IT desk?", "Explain read-only reservation limitations", g("reserve", "reservation", "portal", "cannot", "it desk"), forbidden=("reservation confirmed", "reserved for you")),
    rw("RW-INV-78", "Formal", "Live Loaner Inventory", "What is the policy or fee if I accidentally break or lose a loaner device?", "Explain damage/loss policy without inventing fees", g("damage", "lose", "policy", "fee", "agreement", "helpdesk")),
    rw("RW-INV-79", "Formal", "Live Loaner Inventory", "Will a power adapter be included when I sign out a loaner laptop?", "Explain loaner accessories", g("power adapter", "charger", "included", "sign out", "confirm")),
    rw("RW-INV-80", "Formal", "Live Loaner Inventory", "What is the correct procedure for returning a loaner device back into the active inventory?", "Explain loaner return process", g("return", "helpdesk", "charger", "condition", "check in")),
    rw("RW-INV-81", "Formal", "Live Loaner Inventory", "Are there any iPads or drawing tablets available in the live loaner inventory right now?", "Return live tablet availability", g("ipad", "drawing tablet", "tablet", "available", "currently")),

    # Escalating Unresolved Problems to an IT Helpdesk Ticket (82-90)
    rw("RW-TKT-82", "Formal", "Helpdesk Tickets and Escalation", "Where do I go to submit an official IT helpdesk ticket?", "Open or explain ticket submission", g("submit", "create", "form", "helpdesk", "ticket")),
    rw("RW-TKT-83", "Formal", "Helpdesk Tickets and Escalation", "What specific information (asset tag, room number, error code) do I need to include to get my ticket solved faster?", "List useful ticket details", g("asset tag", "room", "error", "description", "screenshot")),
    rw("RW-TKT-84", "Formal", "Helpdesk Tickets and Escalation", "How do I check the current status or updates on my open helpdesk ticket?", "Explain ticket-status checking", g("status", "updates", "open", "email", "portal")),
    rw("RW-TKT-85", "Formal", "Helpdesk Tickets and Escalation", "Who do I escalate to if my IT ticket hasn't received a response in 48 hours?", "Explain delayed-ticket escalation", g("48 hours", "follow up", "reply", "helpdesk", "urgent")),
    rw("RW-TKT-86", "Formal", "Helpdesk Tickets and Escalation", "Is there an emergency IT phone number for catastrophic tech failures mid-lesson?", "Give only approved emergency contact guidance", g("emergency", "phone", "mid-lesson", "helpdesk", "contact"), forbidden=("555-",)),
    rw("RW-TKT-87", "Formal", "Helpdesk Tickets and Escalation", "How do I capture and attach a screenshot to my IT support ticket?", "Explain screenshot attachment", g("screenshot", "attach", "ticket", "private information")),
    rw("RW-TKT-88", "Formal", "Helpdesk Tickets and Escalation", 'What determines the difference between a "low priority" and "high priority" support ticket?', "Explain priority selection", g("low", "high", "priority", "impact", "urgency")),
    rw("RW-TKT-89", "Formal", "Helpdesk Tickets and Escalation", "How do I add a comment to an open ticket with new information?", "Add information to an open ticket", g("comment", "open ticket", "reply", "update", "new information")),
    rw("RW-TKT-90", "Formal", "Helpdesk Tickets and Escalation", "How do I reopen a helpdesk ticket that was closed before the problem was actually fixed?", "Reopen or follow up on a closed ticket", g("reopen", "closed", "reply", "new ticket", "not fixed")),
)


NATURAL_CASES: tuple[base.TestCase, ...] = (
    rw("RW-NAT-01", "Natural", "Wi-Fi and Internet", "my laptop keeps disconnecting from the school wifi every 5 mins pls help", "Understand rushed intermittent Wi-Fi report", g("disconnect", "5 mins", "forget", "reconnect", "restart")),
    rw("RW-NAT-02", "Natural", "Wi-Fi and Internet", "hey the internet is super slow in room 104, is it just me?", "Check local or wider slow-network impact", g("slow", "room 104", "others", "signal", "outage")),
    rw("RW-NAT-03", "Natural", "Wi-Fi and Internet", "can't connect to the network, it keeps saying invalid passwrod even tho I typed it right", "Understand password typo and Wi-Fi error", g("invalid password", "passwrod", "forget", "reconnect", "qr code")),
    rw("RW-NAT-04", "Natural", "Wi-Fi and Internet", "is there a way to get my iphone on the staff wif-i?", "Understand iPhone/staff Wi-Fi typo", g("iphone", "staff", "wi-fi", "wif-i", "approved")),
    rw("RW-NAT-05", "Natural", "Printers and Print Queues", "i sent my essay to the libary printer but nothing came out", "Understand library-printer typo and missing job", g("library", "libary", "queue", "selected", "print job")),
    rw("RW-NAT-06", "Natural", "Printers and Print Queues", "the big copier by the staff lounge is out of toner and paper jamming again", "Handle copier supplies and paper jam", g("copier", "staff lounge", "toner", "paper jam", "helpdesk")),
    rw("RW-NAT-07", "Natural", "Printers and Print Queues", "how do i print in color? it only gives me black and white options", "Find colour-print settings or policy", g("color", "colour", "black and white", "print settings", "supported")),
    rw("RW-NAT-08", "Natural", "Printers and Print Queues", "accidentaly sent a 100 page pdf to the printer, how do i stop it asap!!", "Urgently cancel a large print job", g("100 page", "pdf", "cancel", "delete", "queue", "stop")),
    rw("RW-NAT-09", "Natural", "Accounts and Google Workspace", "i forgot my password over the summer break and cant login", "Recover a forgotten school password", g("forgot", "password", "can't login", "reset", "helpdesk")),
    rw("RW-NAT-10", "Natural", "Accounts and Google Workspace", "mr clark shared a google doc with me but it says I don't have access?", "Troubleshoot a shared Doc permission", g("mr clark", "google doc", "access", "permission", "correct account")),
    rw("RW-NAT-11", "Natural", "Accounts and Google Workspace", "why didn't my assignment attach in google classrom? teacher gave me a zero", "Troubleshoot Classroom attachment typo", g("assignment", "attach", "classrom", "classroom", "teacher", "submission")),
    rw("RW-NAT-12", "Natural", "Accounts and Google Workspace", "im locked out of my gmail, says suspicious activity or something", "Handle Gmail suspicious-activity lockout", g("locked", "gmail", "suspicious activity", "verify", "helpdesk")),
    rw("RW-NAT-13", "Natural", "Devices, Displays, and AirPlay", "my chromebook screen cracked in my backpack, what do i do", "Handle physical Chromebook damage", g("cracked", "chromebook", "stop using", "damage", "helpdesk")),
    rw("RW-NAT-14", "Natural", "Devices, Displays, and AirPlay", "the hallway digital sign is stuck on a black screen with white text", "Troubleshoot a digital-sign display failure", g("digital sign", "black screen", "white text", "restart", "helpdesk")),
    rw("RW-NAT-15", "Natural", "Devices, Displays, and AirPlay", "trying to airplay to the board but the screen just keeps freezing", "Troubleshoot freezing AirPlay", g("airplay", "board", "freezing", "network", "restart")),
    rw("RW-NAT-16", "Natural", "Devices, Displays, and AirPlay", "macbook battery died and now it wont turn back on even when plugged in", "Troubleshoot a MacBook that will not power on", g("battery", "won't turn on", "plugged in", "charger", "hold power")),
    rw("RW-NAT-17", "Natural", "Devices, Displays, and AirPlay", "i spilled a little bit of water on my keyboard and some keys are sticky", "Give immediate liquid-damage safety steps", g("water", "sticky", "power off", "disconnect", "stop using", "helpdesk"), forbidden=("put it in rice", "hair dryer")),
    rw("RW-NAT-18", "Natural", "Approved Software and Troubleshooting", "can u guys unblock coolmathgames? we have free time", "Apply school web-filter policy", g("blocked", "unblock", "school use", "policy", "not approved", "request review"), forbidden=("vpn", "proxy", "bypass")),
    rw("RW-NAT-19", "Natural", "Approved Software and Troubleshooting", "my canva wont let me export my poster design for some reason", "Troubleshoot Canva export", g("canva", "export", "download", "browser", "storage", "file type")),
    rw("RW-NAT-20", "Natural", "Approved Software and Troubleshooting", "zoom audio isnt working, the teacher cant hear me talking", "Troubleshoot Zoom microphone", g("zoom", "audio", "teacher", "hear", "microphone", "permission")),
    rw("RW-NAT-21", "Natural", "Live Loaner Inventory", "do you have any spare chargers I can borrow for next period?", "Check live charger availability", g("charger", "borrow", "available", "next period")),
    rw("RW-NAT-22", "Natural", "Live Loaner Inventory", "i need a loner laptop, mine is dead and I have a test right now", "Understand loaner typo and urgent availability", g("loner", "loaner", "laptop", "available", "test", "urgent")),
    rw("RW-NAT-23", "Natural", "Helpdesk Tickets and Escalation", "submitted a ticket yesterday but nobody came to look at my smartboard yet", "Follow up on a delayed smartboard ticket", g("ticket", "yesterday", "smartboard", "follow up", "status")),
    rw("RW-NAT-24", "Natural", "Live Loaner Inventory", "where do i go to drop off this broken loaner chrombook?", "Handle broken-loaner return typo", g("drop off", "broken", "loaner", "chrombook", "chromebook", "helpdesk")),
    rw("RW-NAT-25", "Natural", "Helpdesk Tickets and Escalation", "how do I put in a help ticket for a busted mouse?", "Open a mouse hardware ticket", g("ticket", "mouse", "busted", "device", "form")),
    rw("RW-NAT-26", "Natural", "Live Loaner Inventory", "the tech desk closed? where do i leave my loner", "Give safe after-hours loaner return guidance", g("tech desk", "closed", "leave", "loner", "loaner", "return", "secure")),
    rw("RW-NAT-27", "Natural", "Approved Software and Troubleshooting", "why is my python script not running on the school desktop?", "Troubleshoot a Python script", g("python", "script", "error", "terminal", "interpreter", "environment")),
    rw("RW-NAT-28", "Natural", "Wi-Fi and Internet", "is the system down? nothing is loading on the student portal", "Handle a possible portal outage", g("system down", "student portal", "nothing loading", "outage", "other users", "helpdesk")),
)


ALL_CASES: tuple[base.TestCase, ...] = FORMAL_CASES + NATURAL_CASES


def select_cases(args: argparse.Namespace) -> list[base.TestCase]:
    if args.set == "formal":
        cases = list(FORMAL_CASES)
    elif args.set == "natural":
        cases = list(NATURAL_CASES)
    else:
        cases = list(ALL_CASES)

    if args.category:
        wanted = args.category.casefold()
        cases = [case for case in cases if case.category.casefold() == wanted]

    if args.case:
        wanted = args.case.upper()
        cases = [case for case in cases if case.case_id.upper() == wanted]

    if args.limit is not None:
        cases = cases[: args.limit]

    return cases


def print_catalog() -> None:
    print("ALTITUDE REAL-WORLD QUESTION CATALOG")
    print("=" * 100)
    for case in ALL_CASES:
        print(f"{case.case_id:<12} {case.category:<38} {case.question}")
    print(f"\nTotal: {len(ALL_CASES)} questions ({len(FORMAL_CASES)} formal + {len(NATURAL_CASES)} natural).")


def run_self_test() -> int:
    ids = [case.case_id for case in ALL_CASES]
    problems: list[str] = []
    if len(FORMAL_CASES) != 90:
        problems.append(f"Expected 90 formal questions, found {len(FORMAL_CASES)}.")
    if len(NATURAL_CASES) != 28:
        problems.append(f"Expected 28 natural questions, found {len(NATURAL_CASES)}.")
    if len(ALL_CASES) != 118:
        problems.append(f"Expected 118 total questions, found {len(ALL_CASES)}.")
    if len(ids) != len(set(ids)):
        problems.append("Duplicate case IDs detected.")
    for case in ALL_CASES:
        if case.category not in CATEGORY_TERMS:
            problems.append(f"Unknown category on {case.case_id}: {case.category}")
        if not case.required_groups:
            problems.append(f"No relevance rubric on {case.case_id}.")

    if problems:
        print("Self-test failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("Self-test passed.")
    print(f"Formal questions: {len(FORMAL_CASES)}")
    print(f"Natural questions: {len(NATURAL_CASES)}")
    print(f"Total questions: {len(ALL_CASES)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run 118 realistic questions through Altitude and save TXT/JSON/HTML reports.",
    )
    parser.add_argument(
        "--set",
        choices=("all", "formal", "natural"),
        default="all",
        help="Choose all 118 questions, the 90 formal questions, or the 28 natural questions.",
    )
    parser.add_argument("--category", help="Run one exact category shown by --list.")
    parser.add_argument("--case", help="Run one case ID, for example RW-WIFI-01.")
    parser.add_argument("--limit", type=int, help="Run only the first N selected questions.")
    parser.add_argument(
        "--timeout",
        type=float,
        default=base.DEFAULT_TIMEOUT_SECONDS,
        help=f"Per-question timeout in seconds (default: {base.DEFAULT_TIMEOUT_SECONDS:.0f}).",
    )
    parser.add_argument(
        "--strict-latency",
        action="store_true",
        help=f"Fail instead of warn above {base.LATENCY_TARGET_SECONDS:.1f} seconds.",
    )
    parser.add_argument("--stop-on-failure", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list:
        print_catalog()
        return 0
    if args.self_test:
        return run_self_test()
    if args.timeout < 0:
        parser.error("--timeout must be zero or greater")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    cases = select_cases(args)
    if not cases:
        parser.error("No questions matched the selected set/category/case.")

    print("ALTITUDE REAL-WORLD QUESTION TEST")
    print("=" * 100)
    print(f"Project: {PROJECT_ROOT}")
    print(f"Question set: {args.set}")
    print(f"Questions selected: {len(cases)}")
    print(f"Per-question timeout: {args.timeout:.0f}s")
    print("Feedback rule: show after a complete answer; hide while asking a clarification.")
    print("No real ticket will be submitted. Inventory checks are read-only.")

    runner = base.ResponseTestRunner(
        timeout_seconds=args.timeout,
        strict_latency=args.strict_latency,
        stop_on_failure=args.stop_on_failure,
    )

    try:
        for case in cases:
            runner.run_case(case)
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        return 2
    except Exception as error:  # noqa: BLE001
        print(f"\nRunner error: {type(error).__name__}: {error}")
        return 2

    text_path, json_path, html_path = runner.write_reports(
        base_name_prefix="altitude-real-world-question-test",
        report_title="Altitude Real-World Question Test Report",
        scope=(
            "118 realistic school IT questions covering Wi-Fi, printing, accounts, "
            "devices, software, inventory, tickets, natural language, feedback, and latency"
        ),
    )
    summary = runner.summary()
    latency = runner.latency_summary()

    print("\nSUMMARY")
    print("-" * 100)
    print("  ".join(f"{name}: {count}" for name, count in summary.items()))
    print(
        f"Latency: average={latency['average']:.3f}s, median={latency['median']:.3f}s, "
        f"p95={latency['p95']:.3f}s, over target={latency['over_target']}"
    )
    print("Reports:")
    print(f"- {text_path}")
    print(f"- {json_path}")
    print(f"- {html_path}")

    return 1 if runner.has_required_failures() else 0


if __name__ == "__main__":
    raise SystemExit(main())
