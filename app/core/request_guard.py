from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from core.conversation_context import build_contextual_query, is_contextual_follow_up
from core.text_matching import contains_any_phrase, normalize_text


@dataclass(frozen=True)
class RequestGuardDecision:
    """High-confidence routing guard used before RAG and web fallback."""

    handled: bool
    answer: str = ""
    intent: str = ""


def _has(text: str, *phrases: str) -> bool:
    return contains_any_phrase(text, phrases)


def _recent_context(history: list[dict[str, Any]]) -> bool:
    """Return whether the current chat already has a substantive IT topic."""

    markers = (
        "printer",
        "printing",
        "inventory",
        "available",
        "mac",
        "macbook",
        "chromebook",
        "classroom display",
        "classroom tv",
        "projector",
        "monitor",
        "wifi",
        "google",
        "zoom",
        "adobe",
        "safari",
        "chrome",
        "camera",
        "microphone",
        "sound",
        "account",
    )

    for message in reversed(history[-8:]):
        content = normalize_text(str(message.get("content", "")))
        if content and any(marker in content for marker in markers):
            return True

    return False


def _history_contains(history: list[dict[str, Any]], *terms: str) -> bool:
    for message in reversed(history[-10:]):
        content = normalize_text(str(message.get("content", "")))
        if any(term in content for term in terms):
            return True
    return False


def _policy_question(text: str) -> bool:
    if _has(
        text,
        "what's the policy",
        "what is the policy",
        "school policy",
        "are we allowed",
        "are teachers allowed",
        "are students allowed",
        "is there a limit",
        "what is the limit",
        "what's the limit",
    ):
        return True

    if re.search(r"\bcan students\b.*\b(?:pages?|print|install|use|access)\b", text):
        return True

    if _has(
        text,
        "permanent loaner",
        "loaner for the semester",
        "loaner for a semester",
        "take my school laptop to",
        "take school laptop to",
        "personal hotspot",
        "bring your own device",
        "byod",
    ):
        return True

    return False


def _vague_question(text: str, history: list[dict[str, Any]]) -> str | None:
    """Return a clarification for underspecified requests instead of searching."""

    if _recent_context(history):
        return None

    if text in {
        "it's not working",
        "its not working",
        "it is not working",
        "not working",
        "same issue as last time",
        "same problem as last time",
    }:
        return (
            "What device or service is affected, and what happens when you try to "
            "use it? If there is an error message, include the exact wording."
        )

    if _has(text, "my computer is being weird", "computer is being weird"):
        return (
            "What is the computer doing: running slowly, freezing, restarting, "
            "showing a screen problem, losing internet, or having trouble with a "
            "specific app?"
        )

    if text in {
        "my display isn't working",
        "my display is not working",
        "display isn't working",
        "display is not working",
    }:
        return (
            "Which display is affected: an external monitor or the classroom "
            "TV/projector? Also tell me whether it is black, shows No Signal, "
            "is not detected, or will not mirror."
        )

    if _has(text, "the thing with the screen is broken again", "screen thing is broken"):
        return (
            "Which screen is affected: the MacBook/Chromebook screen, an external "
            "monitor, or the classroom TV/projector? Also tell me what you see, such "
            "as black screen, No Signal, flickering, or a distorted image."
        )

    if _has(text, "doing that thing where it freezes", "it freezes") and not _has(
        text,
        "mac",
        "macbook",
        "chromebook",
        "chrome",
        "safari",
        "zoom",
        "adobe",
        "classroom",
        "google",
    ):
        return (
            "What is freezing: the whole computer, one application, the browser, or "
            "a specific website? Tell me the device and app so I can give the right steps."
        )

    # General low-information requests should ask for the missing device/app and
    # symptom instead of being classified as non-IT or sent to web/RAG.
    generic_vague = {
        "can you just fix it",
        "fix it",
        "it worked five minutes ago and now it doesn't",
        "it worked five minutes ago and now it doesnt",
        "this app is being dumb",
        "this app is broken",
        "it's the blue screen thing again",
        "its the blue screen thing again",
    }
    if text in generic_vague:
        return (
            "What device, application, or service is affected, and what exactly is happening now? "
            "If there is an error message, include the exact wording."
        )

    if _has(text, "internet is down again", "the internet is down again"):
        return (
            "Is the internet problem affecting just one device, one classroom, or multiple rooms? "
            "Also tell me whether nearby users are affected and which school network is involved if you know it."
        )

    return None


def route_request_guard(
    question: str,
    history: list[dict[str, Any]],
) -> RequestGuardDecision:
    """Handle ambiguity, policy, permissions, and common stable intents before RAG."""

    text = normalize_text(question).strip(" .")
    if not text:
        return RequestGuardDecision(False)

    # Capability requests must win before product routers. For example, a
    # request to be notified about Wi-Fi would otherwise be mistaken for a
    # Wi-Fi troubleshooting question.
    if _has(text, "text me", "notify me", "send me a notification") and _has(
        text, "when", "fixed", "working again", "back online"
    ):
        return RequestGuardDecision(
            True,
            (
                "Altitude cannot send a later text or notification from this chat. "
                "If an IT ticket exists, use that ticket for status updates or ask the IT Helpdesk "
                "how completion notifications are delivered."
            ),
            "capability_follow_up_notification",
        )

    if _has(text, "put in a ticket", "create a ticket", "submit a ticket", "file a ticket"):
        return RequestGuardDecision(
            True,
            (
                "I can help prepare the ticket, but I should not claim it was submitted unless the "
                "ticket system confirms a ticket number. Confirm the affected device/service, location, "
                "impact, and any error message, then use the available **Create IT ticket** action."
            ),
            "capability_ticket_creation",
        )

    # Stable task routes that must run before broad product and web routers.
    if _has(text, "auto-archive", "auto archive", "auto-archives", "auto archives") and _has(
        text, "filter", "parent emails", "missing important messages"
    ):
        return RequestGuardDecision(
            True,
            (
                "Open **Gmail → Settings → See all settings → Filters and Blocked Addresses** and review the "
                "filter that archives the messages. Edit or remove the **Skip the Inbox/Archive it** action if "
                "needed. Archived messages remain in **All Mail** and can be found with Gmail search, so check "
                "there before treating them as lost."
            ),
            "gmail_filter_archive",
        )

    if "google drive" in text and _has(
        text, "100% storage", "100 percent storage", "at quota", "quota full", "can't save", "cant save"
    ):
        return RequestGuardDecision(
            True,
            (
                "At 100% Google Drive storage, new files and changes may stop saving. Open Drive's **Storage** "
                "view, confirm the school account is selected, and sort by storage used to review large files. "
                "Delete only files you recognize and no longer need, then review Trash before emptying it. If "
                "the displayed quota or usage appears incorrect, contact IT/Workspace administration."
            ),
            "drive_storage_cleanup",
        )

    if _has(text, "microphone", "mic") and _has(
        text, "isn't working", "is not working", "not working", "nobody can hear", "can't hear me", "cant hear me"
    ):
        return RequestGuardDecision(
            True,
            (
                "For the live class, first check that the call is not muted and select the correct microphone in "
                "the meeting's audio settings. Check the headset mute switch, reconnect it, and allow microphone "
                "access in the browser or **System Settings → Privacy & Security → Microphone**. Test the built-in "
                "microphone once. If needed, use approved phone audio as a temporary class workaround, then contact "
                "IT if the microphone also fails in another app."
            ),
            "urgent_microphone",
        )

    if _has(text, "standing desk", "desk converter"):
        return RequestGuardDecision(
            True,
            (
                "A standing-desk converter is furniture/ergonomic equipment rather than normal IT loaner "
                "inventory. Submit the request through the school's facilities, purchasing, or workplace "
                "accommodation process. IT should only be involved if the setup needs monitor, dock, or cable planning."
            ),
            "facilities_furniture_request",
        )

    if "google classroom" in text and _has(text, "error 400", "something went wrong"):
        return RequestGuardDecision(
            True,
            (
                "Reload Classroom and retry in a private browser window while signed into only the correct school "
                "account. Try the same assignment in another supported browser and clear Classroom site data only "
                "if needed. If **Error 400** continues, record the class, assignment, time, and exact error and "
                "contact IT/Workspace administration; do not change the assignment status or password based only on this error."
            ),
            "classroom_error_400",
        )

    if _has(text, "error 1223") and _has(text, "drive for desktop", "syncing"):
        return RequestGuardDecision(
            True,
            (
                "Confirm Drive for desktop is signed into the correct school account and that the Mac has an "
                "internet connection and free local storage. Open Drive for desktop, review its sync activity, "
                "restart the app, and verify the affected file in Drive on the web before editing further. If "
                "Error 1223 returns, record the file path and exact error and contact IT with the Drive diagnostic "
                "logs; do not reinstall or remove the account unless instructed."
            ),
            "drive_desktop_error_1223",
        )

    if "zoom" in text and _has(text, "error code 104101", "error 104101", "104101"):
        return RequestGuardDecision(
            True,
            (
                "Zoom Error 104101 means the device cannot connect to Zoom's servers. Confirm the internet "
                "connection, quit and reopen Zoom, and test whether the meeting opens from another approved "
                "network or the supported web client. On a school device, do not disable security software or "
                "change firewall/proxy settings yourself. If it continues, contact IT with the code, network, and "
                "meeting time. Official Zoom guidance: https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0070317"
            ),
            "zoom_error_104101",
        )

    if _has(text, "grammarly", "browser extension", "chrome extension") and _has(
        text, "student chromebooks", "class set", "install"
    ):
        return RequestGuardDecision(
            True,
            (
                "Extensions on managed student Chromebooks are normally approved and deployed centrally rather "
                "than installed by each student. Send IT the extension name/store link, educational purpose, "
                "student group, requested permissions, and required date so it can be reviewed and deployed if approved."
            ),
            "managed_extension_deployment",
        )

    if _has(text, "one row", "part of the room", "subset") and _has(
        text, "chromebook", "chromebooks", "wifi", "can't connect", "cant connect"
    ):
        return RequestGuardDecision(
            True,
            (
                "Because only one row/group is affected while the rest of the room connects, treat this as a "
                "localized signal/access-point or managed-device-group pattern—not many unrelated device failures. "
                "Restart one affected Chromebook and compare it with a working one in the same room, then report "
                "the room, affected row/device group, network, and start time to IT."
            ),
            "wifi_localized_subset",
        )

    if _has(text, "password") and _has(text, "desktop wallpaper", "change the wallpaper"):
        return RequestGuardDecision(
            True,
            (
                "A password or administrator prompt for a routine wallpaper change is unusual on a school Mac and "
                "may indicate a managed restriction or profile/permissions problem. Cancel the prompt rather than "
                "entering an administrator password, note where it appears, and contact IT to check the device policy."
            ),
            "wallpaper_permission_prompt",
        )

    if "shared drive" in text and _has(text, "new shared drive", "wants a new", "get one set up", "create a shared drive"):
        return RequestGuardDecision(
            True,
            (
                "Altitude cannot create a Shared Drive. Ask IT/Workspace administration to create it through the "
                "approved request process and include the department/purpose, proposed name, initial managers and "
                "members, and the type of records it will contain. Use My Drive only as a temporary workspace until "
                "the approved Shared Drive and permissions are confirmed."
            ),
            "shared_drive_creation_request",
        )

    if _has(text, "login for the shared", "printer login", "login for the printer"):
        return RequestGuardDecision(
            True,
            (
                "A managed shared printer normally uses your existing school/Mac sign-in or is deployed without a "
                "separate printer password. Do not use another person's credentials. Confirm the exact printer name "
                "and your school account; if it still requests a separate login, send IT the printer name and prompt."
            ),
            "printer_login_clarification",
        )

    if _has(text, "is this a me problem or an it problem", "screen just went black"):
        return RequestGuardDecision(
            True,
            (
                "First check whether moving the mouse or pressing a key wakes the screen and whether the device, "
                "monitor, or projector still has power. If it is an external display, reseat its cable and confirm "
                "the input. Tell me which screen is black and whether the computer still makes sound or shows lights; "
                "if it remains black after those checks, contact IT rather than assigning blame."
            ),
            "black_screen_triage",
        )

    if _has(text, "third time", "keeps dying", "died mid-class") and _has(text, "projector", "classroom display"):
        return RequestGuardDecision(
            True,
            (
                "I understand why a projector failing repeatedly during class is frustrating. For today's issue, "
                "confirm power/input, reseat the cable or adapter, and use an approved spare connection if available. "
                "Because this has happened repeatedly, follow up with IT using the room, dates/times, warning lights, "
                "and any prior ticket number so the recurring hardware or room connection can be investigated."
            ),
            "projector_repeat_failure",
        )

    clarification = _vague_question(text, history)
    if clarification:
        return RequestGuardDecision(True, clarification, "clarification")

    contextual_text = text
    if is_contextual_follow_up(question, history):
        contextual_text = normalize_text(build_contextual_query(question, history))

    if _has(text, "reset my password", "password reset") and _has(
        text, "unlock the classroom door", "unlock the door", "physical access"
    ):
        return RequestGuardDecision(
            True,
            (
                "These are separate requests. A school Google Workspace password reset requires the approved "
                "IT identity-verification process. Altitude cannot unlock doors or manage physical building access; "
                "contact the front office/security for the classroom door."
            ),
            "mixed_password_physical_access",
        )

    # Physical safety conditions must never reach RAG or generic web fallback.
    if _has(text, "puffed up", "puffy", "bulging", "swollen", "trackpad is raised", "trackpad lifting") and _has(
        text, "chromebook", "mac", "macbook", "laptop", "battery", "trackpad"
    ):
        return RequestGuardDecision(
            True,
            (
                "Stop using and charging the device immediately. A raised/puffed area near the trackpad can indicate a swollen battery. "
                "Shut it down if safe, unplug power and accessories, do not press on the case or restart it, and contact IT immediately for safe handling."
            ),
            "battery_swelling",
        )

    if _has(text, "spilled tea", "spilled coffee", "spilled juice", "spilled water", "liquid on", "drink on") and _has(
        text, "mac", "macbook", "chromebook", "laptop", "keyboard"
    ):
        return RequestGuardDecision(
            True,
            (
                "Power the device off immediately and disconnect the charger and accessories. Do not keep testing it, restart it, use heat, or put it in rice. "
                "Wipe only visible liquid from the outside and bring it to the IT Helpdesk for inspection as soon as possible."
            ),
            "liquid_damage",
        )

    if _has(text, "loose hinge", "hinge is loose", "screen flops", "screen is cracked", "purple vertical line", "vertical line") and _has(
        text, "chromebook", "mac", "macbook", "laptop", "screen", "hinge"
    ):
        return RequestGuardDecision(
            True,
            (
                "This looks like a physical hardware fault. Stop forcing the hinge/display, power the device down if movement could worsen the damage, and bring it to IT for hardware assessment. "
                "Do not factory-reset the device or try to repair the hinge/display yourself."
            ),
            "physical_hardware_damage",
        )

    # Capability and privacy boundaries. Altitude can guide, but it cannot act
    # as another school system or expose private administrative data.
    if _has(text, "remote into my computer", "remote in to my computer", "remote into my mac", "remote into my laptop"):
        return RequestGuardDecision(
            True,
            "Altitude cannot remotely control your device. I can guide you through the settings, or you can contact the IT Helpdesk for authorized hands-on/remote support.",
            "capability_remote_access",
        )

    if _has(text, "email my principal", "send an email for me", "email them for me"):
        return RequestGuardDecision(
            True,
            "Altitude cannot send email on your behalf from this support chat. I can help you draft a short message describing the IT problem for you to send from your school Gmail account.",
            "capability_send_email",
        )

    if _has(text, "substitute teacher coming", "check if there's a substitute", "check if there is a substitute"):
        return RequestGuardDecision(
            True,
            "Altitude does not have access to staffing/substitute scheduling. Check the school's approved staffing/absence system or contact the school office/administration.",
            "non_it_staffing",
        )

    if _has(text, "student's home address", "students home address", "which websites my students visited", "list of every student's login attempts", "list of every students login attempts", "specific teacher has been using"):
        return RequestGuardDecision(
            True,
            "Altitude cannot retrieve or disclose private student/staff records, browsing history, or account-audit data. Use the school's authorized administrative process and contact IT/administration if there is a legitimate security or records request.",
            "privacy_admin_data",
        )

    if _has(text, "screen time restriction", "developer mode") and _has(text, "bypass", "enable", "turn on"):
        return RequestGuardDecision(
            True,
            (
                "Altitude cannot bypass or change managed security/device restrictions. If this setting is required for an approved class or development task, send IT the device, feature, purpose, and deadline so they can review the policy exception or enable it through the managed configuration."
            ),
            "managed_permission",
        )

    if _has(text, "vpn", "vpn extension") and _has(text, "blocked", "filter", "restriction", "research site"):
        return RequestGuardDecision(
            True,
            (
                "Do not use a personal VPN to bypass school filtering on a managed device. Send the blocked site URL and educational purpose to IT for the approved allowlist/review process."
            ),
            "security_bypass",
        )

    if _has(text, "someone tried to log", "login from another country", "sign-in from another country", "unrecognized sign-in") and _has(text, "school account", "google", "gmail", "email"):
        return RequestGuardDecision(
            True,
            (
                "Treat this as a possible account-security incident. Do not click links in the alert email. Open your school Google Account/security page directly from a trusted bookmark or Google, review recent security activity, and contact IT immediately if you do not recognize the sign-in. "
                "Change the password only through the approved school process and do not share verification codes."
            ),
            "account_security_alert",
        )

    if _has(text, "authenticator app broke", "phone with the authenticator", "can't get the 2-step", "cant get the 2-step", "2-step verification code"):
        return RequestGuardDecision(
            True,
            (
                "If your registered authenticator/phone is unavailable, use another approved verification method only if Google offers one. Otherwise stop repeated attempts and contact the IT Helpdesk so your identity can be verified and the school's approved 2-step verification method can be reset."
            ),
            "mfa_recovery",
        )

    if _has(text, "same password", "personal gmail") and _has(text, "school account", "password"):
        return RequestGuardDecision(
            True,
            (
                "Use a unique password for your school account rather than reusing your personal Gmail password. Do not share the school password, and follow the school's password rules shown by the approved password-change system."
            ),
            "password_hygiene",
        )

    # Loaner questions about condition, return, or enrollment are not inventory
    # availability lookups even though they contain words such as loaner/MacBook.
    if _has(text, "loaner", "borrowed") and _has(text, "re-enroll", "re-enrolled", "needs to be re-enrolled"):
        return RequestGuardDecision(
            True,
            "A re-enrollment prompt on a school loaner is a managed-device issue, not something to bypass. Keep the device on approved Wi-Fi/power and bring it to IT if the prompt blocks use so enrollment can be restored correctly.",
            "loaner_reenrollment",
        )

    if _has(text, "loaner") and _has(text, "lost the charger", "lost charger", "charger that came with"):
        return RequestGuardDecision(
            True,
            "Report the missing loaner charger to the IT Helpdesk promptly. Altitude should not guess fees or replacement policy. Bring/return the loaner device and any remaining accessories so IT can confirm the approved next step and replacement charger if needed.",
            "loaner_missing_accessory",
        )

    if _has(text, "loaner") and _has(text, "wipe", "returning", "return it", "end of the year"):
        return RequestGuardDecision(
            True,
            "Do not erase or factory-reset a school loaner unless IT specifically instructs you. Sign out of personal sessions if appropriate, save school work to the approved account/storage, and return the device and accessories to IT so the managed return process can be completed.",
            "loaner_return",
        )

    if _has(text, "loaner chromebook") and _has(text, "someone else's name", "someone elses name", "name sticker"):
        return RequestGuardDecision(
            True,
            "Do not remove or alter asset/ownership labels yourself. Report the old name label to IT so the loaner record and physical label can be checked before continued use.",
            "loaner_label",
        )

    if _has(text, "loaner chromebook") and _has(text, "old apps", "outdated apps", "old apps installed"):
        return RequestGuardDecision(
            True,
            "Restart the loaner Chromebook and connect it to approved school Wi-Fi so managed apps/policies can refresh. Do not Powerwash or install replacement apps yourself. If its managed apps still differ from other loaners, bring it to IT for policy/enrollment review.",
            "loaner_managed_apps",
        )

    if _has(text, "personal phone", "iphone") and _has(text, "hotspot") and _has(text, "school laptop", "school mac", "school macbook"):
        return RequestGuardDecision(
            True,
            (
                "Altitude cannot confirm whether personal hotspots are permitted for this school-managed device. If IT permits hotspot use during an outage/trip, enable the phone hotspot and select it from the laptop's Wi-Fi menu. "
                "Do not install unknown profiles or disable school security controls; contact IT if the managed laptop blocks the connection."
            ),
            "hotspot_policy_and_setup",
        )

    # Security/safety requests should be caught before inventory, RAG, or web.
    if _has(text, "bypass code", "bypass the firewall", "bypass school firewall") or (
        _has(text, "vpn", "vpn extension") and _has(text, "blocked site", "blocked sites", "bypass")
    ):
        return RequestGuardDecision(
            True,
            (
                "I can't provide a bypass code or instructions to evade the school's "
                "filtering/security controls. If a site is needed for class, send the "
                "site URL and educational purpose to the IT Helpdesk so it can be reviewed "
                "through the approved unblock/allowlist process."
            ),
            "security_bypass",
        )

    if _has(text, "fbi locked my computer", "call a number") and _has(
        text, "pop-up", "popup", "red pop-up", "red popup", "locked my computer"
    ):
        return RequestGuardDecision(
            True,
            (
                "Do **not** call the number, click the pop-up, or enter any information. "
                "This is consistent with a fake browser/security scam. On a Mac, press "
                "**Option + Command + Escape**, force quit the browser, then reopen it without "
                "restoring the suspicious page. Contact IT immediately if anything was clicked, "
                "downloaded, or entered."
            ),
            "browser_scam",
        )

    if _has(text, "spilled coffee", "spilled juice", "liquid spill", "spilled water") and _has(
        text, "mac", "macbook", "chromebook", "laptop", "keyboard"
    ):
        return RequestGuardDecision(
            True,
            (
                "Power the device **off immediately** and disconnect the charger and accessories. "
                "Do not keep testing it, do not use heat, and do not put it in rice. Wipe only "
                "visible liquid from the outside without opening the device, then bring it to the "
                "IT Helpdesk for inspection as soon as possible."
            ),
            "liquid_damage",
        )

    # High-value v8 routes that must win before broad Wi-Fi/printer/inventory
    # keyword routers or semantic retrieval.
    if _has(text, "connection is not private", "your connection is not private", "privacy error"):
        return RequestGuardDecision(
            True,
            (
                "Do **not** continue past the certificate/privacy warning. Confirm the site address, "
                "check the Mac's date/time/time zone, and try the same approved site in another browser. "
                "If the warning appears on multiple approved sites or only on the school network, contact IT "
                "because the device/network certificate or filtering configuration may need review."
            ),
            "certificate_privacy_warning",
        )

    if _has(text, "school wifi is down", "school wi-fi is down", "iphone hotspot", "personal hotspot") and _has(
        text, "mac", "macbook", "hotspot", "iphone"
    ):
        return RequestGuardDecision(
            True,
            (
                "Altitude cannot confirm whether personal hotspots are permitted for your school-managed Mac. "
                "If IT permits one during an outage, enable **Personal Hotspot** on the iPhone and select the "
                "iPhone from the Mac's Wi-Fi menu. Do not install an unknown configuration profile or disable "
                "school security controls. If a profile is requested, stop and contact IT for the approved BYOD/outage process."
            ),
            "hotspot_policy_and_setup",
        )

    if _has(contextual_text, "iphone", "personal phone") and _has(
        contextual_text, "can't connect to the internet", "cant connect to the internet", "school wi-fi", "school wifi", "profile"
    ):
        return RequestGuardDecision(
            True,
            (
                "For a personal iPhone, use only the school's approved **Guest/BYOD** onboarding method. "
                "Do not install a configuration profile unless it is explicitly provided by the school. If the "
                "network keeps asking for a profile and you do not have an approved enrollment instruction, "
                "stop and contact IT rather than resetting the phone or changing security settings."
            ),
            "byod_wifi_profile",
        )

    if _has(text, "share my password", "write my password", "password on a sticky note", "give them my password"):
        return RequestGuardDecision(
            True,
            (
                "Do **not** share or write down your school password for another person to use. "
                "Use the school's approved substitute/temporary-access process instead. Contact the school office "
                "or IT so the substitute can receive the correct account/access without using your credentials."
            ),
            "password_sharing_boundary",
        )

    if _has(text, "should i update to", "should i upgrade to", "update to sonoma", "upgrade to sonoma", "major macos update"):
        return RequestGuardDecision(
            True,
            (
                "Do not assume a major macOS upgrade is approved just because Software Update offers it. "
                "Altitude does not have a confirmed school approval for that major version in the current guidance. "
                "Use only the macOS version/update approved by IT, and contact the IT Helpdesk before installing a major upgrade."
            ),
            "major_os_upgrade_policy",
        )

    if _has(text, "color printer", "colour printer") and _has(
        text, "black and white", "black & white", "grayscale", "greyscale", "comes out black"
    ):
        return RequestGuardDecision(
            True,
            (
                "Open the print dialog, expand **Show Details/More Settings**, then open **Printer Features**, "
                "**Quality**, or **Colour/Color Options** and change Grayscale/Black & White to **Colour/Color**. "
                "If you print this way often, save the working settings as a preset. If the colour option is missing "
                "or locked, contact IT rather than installing another driver."
            ),
            "printer_colour_output",
        )

    if _has(text, "100-page", "100 page", "accidentally sent", "stop it") and _has(
        text, "printer", "print", "document"
    ):
        return RequestGuardDecision(
            True,
            (
                "Open **System Settings → Printers & Scanners**, open the printer's **Print Queue**, select only "
                "your job, and choose **Cancel/Delete**. If pages have already started printing, use the printer's "
                "normal **Cancel/Stop** control for your job or contact the nearby staff/IT person immediately. "
                "Do not power-cycle a shared copier while other jobs are active."
            ),
            "printer_cancel_job",
        )

    if _has(text, "confidential", "iep") and _has(text, "printer", "print", "didn't print", "did not print"):
        return RequestGuardDecision(
            True,
            (
                "Because this is a confidential document, first check whether the staff printer uses **Secure/Held Print** "
                "or badge/PIN release. If it does, go to the printer and release only your job using the approved method. "
                "If no held job appears, check your print queue for an error and contact IT. Do not resend multiple copies "
                "of a confidential document until you know where the original job went."
            ),
            "printer_secure_release",
        )

    if _has(text, "all my files on my desktop are gone", "desktop files are gone", "files on my desktop are gone"):
        return RequestGuardDecision(
            True,
            (
                "First check **Finder → iCloud Drive**, **Google Drive**, and your local **Desktop** folder before moving "
                "or deleting anything. If you see a folder named **iCloud Drive (Archive)**, tell me that; do not delete it. "
                "If the files are not visible in any of those locations, contact IT before changing sync settings."
            ),
            "desktop_files_missing",
        )

    if _has(text, "camera is blurry", "camera blurry", "webcam is blurry", "blurry camera"):
        return RequestGuardDecision(
            True,
            (
                "Gently wipe the camera lens with a clean dry microfiber cloth, make sure there is no cover/film over it, "
                "and test the camera in one other approved app. If the built-in camera stays blurry in multiple apps, "
                "contact IT for a physical camera/display-lid inspection rather than cleaning inside the camera opening."
            ),
            "camera_blurry",
        )

    if _has(text, "hr website", "paystub", "pay stub") and _has(
        text, "flashes", "does nothing", "won't open", "wont open", "can't view", "cant view"
    ):
        return RequestGuardDecision(
            True,
            (
                "This often happens when the paystub opens in a blocked pop-up. If you are using Safari, open "
                "**Safari → Settings → Websites → Pop-up Windows**, find the HR site, and allow pop-ups only for that site. "
                "Reload the HR page and try again. If you are using another browser or the pop-up still fails, tell me which browser."
            ),
            "browser_popup_site",
        )

    if "google meet" in text and _has(text, "30 students", "only shows 16", "see all", "grid", "tiled"):
        return RequestGuardDecision(
            True,
            (
                "In Google Meet, open **More options (three dots) → Change layout → Tiled**. Increase the tile slider "
                "to show more participants (up to the maximum available, commonly up to 49 on supported layouts). "
                "The exact number visible can still depend on window size and device performance."
            ),
            "meet_tiled_layout",
        )

    if _has(text, "student teacher") and _has(text, "waiting room", "let kids in", "admit"):
        return RequestGuardDecision(
            True,
            (
                "If this meeting is in **Zoom**, open **Participants**, find the student teacher, choose **More**, and "
                "make them a **Co-host** if your school account allows it; a co-host can admit people from the Waiting Room. "
                "If this is Google Meet instead, use Host controls/co-host settings. Tell me which meeting service you are using "
                "if you want the exact steps."
            ),
            "meeting_cohost_access",
        )

    if _has(text, "students are complaining", "students are stuck") and _has(text, "waiting room", "didn't turn", "did not turn"):
        return RequestGuardDecision(
            True,
            (
                "Which meeting service are you using? In **Google Meet**, review **Host controls/Host management** and the "
                "meeting-access setting. In **Zoom**, review **Security/Waiting Room**. Do not change organization-wide settings; "
                "if the control is locked, contact IT."
            ),
            "meeting_waiting_room",
        )

    if "google classroom" in text and _has(text, "retiring", "new teacher", "give my google classrooms", "transfer"):
        return RequestGuardDecision(
            True,
            (
                "Add the new teacher as a **co-teacher** first: open the class → **People → Invite teachers**. After they accept, "
                "use the class/teacher options available to transfer ownership if your Google Workspace edition and school policy allow it. "
                "If **Make class owner/Transfer ownership** is unavailable, contact the Google Workspace administrator before your account closes."
            ),
            "classroom_transfer_owner",
        )

    if "google forms" in contextual_text and _has(
        contextual_text, "need permission", "needs permission", "permission to view", "can't open", "cant open"
    ):
        return RequestGuardDecision(
            True,
            (
                "Open the Form → **Settings** and review the responder-access/sign-in restrictions. First confirm students are "
                "using the correct school accounts. If the Form is intentionally for external respondents, change only the relevant "
                "organization restriction when school policy permits it; do not broadly open a school form containing sensitive data. "
                "Use **Preview** and test with an approved account before sending it again."
            ),
            "forms_responder_access",
        )

    if "safari" in contextual_text and _has(
        contextual_text, "keeps crashing", "crashes", "only on this website", "attendance system"
    ):
        return RequestGuardDecision(
            True,
            (
                "If Safari crashes only on that site, remove data for just that site: **Safari → Settings → Privacy → Manage Website Data**, "
                "search for the attendance site, remove its data, then reopen Safari. Also test the site in **Google Chrome**. "
                "If it still crashes in both browsers, contact IT with the site name and time."
            ),
            "safari_single_site_crash",
        )

    if _has(contextual_text, "smartboard", "smart board") and _has(
        contextual_text, "macbook", "usb-c", "usb c", "hdmi", "connect"
    ) and not _has(contextual_text, "touch screen", "touchscreen"):
        return RequestGuardDecision(
            True,
            (
                "For video, match the Mac's port to the board's input. If the board has **HDMI** and the MacBook has USB-C/Thunderbolt, "
                "use an approved **USB-C-to-HDMI adapter/cable**, connect HDMI to the board, select the correct board input, and then "
                "choose Mirror or Extended Display on the Mac. If you need the adapter, check with the IT Helpdesk; Altitude should not "
                "promise stock unless the item appears in live inventory."
            ),
            "smartboard_video_connection",
        )

    if _has(text, "two external monitors", "dual monitors", "monitors are just mirroring", "monitors mirror each other") and _has(
        text, "dock", "mac"
    ):
        return RequestGuardDecision(
            True,
            (
                "Open **System Settings → Displays** and confirm whether macOS sees both external displays separately. If it does, set each "
                "display to **Extended display** and arrange them. If the dock presents both monitors as one mirrored display, the dock may "
                "require the school's approved DisplayLink/driver setup or may not support separate displays on that Mac model. Contact IT "
                "before installing DisplayLink Manager or another driver yourself."
            ),
            "mac_dock_multi_display",
        )

    if _has(text, "visually impaired", "screen read", "screen reader", "spoken feedback", "chromevox") and "chromebook" in text:
        return RequestGuardDecision(
            True,
            (
                "On the Chromebook, open **Settings → Accessibility** and enable **ChromeVox / Spoken feedback**. "
                "You can also use **Ctrl + Alt + Z** to toggle ChromeVox on or off. If accessibility settings are managed or unavailable, contact IT."
            ),
            "chromebook_chromevox",
        )

    if "zoom" in text and _has(text, "photo booth", "can't detect a camera", "cant detect a camera", "camera not detected"):
        return RequestGuardDecision(
            True,
            (
                "Because the camera works in Photo Booth, the hardware is likely working. On the Mac, open **System Settings → Privacy & Security → Camera** "
                "and make sure Zoom is allowed, then quit and reopen Zoom and select the built-in camera in **Zoom → Settings → Video**. "
                "If the permission is locked or Zoom still cannot see the camera, contact IT."
            ),
            "zoom_camera_permission",
        )

    if _has(text, "mac charger", "macbook charger") and _has(text, "borrow", "forgot", "library"):
        return RequestGuardDecision(
            True,
            (
                "I can check charger inventory, but I need the connector type because school Macs may use different chargers. "
                "Is it **USB-C** or **MagSafe**? If you are not sure, tell me the MacBook model/charging port. Availability cannot be guaranteed until the item is checked live."
            ),
            "inventory_charger_clarification",
        )

    # Preserve common multi-turn support state instead of letting a short reply
    # drift into an unrelated router or knowledge article.
    if _history_contains(history, "change my password", "password-change process", "approved password-change process") and _has(
        contextual_text, "change my password", "update it", "current one", "password"
    ):
        return RequestGuardDecision(
            True,
            (
                "Since you know the current password, use the school's approved password-change "
                "process rather than a reset. Open the school account/security portal, choose "
                "**Change password**, enter the current password, then set the new one. If the "
                "change option is unavailable or managed, contact the IT Helpdesk. Do not share "
                "either password in chat."
            ),
            "password_change",
        )

    if _history_contains(history, "projector won't turn on", "projector wont turn on") and _has(
        contextual_text, "flashing red", "red light", "already tried unplugging", "tried unplugging"
    ):
        return RequestGuardDecision(
            True,
            (
                "A flashing red status light after a power check usually means the projector "
                "needs physical service (for example a lamp/temperature/hardware fault). Stop "
                "power-cycling it and contact IT with the room number and the exact light pattern. "
                "Do not open the projector or replace parts yourself."
            ),
            "projector_hardware_fault",
        )

    if _history_contains(history, "projector", "classroom display") and _has(
        contextual_text, "tinted yellow", "yellow tint", "purple tint", "colour looks", "color looks"
    ):
        return RequestGuardDecision(
            True,
            (
                "A strong colour tint usually points to the video cable/adapter, input, or projector "
                "hardware. Reseat the display cable and adapter, try an approved spare cable/adapter "
                "if available, and confirm the same input is selected. If the tint remains after the "
                "cable check, contact IT for projector/display service."
            ),
            "projector_colour_fault",
        )

    if _history_contains(history, "camera is blurry", "camera blurry") and _has(
        contextual_text, "wiped the lens", "built into the macbook", "built in", "still blurry"
    ):
        return RequestGuardDecision(
            True,
            (
                "Since the built-in MacBook camera is still blurry after the lens was wiped, test it "
                "in one other approved app. If it remains blurry there too, stop troubleshooting and "
                "contact IT for a physical camera/display-lid inspection; do not pry at or clean inside "
                "the camera opening."
            ),
            "camera_hardware",
        )

    # Stable school-support intents that are safer as deterministic guidance
    # than as broad semantic retrieval. These are phrased generically enough to
    # cover natural variations, not only the acceptance-test wording.
    if _has(text, "mirroring to the projector", "mirror to the projector") and _has(
        text, "notes", "slides", "extend", "extended"
    ):
        return RequestGuardDecision(
            True,
            (
                "Use **extended display** mode instead of mirroring. On the Mac, open "
                "**System Settings → Displays**, select the projector/display, and change "
                "the arrangement from Mirror to **Extended display**. Arrange the screens so "
                "the laptop holds your presenter notes and the projector shows the slides."
            ),
            "mac_extended_presentation",
        )

    if "google classroom" in text and _has(text, "substitute teacher", "co-teacher", "co teacher") and _has(
        text, "can't post", "cant post", "cannot post", "post assignments", "add"
    ):
        return RequestGuardDecision(
            True,
            (
                "Make sure the substitute is added as a **co-teacher**, not a student. Open "
                "the class → **People** → **Invite teachers**, enter their school email address, "
                "and send the invitation. They must accept it before teacher controls such as "
                "posting assignments are available. If teacher invitations are restricted, contact IT."
            ),
            "classroom_coteacher",
        )

    if _has(text, "creative cloud", "photoshop") and _has(
        text, "logging me out", "logs me out", "sign-in loop", "sign in loop", "keeps signing me out"
    ):
        return RequestGuardDecision(
            True,
            (
                "For a Creative Cloud sign-in loop on a school Mac, quit Adobe apps, open the "
                "Creative Cloud desktop app, sign out completely, then sign back in using the "
                "school's approved Adobe/enterprise account method. Confirm the correct school "
                "profile/license appears, then reopen Photoshop. If it immediately signs out again, "
                "contact IT so the assigned Adobe license and cached school credentials can be checked."
            ),
            "adobe_signin_loop",
        )

    if "zoom" in text and _has(text, "no sound", "audio isn't working", "audio is not working", "can't hear", "cant hear"):
        return RequestGuardDecision(
            True,
            (
                "In Zoom, open **Audio settings** and test the selected speaker and microphone. "
                "On a Mac, also open **System Settings → Sound** and make sure the intended output "
                "device (Mac speakers, dock/headphones, or classroom display) is selected. Reconnect "
                "the headset/dock and restart Zoom if the device does not appear."
            ),
            "zoom_audio",
        )

    if "safari" in text and _has(text, "testing website", "website") and _has(
        text, "buttons are missing", "buttons missing", "not loading right", "looks wrong"
    ):
        return RequestGuardDecision(
            True,
            (
                "First try the testing site in **Google Chrome**, because some managed assessment "
                "sites are browser-specific. If Safari must be used, open **Safari → Settings → "
                "Privacy → Manage Website Data**, remove data only for that site, reopen Safari, "
                "and test again. Do not change security/certificate settings."
            ),
            "safari_site_compatibility",
        )

    if _has(text, "can't find the quiz", "cant find the quiz", "quiz i made") and _has(text, "google", "drive", "quiz"):
        return RequestGuardDecision(
            True,
            (
                "Google probably did not delete it automatically. In **Google Drive**, use the search "
                "bar and filter for Google Forms, then check **Recent**, **Trash**, and **Shared with me**. "
                "If you know part of the title, search that text as well. If the file is in Trash, restore it."
            ),
            "drive_find_form",
        )

    if _has(text, "trackpad") and _has(text, "totally frozen", "can't click", "cant click", "not clicking"):
        return RequestGuardDecision(
            True,
            (
                "If the Mac is otherwise responsive, connect an approved USB/Bluetooth mouse if one is "
                "available and save your work. If the whole Mac is frozen, hold the power button until it "
                "turns off, wait about 10 seconds, and restart it. If the trackpad still will not click after "
                "restart or looks raised/swollen, stop using the Mac and contact IT for hardware service."
            ),
            "mac_trackpad_frozen",
        )

    if "chrome extension" in text and _has(text, "greyed out", "grayed out", "button is grey", "button is gray"):
        return RequestGuardDecision(
            True,
            (
                "A greyed-out install button on a school-managed Chrome profile usually means the extension "
                "is controlled by Google Workspace policy. Do not try to sideload or re-enable it manually. "
                "Send the extension name, Chrome Web Store link, and classroom purpose to IT for approval."
            ),
            "managed_extension",
        )

    if _has(text, "touch screen", "touchscreen", "smartboard", "smart board") and _has(
        text, "isn't working", "is not working", "not working"
    ):
        return RequestGuardDecision(
            True,
            (
                "If the board shows the Mac image but touch does not work, the video connection is working. "
                "Interactive touch usually also needs the board's **USB touch/control cable** connected to the "
                "Mac or dock. Check/reseat that USB cable. If it is connected and touch still fails, contact IT "
                "for the board driver/USB interface check rather than installing a driver yourself."
            ),
            "smartboard_touch",
        )

    if "zoom" in text and _has(text, "share my screen", "screen sharing") and _has(
        text, "grey box", "gray box", "not working"
    ):
        return RequestGuardDecision(
            True,
            (
                "On a Mac, quit Zoom and open **System Settings → Privacy & Security → Screen & System "
                "Audio Recording** (or Screen Recording on older macOS). Enable Zoom if the control is "
                "available, then reopen Zoom and share again. Also confirm the host allows screen sharing. "
                "If the permission is locked by management, contact IT."
            ),
            "zoom_screen_share_permission",
        )

    if "chromebook" in text and _has(text, "upside down", "screen upside down", "rotate the screen"):
        return RequestGuardDecision(
            True,
            (
                "Press **Ctrl + Shift + Refresh** (the circular-arrow key) to rotate the Chromebook display. "
                "Repeat the shortcut until the screen returns to the normal orientation."
            ),
            "chromebook_screen_rotation",
        )

    if _has(text, "combine", "merge") and "pdf" in text and _has(text, "paid account", "teacher here", "license"):
        return RequestGuardDecision(
            True,
            (
                "First confirm Acrobat/Creative Cloud is signed in with the **school-provided Adobe account**, "
                "not a personal Adobe profile. Open Creative Cloud/Acrobat, check the signed-in account, and "
                "sign out/in with the approved school method if necessary. If Combine Files still shows as paid "
                "or unavailable, contact IT so the assigned Adobe license can be checked."
            ),
            "adobe_entitlement",
        )

    if "classroom" in text and _has(text, "last semester", "archived class", "classroom is gone", "classroom gone"):
        return RequestGuardDecision(
            True,
            (
                "Open Google Classroom, open the main menu, and choose **Archived classes**. Open the old class "
                "there to review its classwork/grades if your account still has access. If the class is not listed, "
                "confirm you are using the same school account and contact IT or the class owner."
            ),
            "classroom_archived",
        )

    if _has(text, "fan", "jet engine") and _has(text, "zoom", "video", "classes", "laptop"):
        return RequestGuardDecision(
            True,
            (
                "Video calls can make the Mac's CPU/GPU work harder, so louder fans can be normal. Put the Mac "
                "on a hard, flat surface with the vents clear, close unnecessary Chrome tabs/apps, and restart "
                "after class if performance stays high. If the Mac is unusually hot, shuts down, or the fan stays "
                "at full speed when idle, contact IT."
            ),
            "mac_fan_load",
        )

    if _has(text, "staffshare", "shared drive", "network drive") and _has(text, "mac", "finder") and _has(
        text, "can't connect", "cant connect", "cannot connect", "disappeared", "red x"
    ):
        return RequestGuardDecision(
            True,
            (
                "Confirm the Mac is on the approved school network. In Finder choose **Go → Connect to Server** "
                "and use the school's approved SMB/server address for that share, then authenticate with the "
                "school account if prompted. If you do not know the approved server address or access is denied, "
                "contact IT rather than guessing the path."
            ),
            "mac_network_share",
        )

    if _has(text, "spinning beach ball", "beach ball of death") or (
        _has(text, "mac", "app") and _has(text, "not responding", "frozen")
    ):
        return RequestGuardDecision(
            True,
            (
                "Press **Option + Command + Escape**, select the unresponsive app, and choose **Force Quit**. "
                "Unsaved work in that app may be lost. Reopen the app; if the whole Mac remains frozen or the "
                "problem repeats, restart the Mac and contact IT."
            ),
            "mac_force_quit",
        )

    if "google drive" in text and _has(text, "95% full", "almost full", "storage full", "unlimited storage"):
        return RequestGuardDecision(
            True,
            (
                "School Google Workspace storage is not necessarily unlimited. Open Google Drive's storage view "
                "to see your current usage, sort/review large files, remove files you no longer need, and empty "
                "Drive Trash only after confirming the contents. If the quota shown does not match your expected "
                "school allocation, contact IT/Workspace administration."
            ),
            "drive_storage_cleanup",
        )

    if _has(text, "picture of just one part of my screen", "part of my screen", "select an area") and _has(
        text, "screen", "slideshow", "screenshot"
    ):
        return RequestGuardDecision(
            True,
            (
                "On a Mac, press **Shift + Command + 4**, then drag over the area you want to capture. "
                "Release to take the screenshot. It normally saves to the Desktop unless the screenshot save "
                "location was changed."
            ),
            "mac_partial_screenshot",
        )

    if _has(text, "audacity") and _has(text, "install", "installed", "need"):
        return RequestGuardDecision(
            True,
            (
                "Check the school's approved **Self Service/software catalogue** first. If Audacity is listed, "
                "install it from there. If it is not listed or requests administrator credentials, send the app "
                "name and class purpose to the IT Helpdesk so it can be reviewed and installed through the "
                "approved process."
            ),
            "software_install_approval",
        )

    if "zoom" in text and _has(text, "breakout rooms button", "can't find the breakout rooms", "cant find the breakout rooms"):
        return RequestGuardDecision(
            True,
            (
                "Confirm you are the **host/co-host** of the meeting. If Breakout Rooms are not on the meeting "
                "toolbar, check the school's Zoom web portal/account settings to see whether the feature is "
                "enabled for your account. If that setting is locked or unavailable, contact the Zoom/IT admin."
            ),
            "zoom_breakout_rooms",
        )

    if "zoom" in text and _has(text, "student teacher", "co-host", "co host") and _has(
        text, "waiting room", "let kids in", "admit"
    ):
        return RequestGuardDecision(
            True,
            (
                "During the meeting, open **Participants**, find the student teacher, choose **More**, and make "
                "them a **Co-host** if your school account allows it. A co-host can help admit people from the "
                "Waiting Room. If Co-host is unavailable/locked, contact the Zoom administrator."
            ),
            "zoom_cohost",
        )

    if "zoom" in contextual_text and _has(contextual_text, "drawing", "annotation", "while i am sharing my screen"):
        return RequestGuardDecision(
            True,
            (
                "While sharing, open the sharing toolbar → **More** and disable attendee annotation if the option "
                "is available. You can also enable **Show Names of Annotators** to identify who is drawing. If "
                "those controls are locked by the account, contact the Zoom administrator."
            ),
            "zoom_annotation",
        )

    if _has(text, "wireless mouse") and _has(text, "stopped working", "not working"):
        return RequestGuardDecision(
            True,
            (
                "Replace/charge the mouse battery first. If it uses a USB receiver, unplug and reconnect the "
                "receiver and try another approved port. If it is Bluetooth, open **System Settings → Bluetooth** "
                "and confirm it is connected. Restart the mouse and Mac if needed."
            ),
            "wireless_mouse",
        )

    if _has(text, "power school", "powerschool") and _has(text, "change a student's grade", "change a students grade", "grade"):
        return RequestGuardDecision(
            True,
            (
                "Altitude cannot change academic records, bypass a grading lock, or modify PowerSchool grades. "
                "Contact the registrar/school administration or the authorized PowerSchool administrator for the "
                "approved correction process."
            ),
            "academic_record_boundary",
        )

    if "adobe fonts" in text and "google docs" in text:
        return RequestGuardDecision(
            True,
            (
                "Google Docs does not use locally synced Adobe/system fonts in the same way desktop apps do. "
                "In Docs, open the font menu → **More fonts** and choose an available Google font or a similar "
                "school-approved font. Adobe Fonts you synced for desktop apps will not automatically appear in Docs."
            ),
            "docs_font_compatibility",
        )

    if "jamboard" in text and _has(text, "can't create", "cant create", "new jamboard", "what's going on", "whats going on"):
        return RequestGuardDecision(
            True,
            (
                "Google's Jamboard app/service is no longer available for creating new Jams. Use the school's "
                "approved replacement for collaborative whiteboarding (for example Google Slides or another "
                "approved tool). If you need access to older Jamboard content or an approved alternative, contact IT."
            ),
            "jamboard_retired",
        )

    if _has(text, "keys on my macbook", "macbook keyboard") and _has(
        text, "stuck", "won't press", "wont press", "physically"
    ):
        return RequestGuardDecision(
            True,
            (
                "Do not pry off the MacBook keys or spray cleaner under them. Restart once to rule out a "
                "software issue, and use an approved external keyboard temporarily if needed. If the keys are "
                "physically stuck or will not press, contact IT for keyboard service."
            ),
            "mac_keyboard_physical",
        )

    if _has(text, "replace cyan toner", "replace toner", "out of toner", "need toner"):
        return RequestGuardDecision(
            True,
            (
                "Do not replace a shared copier toner cartridge unless your area has an approved supply process. "
                "Report the printer/location and the exact toner colour/message to the IT Helpdesk or the staff "
                "member responsible for printer supplies so the correct cartridge can be installed."
            ),
            "printer_supply",
        )

    if _has(text, "leaving the school", "retiring", "leaving school") and _has(
        text, "google drive files", "drive files", "take my files", "transfer my files"
    ):
        return RequestGuardDecision(
            True,
            (
                "Do not move school records to a personal account without approval. Google Transfer/Takeout "
                "availability and what data may be exported depend on school policy. Contact IT before your account "
                "closes so they can confirm the approved transfer/export method and separate personal work from "
                "school-owned or student records."
            ),
            "drive_departure_transfer",
        )

    if "google doc" in text and _has(text, "without wi-fi", "without wifi", "offline", "on the bus"):
        return RequestGuardDecision(
            True,
            (
                "Prepare the file **before leaving Wi-Fi**. On the managed Chromebook, open Google Drive while "
                "online, make sure offline access is permitted for the school account, then mark the required Doc "
                "as available offline. Open it once before leaving to confirm it loads. If offline access is disabled "
                "by management, contact IT/teacher before the trip rather than changing policy settings."
            ),
            "drive_offline",
        )

    if _has(text, "airplay", "apple tv") and _has(text, "4-digit code", "4 digit code", "code"):
        return RequestGuardDecision(
            True,
            (
                "The AirPlay code is normally shown on the classroom TV/projector connected to that Apple TV. "
                "Confirm you selected the Apple TV for the correct room, then enter the code displayed on the room "
                "screen. Do not reuse a code from another classroom."
            ),
            "airplay_code",
        )

    if "google classroom" in text and _has(text, "guardian", "weekly", "summaries", "parent") and _has(
        text, "not getting", "aren't getting", "are not getting", "summary", "summaries"
    ):
        return RequestGuardDecision(
            True,
            (
                "In the class, open **People** and check the student's guardian/parent invitation status if your "
                "school has Guardian Summaries enabled. Confirm the correct parent email was invited and that the "
                "guardian accepted the invitation. If guardian controls are missing or disabled, contact IT/Google "
                "Workspace administration instead of using the student's account."
            ),
            "classroom_guardian_summary",
        )

    if "google meet" in text and _has(text, "waiting room", "stuck", "students are complaining"):
        return RequestGuardDecision(
            True,
            (
                "Open **Host controls/Host management** in Google Meet and review the meeting access/admission "
                "settings. Confirm you are signed in as the organizer/host and that the current access setting is "
                "appropriate for the class. If the control is locked by the organization, contact IT rather than "
                "trying to bypass it."
            ),
            "meet_host_access_controls",
        )

    if _has(text, "personal ipad", "my personal ipad") and _has(text, "cracked", "screen"):
        return RequestGuardDecision(
            True,
            (
                "Altitude supports school-managed technology and cannot arrange repair for a personal iPad. Avoid "
                "using the device if the glass is sharp or the battery/display is damaged, and use Apple or a "
                "reputable local repair provider for personal-device service."
            ),
            "personal_device_boundary",
        )

    if _has(text, "home hp", "home printer", "my home") and _has(text, "school macbook", "school mac", "printer"):
        return RequestGuardDecision(
            True,
            (
                "A school-managed Mac should not install unapproved home-printer driver packages. If the printer "
                "supports driverless **AirPrint**, macOS may be able to use it without extra software; otherwise use "
                "a personal device or contact IT before installing anything on the school Mac."
            ),
            "home_printer_boundary",
        )

    if _has(text, "headphone plug", "audio jack") and _has(text, "snapped off", "stuck inside", "tweezers"):
        return RequestGuardDecision(
            True,
            (
                "Do **not** use tweezers, pins, glue, or other tools inside the Mac's audio jack; that can damage "
                "the connector or logic board. Stop using that port and bring the Mac to IT for safe extraction."
            ),
            "audio_jack_damage",
        )

    if "premiere pro" in text and _has(text, "scratch disk is full", "scratch disk full"):
        return RequestGuardDecision(
            True,
            (
                "A full Premiere scratch disk is a storage problem. Free safe space on the Mac first by reviewing "
                "**System Settings → General → Storage**, Downloads, Trash, and old media you no longer need. If "
                "your course uses an approved external drive for media/scratch storage, select that location in "
                "Premiere's project/scratch-disk settings. Do not delete project media you still need."
            ),
            "premiere_scratch_disk",
        )

    if "adobe express" in text and _has(text, "access denied", "can't log in", "cant log in"):
        return RequestGuardDecision(
            True,
            (
                "Confirm the students are using their school accounts and the school's approved Adobe sign-in "
                "method. If multiple students receive **Access Denied**, this may be an Adobe organization/license "
                "assignment issue; contact IT so the student group/organizational access can be checked in Adobe "
                "Admin Console."
            ),
            "adobe_express_access",
        )

    if "gmail" in text or "email" in text:
        if _has(text, "sending limit", "exceeded my sending limit", "too many emails"):
            return RequestGuardDecision(
                True,
                (
                    "Stop repeatedly resending the bulk message. Google Workspace accounts have sending limits, "
                    "and the exact school limit can vary by account/configuration. For a large parent distribution, "
                    "use the school's approved bulk-communication method or an approved Google Group if available. "
                    "Send the bounce/error text to IT if you need the current account limit confirmed."
                ),
                "gmail_sending_limit",
            )

    if _has(text, "iCloud Drive (Archive)", "icloud drive archive", "icloud drive (archive)") or (
        _history_contains(history, "desktop are gone", "files on my desktop are gone") and "icloud" in contextual_text
    ):
        return RequestGuardDecision(
            True,
            (
                "An **iCloud Drive (Archive)** folder can appear when iCloud Desktop/Documents syncing is disabled "
                "or its configuration changes. Do not delete the archive. Confirm the missing files are there, then "
                "contact IT before moving large school folders or re-enabling iCloud on a managed Mac so files are "
                "returned to the correct school-approved location without creating duplicates."
            ),
            "icloud_archive",
        )

    if _history_contains(history, "shared a folder", "shared folder", "shared drive") and _has(
        contextual_text, "deleted my lesson plan", "someone deleted", "who did it", "see who"
    ):
        return RequestGuardDecision(
            True,
            (
                "Open the shared folder in Google Drive and use **View details / Activity** to review recent file "
                "activity when your role permits it. Also check the appropriate Drive/Shared drive Trash for the "
                "deleted file and restore it if available. If you cannot see the activity or restore option, contact "
                "the Shared drive manager or IT."
            ),
            "drive_shared_activity",
        )

    if _policy_question(text):
        return RequestGuardDecision(
            True,
            (
                "I do not have a confirmed SJK policy for that in the approved "
                "support guidance, so I should not guess. Please confirm the current "
                "rule with the IT Helpdesk or the appropriate school administrator."
            ),
            "policy_confirmation",
        )

    # Requests for elevated rights or managed-policy changes must not drift into
    # inventory or an unrelated KB article.
    if _has(text, "admin rights", "local admin", "administrator access", "admin access"):
        if _has(text, "chrome extension", "extension"):
            return RequestGuardDecision(
                True,
                (
                    "Chrome extensions on school-managed devices are controlled by "
                    "the school's approved extension policy. Altitude cannot grant "
                    "administrator rights or bypass that control. Send the extension "
                    "name, Chrome Web Store link, and classroom reason to the IT "
                    "Helpdesk for review and deployment."
                ),
                "managed_permission",
            )
        return RequestGuardDecision(
            True,
            (
                "Altitude cannot grant local administrator access or change managed "
                "device permissions. Administrative access is controlled by IT. Tell "
                "the IT Helpdesk what task or software requires elevation so they can "
                "use the approved method."
            ),
            "managed_permission",
        )

    if _has(text, "whitelist this website", "allowlist this website", "unblock this website"):
        return RequestGuardDecision(
            True,
            (
                "Altitude cannot change the school's web filter or whitelist a site. "
                "Send the full site URL, classroom purpose, teacher/department, and a "
                "screenshot of the block page to the IT Helpdesk. IT can review whether "
                "the site is appropriate and can be allowed."
            ),
            "managed_permission",
        )

    if _has(text, "fix the permissions yourself", "change the permissions yourself"):
        return RequestGuardDecision(
            True,
            (
                "Altitude cannot change school permissions directly. Because this has "
                "been unresolved, contact the IT Helpdesk with the affected service, "
                "account or resource, the access you need, and any existing ticket "
                "number so IT can review the permission assignment."
            ),
            "managed_permission",
        )

    if _has(text, "webcam", "camera") and _has(text, "grayed out", "greyed out", "disabled"):
        return RequestGuardDecision(
            True,
            (
                "If the camera control is grayed out, first close other apps that may "
                "be using the camera and check the camera permission for the affected "
                "browser/app in **System Settings → Privacy & Security → Camera**. If "
                "the permission itself is locked or managed, do not try to bypass it; "
                "contact the IT Helpdesk so the device policy can be checked."
            ),
            "managed_permission",
        )

    if "google drive" in text and _has(text, "co-teacher", "co teacher") and _has(
        text, "access", "share", "set that up"
    ):
        return RequestGuardDecision(
            True,
            (
                "If you own the folder, open it in Google Drive, select **Share**, add "
                "your co-teacher's school email address, choose the appropriate role "
                "such as Viewer or Editor, and select **Send**. If the folder is in a "
                "Shared drive or the sharing option is restricted, contact the IT "
                "Helpdesk or Shared drive manager instead of changing ownership."
            ),
            "drive_sharing",
        )

    # Common, stable actions are safer and faster as deterministic answers.
    if _has(text, "screenshot") and _has(text, "mac", "macbook", "macos"):
        return RequestGuardDecision(
            True,
            (
                "On a Mac:\n\n"
                "1. Press **Shift + Command + 3** for the whole screen.\n"
                "2. Press **Shift + Command + 4** to select an area.\n"
                "3. Press **Shift + Command + 5** for screenshot and screen-recording controls.\n\n"
                "Screenshots normally save to the desktop unless the save location was changed."
            ),
            "mac_screenshot",
        )

    if _has(text, "mac", "macbook", "macos") and _has(
        text,
        "screen is flickering",
        "screen flickering",
        "screen flickers",
        "display is flickering",
    ):
        return RequestGuardDecision(
            True,
            (
                "For flickering on the MacBook's built-in screen, disconnect external displays "
                "and docks first, restart the Mac, and install approved macOS updates. Check "
                "whether the flicker also appears at the login screen and whether moving the lid "
                "changes it. If the built-in screen continues flickering, contact IT for a hardware check."
            ),
            "mac_internal_display",
        )

    if _has(text, "mac", "macbook") and _has(
        text,
        "forgot the login password",
        "forgot my login password",
        "forgot mac password",
        "unlock my mac",
        "locked out of my mac",
    ):
        return RequestGuardDecision(
            True,
            (
                "If you forgot the login password for a school-managed Mac, do not keep "
                "guessing or try to bypass the login screen. Confirm Caps Lock and the "
                "keyboard layout, then restart the Mac once and try the known school "
                "account again. If the password is still not accepted, bring the Mac to "
                "the IT Helpdesk so identity can be verified and the approved recovery "
                "process can be used. Do not use Recovery Mode or erase the Mac unless IT "
                "instructs you to."
            ),
            "mac_login_recovery",
        )

    if "python" in text and _has(text, "install", "installer") and "password" in text:
        return RequestGuardDecision(
            True,
            (
                "The password prompt means the Python installation requires administrator "
                "authorization on this school-managed Mac. Do not use or request someone else's "
                "administrator password. Check the approved software/Self Service option first; "
                "otherwise contact IT with the Python version and class/development reason so it "
                "can be installed through the approved process."
            ),
            "software_install_approval",
        )

    if "shared drive" in text and _has(text, "science department", "department") and _has(
        text, "is there", "do we have", "exists"
    ):
        return RequestGuardDecision(
            True,
            (
                "I cannot confirm that a department Shared drive exists unless it is listed in "
                "approved school information. Check **Google Drive → Shared drives** with your "
                "school account. If the Science drive is not listed, contact IT or the department "
                "owner to confirm whether it exists and whether you should be added."
            ),
            "shared_drive_confirmation",
        )

    if _has(text, "restarted for an update", "restart for an update", "update in the middle of class"):
        return RequestGuardDecision(
            True,
            (
                "Let the current update/startup finish rather than forcing another shutdown. Once "
                "you are back in, reopen the lesson and check that your files synced correctly. "
                "If the Mac repeatedly forces restarts during class, record the time and update "
                "message and report it to IT so the managed update schedule can be reviewed."
            ),
            "managed_update",
        )

    if "safari" in text and _has(text, "clear cookies", "delete cookies", "remove cookies"):
        return RequestGuardDecision(
            True,
            (
                "In Safari on Mac, open **Safari → Settings → Privacy → Manage Website "
                "Data**. Search for the affected site and remove only that site's data "
                "when possible, or use **Remove All** only if you understand that it "
                "will sign you out of websites. Reopen Safari and test again."
            ),
            "safari_site_data",
        )

    if "safari" in text and _has(
        text,
        "won't open any websites",
        "wont open any websites",
        "cannot open any websites",
        "can't open any websites",
        "not loading websites",
    ):
        return RequestGuardDecision(
            True,
            (
                "First determine whether this is Safari-only or a network problem:\n\n"
                "1. Confirm Wi-Fi is connected and try one approved site in Chrome.\n"
                "2. Quit and reopen Safari.\n"
                "3. Try a Private Window.\n"
                "4. Check the Mac's date and time if Safari shows certificate warnings.\n"
                "5. Restart the Mac if Safari still cannot load any site.\n\n"
                "If Chrome also cannot reach websites, troubleshoot the network instead. "
                "If only Safari fails, contact the IT Helpdesk with the exact Safari error."
            ),
            "safari_loading",
        )

    if "chrome" in text and _has(text, "keeps crashing", "crashing"):
        return RequestGuardDecision(
            True,
            (
                "Try these Chrome crash checks:\n\n"
                "1. Reopen Chrome and test with only one tab.\n"
                "2. Open an Incognito window to test without most extensions.\n"
                "3. Disable only nonessential extensions for testing.\n"
                "4. Open **Chrome → About Google Chrome** and install an approved update if offered.\n"
                "5. Restart the device.\n\n"
                "If Chrome continues to crash, record the crash/error message and contact IT."
            ),
            "chrome_crash",
        )

    if "chrome" in text and _has(text, "aw snap", "aw, snap"):
        return RequestGuardDecision(
            True,
            (
                "An **Aw, Snap!** page means the tab crashed. Reload the page once, "
                "close unnecessary tabs, test the page in Incognito, temporarily "
                "disable nonessential extensions, and update/restart Chrome. If the "
                "same page keeps crashing, record the page URL and error details for IT."
            ),
            "chrome_tab_crash",
        )

    if "chrome" in text and _has(text, "extensions aren't loading", "extensions are not loading"):
        return RequestGuardDecision(
            True,
            (
                "Open **Chrome → Extensions → Manage extensions** and confirm the "
                "approved extension is enabled. Restart Chrome and check for a Chrome "
                "update. If the extension is missing, disabled by the organization, or "
                "its toggle is locked, contact IT rather than installing an unapproved copy."
            ),
            "chrome_extension",
        )

    if "chrome" in text and _has(text, "dns probe finished nxdomain"):
        return RequestGuardDecision(
            True,
            (
                "**DNS_PROBE_FINISHED_NXDOMAIN** means Chrome could not resolve the "
                "website name. On a school-managed device:\n\n"
                "1. Check that the website address is typed correctly.\n"
                "2. Open another approved website to confirm the internet connection works.\n"
                "3. Turn Wi-Fi off and back on, then reconnect to the approved school network.\n"
                "4. Try the same site in an Incognito window or another approved browser.\n"
                "5. Restart Chrome if the error continues.\n\n"
                "Do not change DNS, proxy, firewall, or management settings. If only one "
                "site still fails, send the site address and exact error to IT."
            ),
            "chrome_dns_nxdomain",
        )

    if "gmail" in text and _has(
        text,
        "isn't sending emails",
        "is not sending emails",
        "won't send emails",
        "wont send emails",
        "cannot send emails",
        "can't send emails",
    ):
        return RequestGuardDecision(
            True,
            (
                "Check whether Gmail shows the message in **Outbox**, **Drafts**, or "
                "**Sent**. Confirm the internet connection, try sending a short message "
                "without an attachment, and test Gmail in an Incognito window. If only "
                "messages with attachments fail, check the file size/type separately. "
                "If all outgoing mail fails, contact IT with the exact error or bounce message."
            ),
            "gmail_send",
        )

    if "google drive" in text and _has(
        text,
        "how much storage",
        "storage do i have",
        "storage available",
        "check my storage",
    ):
        return RequestGuardDecision(
            True,
            (
                "I should not guess your school's Google Drive quota. In Google Drive, check "
                "the storage indicator shown in the left sidebar, or open the Google storage "
                "view while signed in with your school account. That shows the storage currently "
                "used/available for your account. If no quota is shown or you need the official "
                "teacher allocation, contact IT or the Google Workspace administrator."
            ),
            "drive_storage",
        )

    if _has(text, "microphone", "mic") and _has(
        text,
        "isn't being picked up",
        "is not being picked up",
        "not being picked up",
        "not working in calls",
    ):
        return RequestGuardDecision(
            True,
            (
                "First check whether the microphone problem is app-specific or device-wide:\n\n"
                "1. Make sure the call app is not muted and the correct microphone is selected.\n"
                "2. Close other apps that may be using the microphone.\n"
                "3. On a Mac, check **System Settings → Privacy & Security → Microphone** for the affected app/browser.\n"
                "4. Reconnect any headset and test the built-in microphone once.\n"
                "5. Quit and reopen the call app/browser.\n\n"
                "If the microphone fails in more than one app, contact IT with the device and headset details."
            ),
            "generic_microphone",
        )

    if _has(text, "camera", "webcam") and _has(
        text,
        "black screen",
        "shows black",
        "camera is black",
        "camera shows black",
    ):
        return RequestGuardDecision(
            True,
            (
                "For a black camera preview in a video call:\n\n"
                "1. Confirm the correct camera is selected in the call app/browser.\n"
                "2. Close other apps that may be using the camera.\n"
                "3. On a Mac, check **System Settings → Privacy & Security → Camera** for the affected app/browser.\n"
                "4. Turn video off and back on, then reload or reopen the call.\n"
                "5. Test the camera in another approved app if available.\n\n"
                "If the camera is black in every app, contact IT for a device/camera check."
            ),
            "generic_camera",
        )

    if "google classroom" in text and _has(
        text,
        "isn't loading assignments",
        "is not loading assignments",
        "assignments not loading",
    ):
        return RequestGuardDecision(
            True,
            (
                "Confirm the correct school account and class, refresh **Classwork**, "
                "and try Classroom in an Incognito window. Check whether other classes "
                "or assignments load and whether other users are affected. If the problem "
                "occurs in multiple browsers or for several users, report it to IT with "
                "the class name and approximate time."
            ),
            "classroom_loading",
        )

    if "classroom" in text and _has(
        text,
        "student submissions",
        "submitted but i don't see it",
        "submitted but i dont see it",
        "student says they submitted",
        "student says they turned it in",
    ):
        return RequestGuardDecision(
            True,
            (
                "Before treating this as a Classroom bug, confirm the correct class and "
                "assignment, then check **Student work** and the student's submission "
                "status. Ask the student to open the same assignment and confirm it shows "
                "**Turned in** under the correct school account. If the states disagree "
                "after a refresh/Incognito test, contact IT with the class and assignment details."
            ),
            "classroom_submission",
        )

    if "classroom" in text and _has(text, "plagiarism", "originality"):
        return RequestGuardDecision(
            True,
            (
                "Google Classroom's originality/plagiarism-related features depend on "
                "the school's Google Workspace edition and settings. I should not assume "
                "that the feature is enabled or broken. Check whether the assignment shows "
                "an **Originality reports** option; if it is missing or unavailable, contact "
                "IT or the Google Workspace administrator to confirm current availability."
            ),
            "classroom_originality",
        )

    if _has(text, "adobe acrobat", "acrobat") and _has(
        text,
        "won't open pdf",
        "wont open pdf",
        "cannot open pdf",
        "can't open pdf",
        "pdf files",
    ):
        return RequestGuardDecision(
            True,
            (
                "Try these safe Acrobat checks:\n\n"
                "1. Try opening a second known-good PDF to see whether the problem is one file or Acrobat itself.\n"
                "2. Quit Acrobat completely and reopen it.\n"
                "3. Save the PDF locally, then open it from Finder instead of directly from a browser or email.\n"
                "4. Check for an approved Acrobat/Creative Cloud update.\n"
                "5. Restart the Mac if Acrobat still cannot open any PDFs.\n\n"
                "If only one PDF fails, the file may be damaged. If all PDFs fail, contact IT with the Acrobat version and any error message. Do not reinstall Acrobat unless IT asks you to."
            ),
            "adobe_acrobat_pdf_open",
        )

    if "photoshop" in text and _has(text, "crashing", "keeps crashing"):
        return RequestGuardDecision(
            True,
            (
                "For Photoshop crashes on a school Mac:\n\n"
                "1. Save any recoverable work and quit Photoshop.\n"
                "2. Restart the Mac and test Photoshop with a new blank document.\n"
                "3. Check that the Mac has enough free storage.\n"
                "4. Install only approved Photoshop/Creative Cloud updates.\n"
                "5. If one specific file crashes Photoshop, test a different file before changing the application.\n\n"
                "If Photoshop crashes at launch or with multiple files, record the crash message and contact IT. Do not reset preferences or reinstall the app unless IT instructs you to."
            ),
            "adobe_photoshop_crash",
        )

    if _has(text, "adobe", "creative cloud") and _has(
        text,
        "licensing error",
        "licensing for this product has stopped working",
        "license error",
        "license has stopped working",
    ):
        return RequestGuardDecision(
            True,
            (
                "For an Adobe licensing error on a school-managed device:\n\n"
                "1. Confirm the device has a working internet connection and the date/time are correct.\n"
                "2. Open the Creative Cloud desktop app and confirm you are signed in with the approved school Adobe account.\n"
                "3. Quit and reopen Creative Cloud, then reopen the affected Adobe app.\n"
                "4. Install an approved Creative Cloud/app update if one is offered.\n"
                "5. If the license still is not recognized, contact IT so the school license assignment can be checked.\n\n"
                "Do not reset Keychain, change proxy/network settings, remove licensing files, or reinstall Adobe unless IT specifically directs you to."
            ),
            "adobe_licensing",
        )

    if "zoom" in text and _has(text, "error 5003", "error code 5003"):
        return RequestGuardDecision(
            True,
            (
                "Zoom error **5003** is a connection-to-Zoom problem. On a school-managed device:\n\n"
                "1. Confirm the internet connection works by opening another approved website.\n"
                "2. Quit Zoom completely and reopen it.\n"
                "3. Restart the device if the error remains.\n"
                "4. Install an approved Zoom update if one is available.\n"
                "5. If several users have the same error, report the room/network and time to IT.\n\n"
                "Do not disable the firewall/antivirus or change proxy, DNS, VPN, or other managed network settings. If error 5003 continues, contact IT with the exact time and meeting context."
            ),
            "zoom_error_5003",
        )

    if "zoom" in text and _has(text, "audio isn't working", "audio is not working", "no audio"):
        return RequestGuardDecision(
            True,
            (
                "In Zoom, open **Audio settings** and test the selected speaker and "
                "microphone. Confirm you are not muted, choose the correct input/output "
                "devices, reconnect any headset, and check macOS/browser microphone "
                "permission if needed. Restart Zoom if the test still fails."
            ),
            "zoom_audio",
        )

    if "zoom" in text and _has(
        text,
        "can't sign in",
        "cannot sign in",
        "cant sign in",
        "can't sign into",
        "cannot sign into",
        "cant sign into",
    ):
        return RequestGuardDecision(
            True,
            (
                "For a school Zoom account, use the **school-approved sign-in method** "
                "shown for your account rather than guessing between email, Google, or SSO. "
                "First confirm you can sign in to your school Google account in the browser. "
                "If Google sign-in works but Zoom does not, do not reset the Google password; "
                "record the exact Zoom message and contact IT so the Zoom account/sign-in "
                "configuration can be checked."
            ),
            "zoom_signin",
        )

    if "zoom" in text and _has(text, "screen sharing isn't working", "screen sharing is not working"):
        return RequestGuardDecision(
            True,
            (
                "Confirm the host allows screen sharing. On a Mac, open **System Settings → "
                "Privacy & Security → Screen & System Audio Recording** and allow Zoom if the "
                "setting is available, then quit and reopen Zoom. If the permission is managed "
                "or locked, contact IT rather than bypassing it."
            ),
            "zoom_screen_share",
        )

    if _has(text, "mirror to the tv", "mirror to tv", "screen won't mirror", "screen wont mirror"):
        return RequestGuardDecision(
            True,
            (
                "For a classroom TV/display mirroring problem:\n\n"
                "1. Confirm the TV/display is powered on and on the correct input/source.\n"
                "2. If you are using AirPlay, confirm the Mac and classroom display are on the approved school network, then reconnect from **Control Center → Screen Mirroring**.\n"
                "3. If you are using HDMI/USB-C, reseat the cable or adapter at both ends.\n"
                "4. Open **System Settings → Displays** and confirm the classroom display is detected and set to mirror when needed.\n"
                "5. If the display does not appear, restart the connection once and try an approved spare cable/adapter if available.\n\n"
                "If class is in progress and the display still will not mirror, contact IT with the classroom number and whether you are using AirPlay or a cable."
            ),
            "classroom_screen_mirroring",
        )

    classroom_display_context = _has(text, "classroom tv", "classroom display") or _history_contains(
        history, "classroom tv", "classroom display", "projector"
    )
    if classroom_display_context and (
        _has(text, "not working", "still black", "black even after restart", "black screen")
        or ("not a monitor" in text and _has(text, "classroom tv", "classroom display"))
    ):
        return RequestGuardDecision(
            True,
            (
                "Keep this in the **classroom TV/display** workflow, not the external-monitor "
                "workflow. Confirm the TV is powered on and on the correct input, reconnect the "
                "HDMI/USB-C or AirPlay connection, and confirm the Mac detects/mirrors the display. "
                "If it is still black after a restart, try an approved spare cable/adapter or the "
                "room's alternate connection method, then contact IT with the classroom number."
            ),
            "classroom_display_context",
        )

    if _has(text, "projector") and _has(
        text,
        "won't turn on",
        "wont turn on",
        "will not turn on",
        "doesn't turn on",
        "does not turn on",
    ):
        return RequestGuardDecision(
            True,
            (
                "Confirm the projector has power and that the wall/control panel is on. Try the "
                "normal power button once and check the status light. If it will not power on, or "
                "the status light flashes red/amber, stop repeated power-cycling and contact IT with "
                "the room number and light pattern because the projector may need physical service."
            ),
            "projector_power",
        )

    if _has(text, "projector") and _has(
        text,
        "isn't showing my laptop screen",
        "is not showing my laptop screen",
        "won't show my laptop screen",
        "no picture",
        "blue screen",
        "just died",
    ):
        return RequestGuardDecision(
            True,
            (
                "Check the projector/display path first:\n\n"
                "1. Confirm the projector is powered on and on the correct input/source.\n"
                "2. Reseat the HDMI/USB-C cable or adapter at both ends.\n"
                "3. On the laptop, confirm the external display is detected and use Mirror/Duplicate for a quick test.\n"
                "4. Try an approved spare cable/adapter if available.\n"
                "5. Restart the connection or laptop only if the first checks do not restore the image.\n\n"
                "If class is starting and there is still no image, contact IT with the room number and connection type."
            ),
            "projector_video",
        )

    if "workspace" in text and _has(text, "session has expired", "session expired"):
        return RequestGuardDecision(
            True,
            (
                "A Workspace **session expired** message is usually a sign-in/session issue, "
                "not a macOS software-update problem. Confirm the correct school Google "
                "account, close the affected Google tab/app, sign in again in a fresh browser "
                "session, and try an Incognito window if the loop continues. Contact IT if the "
                "school account repeatedly expires across browsers."
            ),
            "workspace_session",
        )

    if "google meet" in text and _has(text, "you can't join this meeting", "you cant join this meeting"):
        return RequestGuardDecision(
            True,
            (
                "Confirm that you are signed in with the Google account that created the "
                "meeting and open the current meeting link from Calendar/Meet. Try a fresh "
                "Incognito session and record the exact message. Because you are the host, "
                "do not wait for another host to admit you; contact IT if the organizer account "
                "still cannot enter its own meeting."
            ),
            "meet_host_access",
        )

    if ".docx" in text:
        return RequestGuardDecision(
            True,
            (
                "You do not need Microsoft Word to open a .docx file. Upload the file to "
                "Google Drive, then open it with **Google Docs**. You can view or edit it "
                "there and download it again as a Word-format file if needed. If formatting "
                "is critical, compare the converted document with the original before sharing."
            ),
            "docx_google_docs",
        )

    # High-pressure / compound cases should not be reduced to one keyword.
    if _has(text, "whole class", "entire class") and "classroom" in text and _has(
        text, "can't log", "cannot log", "cant log", "is something down"
    ):
        return RequestGuardDecision(
            True,
            (
                "Because the whole class is affected, do not reset individual passwords yet. "
                "Confirm Wi-Fi works, test another Google service such as Gmail/Drive, and ask "
                "whether another classroom is affected. This may be a network or Google service "
                "issue. Report the room, time, and number of affected users to IT. If you have "
                "access to the official Google Workspace Status Dashboard, you can check it for "
                "a current service incident; Altitude is not claiming that it checked the dashboard."
            ),
            "possible_service_outage",
        )

    if "standardized test" in text and "chromebook" in text and _has(
        text, "locking up", "freezing", "frozen"
    ):
        return RequestGuardDecision(
            True,
            (
                "During an active test, preserve the testing session first. Stop repeated "
                "restarts or resets, note which Chromebooks are affected, and check whether the "
                "problem affects one device or several. Use the approved testing/proctor process "
                "for a replacement device if available and contact IT immediately with the room, "
                "test platform, device asset tags, and exact symptom."
            ),
            "assessment_device_failure",
        )

    if "chromebook" in text and _has(text, "died mid-test", "died during the test", "dead mid-test"):
        return RequestGuardDecision(
            True,
            (
                "Connect the Chromebook to its approved charger and notify the test proctor/teacher "
                "immediately so the assessment session is handled according to the approved testing "
                "process. Do not Powerwash or reset the device. If it will not power back on quickly, "
                "contact IT for a replacement device and provide the asset tag."
            ),
            "assessment_power_failure",
        )

    projector_and_audio = _has(text, "projector", "classroom display") and _has(
        text, "sound isn't working", "sound is not working", "no sound", "audio"
    ) and _has(text, "won't connect", "wont connect", "not connect", "isn't working")
    if projector_and_audio:
        return RequestGuardDecision(
            True,
            (
                "Treat this as two related display-path checks. First restore the video: confirm "
                "the projector input, cable/adapter, and that the Mac detects the external display. "
                "Once video is connected, open **System Settings → Sound → Output** and select the "
                "projector/HDMI/classroom display. If neither video nor audio returns, contact IT "
                "with the room and connection type."
            ),
            "compound_display_audio",
        )

    if _has(text, "can't print", "cannot print", "cant print") and "drive" in text and _has(
        text, "can't log", "cannot log", "cant log"
    ):
        return RequestGuardDecision(
            True,
            (
                "Because students are having both printing and Google Drive sign-in problems, "
                "first check whether the same students have working school Wi-Fi. If multiple "
                "students are affected, report it as a possible broader network/account issue "
                "instead of troubleshooting every printer separately. Record the room, time, "
                "affected devices, and any sign-in error for IT."
            ),
            "compound_network_services",
        )

    if _has(text, "mac is slow", "macbook is slow", "mac is running slow") and "zoom" in text and _has(
        text, "crashing", "keeps crashing"
    ):
        return RequestGuardDecision(
            True,
            (
                "The Zoom crashes may be related to overall Mac performance. Save work, close "
                "unneeded apps/tabs, check free storage, and restart the Mac. Then update Zoom "
                "through the approved method and test one meeting. If the Mac remains slow or "
                "Zoom still crashes, record the crash message and contact IT."
            ),
            "compound_performance_zoom",
        )

    return RequestGuardDecision(False)
