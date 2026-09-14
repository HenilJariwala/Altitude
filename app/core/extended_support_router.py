from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.text_matching import contains_any_phrase, normalize_text
from core.topic_context import build_topic_context


@dataclass(frozen=True)
class ExtendedSupportDecision:
    """Deterministic answer for common school IT requests.

    These rules run before RAG so a clear, high-frequency request cannot be
    matched to an unrelated knowledge-base topic. The answers deliberately
    avoid inventing school-specific phone numbers, fees, locations, or policy
    details that are not configured in Altitude.
    """

    handled: bool
    answer: str = ""


def _has(text: str, *phrases: str) -> bool:
    return contains_any_phrase(text, phrases)


def _has_all(text: str, *groups: tuple[str, ...]) -> bool:
    return all(contains_any_phrase(text, group) for group in groups)


def _recent_topic(history: list[dict[str, Any]], *terms: str) -> bool:
    for message in reversed(history[-10:]):
        content = normalize_text(str(message.get("content", "")))
        if any(term in content for term in terms):
            return True
    return False


def route_extended_support_question(
    question: str,
    history: list[dict[str, Any]],
) -> ExtendedSupportDecision:
    """Handle broad real-world support intents before semantic retrieval."""

    topic_context = build_topic_context(question, history)
    text = topic_context.effective_text.strip(" .")
    if not text:
        return ExtendedSupportDecision(False)

    if ("zooom" in text or "zoom" in text) and _has(text, "help", "fix", "not working", "issue", "problem"):
        return ExtendedSupportDecision(
            True,
            (
                "I can help troubleshoot **Zoom**. Try these first:\n\n"
                "1. Quit and reopen Zoom.\n"
                "2. Confirm the microphone, camera, and speaker selected in Zoom are correct.\n"
                "3. Check browser or macOS/Windows permission if using Zoom in a browser.\n"
                "4. Restart the device if audio, video, or joining still fails.\n"
                "5. Record the exact Zoom error message.\n\n"
                "If Zoom still does not work, create an IT ticket or contact the IT Helpdesk with the meeting link source, device, and error."
            ),
        )

    # ------------------------------------------------------------------
    # External monitors / USB-C docks
    # ------------------------------------------------------------------
    monitor_terms = (
        "monitor",
        "monitors",
        "external monitor",
        "external monitors",
        "external display",
        "external displays",
        "second monitor",
        "second screen",
        "dual monitor",
        "dual monitors",
        "two monitors",
    )
    dock_terms = (
        "dock",
        "docking station",
        "usb-c dock",
        "usb c dock",
        "usb-c docking station",
        "usb c docking station",
    )
    monitor_problem_terms = (
        "not detected",
        "not detecting",
        "does not detect",
        "doesn't detect",
        "cannot detect",
        "can't detect",
        "only detects one",
        "only detect one",
        "only sees one",
        "only see one",
        "only one monitor",
        "second monitor",
        "second screen",
        "one monitor",
        "one of the two",
        "not showing",
        "does not show",
        "doesn't show",
    )

    current_monitor_dock_issue = (
        _has(text, *monitor_terms)
        and _has(text, *dock_terms)
        and _has(text, *monitor_problem_terms)
    )

    # A user may correct a bad interpretation with wording such as
    # "I mean the monitor, not Classroom". Preserve the recent hardware
    # context instead of allowing the word "classroom" to send the query
    # toward Google Classroom knowledge.
    monitor_context_correction = (
        topic_context.is_correction
        and topic_context.allows("external_monitor")
        and topic_context.mentions("external_monitor")
        and bool(topic_context.prior_issue)
    )

    if (
        topic_context.allows("external_monitor")
        and (current_monitor_dock_issue or monitor_context_correction)
    ):
        prefix = (
            "Thanks for clarifying — this is about the **external monitor / USB-C dock**, not Google Classroom.\n\n"
            if monitor_context_correction
            else "For a laptop that detects only one monitor through a **USB-C docking station**:\n\n"
        )
        return ExtendedSupportDecision(
            True,
            (
                prefix
                + "1. Confirm both monitors are powered on and set to the correct input/source.\n"
                + "2. Reseat each HDMI/DisplayPort cable at the monitor and the dock.\n"
                + "3. Disconnect and reconnect the dock's USB-C cable to the laptop.\n"
                + "4. Open the laptop's display settings and check whether both external displays are detected.\n"
                + "5. If available, swap the display cables or dock video ports to see whether the problem follows a cable/port.\n\n"
                + "If it still detects only one monitor after these checks, tell me that the problem continues and I can route it to IT."
            ),
        )

    # ------------------------------------------------------------------
    # Additional high-confidence school IT routes from 96-question testing
    # ------------------------------------------------------------------
    if _has_all(text, ("laptop", "school network"), ("won't connect", "wont connect", "cannot connect", "can't connect", "what do i do")):
        return ExtendedSupportDecision(
            True,
            (
                "For a laptop that will not connect to the **school network**:\n\n"
                "1. Confirm Wi-Fi is turned on and Airplane Mode is off.\n"
                "2. Forget the saved school network and reconnect using the approved Student, Staff, or Guest method.\n"
                "3. Restart the laptop and try one approved website.\n"
                "4. Check whether other people in the same room can connect.\n"
                "5. Record the exact error message.\n\n"
                "If it still cannot connect, contact the IT Helpdesk with the laptop type, room, network name, and error."
            ),
        )

    if _has_all(text, ("wifi", "internet"), ("slow", "testing week", "multiple users")):
        return ExtendedSupportDecision(
            True,
            (
                "Slow Wi-Fi during testing week may be caused by high usage, weak signal, or a local network issue.\n\n"
                "1. Check whether multiple users in the same room are slow.\n"
                "2. Move closer to the access point if possible.\n"
                "3. Close streaming, cloud-sync, and unused browser tabs.\n"
                "4. Restart Wi-Fi on the device and test one approved site.\n"
                "5. Report the room, time, network name, and affected devices to the IT Helpdesk if it affects several users."
            ),
        )

    if _has_all(text, ("wifi",), ("password",)):
        return ExtendedSupportDecision(
            True,
            (
                "For security reasons, the **Wi-Fi password is not provided in plain text**. "
                "Use the approved Student, Staff, or Guest Wi-Fi QR code or enrollment method for the classroom. "
                "If the QR code or approved method does not work, contact the IT Helpdesk with the classroom and device type."
            ),
        )

    if _has_all(text, ("network settings", "reset my network"), ("school laptop", "laptop")):
        return ExtendedSupportDecision(
            True,
            (
                "Try safe network-reset steps before changing managed settings:\n\n"
                "1. Turn Wi-Fi off and back on.\n"
                "2. Forget the school Wi-Fi network and reconnect using the approved method.\n"
                "3. Restart the laptop.\n"
                "4. Confirm the date, time, and time zone are correct.\n"
                "5. Do not manually change DNS, proxy, certificates, or security profiles on a school device.\n\n"
                "If it still cannot connect, contact IT with the device, room, network name, and error."
            ),
        )

    if _has_all(text, ("certain websites", "access websites", "classroom wifi", "classroom wi-fi"), ("access", "blocked", "can't", "cannot", "why")):
        return ExtendedSupportDecision(
            True,
            (
                "If certain websites will not open from classroom Wi-Fi, first confirm whether the problem is a block page, DNS error, or site outage.\n\n"
                "1. Try another approved school website.\n"
                "2. Test in a private browser window.\n"
                "3. Record the exact URL and error message.\n"
                "4. Do not bypass the school filter with a hotspot, proxy, or VPN.\n"
                "5. If the site is needed for class, submit a helpdesk review request with the teacher, course, and reason."
            ),
        )

    if _has_all(text, ("wifi", "wi-fi"), ("gym", "classrooms")):
        return ExtendedSupportDecision(
            True,
            (
                "To compare Wi-Fi issues in the **gym** versus classrooms, check whether the same device works in both locations and ask whether others nearby are affected. "
                "Record the location, time, device type, signal strength if available, and whether Student or Staff Wi-Fi is affected. "
                "Send those details to the IT Helpdesk so they can check access-point coverage or a local outage."
            ),
        )

    if _has_all(text, ("students", "phones"), ("school wifi", "school wi-fi", "wifi")):
        return ExtendedSupportDecision(
            True,
            (
                "Students may connect phones to school Wi-Fi only when school policy allows it and only through the approved Student or Guest Wi-Fi method. "
                "The password is not shared in plain text. Use the approved QR code or ask the IT Helpdesk if the phone cannot join."
            ),
        )

    if _has_all(text, ("printer",), ("front office", "respond")):
        return ExtendedSupportDecision(
            True,
            (
                "For a **front office printer** that will not respond:\n\n"
                "1. Confirm the printer is powered on and has no toner, paper, or jam warning.\n"
                "2. Confirm your computer is on the approved school network.\n"
                "3. Open the print queue and check whether the job is paused or stuck.\n"
                "4. Remove only your failed job and send one test page.\n"
                "5. If multiple users are affected, contact IT with the printer name and location."
            ),
        )

    if _has_all(text, ("personal laptop",), ("print", "school printer")):
        return ExtendedSupportDecision(
            True,
            (
                "Printing from a **personal laptop** to a school printer may be restricted. "
                "Use an approved school-managed device or the school's approved guest/mobile printing process if one exists. "
                "Do not install unknown printer drivers. Contact IT with the printer name, device type, and whether this is for staff, student, or guest use."
            ),
        )

    if _has_all(text, ("printer",), ("jamming", "double-sided", "duplex")):
        return ExtendedSupportDecision(
            True,
            (
                "Double-sided or **duplex** jams are often caused by paper type, tray alignment, or the duplex path.\n\n"
                "1. Stop sending more jobs.\n"
                "2. Read the printer display for the jam location.\n"
                "3. Use the correct paper tray and reload paper neatly.\n"
                "4. Try a one-page single-sided test.\n"
                "5. If duplex jobs keep jamming, contact the IT Helpdesk or copier support with the printer location."
            ),
        )

    if _has_all(text, ("which printer", "printer my document went to"), ("document", "went to", "find out")):
        return ExtendedSupportDecision(
            True,
            (
                "To find which printer your document went to, open the print queue or printer icon on your device and check the selected printer name. "
                "In the application print window, review the destination before sending another job. If the job already printed, check nearby printers listed in your queue and contact IT with the document time and printer names."
            ),
        )

    if _has_all(text, ("jobs ahead", "queue", "ahead of mine"), ("printer", "jobs", "queue")):
        return ExtendedSupportDecision(
            True,
            (
                "Open the printer's **print queue** to see your job status. Some shared copiers show only your own jobs, while staff with printer access may see more queue details. "
                "If your job is stuck behind another job, do not power-cycle the copier; cancel only your job or contact the IT Helpdesk with the printer name."
            ),
        )

    if _has_all(text, ("print job", "document"), ("blank", "came out blank")):
        return ExtendedSupportDecision(
            True,
            (
                "If a print job came out **blank**:\n\n"
                "1. Open print preview and confirm the document content is visible.\n"
                "2. Check that the correct pages were selected.\n"
                "3. Try printing one page as a PDF or from another approved app.\n"
                "4. Check whether other users see blank output from the same printer.\n"
                "5. Report toner, print-quality, or copier issues to IT with the printer location."
            ),
        )

    if _has_all(text, ("printer",), ("disconnect", "network", "overnight")):
        return ExtendedSupportDecision(
            True,
            (
                "A printer disconnecting from the network overnight may be entering sleep mode, losing its network lease, or having a configuration issue. "
                "Confirm the printer wakes normally, check whether others see it offline in the morning, and report the printer name, location, and time pattern to IT. "
                "Do not change network settings on the copier unless instructed."
            ),
        )

    if _has_all(text, ("add", "new printer"), ("printer", "laptop")):
        return ExtendedSupportDecision(
            True,
            (
                "To add a school printer, first confirm the printer name or location and make sure the laptop is on the approved school network. "
                "On a Mac, open **System Settings → Printers & Scanners → Add Printer**. On Windows, open **Settings → Bluetooth & devices → Printers & scanners → Add device**. "
                "Use the school's approved printer details only, and contact IT if administrator credentials or a driver prompt appears."
            ),
        )

    # Require an explicit classroom-display phrase. The previous condition used
    # ("laptop", "classroom display") as alternatives, which accidentally made
    # any question containing "laptop" + "connect" look like a classroom-display
    # request (for example, a laptop connected to a USB-C docking station).
    if (
        topic_context.allows("classroom_display")
        and _has(text, "classroom display", "interactive classroom display", "display board")
        and _has(text, "laptop", "macbook", "chromebook", "computer")
        and _has(text, "connect", "connecting")
    ):
        return ExtendedSupportDecision(
            True,
            (
                "To connect a laptop to the **classroom display**:\n\n"
                "1. Turn on the display and select the correct input/source.\n"
                "2. Connect with the approved HDMI/USB-C cable and adapter, or use AirPlay if that room supports it.\n"
                "3. On the laptop, open display settings and choose mirror or extend.\n"
                "4. If using AirPlay, select the classroom Apple TV and enter the onscreen code.\n"
                "5. If nothing appears, reseat the cable or try the correct input."
            ),
        )

    if _has_all(text, ("ipad",), ("mirror", "projector", "wireless")):
        return ExtendedSupportDecision(
            True,
            (
                "An iPad can mirror wirelessly only when the classroom projector or display supports **AirPlay** and the iPad is on the approved network. "
                "Open Control Center, choose **Screen Mirroring**, select the classroom Apple TV/display, and enter the onscreen code. "
                "If AirPlay is not listed, use an approved cable/adapter or contact IT."
            ),
        )

    if _has_all(text, ("airplay",), ("show up", "option", "missing")):
        return ExtendedSupportDecision(
            True,
            (
                "If **AirPlay** does not show as an option, confirm the device and Apple TV are on the same approved school network, open Control Center → Screen Mirroring, and restart Wi-Fi on the device. "
                "Make sure the classroom display or Apple TV is awake and on the correct input. If it still does not appear, restart the device and contact IT with the room and Apple TV name."
            ),
        )

    if _has_all(text, ("chromebook",), ("factory settings", "factory reset", "reset")):
        return ExtendedSupportDecision(
            True,
            (
                "Do not factory-reset or Powerwash a school-managed Chromebook unless IT specifically instructs you. "
                "A reset can remove local data and may require re-enrollment. If the Chromebook is stuck or unusable, restart it and bring it to the IT Helpdesk with the asset tag and error message."
            ),
        )

    if _has_all(text, ("hdmi", "airplay"), ("wireless", "working", "instead")):
        return ExtendedSupportDecision(
            True,
            (
                "Yes, **HDMI** can be a good fallback when AirPlay or wireless display is not working, if the classroom display has the correct input and you have an approved adapter. "
                "Connect the cable, select the HDMI input/source on the display, then choose mirror or extend in display settings. Contact IT if the adapter or input is missing."
            ),
        )

    if (
        topic_context.allows("classroom_display")
        and _has_all(text, ("flickering",), ("classroom display", "display"))
    ):
        return ExtendedSupportDecision(
            True,
            (
                "For a **flickering classroom display**, check the input and connection first. Reseat the HDMI/USB-C cable, try the correct input/source, reduce unusual display scaling, and test another approved cable or adapter if available. "
                "If the flicker continues, contact IT with the room, display, device, cable type, and whether it happens for multiple laptops."
            ),
        )

    if _has_all(text, ("chromebook", "keyboard"), ("wrong characters", "typing")):
        return ExtendedSupportDecision(
            True,
            (
                "If a **Chromebook keyboard** types the wrong characters, check the keyboard layout and input language. Open Settings, search for **Keyboard** or **Input methods**, choose the correct layout, and remove layouts you do not use. "
                "Restart the Chromebook and test again. Contact IT if keys are physically damaged or the layout keeps changing."
            ),
        )

    if _has_all(text, ("chrome", "extensions"), ("block", "blocked", "school")):
        return ExtendedSupportDecision(
            True,
            (
                "The school may block some **Chrome extensions** for security, privacy, licensing, or classroom-management reasons. "
                "Use only approved extensions from the managed list. If an extension is needed for teaching or accessibility, submit a helpdesk/software review request with the extension name, purpose, and users affected."
            ),
        )

    if _has_all(text, ("app", "chromebook"), ("crashing", "crash", "keep crashing")):
        return ExtendedSupportDecision(
            True,
            (
                "For an app that keeps **crashing on a Chromebook**:\n\n"
                "1. Close and reopen the app or tab.\n"
                "2. Restart the Chromebook.\n"
                "3. Check for approved ChromeOS or app updates.\n"
                "4. Confirm there is enough storage and close extra tabs.\n"
                "5. Record the app name and error message for IT."
            ),
        )

    if _has_all(text, ("antivirus",), ("school laptop", "own")):
        return ExtendedSupportDecision(
            True,
            (
                "Do not install your own **antivirus** software on a school-managed laptop unless IT approves it. "
                "Managed devices already use school-approved security tools and adding another antivirus can conflict with updates, filtering, or monitoring. Contact IT if you see a virus warning or need a security review."
            ),
        )

    if _has_all(text, ("updates", "installing updates"), ("block", "school", "myself")):
        return ExtendedSupportDecision(
            True,
            (
                "School devices may block manual update installation because updates are managed for compatibility, security, testing schedules, and bandwidth. "
                "Keep the device on power and school Wi-Fi, restart when prompted, and use the approved update tool or Self Service/Company Portal. Contact IT if an urgent security patch or required app update is missing."
            ),
        )

    if _has_all(text, ("admin access",), ("plugin", "install")):
        return ExtendedSupportDecision(
            True,
            (
                "I cannot provide temporary **administrator access** or help bypass school device controls. "
                "Submit a software/plugin approval request with the plugin name, vendor, purpose, affected class or user group, and deadline. If approved, IT will install it using the authorized process."
            ),
        )

    if _has_all(text, ("loaner",), ("damaged", "gets damaged")):
        return ExtendedSupportDecision(
            True,
            (
                "Report the damaged **loaner** to the IT Helpdesk immediately and stop using it if there is a safety risk. Do not attempt repairs. "
                "Bring the device, charger, and accessories to IT and provide the asset tag, what happened, and when the damage occurred."
            ),
        )

    if _has_all(text, ("loaner",), ("deadline", "returned", "overdue")):
        return ExtendedSupportDecision(
            True,
            (
                "If a loaner is not returned by the **deadline**, contact the IT Helpdesk as soon as possible. The device may be marked overdue and IT may follow up with the borrower or department. "
                "Return the loaner, charger, and accessories promptly, or ask IT before the due date if an extension is needed."
            ),
        )

    if _has_all(text, ("loaner projector", "projector"), ("teachers", "event", "request")):
        return ExtendedSupportDecision(
            True,
            (
                "Teachers can request a **loaner projector or event equipment** through the IT Helpdesk when available. Include the event date, time, location, audience size, connection type, and whether audio or adapters are needed. "
                "Submit the request early because live inventory availability can change."
            ),
        )

    if _has_all(text, ("ticket", "classroom"), ("whole classroom", "on behalf")):
        return ExtendedSupportDecision(
            True,
            (
                "Yes, you can submit a ticket on behalf of a whole classroom when the issue affects multiple people. Include the room, number of affected users, device or service, exact error, start time, and any troubleshooting already tried. "
                "Choose a priority based on classroom impact and urgency."
            ),
        )

    if _has_all(text, ("ticket",), ("not urgent",)):
        return ExtendedSupportDecision(
            True,
            (
                "For a non-urgent issue, submit an IT helpdesk ticket with a clear title, location, device, category, priority, and description of what is happening. "
                "Choose **Low** or **Medium** priority when there is a workaround and no class-wide impact. Include screenshots or error messages when helpful."
            ),
        )

    if _has_all(text, ("ticket", "tickets"), ("response time", "typical")):
        return ExtendedSupportDecision(
            True,
            (
                "Typical IT ticket response time depends on priority, impact, staffing, and current workload. Urgent classroom-wide or critical-service issues are usually reviewed before low-priority individual requests. "
                "Check the ticket confirmation or helpdesk portal for updates, and add a comment if the impact changes."
            ),
        )

    if _has_all(text, ("ticket",), ("reopen", "resolved")):
        return ExtendedSupportDecision(
            True,
            (
                "No, Altitude cannot directly reopen a ticket that was marked **resolved** or **closed**. "
                "If the problem is still happening, create a new IT ticket and mention your previous Altitude reference number if you have it. "
                "For urgent or repeated issues, contact the IT Helpdesk directly and mention the same reference."
            ),
        )

    if _has_all(text, ("ticket", "reference"), ("status", "check", "updates")):
        return ExtendedSupportDecision(
            True,
            (
                "To check a ticket created through Altitude, send the **Altitude reference** such as `ALT-2026-000009`. "
                "If the reference is from this chat, I can show the latest status saved by Altitude and refresh it from the ticketing dashboard when available. "
                "If it is from another chat, include the same school email used when the ticket was submitted so I can verify it."
            ),
        )

    if _has_all(text, ("ticket",), ("assigned", "assigned to someone")):
        return ExtendedSupportDecision(
            True,
            (
                "Check the helpdesk portal or ticket confirmation email for assignment details, technician updates, or status changes. Some systems may show only the status, not the technician name. "
                "If you need confirmation, reply to the ticket with the ticket number and ask whether it has been assigned."
            ),
        )

    if _has_all(text, ("gmail", "phone"), ("log into", "can't", "cannot")):
        return ExtendedSupportDecision(
            True,
            (
                "For Gmail sign-in on a phone, confirm you are using the full school email address, not a personal account. Use the approved Gmail app or browser, check that the phone date and time are correct, and complete any required 2FA prompt. "
                "If the account is locked or the password is rejected, visit the IT Helpdesk and do not share your password or verification codes."
            ),
        )

    if _has_all(text, ("verify my identity", "identity"), ("log in", "login")):
        return ExtendedSupportDecision(
            True,
            (
                "Repeated identity-verification prompts usually mean Google or the school account system needs to confirm the sign-in. Use the approved verification method, check the device date and time, avoid repeated failed attempts, and do not share codes. "
                "Contact the IT Helpdesk if the prompt loops or your recovery method is unavailable."
            ),
        )

    if _has_all(text, ("parent", "child"), ("classroom", "access")):
        return ExtendedSupportDecision(
            True,
            (
                "Parents should not sign in to a student's Google Classroom account unless school policy specifically provides that access. Classroom access and guardian summaries are managed through approved school procedures. "
                "Contact the teacher or school office for parent/guardian access options that protect student privacy."
            ),
        )

    if _has_all(text, ("chromebook",), ("stuck", "login screen")):
        return ExtendedSupportDecision(
            True,
            (
                "For a Chromebook stuck on the login screen, restart it first by holding Power until it shuts down, then start it again. Confirm the Wi-Fi connection, use the correct school account, and check for an exact error message. "
                "If it still cannot sign in, bring the Chromebook to IT; do not factory-reset it yourself."
            ),
        )

    if _has_all(text, ("security patch", "latest security"), ("device", "check")):
        return ExtendedSupportDecision(
            True,
            (
                "To check security patch status, open the device's approved update area: **System Settings → General → Software Update** on Mac, **Settings → Windows Update** on Windows, or **Settings → About ChromeOS** on Chromebook. "
                "Managed devices may install updates on a school schedule. Contact IT if the device is far behind or update controls are locked."
            ),
        )

    if _has_all(text, ("video editing",), ("approved", "student projects")):
        return ExtendedSupportDecision(
            True,
            (
                "Use only school-approved video editing tools for student projects. Check the approved software list or submit a helpdesk request with the tool name, class purpose, devices, licensing needs, and privacy considerations. "
                "Do not install unapproved editors or browser extensions on school devices."
            ),
        )

    if _has_all(text, ("urgent",), ("call it", "call directly", "urgent issue")):
        return ExtendedSupportDecision(
            True,
            (
                "For an urgent IT issue, use the school's approved urgent-contact process, office contact, or helpdesk escalation path. Altitude will not invent a phone number. Include the room, service, number of affected users, and whether teaching is blocked."
            ),
        )

    # ------------------------------------------------------------------
    # Helpdesk ticket information and follow-up
    # ------------------------------------------------------------------
    if _has(text, "where do i go to submit", "how do i submit", "put in a help ticket", "submit an official it helpdesk ticket"):
        return ExtendedSupportDecision(
            True,
            (
                "You can start the **IT helpdesk ticket** workflow directly in "
                "Altitude by asking to create a ticket. The form will collect your "
                "school email, location, device, category, priority, and issue details.\n\n"
                "Include the exact error, what you already tried, and whether other "
                "people are affected. Altitude will not submit anything until you "
                "review and complete the required form fields."
            ),
        )

    if _has_all(
        text,
        ("ticket", "helpdesk", "support"),
        ("asset tag", "room number", "error code", "solved faster"),
    ):
        return ExtendedSupportDecision(
            True,
            (
                "Include these details in the helpdesk ticket so IT can resolve it faster:\n\n"
                "1. A short, specific description of the problem.\n"
                "2. Device type and **asset tag**, when available.\n"
                "3. **Room number** or exact location.\n"
                "4. The full **error code or message**.\n"
                "5. What you were doing when it started.\n"
                "6. Troubleshooting steps already attempted.\n"
                "7. Whether one person or multiple users are affected.\n"
                "8. A screenshot that does not expose passwords or private student data."
            ),
        )

    if _has_all(text, ("ticket", "helpdesk"), ("status", "updates", "open ticket")):
        return ExtendedSupportDecision(
            True,
            (
                "Check the confirmation email or the school's helpdesk portal for the "
                "current **ticket status** and technician updates. Reply in the same "
                "ticket thread when possible so the new information stays attached to "
                "the original request. If no portal link was provided, contact the IT "
                "Helpdesk and provide the ticket number."
            ),
        )

    if _has_all(text, ("ticket", "smartboard"), ("yesterday", "48 hours", "no response", "nobody came", "hasn't received")) or _has_all(
        text,
        ("ticket",),
        ("48 hours", "no response", "hasn't received a response"),
    ):
        return ExtendedSupportDecision(
            True,
            (
                "Follow up on the existing **ticket** rather than opening duplicates. "
                "Reply with the ticket number, classroom or room, current impact, and "
                "any new error details. If the problem is blocking a lesson or affects "
                "multiple users, state that clearly so the IT Helpdesk can reassess the "
                "priority."
            ),
        )

    if _has_all(text, ("emergency", "catastrophic", "mid-lesson"), ("phone", "number", "it")):
        return ExtendedSupportDecision(
            True,
            (
                "Altitude does not display an emergency phone number unless one has been "
                "approved and configured by the school. For a catastrophic mid-lesson "
                "failure, contact the IT Helpdesk through the school's approved urgent "
                "channel or notify the school office. Include the room, affected system, "
                "and whether the whole class is impacted."
            ),
        )

    if _has_all(text, ("screenshot",), ("ticket", "support")):
        return ExtendedSupportDecision(
            True,
            (
                "To attach a screenshot to an IT support ticket:\n\n"
                "1. On a Mac, press **Shift + Command + 4** and select the affected area.\n"
                "2. On a Chromebook, press **Ctrl + Show windows** for the full screen, "
                "or **Ctrl + Shift + Show windows** for part of the screen.\n"
                "3. Review the image and remove or cover passwords, student names, and "
                "other private information.\n"
                "4. Use the ticket form's attachment control or reply to the ticket "
                "confirmation email with the screenshot."
            ),
        )

    if _has_all(text, ("priority",), ("low", "high", "difference", "determines")):
        return ExtendedSupportDecision(
            True,
            (
                "Ticket **priority** should reflect impact and urgency:\n\n"
                "- **Low:** a minor issue with a workaround and no immediate teaching impact.\n"
                "- **Medium:** normal work is disrupted for one user or room, but the school can continue operating.\n"
                "- **High:** a lesson, critical service, whole classroom, or multiple users are significantly blocked.\n\n"
                "Choose the lowest accurate priority. IT may adjust it after reviewing "
                "the scope and impact."
            ),
        )

    if _has_all(text, ("comment", "new information"), ("open ticket", "ticket")):
        return ExtendedSupportDecision(
            True,
            (
                "Open the existing ticket in the helpdesk portal or reply to its "
                "confirmation email, then add a **comment** with the new information. "
                "Include the ticket number, what changed, any new error message, and "
                "additional troubleshooting. Avoid opening a duplicate ticket for the "
                "same issue."
            ),
        )

    if _has_all(text, ("reopen", "closed"), ("ticket", "problem", "not fixed")):
        return ExtendedSupportDecision(
            True,
            (
                "No, Altitude cannot directly reopen a ticket that was marked **resolved** or **closed**. "
                "If the problem is still happening, create a new IT ticket and mention your previous Altitude reference number if you have it. "
                "The IT Helpdesk can use that reference to review the earlier request. For urgent or repeated issues, contact the IT Helpdesk directly."
            ),
        )

    # ------------------------------------------------------------------
    # Loaner policies and logistics. Live counts remain in inventory_router.
    # ------------------------------------------------------------------
    if _has_all(text, ("loaner", "loner"), ("pickup", "pickup desk", "securing")):
        return ExtendedSupportDecision(
            True,
            (
                "Loaner devices should be picked up from the **IT Helpdesk or designated "
                "loaner desk**. Because the exact pickup location can change, confirm the "
                "current location with IT before travelling there. Bring any required "
                "school identification and wait for the device to be formally signed out."
            ),
        )

    if _has_all(text, ("loaner", "macbook", "chromebook"), ("how long", "duration", "keep", "due")):
        return ExtendedSupportDecision(
            True,
            (
                "The allowed **loan duration** depends on the school's current loaner "
                "policy and the reason for the loan. Confirm the due date when the device "
                "is signed out, keep the charger and accessories together, and return it "
                "by that date. Contact the IT Helpdesk before the due date if an extension "
                "is required."
            ),
        )

    if _has_all(text, ("loaner", "laptop"), ("reserve", "portal", "before")):
        return ExtendedSupportDecision(
            True,
            (
                "Altitude can check live inventory, but it cannot **reserve or hold** a "
                "loaner. Contact or visit the IT Helpdesk to request one. Availability can "
                "change before pickup, so a displayed count is not a guaranteed reservation."
            ),
        )

    if _has_all(text, ("loaner",), ("break", "broken", "lose", "lost", "fee", "damage")) and not _has(text, "drop off", "return", "leave"):
        return ExtendedSupportDecision(
            True,
            (
                "Report a damaged or lost **loaner device** to the IT Helpdesk immediately. "
                "Do not attempt repairs or hide the damage. Provide the asset tag, what "
                "happened, and the last known location. Altitude will not invent a fee; "
                "charges or responsibility depend on the signed loan agreement and current "
                "school policy."
            ),
        )

    if _has_all(text, ("power adapter", "charger"), ("included", "sign out", "loaner")):
        return ExtendedSupportDecision(
            True,
            (
                "A power adapter may be included with a loaner, but the exact accessory "
                "bundle depends on the device and current stock. Confirm the charger and "
                "all accessories on the sign-out record before leaving the IT Helpdesk, "
                "and return the same items with the loaner."
            ),
        )

    if _has_all(text, ("loaner", "loner"), ("return", "returning", "drop off", "leave")):
        after_hours = _has(text, "desk closed", "tech desk closed", "after hours", "where do i leave")
        broken = _has(text, "broken", "cracked", "damaged")
        if after_hours:
            answer = (
                "Do not leave a loaner unattended outside a closed desk. Keep it secure "
                "and contact the IT Helpdesk or school office for the approved after-hours "
                "return location. Include the charger and accessories, and obtain a return "
                "confirmation when the desk reopens."
            )
        elif broken:
            answer = (
                "Bring the broken loaner, charger, and accessories directly to the IT "
                "Helpdesk. Tell the technician what happened and do not place it back into "
                "general circulation. The device must be inspected and formally checked in."
            )
        else:
            answer = (
                "Return the loaner to the IT Helpdesk with its charger and accessories. "
                "Do not leave it unattended. Tell IT about any damage or missing items and "
                "wait until the device is formally **checked in** to the active inventory."
            )
        return ExtendedSupportDecision(True, answer)

    # ------------------------------------------------------------------
    # Wi-Fi and internet diagnostics
    # ------------------------------------------------------------------
    if _has_all(text, ("student", "staff"), ("wifi", "wireless", "network")) and _has(text, "connect", "won't", "wont", "cannot"):
        return ExtendedSupportDecision(
            True,
            (
                "Use the approved network for your role: students should reconnect to "
                "**Student Wi-Fi** with the approved QR code, while staff should use the "
                "school-managed Staff/SJK Wi-Fi enrollment method. Open Wi-Fi settings, "
                "forget the old school network, restart Wi-Fi, and join the correct network. "
                "If the device still cannot connect, contact IT with the device and exact error."
            ),
        )

    if _has_all(text, ("forget",), ("wifi", "wireless", "network")):
        return ExtendedSupportDecision(
            True,
            (
                "To forget and reconnect to the school wireless network:\n\n"
                "1. Open the device's **Wi-Fi settings**.\n"
                "2. Select the saved school network.\n"
                "3. Choose **Forget This Network** or **Forget network**.\n"
                "4. Turn Wi-Fi off and back on.\n"
                "5. Rejoin the approved Student, Staff, or Guest network using the "
                "school-approved QR code or sign-in method.\n"
                "6. Confirm the device date and time are correct.\n\n"
                "If reconnecting fails, record the exact error and contact the IT Helpdesk."
            ),
        )

    if _has_all(text, ("wifi", "wireless"), ("dropping", "disconnecting", "every 5 mins", "randomly")):
        return ExtendedSupportDecision(
            True,
            (
                "For Wi-Fi that keeps **disconnecting**:\n\n"
                "1. Move closer to the classroom access point and check whether others are affected.\n"
                "2. Forget the school network and reconnect using the approved method.\n"
                "3. Turn Wi-Fi off and back on, then restart the device.\n"
                "4. Disable a personal VPN or hotspot while testing.\n"
                "5. Confirm the date, time, and operating-system updates are current.\n\n"
                "If it continues, contact the IT Helpdesk with the room, device, network name, and approximate times."
            ),
        )

    if _has_all(text, ("no internet", "full wifi bars", "full bars", "exclamation mark"), ("wifi", "chromebook", "internet")):
        return ExtendedSupportDecision(
            True,
            (
                "The Wi-Fi icon can show a strong signal even when the device has no "
                "internet access.\n\n"
                "1. Open another approved website to confirm the problem.\n"
                "2. Turn Wi-Fi off and back on.\n"
                "3. Forget and reconnect to the approved school network.\n"
                "4. Restart the Chromebook or laptop.\n"
                "5. Check whether other users in the room are also affected.\n\n"
                "If several users have the same issue, report a possible network outage to IT."
            ),
        )

    if _has(text, "connection is not private", "your connection is not private", "certificate warning"):
        return ExtendedSupportDecision(
            True,
            (
                "Do **not proceed past the privacy or certificate warning** until the site is verified.\n\n"
                "1. Confirm that the school-site address is spelled correctly.\n"
                "2. Check the device's date, time, and time zone.\n"
                "3. Try the same approved site in another browser.\n"
                "4. Reconnect to the approved school Wi-Fi.\n"
                "5. Take a screenshot that does not expose private information.\n\n"
                "Contact the IT Helpdesk with the school site, warning text, device, and time."
            ),
        )

    if _has(text, "dns server not responding", "dns error", "dns failure"):
        return ExtendedSupportDecision(
            True,
            (
                "A **DNS server not responding** error means the device cannot translate "
                "site names into network addresses.\n\n"
                "1. Confirm whether other websites and devices work.\n"
                "2. Turn Wi-Fi off and back on.\n"
                "3. Forget and reconnect to the approved school network.\n"
                "4. Restart the browser and device.\n"
                "5. Do not manually change school DNS, proxy, or security settings.\n\n"
                "If the error affects multiple users, report the room and time to the IT Helpdesk."
            ),
        )

    if _has_all(text, ("hotspot",), ("personal", "cellular", "allowed", "school wifi")):
        return ExtendedSupportDecision(
            True,
            (
                "Use the approved school Wi-Fi whenever possible. A personal cellular "
                "hotspot may be restricted by school policy, can bypass required filtering, "
                "and may use personal data. Ask the IT Helpdesk or supervising staff for "
                "approval before using one on a school-managed device."
            ),
        )

    if _has_all(text, ("wifi",), ("asking for a password", "keeps asking", "invalid passwrod", "invalid password")):
        return ExtendedSupportDecision(
            True,
            (
                "Do not keep entering a remembered Wi-Fi password.\n\n"
                "1. Forget the saved school network.\n"
                "2. Confirm the device date and time.\n"
                "3. Reconnect using the approved Student, Staff, or Guest Wi-Fi QR code or sign-in method.\n"
                "4. Restart the device if the prompt returns.\n\n"
                "The chatbot will not reveal protected Wi-Fi credentials. Contact IT if the approved method fails."
            ),
        )

    if _has_all(text, ("signal strength", "network speeds", "speed test"), ("mac", "macbook", "wifi")):
        return ExtendedSupportDecision(
            True,
            (
                "On a Mac, hold **Option** and select the **Wi-Fi menu** to view signal "
                "details such as RSSI and noise. A signal closer to 0 is stronger; roughly "
                "-50 dBm is strong, while values near -80 dBm are weak. For network speed, "
                "use the school's approved speed-test site and record the room, time, "
                "download, upload, and latency. Do not install unapproved network tools."
            ),
        )

    if _has_all(text, ("iphone",), ("staff wifi", "staff wif-i", "wifi")):
        return ExtendedSupportDecision(
            True,
            (
                "A personal iPhone may only join the **Staff or Guest Wi-Fi** when school "
                "policy permits it. Use the approved QR code or enrollment method provided "
                "by IT; do not request the password in plain text. If Staff Wi-Fi is limited "
                "to managed devices, use Guest Wi-Fi or contact the IT Helpdesk."
            ),
        )

    if _has_all(text, ("internet",), ("slow", "room 104", "is it just me")):
        return ExtendedSupportDecision(
            True,
            (
                "First check whether the slow internet is limited to one device or affects "
                "others in **room 104**. Close unnecessary tabs, reconnect to Wi-Fi, and "
                "restart the device. If several users are slow in the same room, report the "
                "room, network name, time, and affected devices to IT as a possible local "
                "signal or network issue."
            ),
        )

    if _has_all(text, ("known network outage", "network outage", "system down", "student portal"), ("campus", "right now", "nothing is loading", "outage")):
        return ExtendedSupportDecision(
            True,
            (
                "Altitude cannot confirm a live campus outage unless a status integration "
                "reports one. Check whether multiple users, devices, and services are "
                "affected. Try one other approved website and record the room, network, "
                "time, and error. If the impact is widespread, contact the IT Helpdesk "
                "immediately as a possible outage."
            ),
        )

    # ------------------------------------------------------------------
    # Printer and copier support
    # ------------------------------------------------------------------
    if _has_all(text, ("print", "printer"), ("stuck", "queue", "cancel", "100 page", "stop it")):
        return ExtendedSupportDecision(
            True,
            (
                "To stop or clear the print job:\n\n"
                "1. Open **Printers & Scanners** or the printer icon and open the **print queue**.\n"
                "2. Select only your document.\n"
                "3. Choose **Cancel**, **Delete**, or **Remove**.\n"
                "4. If the queue is paused, choose **Resume** after the unwanted job disappears.\n"
                "5. If a large job already reached the copier, contact the IT Helpdesk or responsible staff member immediately.\n\n"
                "Do not power-cycle a shared copier while other jobs are active unless IT instructs you."
            ),
        )

    if _has_all(text, ("printer",), ("offline",)):
        return ExtendedSupportDecision(
            True,
            (
                "For a printer showing **Offline**:\n\n"
                "1. Confirm the printer is powered on and has no paper, toner, or jam warning.\n"
                "2. Confirm your computer is on the approved school Wi-Fi.\n"
                "3. Open the print queue, select the correct printer, and resume a paused queue.\n"
                "4. Remove only your failed print jobs.\n"
                "5. Restart the application and send a one-page test.\n\n"
                "If other users also see it offline, report the printer name and location to IT."
            ),
        )

    if _has_all(text, ("copier",), ("pin", "department id", "id code")):
        return ExtendedSupportDecision(
            True,
            (
                "The staff copier may require an authorized **PIN or department ID** for "
                "accounting and access control. Do not guess codes or use another person's "
                "code. Confirm that the correct department or secure-print option is "
                "selected, then contact the IT Helpdesk or department administrator for "
                "an approved code or account assignment."
            ),
        )

    if _has_all(text, ("double-sided", "duplex"), ("chromebook", "print")):
        return ExtendedSupportDecision(
            True,
            (
                "In the Chromebook print dialog, open **More settings** and enable "
                "**Two-sided** or **Duplex** printing. Choose long-edge binding for normal "
                "portrait documents. If the option is missing, the selected printer or "
                "driver may not support duplex from the Chromebook; choose another approved "
                "printer or contact IT."
            ),
        )

    if _has_all(text, ("printing", "document"), ("black streaks", "faded text", "streaks", "faded")):
        return ExtendedSupportDecision(
            True,
            (
                "Black streaks or faded text usually indicate a **toner, drum, or printer "
                "maintenance** problem rather than the document. Try one test page and, if "
                "available, another printer. Do not open toner or internal service areas. "
                "Report the printer name, location, and a sample page to the IT Helpdesk or "
                "copier service contact."
            ),
        )

    if _has_all(text, ("print quota", "quota"), ("student", "semester", "left", "balance")):
        return ExtendedSupportDecision(
            True,
            (
                "Check the school's approved printing portal or print-management window for "
                "your student **quota or balance**. If no balance is displayed, contact the "
                "IT Helpdesk with your school account; Altitude cannot invent or change a "
                "semester quota."
            ),
        )

    if _has_all(text, ("print", "printer"), ("access denied", "permission")):
        return ExtendedSupportDecision(
            True,
            (
                "An **Access Denied** print error usually means the account, printer, or "
                "department permission is not authorized. Confirm you are signed in with "
                "the correct school account, connected to the approved network, and using "
                "the correct printer. Remove and retry only your job. Contact IT if the "
                "printer should be available to your role."
            ),
        )

    if _has_all(text, ("printer",), ("wake up", "sleep mode", "sleep")):
        return ExtendedSupportDecision(
            True,
            (
                "Press the printer's normal **wake or power** button once and wait for the "
                "screen to become ready. Check for paper, toner, jam, or network warnings. "
                "Do not repeatedly switch off a shared printer. If it remains asleep or "
                "offline, report the printer name and location to the IT Helpdesk."
            ),
        )

    if _has_all(text, ("pdf", "google drive"), ("print", "copier")):
        return ExtendedSupportDecision(
            True,
            (
                "Open the PDF in Google Drive, select the **Print** icon, choose the approved "
                "school copier, review page range, colour, and two-sided settings, then print. "
                "If browser printing is blocked, download the PDF to an approved school "
                "device and print it from the system PDF viewer. Do not download confidential "
                "files to a personal device."
            ),
        )

    if _has_all(text, ("smartphone", "tablet", "phone"), ("print", "school printer")):
        return ExtendedSupportDecision(
            True,
            (
                "Mobile printing from a personal smartphone or tablet is only supported when "
                "the school has approved a mobile-print service for that printer. Do not "
                "install unknown printer apps or enter staff credentials. Use a managed school "
                "device or contact the IT Helpdesk to confirm the supported mobile-print policy."
            ),
        )

    if _has_all(text, ("libary printer", "library printer", "learning commons"), ("nothing came out", "not printing", "essay")):
        return ExtendedSupportDecision(
            True,
            (
                "For a missing Learning Commons or library print job:\n\n"
                "1. Confirm your device is on SJK or Student Wi-Fi.\n"
                "2. Open the print queue and confirm the job is not paused or failed.\n"
                "3. Verify the Learning Commons printer is selected.\n"
                "4. Remove the failed job and send a one-page test.\n"
                "5. Check the printer display for paper, toner, or jam warnings.\n\n"
                "Contact IT if the job still does not appear."
            ),
        )

    if _has_all(text, ("print",), ("color", "colour", "black and white")):
        return ExtendedSupportDecision(
            True,
            (
                "Open the print dialog's **More settings**, **Printer properties**, or "
                "**Colour options**, then select Colour instead of Black and White. If the "
                "option is unavailable, the selected printer, driver, account, or school "
                "policy may not permit colour printing. Contact IT rather than installing an "
                "unapproved driver."
            ),
        )

    # ------------------------------------------------------------------
    # School accounts and Google Workspace
    # ------------------------------------------------------------------
    if _has_all(text, ("password",), ("90-day", "expiration", "before", "change my password")):
        return ExtendedSupportDecision(
            True,
            (
                "Use the school's **approved password-change process** before the 90-day "
                "expiration date. Sign in to the school account portal, open Security or "
                "Change password, enter the current password, and create a unique new one. "
                "If self-service change is disabled, visit the IT Helpdesk for identity "
                "verification. Never share the old or new password in chat."
            ),
        )

    if _has_all(text, ("email", "emails", "gmail"), ("not receiving external", "missing external", "external emails")) and not _has(text, "bounce", "bounce back"):
        return ExtendedSupportDecision(
            True,
            (
                "For missing external email in school Gmail, check **Spam**, **All Mail**, "
                "filters, blocked senders, and account storage. Ask the sender whether they "
                "received a bounce message and confirm the exact recipient address. If messages "
                "from multiple external domains are missing, contact the IT Helpdesk with the "
                "sender address, approximate time, and subject."
            ),
        )

    if _has_all(text, ("email", "emails", "gmail"), ("bounce", "bounce back", "outside", "external", "school domain")):
        return ExtendedSupportDecision(
            True,
            (
                "Open the Gmail or email bounce message and read the exact **error or rejection code**. "
                "Confirm the recipient address, remove oversized attachments, and try one "
                "plain test message. External delivery may be blocked by recipient policy or "
                "school-domain restrictions. Send the bounce details and recipient domain to "
                "the IT Helpdesk; do not repeatedly resend the same message."
            ),
        )

    if _has_all(text, ("google drive", "drive"), ("storage full", "storage is full", "full warning")):
        return ExtendedSupportDecision(
            True,
            (
                "A Google Drive **Storage Full** warning can stop uploads, email, or syncing. "
                "Open Google storage, review the largest files, empty Drive Trash only after "
                "confirming the files are no longer needed, and check large Gmail attachments. "
                "Do not delete shared or school-record files without authorization. Contact IT "
                "if the quota appears incorrect or required school files cannot be removed."
            ),
        )

    if _has_all(text, ("sign out",), ("shared", "library computer", "google account")):
        return ExtendedSupportDecision(
            True,
            (
                "On a shared library computer, select your Google profile picture and choose "
                "**Sign out of all accounts**. Close every browser window, remove any saved "
                "downloaded files, and do not save the password. If you used a normal browser "
                "session, clear only your account session or use an incognito/private window "
                "next time."
            ),
        )

    if _has_all(text, ("transfer ownership", "ownership"), ("google doc", "teacher", "collaborative")):
        return ExtendedSupportDecision(
            True,
            (
                "Open the Google Doc's **Share** settings, add the teacher's correct school "
                "email as an editor, then use the role menu to select **Transfer ownership** "
                "when that option is allowed. Google Workspace may restrict transfers to the "
                "same school domain or block student ownership changes. Contact the teacher "
                "or IT if the option is unavailable."
            ),
        )

    if _has_all(text, ("gmail",), ("native mail", "mail app", "sync")):
        return ExtendedSupportDecision(
            True,
            (
                "On a Mac, open **System Settings → Internet Accounts → Add Account → Google**, "
                "sign in with the school account, complete the school's approved verification, "
                "and enable Mail. If the account is managed or the Mail app is not approved, "
                "use Gmail in Chrome and contact IT instead of changing IMAP or security settings."
            ),
        )

    if _has_all(text, ("account",), ("hacked", "compromised", "suspect")):
        return ExtendedSupportDecision(
            True,
            (
                "Treat a suspected school-account compromise as urgent:\n\n"
                "1. Stop approving unexpected sign-in or verification prompts.\n"
                "2. From a trusted device, change the password using the approved process if permitted.\n"
                "3. Sign out of other sessions and review recovery methods.\n"
                "4. Preserve suspicious emails or alerts; do not forward passwords or codes.\n"
                "5. Contact the IT Helpdesk immediately with the account, time, and observed activity."
            ),
        )

    if _has_all(text, ("offline",), ("google docs", "classroom", "google")):
        return ExtendedSupportDecision(
            True,
            (
                "Google Docs offline access must be enabled while connected to the internet. "
                "In approved Chrome, open Google Drive settings and enable **Offline**, then "
                "mark required files available offline. Google Classroom itself has limited "
                "offline capability, so open or download required materials before losing the "
                "connection. Use only a school-managed device and approved extension."
            ),
        )

    if _has_all(text, ("2fa", "two-factor", "two factor"), ("set up", "staff account")):
        return ExtendedSupportDecision(
            True,
            (
                "To set up approved two-factor authentication for a staff account, open the "
                "school Google account's **Security → 2-Step Verification**, sign in again, "
                "and enroll an approved method such as an authenticator or security key. Save "
                "recovery methods securely and never share verification codes. Contact IT if "
                "enrollment is controlled by school policy."
            ),
        )

    if _has_all(text, ("assignment",), ("attach", "classrom", "classroom", "teacher gave me a zero")):
        return ExtendedSupportDecision(
            True,
            (
                "Open the Google Classroom assignment and confirm the file appears under "
                "**Your work** before selecting Turn in. If it is missing, choose **Add or create**, "
                "attach the correct Drive file, wait for the upload to finish, and then submit. "
                "Confirm the status says **Turned in**. Contact the teacher about the grade and IT "
                "if the attachment repeatedly fails."
            ),
        )

    # ------------------------------------------------------------------
    # Devices, classroom displays, and AirPlay
    # ------------------------------------------------------------------
    if _has_all(text, ("chromebook",), ("touchscreen", "touch screen")) and _has(text, "not responding", "not working", "suddenly"):
        return ExtendedSupportDecision(
            True,
            (
                "Clean and dry the Chromebook touchscreen with a microfiber cloth, remove any "
                "case or screen protector that may press the edges, and restart the device. "
                "Test touch on the sign-in screen and in another app. Do not use a factory reset "
                "or developer mode. If touch still fails while the keyboard and trackpad work, "
                "contact IT for hardware inspection."
            ),
        )

    if _has_all(text, ("chromebook",), ("hard reset", "completely frozen", "screen frozen")):
        return ExtendedSupportDecision(
            True,
            (
                "For a frozen Chromebook, first hold **Power** until it shuts down, wait ten "
                "seconds, and turn it back on. If it remains frozen, use the hardware restart "
                "shortcut **Refresh + Power** once. This restarts the Chromebook; it is not a "
                "factory reset. Contact IT if the device repeatedly freezes."
            ),
        )

    if _has_all(text, ("macbook",), ("interactive classroom display", "display board", "classroom display")):
        return ExtendedSupportDecision(
            True,
            (
                "Connect the MacBook using the classroom's approved HDMI/USB-C adapter or "
                "AirPlay method. Turn on the display, select the correct input, then open "
                "**System Settings → Displays** and choose Mirror or Extend. If using AirPlay, "
                "open Control Center → Screen Mirroring and select the classroom display."
            ),
        )

    if _has_all(text, ("chromebook",), ("black", "power light")):
        return ExtendedSupportDecision(
            True,
            (
                "For a Chromebook with a black screen but power light on:\n\n"
                "1. Increase screen brightness.\n"
                "2. Disconnect accessories and external displays.\n"
                "3. Hold Power until it turns off, wait ten seconds, and restart.\n"
                "4. Try **Refresh + Power** once.\n"
                "5. Connect the approved charger and wait several minutes.\n\n"
                "If the screen remains black, stop and contact IT for hardware inspection."
            ),
        )

    if _has_all(text, ("audio", "sound"), ("display", "laptop", "video playing")):
        return ExtendedSupportDecision(
            True,
            (
                "The video connection is working, but the laptop is still selected for audio. "
                "Open the device's **Sound output** settings and select the classroom display, "
                "HDMI, Apple TV, or AirPlay device. Confirm the display is not muted and test "
                "a short clip. Reconnect the cable or AirPlay session if the output is missing."
            ),
        )

    if _has_all(text, ("airplay",), ("lag", "stuttering", "freezing", "screen just keeps freezing")):
        return ExtendedSupportDecision(
            True,
            (
                "For AirPlay lag, stuttering, or freezing:\n\n"
                "1. Confirm the Mac and Apple TV are on the same approved school network.\n"
                "2. Move closer to the access point and disconnect VPNs or hotspots.\n"
                "3. Close high-bandwidth applications and unnecessary browser tabs.\n"
                "4. Stop mirroring, restart the Mac, and reconnect.\n"
                "5. Lower the mirrored display resolution or video quality when possible.\n\n"
                "Report the classroom and Apple TV name if the problem continues."
            ),
        )

    if _has_all(text, ("clean", "cleaning"), ("device screen", "screen")):
        return ExtendedSupportDecision(
            True,
            (
                "Power the device off and unplug it. Use a clean, soft **microfiber cloth** "
                "lightly dampened with water or a school-approved screen cleaner. Wipe gently "
                "and never spray liquid directly on the screen, keyboard, openings, or ports. "
                "Do not use abrasive cloths, harsh household chemicals, or excessive liquid."
            ),
        )

    if _has_all(text, ("freeze", "blank"), ("classroom display", "image", "projector")):
        return ExtendedSupportDecision(
            True,
            (
                "Use the classroom display or projector remote's approved **Freeze**, **Blank**, "
                "or **AV Mute** control if available. This freezes or hides the projected image "
                "while the laptop continues operating. Press the same control again to restore "
                "the live image. Do not power off the display during a lesson unless necessary."
            ),
        )

    if _has_all(text, ("flashing folder", "question mark"), ("mac", "turn it on")):
        return ExtendedSupportDecision(
            True,
            (
                "A flashing folder with a question mark means the Mac cannot find a valid "
                "startup disk. Shut it down, disconnect external drives, and try one normal "
                "restart. Do not erase, initialize, or reinstall macOS through the public "
                "chatbot. Contact the IT Helpdesk for startup-disk and data inspection."
            ),
        )

    if _has_all(text, ("chromebook",), ("cracked", "screen cracked")):
        return ExtendedSupportDecision(
            True,
            (
                "Stop using the Chromebook if the cracked screen has sharp glass, exposed "
                "parts, flickering, or pressure marks. Do not press on or tape over severe "
                "damage. Bring the device and charger to the IT Helpdesk and provide the asset "
                "tag and what happened."
            ),
        )

    if _has_all(text, ("digital sign",), ("black screen", "white text", "stuck")):
        return ExtendedSupportDecision(
            True,
            (
                "A hallway digital sign showing a black screen with white text may be at a "
                "boot, network, or player error screen. Record or photograph the exact text, "
                "location, and time. Confirm the display has power, but do not repeatedly "
                "power-cycle or change kiosk settings. Contact the IT Helpdesk or signage "
                "administrator for the approved restart procedure."
            ),
        )

    if _has_all(text, ("macbook",), ("battery died", "wont turn back on", "plugged in")):
        return ExtendedSupportDecision(
            True,
            (
                "Connect the MacBook directly to a known working outlet with an approved "
                "charger and leave it charging for at least five minutes. Disconnect docks "
                "and accessories, then hold the **Power** button for about ten seconds, release "
                "it, and press Power normally. If it still will not turn on while plugged in, "
                "contact IT and test another approved charger only if available."
            ),
        )

    if _has_all(text, ("water", "liquid"), ("keyboard", "sticky", "spilled")):
        return ExtendedSupportDecision(
            True,
            (
                "Stop using the device immediately. Power it off, disconnect the charger and "
                "accessories, and keep it on a dry surface. Do not keep pressing sticky keys, "
                "apply heat, use compressed air, or use home drying remedies. Contact the IT Helpdesk "
                "immediately and describe the liquid and amount."
            ),
        )

    # ------------------------------------------------------------------
    # Approved software and application troubleshooting
    # ------------------------------------------------------------------
    if _has_all(text, ("software", "program", "application"), ("requesting", "request", "approved", "classroom use")):
        return ExtendedSupportDecision(
            True,
            (
                "Submit a helpdesk ticket requesting **software approval**. Include the exact "
                "application name and vendor, educational purpose, classes or users affected, "
                "required date, device type, licensing cost, data collected, and any privacy or "
                "account requirements. Do not install it until IT confirms security, licensing, "
                "privacy, and device compatibility."
            ),
        )

    if _has_all(text, ("web filter", "blocked", "unblock"), ("legitimate", "research", "website", "unblock", "coolmathgames")):
        legitimate = not _has(text, "coolmathgames", "free time", "game")
        if legitimate:
            answer = (
                "Do not bypass the school web filter or use a browser workaround. Submit a review request or helpdesk "
                "ticket with the full URL, classroom purpose, teacher or department, time "
                "needed, and screenshot of the block page. IT can review whether the site is "
                "legitimate, safe, and permitted by school policy."
            )
        else:
            answer = (
                "I cannot unblock or help bypass the school web filter for an unapproved game. "
                "Filtering decisions follow school-use and safety policy. A teacher may submit "
                "a formal review request when a blocked site has a legitimate instructional need."
            )
        return ExtendedSupportDecision(True, answer)

    if _has_all(text, ("self service", "company portal"), ("install", "approved", "applications")):
        return ExtendedSupportDecision(
            True,
            (
                "Open the school-managed **Self Service** or **Company Portal**, sign in with "
                "the school account if requested, search for the approved app, and select "
                "Install. Keep the device on power and Wi-Fi until it finishes. If the app is "
                "missing, installation fails, or administrator credentials appear, contact IT "
                "rather than downloading a separate installer."
            ),
        )

    if _has_all(text, ("approved app", "app"), ("crash", "crashes", "immediately", "open")):
        return ExtendedSupportDecision(
            True,
            (
                "For an approved app that crashes on launch, save other work, close the app, "
                "restart the device, and install approved app and operating-system updates. "
                "Confirm sufficient storage and record the crash message. Do not delete managed "
                "profiles or reinstall from an unapproved source; contact IT if it still crashes."
            ),
        )

    if _has_all(text, ("google chrome", "chrome"), ("manually update", "managed by my organization", "update")):
        return ExtendedSupportDecision(
            True,
            (
                "Open **Chrome → About Google Chrome** to let Chrome check for an update, then "
                "select Relaunch if offered. On a school-managed device, updates may be "
                "controlled by the organization and manual changes may be blocked. Restart the "
                "device and contact IT if Chrome remains outdated or says the update is disabled."
            ),
        )

    if _has_all(text, ("zoom", "google meet", "meet"), ("audio isnt working", "can't hear me", "cant hear me", "teacher cant hear", "microphone")):
        return ExtendedSupportDecision(
            True,
            (
                "Check the meeting microphone before rejoining: unmute, open Zoom or Google "
                "Meet audio settings, select the correct **microphone**, and confirm the input "
                "meter moves when you speak. Allow microphone permission in the browser or "
                "system settings, close other apps using the mic, reconnect the headset, and "
                "restart the meeting app. Contact IT if the microphone fails in every app."
            ),
        )

    if _has_all(text, ("cache", "cookies"), ("clear", "browser", "loading")):
        return ExtendedSupportDecision(
            True,
            (
                "In Chrome, open **Settings → Privacy and security → Delete browsing data**. "
                "Select **Cached images and files** and, only when necessary, **Cookies and "
                "other site data**, then choose an appropriate time range. Clearing cookies "
                "signs you out of sites. Reopen the browser and test the page in a private window."
            ),
        )

    if _has_all(text, ("virus warning", "popup", "clicked a link"), ("accidentally", "virus", "warning")):
        return ExtendedSupportDecision(
            True,
            (
                "Do not click the popup, call a displayed number, install software, or enter "
                "credentials. Close the tab or browser; if it will not close, disconnect the "
                "device from Wi-Fi and contact the IT Helpdesk immediately. Record the site, "
                "time, and what was clicked. Change a password only through the approved process "
                "if credentials were entered."
            ),
        )

    if _has_all(text, ("accessibility", "extension"), ("enable", "approved", "browser")):
        return ExtendedSupportDecision(
            True,
            (
                "Open Chrome's **Extensions** page or the school-managed app catalogue and "
                "enable only the accessibility extension approved for your account. If the "
                "toggle is locked or the extension is missing, do not install another copy from "
                "the public store; contact IT or the accessibility-support contact."
            ),
        )

    if _has_all(text, ("text-to-speech", "text to speech"), ("document", "failing", "read")):
        return ExtendedSupportDecision(
            True,
            (
                "Confirm the document contains selectable text rather than only a scanned image. "
                "Try a small section, check the text-to-speech voice and output device, reopen "
                "the document, and test another approved document. A protected PDF may require "
                "OCR or an accessible copy from the owner. Contact accessibility support or IT "
                "if the same document remains unreadable."
            ),
        )

    if _has_all(text, ("uninstall",), ("app", "space", "macbook")):
        return ExtendedSupportDecision(
            True,
            (
                "First confirm the app is not required or managed by the school. For an approved "
                "removable Mac app, quit it, open **Applications**, move it to Trash, and empty "
                "Trash only when school policy permits. Do not remove security, management, VPN, "
                "testing, or accessibility software. Contact IT when administrator approval is required."
            ),
        )

    if _has_all(text, ("respondus", "lockdown", "testing browser", "secure testing browser"), ("failing", "launch", "open")):
        return ExtendedSupportDecision(
            True,
            (
                "Restart the device, close other apps, confirm the test date and course link, and "
                "open the secure testing browser from the approved school installation. Install "
                "approved updates and record the exact launch error. Do not disable security, "
                "screen-recording, or management controls. Contact IT and the teacher before the test."
            ),
        )

    if _has_all(text, ("canva",), ("export", "poster", "download")):
        return ExtendedSupportDecision(
            True,
            (
                "For a Canva export problem, confirm the design is fully saved, choose the "
                "required file type, and try a smaller or flattened export. Check browser "
                "downloads, available storage, pop-up/download permissions, and try a private "
                "window or approved browser. Record any error and contact IT if school filtering "
                "or account permissions block the export."
            ),
        )

    if _has_all(text, ("python",), ("script", "not running", "school desktop")):
        return ExtendedSupportDecision(
            True,
            (
                "Open the project in the approved editor and copy the exact Python error. Confirm "
                "the selected **Python interpreter**, file path, and required environment or "
                "virtual environment. Run `python --version` and then the script from the approved "
                "terminal. Do not install packages globally without permission; contact IT or the "
                "course instructor with the error and dependency name."
            ),
        )

    return ExtendedSupportDecision(False)
