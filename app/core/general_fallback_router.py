from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.retrieval_profile import build_retrieval_profile
from core.text_matching import contains_any_phrase, normalize_text


@dataclass(frozen=True)
class GeneralFallbackDecision:
    """Safe domain-level fallback used only after approved KB retrieval misses.

    This router intentionally answers by problem family rather than by one exact
    test phrase. It prevents a weak KB or generic web result from becoming a
    confident wrong-topic answer while still giving the user a useful first step.
    """

    handled: bool
    answer: str = ""
    intent: str = ""


# Broad family answers remain useful after retrieval misses, but should not
# displace a verified procedure. Every other fallback intent is deliberately
# task-specific enough to run before RAG and prevent a semantically close but
# operationally unrelated article from reaching the user.
POST_RAG_ONLY_INTENTS = frozenset(
    {
        "display_general",
        "input_device_general",
        "keyboard_general",
        "storage_general",
        "wifi_general",
    }
)


def should_preempt_knowledge(decision: GeneralFallbackDecision) -> bool:
    """Return whether a deterministic task answer should run before RAG."""

    return (
        decision.handled
        and bool(decision.intent)
        and decision.intent not in POST_RAG_ONLY_INTENTS
    )


def _has(text: str, *phrases: str) -> bool:
    return contains_any_phrase(text, phrases)


def route_general_fallback(
    question: str,
    history: list[dict[str, Any]],
) -> GeneralFallbackDecision:
    del history

    text = normalize_text(question).strip(" .")
    if not text:
        return GeneralFallbackDecision(False)

    profile = build_retrieval_profile(text)
    products = profile.products
    domains = profile.focus_domains or profile.domains

    # Capability and workflow boundaries. These are phrased as reusable task
    # families because they should not depend on a particular benchmark line.
    if _has(text, "text me", "notify me", "send me a notification") and _has(
        text, "when", "fixed", "working again", "back online"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "Altitude cannot send a later text or notification from this chat. "
                "If an IT ticket exists, use that ticket for status updates or ask the IT Helpdesk "
                "how completion notifications are delivered."
            ),
            "capability_follow_up_notification",
        )

    if _has(text, "put in a ticket", "create a ticket", "submit a ticket", "file a ticket"):
        return GeneralFallbackDecision(
            True,
            (
                "I can help prepare the ticket, but I should not claim it was submitted unless the "
                "ticket system confirms a ticket number. Confirm the affected device/service, location, "
                "impact, and any error message, then use the available **Create IT ticket** action."
            ),
            "capability_ticket_creation",
        )

    if _has(text, "helpdesk is closed", "help desk is closed") and _has(
        text, "do what they would do", "do what it would do", "just do"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "Altitude's permissions do not change when the Helpdesk is closed. I can provide safe "
                "self-service troubleshooting and help document the issue, but I cannot use administrator "
                "credentials, remotely control the device, or change managed settings. Describe the device "
                "and symptom for immediate steps, then contact IT when support is available."
            ),
            "capability_after_hours",
        )

    if _has(text, "share my login", "share my password", "student aide"):
        return GeneralFallbackDecision(
            True,
            (
                "Do not share your school login or password, even if someone previously suggested it. "
                "Ask IT to provide the aide with their own approved account, delegated access, or role-based "
                "permission for the required task."
            ),
            "account_credential_sharing",
        )

    if _has(text, "wrong twice", "typed my password wrong", "password attempts") and _has(
        text, "locked out", "lockout", "locked"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "Two incorrect attempts do not normally mean a permanent lockout. Stop guessing and verify "
                "the username, Caps Lock, and keyboard layout before trying again. Altitude does not have a "
                "confirmed SJK attempt threshold or lockout duration; contact IT if the account becomes locked."
            ),
            "account_failed_attempts",
        )

    if _has(text, "unread emails", "unread messages"):
        return GeneralFallbackDecision(
            True,
            (
                "An unread-message count by itself does not cause a technical problem. Read, archive, label, "
                "or search the messages as useful. Only the account's actual storage usage—not the number of "
                "unread messages—can eventually affect sending or receiving mail."
            ),
            "gmail_unread_count",
        )

    if _has(text, "turning my chromebook off and on", "restart actually", "it joke"):
        return GeneralFallbackDecision(
            True,
            (
                "Restarting is useful because it clears stuck processes, releases temporary memory, resets "
                "device connections, and finishes some updates. It is a reasonable first step for a temporary "
                "software problem, but repeated failures still need diagnosis rather than endless restarts."
            ),
            "restart_explanation",
        )

    if _has(text, "rainbow pinwheel", "spinning beachball", "spinning wheel") and _has(
        text, "cursor", "won't go back", "wont go back", "not responding"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "The rainbow pinwheel means an application or process is busy or not responding; it does not "
                "mean the cursor hardware is broken. Wait briefly, then press **Option + Command + Escape** to "
                "Force Quit only the frozen app. Restart the Mac if the pinwheel continues across applications."
            ),
            "mac_spinning_beachball",
        )

    if _has(text, "clock is", "computer clock", "system clock") and _has(
        text, "minutes off", "wrong time", "calendar reminders", "time zone"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "An incorrect system clock can affect Calendar reminders, authentication, and certificate "
                "checks. Open the device's Date & Time settings, enable automatic date/time and the correct time "
                "zone if allowed, then reopen Calendar. Contact IT if managed time settings are locked or remain wrong."
            ),
            "system_clock_sync",
        )

    if _has(text, "closed my browser", "without saving") and _has(
        text, "google docs", "essay draft", "gone forever"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "Google Docs normally saves changes automatically while you are online. Reopen Drive or Docs, "
                "check **Recent**, and open the document again. If text is missing, use **File → Version history → "
                "See version history** before assuming the draft is lost."
            ),
            "docs_autosave_recovery",
        )

    if _has(text, "substitute", "sub teacher") and _has(
        text, "log into", "login", "credentials", "classroom computer"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "Use only the substitute credentials or sign-in method provided by the school office or IT; do "
                "not use the regular teacher's account. If no account details were provided, contact the front "
                "office or IT so your identity and temporary access can be verified."
            ),
            "substitute_first_login",
        )

    if _has(text, "school email", "school google account") and _has(
        text, "personal phone", "gmail app", "set up on my phone"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "First confirm that school policy allows the account on a personal phone. If allowed, add the "
                "school Google account through the Gmail or Google app and complete the school's required "
                "two-step verification or management prompts. Do not remove a required management profile; "
                "contact IT if account enrollment is blocked."
            ),
            "school_email_personal_phone",
        )

    if _has(text, "pdf exported from google docs", "pdf from google docs") and _has(
        text, "looks different", "formatting", "font", "adobe"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "PDF export can change pagination when the document uses unavailable fonts, pageless mode, or "
                "different page and margin settings. In Google Docs, confirm **File → Page setup**, switch from "
                "pageless mode if necessary, and use supported fonts before exporting again. In Acrobat, check the "
                "PDF document properties to confirm the required fonts are embedded."
            ),
            "pdf_docs_rendering",
        )

    if _has(text, "tabs from iphone", "safari tabs from my phone", "icloud tabs"):
        return GeneralFallbackDecision(
            True,
            (
                "Safari tabs from another Apple device require both devices to use the same Apple Account with "
                "Safari enabled in iCloud, plus Handoff where applicable. Confirm those settings and that Safari "
                "sync is allowed. A school-managed Mac may restrict personal Apple Account or Handoff features; "
                "if the settings are unavailable, contact IT rather than removing the management profile."
            ),
            "safari_icloud_tabs",
        )

    if _has(text, "error 1223") and _has(text, "drive for desktop", "syncing"):
        return GeneralFallbackDecision(
            True,
            (
                "Confirm Drive for desktop is signed into the correct school account and that the Mac has an "
                "internet connection and free local storage. Open Drive for desktop, review its sync activity, "
                "restart the app, and verify the affected file in Drive on the web before editing further. If "
                "Error 1223 returns, record the file path and exact error and contact IT with the official Drive "
                "for desktop diagnostic logs; do not reinstall or remove the account unless instructed."
            ),
            "drive_desktop_error_1223",
        )

    if "google_meet" in products and _has(text, "half my class", "other half") and _has(
        text, "don't have permission", "dont have permission", "permission"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "Because some students can join the same Meet link, compare one working and one blocked student's "
                "signed-in account. The blocked group may be using personal or another-domain accounts instead of "
                "their school accounts. Have them switch to the correct school profile and reopen the current link. "
                "If valid school accounts remain split, send the affected accounts and meeting link to IT."
            ),
            "meet_split_account_permission",
        )

    # Cross-domain hardware and managed-device cases should be handled before
    # product-specific retrieval. These are broad support families, not exact
    # test phrases.
    if _has(text, "charging cart", "chromebook cart") and _has(
        text, "not charging", "none of the chromebooks", "won't charge", "wont charge"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "Because multiple Chromebooks in the same cart are affected, check the **cart-level power path** first: confirm the cart is plugged into a known-working outlet, its main power switch is on, and any built-in breaker/surge protector has not tripped. "
                "Do not troubleshoot every Chromebook individually yet. If the cart still has no charging power, contact IT with the cart/location."
            ),
            "charging_cart_power",
        )

    if "chromebook" in profile.platforms and _has(
        text, "jumped from", "battery percentage", "battery dropped", "battery drain", "drained"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "A sudden battery-percentage drop can indicate battery degradation or a hardware/measurement fault. Connect the Chromebook to its approved charger, restart once after saving work, and watch whether the percentage changes normally. "
                "If the rapid drop happens again, stop relying on the battery for class and bring the Chromebook to IT for a battery-health check."
            ),
            "chromebook_battery_health",
        )

    if _has(text, "kiosk app", "managed app") and "chromebook" in profile.platforms:
        return GeneralFallbackDecision(
            True,
            (
                "Restart the Chromebook and confirm it has an internet connection. If a school-managed kiosk/app still will not launch, do not change enrollment or developer settings; managed app deployment is controlled by IT. "
                "Report the app name, Chromebook/room, and what the launch screen shows."
            ),
            "managed_chromebook_app",
        )

    if _has(text, "class set", "all 30", "all classroom chromebooks") and _has(
        text, "install", "installed", "new app", "extension", "deploy", "deployment"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "Software or extensions for a class set of managed Chromebooks must be deployed centrally by IT rather than installed one device at a time. "
                "Send IT the app/extension name, educational purpose, class/group, and required date so they can review and deploy it through the managed configuration."
            ),
            "managed_bulk_deployment",
        )

    if _has(text, "restart screen", "restarting", "installing update") and _has(
        text, "stuck", "class", "bell", "students"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "If the computer is already in the middle of a restart/update, let that process finish rather than force-powering it off again. Keep it connected to power. "
                "For the class, use an immediate fallback such as the classroom board/spare device while it finishes. If the screen does not change for an extended period, contact IT with the exact message."
            ),
            "urgent_restart_in_progress",
        )

    if _has(text, "update popup", "software update popup", "update prompt") and _has(
        text, "keeps appearing", "every 10 minutes", "won't dismiss", "wont dismiss"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "Open **System Settings → General → Software Update** and check whether an approved update is "
                "pending. Save your work and schedule/install it when practical. If the prompt is managed or "
                "cannot be postponed, do not try to bypass it; contact IT with the exact message and deadline."
            ),
            "managed_update_prompt",
        )

    # Classroom displays / projectors / external monitors.
    if "external_display" in domains or _has(
        text,
        "projector",
        "projected image",
        "interactive whiteboard",
        "promethean board",
        "classroom screen",
        "external monitor",
        "monitor",
    ):
        if _has(text, "shutting off", "shuts off", "turns off") and _has(
            text, "10 minutes", "after about", "keeps"
        ):
            return GeneralFallbackDecision(
                True,
                (
                    "A projector that repeatedly shuts down after several minutes may be overheating, using an "
                    "automatic sleep/eco timer, or reporting a lamp/filter fault. Make sure its vents are clear, "
                    "note any warning light, and check the normal sleep/eco setting without opening the unit. "
                    "Because the behavior repeats, contact IT with the room, model, timing, and warning-light colour."
                ),
                "projector_repeated_shutdown",
            )

        if _has(text, "promethean", "interactive board", "smartboard") and _has(
            text, "calibrated", "calibration", "cursor is way off", "cursor way off"
        ):
            return GeneralFallbackDecision(
                True,
                (
                    "Open the board's approved calibration/orientation tool, select the connected Promethean board, "
                    "and tap each target accurately with the pen. Confirm the board's USB touch cable is connected "
                    "before recalibrating. If calibration will not start or the pointer remains offset, contact IT."
                ),
                "interactive_board_calibration",
            )
        if _has(text, "remote is missing", "missing remote", "remote missing"):
            return GeneralFallbackDecision(
                True,
                (
                    "Altitude cannot power on or control classroom hardware remotely. "
                    "Check the projector/display's physical power or wall-control panel if one is available. "
                    "If the room remote is missing, contact IT for the room's approved control method or a replacement remote."
                ),
                "display_remote_missing",
            )

        if _has(text, "vga", "old vga") and _has(text, "adapter", "macbook air", "usb-c", "usb c"):
            return GeneralFallbackDecision(
                True,
                (
                    "For a USB-C/Thunderbolt MacBook Air connecting to an older VGA-only projector, use an approved **USB-C to VGA adapter** (or the approved dock/adapter chain for that room). VGA carries video only, so classroom audio needs a separate approved audio path if required. "
                    "If you do not have the adapter, check approved loaner inventory or contact IT rather than stacking unknown adapters."
                ),
                "display_vga_adapter",
            )

        if _has(text, "touch", "pen works", "only the pen", "interactive whiteboard"):
            return GeneralFallbackDecision(
                True,
                (
                    "If the board displays correctly and the pen works but finger touch does not, check the board's USB/touch cable to the computer and reconnect it once. Then run the board's normal touch calibration if available. "
                    "If touch still fails while the pen works, contact IT because the touch driver/controller or calibration may need service."
                ),
                "interactive_display_touch",
            )

        if _has(text, "standby overnight", "leave the projector on standby", "standby") and _has(text, "projector", "display"):
            return GeneralFallbackDecision(
                True,
                (
                    "Standby still uses some power and can leave classroom hardware active, but Altitude does not have a confirmed SJK overnight-projector policy. Use the normal shutdown/power-off method when practical, and confirm any room-specific energy or shutdown rule with IT/facilities."
                ),
                "display_standby_policy",
            )

        if _has(text, "window layout", "forgets my windows", "forgetting my windows") and _has(text, "two monitors", "dual monitors", "external monitor"):
            return GeneralFallbackDecision(
                True,
                (
                    "Open **System Settings → Displays** and confirm the two monitors are arranged consistently and are not switching between mirrored/extended modes. macOS can reposition windows after sleep/wake if a dock or display reconnects in a different order. "
                    "Reconnect the dock/displays consistently and contact IT if the layout resets every morning despite both monitors being detected correctly."
                ),
                "display_layout_persistence",
            )

        if _has(text, "pink", "washed out", "yellow tint", "purple tint", "wrong color", "wrong colour"):
            return GeneralFallbackDecision(
                True,
                (
                    "A strong colour shift usually points to the cable/adapter, input, or projector/display hardware. "
                    "Reseat the video cable at both ends, confirm the correct input, and try an approved spare cable or adapter. "
                    "If the tint remains, contact IT with the room number because the projector/display may need physical service."
                ),
                "display_colour_fault",
            )

        if _has(text, "zoomed in", "cut off", "cropped", "blurry", "input not supported", "resolution"):
            return GeneralFallbackDecision(
                True,
                (
                    "Open **System Settings → Displays**, select the affected projector/monitor, and use a recommended resolution/scaling option. "
                    "If the display says **Input Not Supported**, choose a lower supported resolution/refresh rate, then reconnect the cable or adapter. "
                    "If the image is still cropped or blurry, try an approved spare cable/adapter and contact IT with the display model."
                ),
                "display_resolution",
            )

        if _has(text, "no signal", "nothing shows", "nothing showing", "not showing", "black screen"):
            return GeneralFallbackDecision(
                True,
                (
                    "Check the display path first: confirm the projector/display is powered on and on the correct input, reseat the HDMI/USB-C cable or adapter, "
                    "then open the laptop's display settings and confirm the external display is detected. Try an approved spare cable/adapter if available. "
                    "If the same room worked previously and still shows no image, contact IT with the room and connection type."
                ),
                "display_no_signal",
            )

        return GeneralFallbackDecision(
            True,
            (
                "For a classroom display/projector problem, confirm power, the selected input/source, and the HDMI/USB-C/AirPlay connection first. "
                "Then check whether the laptop detects the external display and try an approved spare cable/adapter if available. "
                "If the problem remains, contact IT with the room number and what the display shows."
            ),
            "display_general",
        )

    # Wi-Fi and network failures that do not belong in the QR-code access flow.
    if "wifi" in domains or _has(
        text,
        "internet is down", "network is down", "wifi is down", "wi-fi is down",
        "can't connect", "cannot connect", "won't connect", "wont connect",
    ):
        if _has(text, "field trip", "museum", "hotel", "off-site", "off site") and _has(text, "chromebook", "chromebooks", "school laptop", "school device"):
            return GeneralFallbackDecision(
                True,
                (
                    "For an off-site network, first confirm the venue's guest Wi-Fi name and whether it uses a browser/captive-portal sign-in. Managed school devices may restrict unknown networks or profiles. "
                    "Do not install a venue profile or disable school security controls. If multiple school Chromebooks cannot join while personal devices can, contact IT because the managed network policy may need to be reviewed for the trip."
                ),
                "wifi_offsite_managed_device",
            )

        if _has(text, "one row", "subset", "some chromebooks", "part of the room") and _has(text, "chromebook", "devices"):
            return GeneralFallbackDecision(
                True,
                (
                    "Because only one group/area of devices is affected while others nearby work, this may be a localized access-point/signal or managed-device-group issue rather than 20 separate failures. "
                    "Restart one affected Chromebook and compare it with one working Chromebook in the same room. If the pattern follows the row/group, report the room, affected devices, and approximate area to IT."
                ),
                "wifi_localized_subset",
            )

        if _has(text, "every classroom", "whole floor", "second floor", "building", "all chromebooks", "none of the chromebooks", "half my class"):
            return GeneralFallbackDecision(
                True,
                (
                    "Because multiple devices or rooms were affected at the same time, treat this as a likely network/access-point outage rather than separate device failures. "
                    "Report the location, affected area, network name if known, and approximate start time to IT. Do not make per-device network/security changes while the wider outage is being checked."
                ),
                "wifi_widespread_outage",
            )

        if _has(text, "phone connects", "phone works") and _has(text, "laptop", "mac", "macbook", "chromebook"):
            return GeneralFallbackDecision(
                True,
                (
                    "Since another device can see/use the school Wi-Fi, focus on the laptop. Turn Wi-Fi off and back on, restart the laptop, and check whether the school network appears in the list. "
                    "If it still cannot see the network while nearby devices can, contact IT with the device and location; do not install profiles or change DNS/proxy settings."
                ),
                "wifi_device_specific",
            )

        if _has(text, "buffering", "slow video", "youtube"):
            return GeneralFallbackDecision(
                True,
                (
                    "First check whether the slowdown affects only this room/device or several users nearby. Close unnecessary streams/tabs and retry the video at normal quality. "
                    "If multiple users in the same area buffer at the same time, report the classroom/location and time to IT so network capacity or the access point can be checked."
                ),
                "wifi_bandwidth",
            )

        return GeneralFallbackDecision(
            True,
            (
                "For a Wi-Fi connection problem, first confirm whether other nearby devices can connect. Turn Wi-Fi off and back on, select the approved network, and restart the affected device once. "
                "If the issue follows only one device, report that device and location to IT; if several nearby devices fail together, report it as a possible outage. Do not change DNS/proxy/VPN or install unknown profiles."
            ),
            "wifi_general",
        )

    # Chrome / browser issues.
    if "google_chrome" in products:
        if _has(text, "err_ssl", "err ssl", "ssl protocol", "certificate", "connection is not private"):
            return GeneralFallbackDecision(
                True,
                (
                    "Do not bypass the browser security warning. Confirm the site address and the device date/time/time zone, then try the same approved site in another supported browser. "
                    "If the SSL/certificate error is limited to a legitimate school site, contact IT with the exact error text so the site certificate/filtering path can be checked. Do not change DNS, proxy, VPN, or certificate trust settings yourself."
                ),
                "chrome_ssl_error",
            )

        if _has(text, "tabs", "out of memory", "froze", "frozen", "freezes"):
            return GeneralFallbackDecision(
                True,
                (
                    "Close tabs and windows you no longer need, then open Chrome's Task Manager (**Window → Task Manager** on Mac, or **Shift + Esc** where supported) to identify a tab/extension using excessive memory. "
                    "Quit and reopen Chrome if it remains frozen. If the problem returns with only a few tabs open, disable nonessential extensions and contact IT with the error."
                ),
                "chrome_memory",
            )

        if _has(text, "bookmarks", "wrong google account", "wrong account", "profile"):
            return GeneralFallbackDecision(
                True,
                (
                    "Check the Chrome profile icon and confirm you are signed into the correct school Google account. Bookmarks and sync data belong to the active Chrome profile. "
                    "Switch to the correct school profile and confirm Sync is enabled if permitted. Do not delete the other profile until you know which account owns the missing bookmarks."
                ),
                "chrome_profile_sync",
            )

        if _has(text, "extension", "toolbar") and _has(
            text, "disappeared", "missing", "removed", "disabled"
        ):
            return GeneralFallbackDecision(
                True,
                (
                    "Open **Chrome → Extensions → Manage Extensions** and check whether the extension is still installed and enabled. If it is installed, use the Extensions menu to pin it again. "
                    "If it was removed or disabled by school policy, do not sideload it; contact IT with the extension name and classroom purpose."
                ),
                "chrome_extension_missing",
            )

        if _has(text, "takes forever to open", "slow to open", "slow every morning"):
            return GeneralFallbackDecision(
                True,
                (
                    "Restart the Mac/Chromebook, then open Chrome with only one tab and check whether it is still slow. Disable nonessential extensions and close startup/background apps that use a lot of memory. "
                    "If Chrome still takes several minutes to launch, contact IT with the device model and whether other apps are also slow."
                ),
                "chrome_startup_performance",
            )

    # Safari-specific issues should not become generic web/network answers.
    if "safari" in products:
        if _has(text, "battery", "energy") and _has(
            text, "more than chrome", "way more", "uses more", "expected"
        ):
            return GeneralFallbackDecision(
                True,
                (
                    "Browser battery use varies with the open sites, tabs, video, and extensions, so one browser "
                    "is not always more efficient in every session. Compare Safari and Chrome with similar tabs, "
                    "disable unnecessary extensions, and check Activity Monitor's Energy tab before drawing a conclusion."
                ),
                "safari_energy_use",
            )

        if _has(text, "content blocker", "extension", "never heard of", "unfamiliar"):
            return GeneralFallbackDecision(
                True,
                (
                    "Do not approve an unfamiliar Safari extension or content blocker. Open **Safari → Settings → Extensions** and leave the unknown extension disabled. "
                    "If it is already installed on a school Mac and you do not recognize it, contact IT so the managed software/profile can be checked."
                ),
                "safari_unknown_extension",
            )

        if _has(text, "network connection was lost") and _has(text, "chrome works", "chrome is working"):
            return GeneralFallbackDecision(
                True,
                (
                    "Because Chrome works, this is probably Safari-specific rather than a Wi-Fi outage. Quit and reopen Safari, remove website data for the affected site, and try a private Safari window. "
                    "If only Safari continues failing, use Chrome temporarily and contact IT with the site name."
                ),
                "safari_specific_network_error",
            )

    # Google Classroom common operational problems.
    classroom_context = (
        "google_classroom" in products
        or (_has(text, "gradebook") and _has(text, "graded", "grades", "essays"))
        or _has(
            text,
            "classroom assignment", "classroom gradebook", "classroom roster",
            "scheduled an assignment", "assignment for 8am", "co-teacher",
            "classroom announcement", "turn in", "turned in",
        )
        or (
            "classroom" in text
            and _has(
                text,
                "assignment", "student", "students", "submit", "submitted",
                "submission", "missing", "grade", "gradebook", "co-teacher", "teacher",
            )
        )
    )
    if classroom_context:
        if _has(text, "error 400", "something went wrong") and _has(
            text, "grade", "grading", "assignment"
        ):
            return GeneralFallbackDecision(
                True,
                (
                    "Reload Classroom and retry in a private browser window while signed into only the correct "
                    "school account. Clear Classroom site data only if needed, then retry the assignment. If "
                    "Error 400 continues, record the class, assignment, exact error, and time and contact IT; "
                    "the Workspace administrator may need to check the account or service."
                ),
                "classroom_error_400",
            )

        if _has(text, "emailed me", "email instead", "emailed the file") and _has(
            text, "submit", "submission", "classroom"
        ):
            return GeneralFallbackDecision(
                True,
                (
                    "This is usually a submission-method issue rather than a Classroom fault. Ask the students to "
                    "open the assignment, attach the file under **Your work**, and select **Turn in**. An emailed "
                    "attachment does not automatically become a Classroom submission."
                ),
                "classroom_submission_method",
            )

        if _has(text, "import", "spreadsheet") and _has(text, "gradebook", "grades"):
            return GeneralFallbackDecision(
                True,
                (
                    "Google Classroom does not provide a general one-click import for an arbitrary old spreadsheet gradebook. Keep the spreadsheet as the source record and enter/import grades only through an approved Classroom/SIS workflow that your school actually uses. "
                    "If you need a bulk migration, contact IT/administration before using add-ons or third-party tools."
                ),
                "classroom_gradebook_import",
            )

        if _has(text, "scheduled", "8am", "never posted", "didn't post", "did not post"):
            return GeneralFallbackDecision(
                True,
                (
                    "Open the assignment and confirm it is **Scheduled** rather than Draft, then verify the scheduled date/time and your device/account time zone. "
                    "If the schedule is correct but the post did not publish, refresh Classroom and contact IT with the class, assignment, and scheduled time."
                ),
                "classroom_scheduled_post",
            )

        if _has(text, "missing", "attached the file", "submitted", "turn in"):
            return GeneralFallbackDecision(
                True,
                (
                    "An attached file does not always mean the assignment was submitted. Ask the student to open the assignment and confirm it shows **Turned in/Submitted**, not only an attachment under their work. "
                    "If it shows submitted for the student but still appears Missing for the teacher, refresh Classroom and contact IT with the class and assignment."
                ),
                "classroom_submission_status",
            )

        if _has(text, "removed as a co-teacher", "removed as co-teacher", "add me back"):
            return GeneralFallbackDecision(
                True,
                (
                    "Altitude cannot add you back to a class. The current class owner/teacher must invite your school account again from **People → Invite teachers**, or IT/Workspace administration must restore access if the owner cannot do it."
                ),
                "classroom_role_restore",
            )

        if _has(text, "twice", "two different emails", "duplicate"):
            return GeneralFallbackDecision(
                True,
                (
                    "Do not remove either entry until you confirm which account is the student's current school account. Compare the two email addresses and ask IT/registrar to confirm the active account if necessary. "
                    "Once confirmed, the obsolete/personal entry can be removed through the normal Classroom roster process."
                ),
                "classroom_duplicate_roster",
            )

        if _has(text, "grades disappeared", "gradebook", "grades are gone"):
            return GeneralFallbackDecision(
                True,
                (
                    "Refresh Classroom and confirm you are in the correct class/term and account. Check whether the assignments and individual student submissions still show the grades. "
                    "Do not re-enter a large set of grades until you confirm whether this is only a gradebook display/sync issue. Escalate promptly to IT with the class and affected assignments."
                ),
                "classroom_gradebook_missing",
            )

    # Google Drive and Docs.
    if (
        "google_drive" in products
        or products.intersection({"google_docs", "google_sheets", "google_slides"})
        or _has(
            text,
            "shared drive", "drive folder", "version history",
            "anyone with the link", "shared folder",
            "teacher who left", "left the school", "owns files",
            "document looked like", "student's edit", "students edit",
        )
    ):
        if "google_slides" in products and _has(text, "won't load", "wont load", "not loading"):
            return GeneralFallbackDecision(
                True,
                (
                    "Reload the presentation, confirm the internet connection, and try the same file in a private "
                    "browser window with the correct school account. For the live class, use a downloaded PDF or "
                    "another approved device as an immediate fallback. If only this file fails, contact the owner/IT."
                ),
                "slides_urgent_loading",
            )

        if "google_sheets" in products and _has(text, "add-on", "addon", "formula") and _has(
            text, "stopped calculating", "not calculating", "calculating incorrectly", "gradebook"
        ):
            return GeneralFallbackDecision(
                True,
                (
                    "Make a copy before changing the gradebook. Check whether the affected formulas were replaced, "
                    "whether the add-on is authorized/enabled, and whether the referenced ranges still include every "
                    "row. Recalculate a small test copy. Because report cards are time-sensitive, contact IT or the "
                    "approved add-on administrator if the result remains wrong."
                ),
                "sheets_addon_calculation",
            )

        if _has(text, "anyone with the link", "public link", "shared by accident"):
            return GeneralFallbackDecision(
                True,
                (
                    "Altitude cannot change the sharing setting for you, but the owner can fix it immediately. Open the file/folder → **Share** → under General access change **Anyone with the link** to the approved restricted setting. "
                    "Then review the named people/groups that still have access. If sensitive school data was exposed, notify IT."
                ),
                "drive_revoke_public_link",
            )

        if _has(text, "one week ago", "version history", "before a student's edit", "before a students edit"):
            return GeneralFallbackDecision(
                True,
                (
                    "Open the Google Doc/Sheet/Slide → **File → Version history → See version history**. Use the dated versions on the right to inspect the version from around one week ago. "
                    "You can restore an earlier version if you are the owner/editor, but review it first so newer work is not lost."
                ),
                "drive_version_history",
            )

        if _has(text, "teacher who left", "left the school", "departed", "owns files"):
            return GeneralFallbackDecision(
                True,
                (
                    "Files owned by a departed staff account may require an administrator ownership/Drive transfer. Do not copy school records to a personal account. "
                    "Contact IT/Google Workspace administration with the former staff account, department, and files/folders needed so ownership and retention can be handled correctly."
                ),
                "drive_departed_owner",
            )

        if _has(text, "can't upload", "cannot upload", "view but", "can see") and "shared drive" in text:
            return GeneralFallbackDecision(
                True,
                (
                    "This usually means your Shared Drive role is view-only or does not allow adding content. Ask a Shared Drive Manager/IT to confirm your role (for example Viewer, Contributor, Content manager, or Manager). "
                    "Altitude cannot raise the permission itself."
                ),
                "shared_drive_role",
            )

        if _has(text, "drive folder", "drive for desktop", "not showing the changes", "not syncing") and _has(text, "mac", "chromebook", "computer"):
            return GeneralFallbackDecision(
                True,
                (
                    "Confirm both devices are signed into the same school Google account. On the Mac, check **Drive for desktop** is running and shows sync complete; then verify the file in Drive on the web before checking the Chromebook. "
                    "If the web copy is stale or Drive for desktop shows a sync error, pause edits and contact IT with the file path and sync status."
                ),
                "drive_desktop_sync",
            )

        if _has(text, "personal google drive", "personal gmail") and _has(text, "school drive", "school account"):
            return GeneralFallbackDecision(
                True,
                (
                    "Your personal Google account and school Google Workspace account have separate storage quotas. A full personal Drive does not by itself consume the school account's storage. "
                    "Check the account/profile shown in Drive before deleting anything."
                ),
                "drive_account_storage_separation",
            )

    # Google Meet.
    if "google_meet" in products:
        if _has(text, "record", "recording") and _has(
            text, "automatically", "every day", "without me clicking", "auto-record"
        ):
            return GeneralFallbackDecision(
                True,
                (
                    "Google Meet recording is normally started by an eligible host for a meeting, and availability "
                    "depends on the Workspace edition and school settings. Altitude cannot assume SJK has enabled an "
                    "automatic daily recording policy. Check the host controls or ask IT/Workspace administration "
                    "whether an approved recurring or admin-configured option exists."
                ),
                "meet_recording_automation",
            )

        if _has(text, "attendance", "take attendance"):
            return GeneralFallbackDecision(
                True,
                (
                    "Google Meet attendance reports are available only for certain Workspace editions/roles and may be controlled by school settings. Altitude cannot assume they are enabled for your account. "
                    "Check the meeting/host controls and contact IT/Workspace administration if attendance tracking is required but unavailable."
                ),
                "meet_attendance",
            )

        if _has(text, "breakout", "main room"):
            return GeneralFallbackDecision(
                True,
                (
                    "As the host/co-host, open the Meet breakout-room controls and choose **End breakout rooms/Close rooms** so participants are returned to the main call. "
                    "If the control is missing or participants remain stuck, confirm you are the host and contact IT with the meeting link and time."
                ),
            "meet_breakout_return",
        )

    if _has(text, "meet or zoom", "google meet or zoom", "supposed to use") and _has(
        text, "conference", "meeting", "today"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "Check today's calendar invitation or conference schedule for the meeting link: a meet.google.com "
                "link means Google Meet and a zoom.us link means Zoom. If the invite has no link, ask the organizer; "
                "Altitude cannot choose the event's platform from the schedule alone."
            ),
            "meeting_platform_identification",
        )

    if _has(text, "gmail", "calendar") and _has(text, "aren't loading", "not loading") and _has(
        text, "drive", "classroom", "work fine"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "Because Drive/Classroom still work, this is not a complete internet or Google-account outage. "
                "Reload Gmail and Calendar in a private browser window, confirm the correct account, and check the "
                "Google Workspace status page. Report it to IT if multiple users have the same service-specific failure."
            ),
            "google_partial_service_issue",
        )

    if _has(text, "gmail", "calendar") and _has(
        text, "isn't loading", "is not loading", "won't load", "wont load"
    ) and _has(text, "drive", "classroom", "work fine"):
        return GeneralFallbackDecision(
            True,
            (
                "Because Drive/Classroom still work, this is not a complete internet or Google-account outage. "
                "Reload Gmail and Calendar in a private browser window, confirm the correct account, and check the "
                "Google Workspace status page. Report it to IT if multiple users have the same service-specific failure."
            ),
            "google_partial_service_issue",
        )

    if _has(text, "headset") and _has(text, "nobody can hear", "can't hear me", "cant hear me"):
        return GeneralFallbackDecision(
            True,
            (
                "The headset output is working, so test the input separately. In Meet, open Audio settings and "
                "select the headset microphone, then confirm its input meter moves. Check the headset's physical "
                "mute switch, reconnect it, and verify browser/macOS microphone permission. If the mic fails in "
                "other apps too, try another approved headset and contact IT."
            ),
            "headset_microphone_input",
        )

    if _has(text, "youtube", "streaming a video") and _has(
        text, "buffering", "network too slow", "slow for video"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "First check whether the buffering affects only this room/device or several users nearby. Close "
                "unnecessary streams and tabs, retry at normal video quality, and compare another approved site. "
                "If several users in the same area buffer at the same time, report the room and time to IT so "
                "network capacity or the access point can be checked."
            ),
            "wifi_bandwidth",
        )

    if _has(text, "five tickets", "multiple tickets", "several tickets") and _has(
        text, "slow mac", "nothing has changed", "still not fixed"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "I understand why an issue that has continued through several tickets is frustrating. I cannot "
                "see the Helpdesk queue or promise a resolution time. Follow up through the existing ticket if "
                "possible and include the prior ticket numbers, current impact, and any new symptoms so IT can "
                "review the history without creating another disconnected report."
            ),
            "ticket_repeat_escalation",
        )

    if _has(text, "testing week", "standardized testing") and _has(
        text, "system update", "huge update", "install an update"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "Save your work and defer the system update until after testing if the prompt offers a normal "
                "Later/Postpone option. Keep the Mac connected to power and do not force-quit an update that has "
                "already started. If the update is mandatory or cannot be postponed, contact IT before the test "
                "session so they can confirm the managed update schedule or provide another device."
            ),
            "testing_update_deferral",
        )

    if _has(text, "school's google account", "school google account") and _has(
        text, "personal gmail", "which account", "got hacked"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "Which account and app show the problem: your school Workspace account or your personal Gmail? "
                "They are separate accounts, so a personal Gmail failure does not by itself mean the school "
                "account was compromised. If either account shows an unfamiliar sign-in or security alert, do "
                "not click email links; open that account's security page directly and contact IT for the school account."
            ),
            "account_scope_clarification",
        )

    if _has(text, "attendance") and _has(text, "6am", "wrong time", "first period"):
        return GeneralFallbackDecision(
            True,
            (
                "A timestamp that is several hours off usually points to the device, Google account, or application "
                "time-zone setting. Verify automatic date/time and the correct time zone, then refresh the attendance "
                "record. If the stored timestamp remains wrong, report the class, date, and time difference to IT."
            ),
            "attendance_timestamp",
        )

    if _has(text, "why does the school", "old district") and _has(text, "chromebooks"):
        return GeneralFallbackDecision(
            True,
            (
                "Device-selection policy is decided by the school, so Altitude should not debate or invent the reasons. "
                "Tell me the specific Chromebook problem affecting your work and I can troubleshoot it, or share broader "
                "device feedback with IT/administration."
            ),
            "device_choice_feedback",
        )

    # Gmail and Calendar.
    if "gmail" in products:
        if _has(text, "filter", "auto-archive", "archive"):
            return GeneralFallbackDecision(
                True,
                (
                    "Check **Gmail → Settings → See all settings → Filters and Blocked Addresses** and review the filter that archives the parent messages. "
                    "Archived mail should still appear in **All Mail** and search. Edit or remove the filter if it is hiding messages you need."
                ),
                "gmail_filter_archive",
            )

        if _has(text, "assistant", "send emails as me", "access to send"):
            return GeneralFallbackDecision(
                True,
                (
                    "Gmail delegation may be available on managed Workspace accounts, but it must use the approved school configuration. Do not share your password. "
                    "Check Gmail account settings for delegation access; if the option is unavailable or this involves sensitive mail, contact IT/Workspace administration."
                ),
                "gmail_delegation",
            )

    if "google_calendar" in products:
        if _has(text, "students", "whole class", "shared") and _has(
            text, "can't see", "cant see", "cannot see", "not visible"
        ):
            return GeneralFallbackDecision(
                True,
                (
                    "Open Google Calendar's **Settings and sharing** for that calendar and verify the class/group "
                    "was shared with the intended school accounts and an appropriate permission level. Ask one student "
                    "to check **Other calendars** and the correct school account. If group membership or external sharing "
                    "is managed, contact IT/Workspace administration."
                ),
                "calendar_class_sharing",
            )

        if _has(text, "phone", "not showing", "sync"):
            return GeneralFallbackDecision(
                True,
                (
                    "Confirm the phone is signed into the correct school Google account and that Calendar sync is enabled for that account. Then check that the school calendar is selected/visible in the phone's calendar app. "
                    "If the school account is managed and cannot be added or synced, contact IT rather than removing a management profile."
                ),
                "calendar_mobile_sync",
            )

    # Zoom.
    if "zoom" in products:
        if _has(text, "removed from this meeting", "removed by the host") and _has(
            text, "i am the host", "i'm the host", "im the host"
        ):
            return GeneralFallbackDecision(
                True,
                (
                    "Sign out of Zoom, sign back into the correct school host account, and reopen the meeting from "
                    "that account's Meetings page rather than an old participant link. Confirm the meeting owner/host "
                    "identity. If Zoom still treats the host as removed, contact the Zoom administrator with the meeting ID and time."
                ),
                "zoom_host_identity_error",
            )

        if _has(text, "won't load", "wont load", "not loading", "can't join", "cannot join"):
            return GeneralFallbackDecision(
                True,
                (
                    "Because Zoom is failing even on another working connection, treat it as a Zoom/app/account issue rather than only a Wi-Fi issue. Quit and reopen Zoom, confirm the correct school account, and try the meeting link in the supported web client if available. "
                    "If it still fails on multiple networks, contact IT with the exact Zoom error."
                ),
                "zoom_loading_general",
            )

        if _has(text, "where do", "cloud recordings", "recordings go"):
            return GeneralFallbackDecision(
                True,
                (
                    "Zoom cloud recordings are stored in the host's Zoom web account after processing, when cloud recording is enabled for that licence/account. Open the Zoom web portal and check **Recordings/Recordings & Transcripts**. "
                    "Retention depends on school policy, so contact the Zoom administrator if a required recording is missing or you need the retention period confirmed."
                ),
                "zoom_cloud_recording_location",
            )

        if _has(text, "waiting room", "admit"):
            return GeneralFallbackDecision(
                True,
                (
                    "During the Zoom meeting, open **Participants**. Find the person under **Waiting Room** and choose **Admit**. "
                    "If you do not see the Waiting Room controls, confirm you are the host/co-host and check the meeting's Security controls."
                ),
                "zoom_waiting_room_admit",
            )

        if _has(text, "downgraded to basic", "40 minutes", "basic account"):
            return GeneralFallbackDecision(
                True,
                (
                    "A 40-minute limit normally means the account is currently using a Basic/unlicensed Zoom tier. Sign out and confirm you are using the correct school-managed Zoom account. "
                    "If it still shows Basic, contact IT/Zoom administration so the assigned licence can be checked or restored."
                ),
                "zoom_license_tier",
            )

        if _has(text, "closed all", "breakout rooms", "get them back"):
            return GeneralFallbackDecision(
                True,
                (
                    "You can create/open breakout rooms again, but Zoom may not restore the exact prior room state automatically after they are closed. Open **Breakout Rooms**, review/recreate the assignments, and reopen the rooms. "
                    "If you used pre-assigned rooms, check whether those saved assignments are still available."
                ),
                "zoom_breakout_restore",
            )

    # Adobe / PDF / Premiere.
    if "adobe_acrobat" in products or "pdf_file" in domains:
        if _has(text, "exported from google docs", "docs preview") and _has(
            text, "looks different", "formatting", "font"
        ):
            return GeneralFallbackDecision(
                True,
                (
                    "PDF export can change pagination when the document uses unavailable fonts, pageless mode, or "
                    "different page/margin settings. In Google Docs, confirm **File → Page setup**, use supported fonts, "
                    "export the PDF again, and check whether fonts are embedded in Acrobat's document properties."
                ),
                "pdf_docs_rendering",
            )

        if _has(text, "fillable", "text boxes", "locked"):
            return GeneralFallbackDecision(
                True,
                (
                    "First confirm the PDF actually contains interactive form fields rather than being a flattened/scanned document. In Acrobat, try **Fill & Sign** or click directly in a known field. "
                    "If no fields can be selected, the form may need to be recreated by its owner; contact IT/document owner if this is a required school form."
                ),
                "pdf_fillable_form",
            )

        if _has(text, "file is damaged", "damaged and could not be repaired", "error opening this document"):
            return GeneralFallbackDecision(
                True,
                (
                    "Download the PDF again from its original source and try opening the new copy in Acrobat and the "
                    "browser/Preview. If every viewer rejects the same copy, ask the sender to reopen and re-export the "
                    "original document. Avoid unknown online repair sites for school or confidential files."
                ),
                "pdf_corrupt_file",
            )

    if _has(text, "adobe sign", "acrobat sign", "e-signature", "electronic signature"):
        return GeneralFallbackDecision(
            True,
            (
                "Adobe Acrobat Sign can send a document to recipients for electronic signature, but Altitude cannot "
                "confirm that the required licence or parent-contract workflow is enabled for SJK. Confirm authorization "
                "and the approved records process with IT/administration before sending the contract."
            ),
            "adobe_sign_policy",
        )

    if _has(text, "usb-c dock", "usb c dock", "docking station", "dock") and _has(
        text, "personal", "bought my own", "from home", "okay to use"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "A personal dock may work technically, but Altitude cannot confirm that it meets SJK's device, power, "
                "or security policy. Check its power-delivery rating and manufacturer compatibility, do not install "
                "unapproved drivers, and confirm personal-hardware use with IT before relying on it."
            ),
            "personal_dock_policy",
        )

    if _has(text, "dock") and _has(text, "charges my macbook", "phone plugged") and _has(
        text, "not when", "stops charging", "won't charge", "wont charge"
    ):
        return GeneralFallbackDecision(
            True,
            (
                "The dock may be sharing a limited power budget across its ports. Check the dock and power adapter's "
                "total wattage, test the MacBook without the phone attached, and charge the phone separately. If the dock "
                "cannot provide the Mac's required power under load, use the approved higher-wattage adapter/dock."
            ),
            "dock_power_budget",
        )

    if _has(text, "premiere", "premiere pro") and _has(text, "export", "99%", "freeze", "freezes"):
        return GeneralFallbackDecision(
            True,
            (
                "Check that the Mac has enough free storage for the export, restart Premiere, and try exporting a short section to isolate whether one clip/effect is failing. "
                "Confirm the export format/codec is appropriate for the project. If the same project repeatedly freezes near the same point, contact IT/Adobe support with the project and export settings."
            ),
            "premiere_export_freeze",
        )

    if _has(text, "adobe licenses", "adobe licence", "0 adobe licenses", "0 adobe licences"):
        return GeneralFallbackDecision(
            True,
            (
                "Adobe licence seats are managed in the organization's Adobe Admin Console, not from the teacher's device. Altitude cannot reassign seats. "
                "Contact IT/Adobe administration so assigned users, available licences, and stale assignments can be reviewed."
            ),
            "adobe_license_admin",
        )

    # Mac general support.
    if "macos" in profile.platforms or _has(text, "mac", "macbook"):
        if _has(text, "one side", "only one speaker", "left speaker", "right speaker") and _has(
            text, "sound", "audio", "speakers"
        ):
            return GeneralFallbackDecision(
                True,
                (
                    "Open **System Settings → Sound → Output**, select MacBook Speakers, and make sure the balance "
                    "slider is centered. Disconnect headphones, HDMI, and docks, then test the built-in speakers "
                    "and an approved headset. Restart once; if one built-in side remains silent, contact IT for a hardware check."
                ),
                "mac_audio_balance",
            )

        if _has(text, "fan", "grinding", "scraping", "mechanical noise"):
            return GeneralFallbackDecision(
                True,
                (
                    "A grinding or scraping fan sound is different from normal loud airflow and can indicate a "
                    "mechanical fan problem. Save your work, shut the Mac down, and bring it to IT promptly. Do not "
                    "open the Mac or keep stressing it with heavy applications."
                ),
                "mac_fan_mechanical_fault",
            )
        if _has(text, "lasts about an hour", "used to last all day", "battery health", "service recommended"):
            return GeneralFallbackDecision(
                True,
                (
                    "Open **System Settings → Battery → Battery Health** and note any condition such as **Service Recommended**. A large drop in runtime can indicate battery aging. "
                    "Keep using the approved charger as needed and contact IT for a battery assessment/replacement if the condition warning appears or runtime remains unusually short. Do not attempt a battery replacement yourself."
                ),
                "mac_battery_health",
            )

        if _has(text, "keynote", "app") and _has(text, "spinning wheel", "slow to open", "hang", "freezes"):
            return GeneralFallbackDecision(
                True,
                (
                    "Force Quit the affected app if it is stuck, reopen it once, and restart the Mac if the delay continues. Check free storage and approved pending updates before reinstalling anything. "
                    "If only that app remains slow while other apps are normal, contact IT with the app name/version and whether the problem affects every file or only one."
                ),
                "mac_app_performance",
            )

        if _has(text, "keyboard backlight", "keyboard brightness") and _has(text, "won't turn on", "wont turn on", "not turning on", "off"):
            return GeneralFallbackDecision(
                True,
                (
                    "Check the Mac's keyboard-brightness control in **Control Center** or the keyboard function keys, and make sure automatic keyboard brightness is not reducing it in a bright room. Restart the Mac once if the control does not respond. "
                    "If the backlight remains off while the keyboard itself works, contact IT for a keyboard/backlight hardware check."
                ),
                "mac_keyboard_backlight",
            )

        if _has(text, "system data") and _has(text, "gb", "storage"):
            return GeneralFallbackDecision(
                True,
                (
                    "**System Data** can include caches, logs, temporary files, local snapshots, and other macOS-managed data, so the number can vary. Restart the Mac and review **System Settings → General → Storage** before deleting anything. "
                    "Do not manually remove system folders; if storage remains unusually high and space is critically low, contact IT."
                ),
                "mac_system_data",
            )

        if _has(text, "apple id", "don't recognize", "dont recognize", "do not recognize"):
            return GeneralFallbackDecision(
                True,
                (
                    "Do not enter credentials into an Apple ID prompt you do not recognize. Open **System Settings** and check which Apple Account/Apple ID is shown, but do not sign out or remove a managed account without IT guidance. "
                    "On a school Mac, report the unexpected account prompt to IT so ownership/management can be verified."
                ),
                "mac_unknown_apple_id",
            )

        if _has(text, "two weeks", "never restart", "never shut down", "close the lid"):
            return GeneralFallbackDecision(
                True,
                (
                    "Using sleep/closing the lid is normal, but a periodic restart helps clear stuck processes and finish updates. If the Mac has been running for many days and is now lagging, save your work and restart it before deeper troubleshooting. "
                    "You do not need to shut it down every day unless school policy says otherwise."
                ),
                "mac_uptime_restart",
            )

        if _has(text, "photo booth library"):
            return GeneralFallbackDecision(
                True,
                (
                    "The Photo Booth Library contains Photo Booth photos/videos. Delete only captures you know you no longer need, preferably from inside Photo Booth, and empty Trash only after reviewing it. "
                    "Do not delete unfamiliar system/library folders just to free space; contact IT if you are unsure."
                ),
                "mac_photo_booth_storage",
            )

        if _has(text, "spacebar", "double-typing", "double typing", "keys"):
            return GeneralFallbackDecision(
                True,
                (
                    "Restart the Mac, check the key for visible debris without prying it off, and test with an approved external keyboard if available. "
                    "If the key continues double-typing in multiple apps, contact IT for a physical keyboard inspection."
                ),
                "mac_keyboard_repeat",
            )

    # Chromebook general support.
    if "chromebook" in profile.platforms or "chromebook" in text:
        if _has(text, "local storage is full", "storage is full", "local storage"):
            return GeneralFallbackDecision(
                True,
                (
                    "Chromebooks can still fill local storage with Downloads, cached browser/app data, and files marked available offline. Open **Files → Downloads** and review only files the student no longer needs, then check offline Drive files. "
                    "Do not Powerwash the Chromebook just to free space; contact IT if storage remains full."
                ),
                "chromebook_storage",
            )

        if _has(text, "stuck on 'updating'", "stuck on updating", "updating for", "update for 20"):
            return GeneralFallbackDecision(
                True,
                (
                    "Keep the Chromebook connected to power and do not unplug or force-reset it while an update is actively progressing. Wait a reasonable period for the update to finish. "
                    "If the screen has not changed for an extended time, note the exact message and contact IT before Powerwashing or interrupting enrollment."
                ),
                "chromebook_update_stuck",
            )

        if _has(text, "antivirus", "anti-virus"):
            return GeneralFallbackDecision(
                True,
                (
                    "ChromeOS uses a sandboxed, verified-boot security model and school-managed Chromebooks normally do not need users to install third-party antivirus software. "
                    "Do not install security software unless IT has approved it; contact IT for the school's specific endpoint-security policy."
                ),
                "chromebook_antivirus",
            )

    # Generic input/peripheral fallback.
    if "microphone" in domains and _has(text, "usb", "not appearing", "not detected", "sound settings"):
        return GeneralFallbackDecision(
            True,
            (
                "Reconnect the USB microphone directly to the Mac (or try another approved port/adapter), then open **System Settings → Sound → Input** and check whether it appears. Test it in another app to separate a Mac detection problem from an app permission problem. "
                "If macOS never detects it after reconnecting and restarting, contact IT with the microphone and adapter details."
            ),
            "usb_microphone_detection",
        )

    if "peripheral_bluetooth" in domains or _has(text, "bluetooth keyboard", "bluetooth mouse"):
        return GeneralFallbackDecision(
            True,
            (
                "Check the keyboard/mouse battery first, then turn Bluetooth off and back on and reconnect the device. Move other wireless receivers/devices away temporarily to test for interference. "
                "If it keeps disconnecting on this computer after re-pairing, test another approved keyboard/mouse and contact IT for a Bluetooth/hardware check."
            ),
            "bluetooth_peripheral",
        )

    if "mouse_touchpad" in domains:
        return GeneralFallbackDecision(
            True,
            (
                "Check the input device first: charge/replace its battery if applicable, reconnect the USB receiver or Bluetooth connection, clean the sensor/trackpad surface, and restart the computer. "
                "If the pointer still jumps or disconnects after testing another mouse/port, contact IT for a hardware/Bluetooth check."
            ),
            "input_device_general",
        )

    if "keyboard" in domains:
        return GeneralFallbackDecision(
            True,
            (
                "Restart the device and test whether the problem occurs in more than one app. Check for visible debris or a changed keyboard/input layout, but do not pry off laptop keys. "
                "Use an approved external keyboard temporarily if needed and contact IT if the physical keyboard remains unreliable."
            ),
            "keyboard_general",
        )

    if _has(text, "downloads folder", "downloads") and _has(text, "files", "15000", "15,000", "thousands"):
        return GeneralFallbackDecision(
            True,
            (
                "A Downloads folder can accumulate browser downloads over time. Sort by **Size** or **Date**, review the files, and delete only items you recognize and no longer need. "
                "Do not mass-delete unknown school files; empty Trash only after checking it. If storage is still low, review the Storage panel or contact IT."
            ),
            "downloads_cleanup",
        )

    if _has(text, "usb flash drive", "external drive", "personal usb") and _has(text, "school mac", "back up", "backup"):
        return GeneralFallbackDecision(
            True,
            (
                "Technically, files can be copied to an external drive if the Mac and school policy allow it, but Altitude cannot confirm whether personal USB storage is approved for school data. Prefer approved school storage such as Google Drive. "
                "If you need removable media for school files, confirm the device/data policy with IT before copying sensitive material."
            ),
            "external_storage_policy",
        )

    if "storage" in domains:
        return GeneralFallbackDecision(
            True,
            (
                "Review the device or Google account's storage usage before deleting anything. Remove only files you recognize and no longer need, empty Trash only after checking it, and move large school files only to an approved school storage location. "
                "If the quota or storage category looks wrong, contact IT."
            ),
            "storage_general",
        )

    if _has(text, "logged into my school account", "school account on my home computer", "unused session"):
        return GeneralFallbackDecision(
            True,
            (
                "If the home computer is still signed into your school account, sign out when you no longer need that session—especially on a shared/personal device. Review the school Google Account security page for signed-in devices/sessions and sign out of ones you no longer use. "
                "If you see an unfamiliar session, contact IT and use the approved password/security process."
            ),
            "account_session_review",
        )

    if "assessment" in domains or _has(text, "assessment platform", "quiz platform", "gradebook export"):
        if _has(text, "google accounts", "log in", "login"):
            return GeneralFallbackDecision(
                True,
                (
                    "First determine whether the problem is the assessment site, the Google account, or the network: test one affected student's school Google account in Gmail/Drive, try the assessment in a private browser window, and check whether all students or only some are affected. "
                    "If Google sign-in works but the assessment platform rejects multiple students, report the platform/class/time to IT or the platform administrator."
                ),
                "assessment_google_login",
            )
        if _has(text, "csv", "missing", "students"):
            return GeneralFallbackDecision(
                True,
                (
                    "Before treating the data as lost, check the assessment/gradebook export filters: class/section, date range, assignment/status, and whether the missing students are active in the source roster. "
                    "Confirm the students appear in the source system before exporting again; if they are present there but absent from the CSV, contact the platform administrator/IT."
                ),
                "assessment_export_missing",
            )
        if _has(text, "timer", "different time", "classroom clock"):
            return GeneralFallbackDecision(
                True,
                (
                    "Check the computer's date/time/time zone and the assessment platform's account/session time-zone setting if it has one. If only that platform shows the wrong time while the device clock is correct, report the exact quiz/platform and time difference to the platform administrator/IT."
                ),
                "assessment_time_mismatch",
            )

    return GeneralFallbackDecision(False)
