from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.platform_context import detect_platform
from core.text_matching import normalize_text
from core.topic_context import build_topic_context


LEARNING_COMMONS_IP = "192.168.1.205"


@dataclass(frozen=True)
class PrinterDecision:
    handled: bool
    answer: str = ""


def get_last_assistant_message(
    history: list[dict[str, Any]],
) -> str:
    for message in reversed(history):
        if message.get("role") == "assistant":
            return normalize_text(
                str(
                    message.get(
                        "content",
                        "",
                    )
                )
            )

    return ""


def get_expected_printer_step(
    history: list[dict[str, Any]],
) -> str | None:
    last_assistant = get_last_assistant_message(
        history
    )

    recent_user_printer_context = any(
        any(
            term in normalize_text(str(message.get("content", "")))
            for term in ("printer", "printing", "print queue", "library printer", "learning commons")
        )
        for message in history[-10:]
        if message.get("role") == "user"
    )

    if any(
        marker in last_assistant
        for marker in (
            "reply with add or already added",
            "add the printer to your device",
            "troubleshoot a printer that is already added",
            "when you say connect",
        )
    ):
        return "action"

    if any(
        marker in last_assistant
        for marker in (
            "which printer are you trying to use",
            "which printer would you like to add",
            "please choose the printer",
            "learning commons library printer",
            "another school printer",
        )
    ):
        return "printer"

    if recent_user_printer_context and any(
        marker in last_assistant
        for marker in (
            "are you using a mac or a chromebook",
            "are you using a chromebook or a mac",
            "reply with mac or chromebook",
        )
    ):
        return "device"

    return None


def is_printer_supply_request(
    question: str,
) -> bool:
    normalized = normalize_text(question).strip(" .")

    return any(
        phrase in normalized
        for phrase in (
            "out of paper",
            "need more paper",
            "where is the paper",
            "where do i find paper",
            "paper tray",
            "replace paper",
            "paper jam",
            "printer jam",
            "jammed",
            "replace toner",
            "out of toner",
            "need toner",
            "replace ink",
            "out of ink",
            "need staples",
        )
    )


def has_explicit_printer_reference(
    question: str,
) -> bool:
    normalized = normalize_text(question)

    words = set(
        normalized.split()
    )

    if words.intersection(
        {
            "printer",
            "printing",
            "print",
            "kyocera",
        }
    ):
        return True

    return any(
        phrase in normalized
        for phrase in (
            "learning commons printer",
            "library printer",
            "library kyocera",
            "print in library",
            "print in the library",
            "print at library",
            "print at the library",
            "print in learning commons",
            "print at learning commons",
            "print in libary",
            "print at libary",
            "mz4001ci",
            "192.168.1.205",
            "192 168 1 205",
        )
    )


def detect_action(
    text: str,
) -> str | None:
    normalized = normalize_text(text)

    troubleshoot_phrases = (
        "already added",
        "already installed",
        "printer is added",
        "printer is installed",
        "cannot print",
        "can't print",
        "cant print",
        "not printing",
        "nothing prints",
        "nothing came out",
        "did not come out",
        "didn't come out",
        "won't print",
        "wont print",
        "failed to print",
        "fails to print",
        "print job",
        "printer unavailable",
        "printer is not responding",
        "offline",
        "printer issue",
    )

    if any(
        phrase in normalized
        for phrase in troubleshoot_phrases
    ):
        return "troubleshoot"

    if any(
        phrase in normalized
        for phrase in (
            "won't show up in the list",
            "won't even show up in the list",
            "wont show up in the list",
            "wont even show up in the list",
            "doesn't show up in the list",
            "does not show up in the list",
            "not showing in the list",
            "missing from the list",
            "not in the printer list",
        )
    ):
        return "add"

    # A user who says they want/need to print in the Library or Learning
    # Commons is asking to get that printer ready for use. Treat this as
    # setup so Altitude can move directly to the device question instead
    # of asking redundant printer/action clarifications.
    library_location = any(
        phrase in normalized
        for phrase in (
            "library",
            "libary",
            "learning commons",
        )
    )
    new_print_intent = any(
        phrase in normalized
        for phrase in (
            "i want to print",
            "want to print",
            "i need to print",
            "need to print",
            "how do i print",
            "how can i print",
            "how to print",
        )
    )

    if library_location and new_print_intent:
        return "add"

    add_words = {
        "add",
        "install",
        "setup",
        "ad",
    }

    if (
        set(
            normalized.split()
        ).intersection(
            add_words
        )
        or "set up" in normalized
    ):
        return "add"

    return None


def detect_printer(
    text: str,
) -> str | None:
    normalized = normalize_text(text)

    library_location = (
        "library" in normalized
        or "libary" in normalized
        or "learning commons" in normalized
    )
    print_context = any(
        term in normalized
        for term in (
            "print",
            "printer",
            "kyocera",
        )
    )

    if (
        any(
            term in normalized
            for term in (
                "learning commons",
                "library printer",
                "library kyocera",
                "kyocera mz4001ci",
                "mz4001ci",
                "192.168.1.205",
                "192 168 1 205",
            )
        )
        or (library_location and print_context)
        or normalized in {
            "library",
            "libary",
            "kyocera",
            "it's the library one",
            "its the library one",
            "the library one",
            "library one",
            "for the library",
            "no for the library",
            "no, for the library",
        }
        or (library_location and len(normalized.split()) <= 6 and normalized.startswith(("no ", "yes ", "for ", "the ")))
    ):
        return "learning_commons"

    if (
        any(
            term in normalized
            for term in (
                "another school printer",
                "other printer",
                "staff printer",
                "staff room printer",
                "office printer",
                "classroom printer",
                "faculty printer",
            )
        )
        or normalized in {
            "other",
            "another",
        }
    ):
        return "other"

    return None


def detect_device(
    text: str,
) -> str | None:
    platform = detect_platform(text)

    if platform == "macos":
        return "mac"

    if platform == "chromebook":
        return "chromebook"

    if platform == "windows":
        return "unsupported_windows"

    normalized = normalize_text(text)

    if normalized in {"mc", "mack"}:
        return "mac"

    if normalized in {"chrome book", "chromeos", "chrome os"}:
        return "chromebook"

    if normalized in {"win", "window"}:
        return "unsupported_windows"

    return None


def is_ambiguous_connect_request(
    text: str,
) -> bool:
    normalized = normalize_text(text)

    return (
        (
            "connect" in normalized
            or "connection" in normalized
        )
        and has_explicit_printer_reference(text)
        and detect_action(text) is None
    )


def is_learning_commons_wifi_question(
    text: str,
) -> bool:
    normalized = normalize_text(text)

    return (
        detect_printer(text)
        == "learning_commons"
        and "wifi" in normalized
        and any(
            term in normalized
            for term in (
                "need",
                "require",
                "which",
                "student",
                "sjk",
            )
        )
    )


def recent_user_messages(
    history: list[dict[str, Any]],
    current_question: str,
) -> list[str]:
    normalized_current = normalize_text(
        current_question
    )

    values: list[str] = []

    for message in reversed(
        history[-14:]
    ):
        if message.get("role") != "user":
            continue

        content = str(
            message.get(
                "content",
                "",
            )
        ).strip()

        if not content:
            continue

        if (
            not values
            and normalize_text(content)
            == normalized_current
        ):
            continue

        values.append(content)

    return values


def find_recent_action(
    history: list[dict[str, Any]],
    current_question: str,
) -> str | None:
    for content in recent_user_messages(
        history,
        current_question,
    ):
        value = detect_action(content)

        if value:
            return value

    return None


def find_recent_printer(
    history: list[dict[str, Any]],
    current_question: str,
) -> str | None:
    for content in recent_user_messages(
        history,
        current_question,
    ):
        value = detect_printer(content)

        if value:
            return value

    return None


def find_recent_device(
    history: list[dict[str, Any]],
    current_question: str,
) -> str | None:
    for content in recent_user_messages(history, current_question):
        value = detect_device(content)
        if value:
            return value
    return None


def valid_workflow_reply(
    question: str,
    expected_step: str | None,
) -> bool:
    if expected_step is None:
        return False

    if (
        len(
            normalize_text(
                question
            ).split()
        )
        > 10
    ):
        return False

    if expected_step == "action":
        return detect_action(question) is not None

    if expected_step == "printer":
        return detect_printer(question) is not None

    if expected_step == "device":
        return detect_device(question) is not None

    return False


def failure_follow_up(
    question: str,
    history: list[dict[str, Any]],
) -> str | None:
    normalized = normalize_text(question)

    failure_terms = (
        "still not working",
        "that did not work",
        "that didn't work",
        "it did not work",
        "it didn't work",
        "same issue",
        "still cannot print",
        "still can't print",
    )

    if not any(
        term in normalized
        for term in failure_terms
    ):
        return None

    last_assistant = get_last_assistant_message(
        history
    )

    if (
        "add printer scanner or fax"
        in last_assistant
        or "tcp ip device"
        in last_assistant
    ):
        return "setup"

    if (
        "confirm that the correct"
        in last_assistant
        and "try printing again"
        in last_assistant
    ):
        return "printing"

    return None


def mac_setup_instructions() -> str:
    return (
        "Make sure your Mac is connected to either "
        "**SJK Wi-Fi** or **Student Wi-Fi**.\n\n"
        "1. Open **System Settings**.\n"
        "2. Select **Printers & Scanners**.\n"
        "3. Click **Add Printer, Scanner, or Fax**.\n"
        "4. Open the **IP** section.\n"
        f"5. Enter **{LEARNING_COMMONS_IP}** in the "
        "Address field.\n"
        "6. Set Protocol to "
        "**Line Printer Daemon – LPD**.\n"
        "7. Wait for the printer information to load.\n"
        "8. Confirm the Kyocera printer is detected, "
        "then click **Add**.\n"
        "9. Print a test page.\n\n"
        "If administrator credentials are requested "
        "or setup cannot be completed, please visit "
        "the IT Helpdesk."
    )


def chromebook_setup_instructions() -> str:
    return (
        "On a school-managed **Chromebook**, first check whether the printer "
        "has already been deployed by IT.\n\n"
        "1. Open **Settings**.\n"
        "2. Search for **Print** or open **Device → Print and scan**.\n"
        "3. Open **Printers** and look for the Learning Commons / Library printer.\n"
        "4. If it is available, select it and print a test page.\n"
        "5. If it is missing or locked by management, do not add an IP address or "
        "driver manually. Contact the IT Helpdesk so the managed printer can be "
        "assigned correctly."
    )


def route_printer_question(
    question: str,
    history: list[dict[str, Any]],
) -> PrinterDecision:
    topic_context = build_topic_context(question, history)
    if not topic_context.allows("printer"):
        return PrinterDecision(handled=False)

    normalized = normalize_text(question)
    effective_normalized = topic_context.effective_text

    if any(
        phrase in normalized
        for phrase in (
            "all printers in the building",
            "all printers are unavailable",
            "all printers unavailable",
            "every printer is unavailable",
            "multiple printers are unavailable",
        )
    ):
        return PrinterDecision(
            handled=True,
            answer=(
                "Because multiple or all printers are unavailable, this may be a "
                "printer-service outage rather than a problem with one device. Please "
                "contact the IT Helpdesk or IT team and report the building area, "
                "affected printers, and approximate start time."
            ),
        )

    if any(
        phrase in normalized
        for phrase in (
            "stuck in the print queue",
            "stuck in print queue",
            "print job is stuck",
            "document is stuck in the queue",
        )
    ):
        return PrinterDecision(
            handled=True,
            answer=(
                "Try clearing the stuck print job:\n\n"
                "1. Open the printer's **print queue** on your device.\n"
                "2. Select only your stuck or failed print job.\n"
                "3. Choose **Cancel**, **Delete**, or **Remove**.\n"
                "4. Confirm that the queue is not paused; choose **Resume** if needed.\n"
                "5. Close and reopen the document, then send a one-page test print.\n"
                "6. Restart the device if the job cannot be removed.\n\n"
                "If the queue remains stuck, contact the IT Helpdesk with the printer name."
            ),
        )

    if "printer works for everyone except me" in normalized or (
        "printer" in normalized
        and "everyone" in normalized
        and any(term in normalized for term in ("except me", "but me", "only me"))
    ):
        return PrinterDecision(
            handled=True,
            answer=(
                "Since the printer works for everyone else, focus on your device:\n\n"
                "1. Confirm that your device is on the approved school Wi-Fi.\n"
                "2. Confirm that the correct printer is selected.\n"
                "3. Open the print queue and remove only your failed jobs.\n"
                "4. Confirm that the queue is not paused.\n"
                "5. Restart the application and try a one-page test print.\n"
                "6. If the printer is missing, the driver or printer may need to be re-added by IT.\n\n"
                "Contact the IT Helpdesk if the problem continues."
            ),
        )

    recent_printer_context = any(
        any(term in normalize_text(str(message.get("content", ""))) for term in (
            "printer", "printing", "print queue"
        ))
        for message in history[-10:]
    )

    if recent_printer_context and normalized in {
        "i already restarted it",
        "already restarted it",
        "i restarted it already",
    }:
        return PrinterDecision(
            handled=True,
            answer=(
                "Since it was already restarted, try the next printer checks:\n\n"
                "1. Confirm that the correct printer is selected.\n"
                "2. Open the print queue and remove only your failed job.\n"
                "3. Confirm that the queue is not paused.\n"
                "4. Verify the device is on the approved school Wi-Fi.\n"
                "5. Send a one-page test print.\n\n"
                "If it still fails, contact the IT Helpdesk or create a ticket."
            ),
        )

    if recent_printer_context and normalized in {
        "it still does not work",
        "it still doesn't work",
        "still does not work",
        "still not working",
    }:
        return PrinterDecision(
            handled=True,
            answer=(
                "The printer issue is still unresolved after the approved checks. "
                "The next step is to contact the IT Helpdesk or create a ticket with "
                "the printer name, device type, and any error message."
            ),
        )

    if any(phrase in normalized for phrase in ("paper jam", "printer jam", "jammed")):
        return PrinterDecision(
            handled=True,
            answer=(
                "Try these safe paper-jam checks:\n\n"
                "1. Stop the print job and read the printer display for the jam location.\n"
                "2. Open only the tray or access panel identified by the printer.\n"
                "3. Gently remove visible paper in the normal paper path; do not force it.\n"
                "4. Check for small torn pieces and reload the paper tray correctly.\n"
                "5. Close all panels and try one test page.\n\n"
                "If paper is not visible, cannot be removed easily, or the warning remains, "
                "stop and contact the IT Helpdesk."
            ),
        )

    # Diagnose explicit printer symptoms before asking setup/location questions.
    if any(phrase in normalized for phrase in ("print preview", "preview")) and any(
        phrase in normalized for phrase in ("blank page", "blank pages", "shows blank", "preview is blank")
    ):
        return PrinterDecision(
            handled=True,
            answer=(
                "Because the document has content but **Chrome's print preview is blank**, first test whether this is browser-specific: reload the page/document, then try printing or saving as PDF from the source app if available. "
                "Also try another approved browser. If the same printer works from another app/browser, the printer itself is probably not the problem. Contact IT if Chrome preview stays blank for required school content."
            ),
        )

    if any(phrase in normalized for phrase in ("sent the same", "five times", "multiple copies", "will it print", "duplicate print")) and "print" in normalized:
        return PrinterDecision(
            handled=True,
            answer=(
                "Yes, queued copies can print later when the printer reconnects. Open the printer's **Print Queue**, cancel the extra jobs, and leave only the copy you actually want. "
                "If pages have already started printing, use the printer's normal Stop/Cancel control for your job; do not power-cycle a shared copier."
            ),
        )

    if any(phrase in normalized for phrase in ("grey line", "gray line", "line down", "streak", "faint line", "smudged")) and "print" in normalized:
        return PrinterDecision(
            handled=True,
            answer=(
                "A repeated line/streak on every page usually points to toner/drum/fuser or another physical print-path issue. Print one simple test page to confirm the pattern. "
                "If the same line appears again, stop troubleshooting from the computer and contact IT/copier support with the printer location and a sample page."
            ),
        )

    if any(phrase in normalized for phrase in ("print in color", "print in colour", "color only", "colour only", "black and white only")):
        return PrinterDecision(
            handled=True,
            answer=(
                "If the printer supports colour, open the print dialog, expand **Show Details/More Settings**, and look for **Color/Colour**, **Quality**, or **Printer Features**. "
                "Choose Colour instead of Black & White/Grayscale. If the option is missing or locked, Altitude should not guess the printer policy or install another driver; contact IT with the printer name/location."
            ),
        )

    if any(phrase in normalized for phrase in ("from my phone", "from my iphone", "from my android", "mobile printing", "print directly from my phone")) and "print" in normalized:
        return PrinterDecision(
            handled=True,
            answer=(
                "Mobile printing is supported only if the school has an approved AirPrint/mobile-print workflow for that printer. Do not install unknown printer apps or drivers. "
                "Tell me the printer name/location; if there is no approved mobile-print method for it, use a school-managed Mac/Chromebook or contact IT."
            ),
        )

    if any(phrase in normalized for phrase in ("isn't showing up", "is not showing up", "not showing up", "can't find the printer", "cant find the printer")) and "printer" in normalized:
        return PrinterDecision(
            handled=True,
            answer=(
                "Confirm the Mac is on the approved school Wi-Fi, then open **System Settings → Printers & Scanners** and search for the exact printer name/location. "
                "If it is a managed printer and still does not appear, contact IT rather than installing an unapproved driver or guessing an IP address."
            ),
        )

    expected_step = get_expected_printer_step(
        history
    )

    if is_printer_supply_request(question):
        if "out of paper" in normalized and any(
            term in normalized for term in ("but", "isn't", "is not", "not empty")
        ):
            return PrinterDecision(
                handled=True,
                answer=(
                    "If the printer says **Out of Paper** even though paper is loaded:\n\n"
                    "1. Remove and reseat the paper stack so it sits flat under the tray guides.\n"
                    "2. Confirm the tray is fully closed.\n"
                    "3. Check the printer display for the specific tray or paper size it is requesting.\n"
                    "4. Make sure the selected paper size/type matches the loaded tray.\n"
                    "5. Try one test page.\n\n"
                    "If the warning remains, do not force the tray or sensors; contact the IT Helpdesk for service."
                ),
            )
        return PrinterDecision(
            handled=True,
            answer=(
                "Printer paper and supply locations vary by printer. Check the printer display "
                "for the requested tray or supply, and contact the IT Helpdesk or the staff member "
                "responsible for that area if the correct supply is not available."
            ),
        )

    explicit = has_explicit_printer_reference(question)
    recent_printer_context = recent_printer_context or has_explicit_printer_reference(
        effective_normalized
    )
    current_device = detect_device(question)
    current_action = detect_action(question)

    if (
        expected_step
        and normalized
        in {
            "yes",
            "yeah",
            "yep",
            "no",
            "nope",
        }
    ):
        if expected_step == "action":
            return PrinterDecision(
                handled=True,
                answer=(
                    "Please reply with **add** or "
                    "**already added**."
                ),
            )

        if expected_step == "printer":
            return PrinterDecision(
                handled=True,
                answer=(
                    "Please choose "
                    "**Learning Commons / Library printer** "
                    "or **another school printer**."
                ),
            )

        if expected_step == "device":
            return PrinterDecision(
                handled=True,
                answer=(
                    "Please reply with **Mac** or "
                    "**Chromebook**."
                ),
            )

    context_sensitive_reply = (
        recent_printer_context
        and (
            current_device is not None
            or current_action is not None
            or len(normalized.split()) <= 8
            and any(
                phrase in normalized
                for phrase in (
                    "offline",
                    "not showing",
                    "won't show",
                    "won't even show",
                    "wont show",
                    "wont even show",
                    "missing",
                    "stuck",
                    "still",
                )
            )
        )
    )

    if (
        not explicit
        and not valid_workflow_reply(question, expected_step)
        and not context_sensitive_reply
    ):
        return PrinterDecision(handled=False)

    failed = failure_follow_up(
        question,
        history,
    )

    if failed == "setup":
        return PrinterDecision(
            handled=True,
            answer=(
                "The printer setup could not be "
                "completed. Please visit the IT Helpdesk "
                "so the IT team can finish adding the printer."
            ),
        )

    if failed == "printing":
        return PrinterDecision(
            handled=True,
            answer=(
                "The approved printing checks did not "
                "resolve the issue. Please visit or contact "
                "the IT Helpdesk for further assistance."
            ),
        )

    if is_learning_commons_wifi_question(
        question
    ):
        return PrinterDecision(
            handled=True,
            answer=(
                "The Learning Commons or Library printer "
                "works while connected to either "
                "**SJK Wi-Fi** or **Student Wi-Fi**."
            ),
        )

    if (
        expected_step is None
        and is_ambiguous_connect_request(
            question
        )
    ):
        return PrinterDecision(
            handled=True,
            answer=(
                "When you say connect, do you mean:\n\n"
                "- **Add** the printer to your device, or\n"
                "- Troubleshoot a printer that is "
                "**already added**?\n\n"
                "Reply with **add** or "
                "**already added**."
            ),
        )

    action = detect_action(question)
    printer = detect_printer(question)
    device = detect_device(question)

    if printer is None and recent_printer_context:
        printer = find_recent_printer(history, question)
    if action is None and recent_printer_context:
        action = find_recent_action(history, question)
    if device is None and recent_printer_context:
        device = find_recent_device(history, question)

    if (
        expected_step == "action"
        and printer is None
    ):
        printer = find_recent_printer(
            history,
            question,
        )

    elif (
        expected_step == "printer"
        and action is None
    ):
        action = find_recent_action(
            history,
            question,
        )

    elif expected_step == "device":
        if action is None:
            action = find_recent_action(
                history,
                question,
            )

        if printer is None:
            printer = find_recent_printer(
                history,
                question,
            )

    if printer is None:
        prompt_intro = (
            "Which printer is showing **Offline**?"
            if "offline" in normalized
            else "Which printer are you trying to use?"
        )
        return PrinterDecision(
            handled=True,
            answer=(
                f"{prompt_intro}\n\n"
                "- **Learning Commons / Library printer**\n"
                "- **Another school printer**"
            ),
        )

    if action is None:
        return PrinterDecision(
            handled=True,
            answer=(
                "Please clarify whether you want to:\n\n"
                "- **Add** the printer to your device, or\n"
                "- Troubleshoot a printer that is "
                "**already added**."
            ),
        )

    if (
        action == "add"
        and printer == "other"
    ):
        return PrinterDecision(
            handled=True,
            answer=(
                "Please visit the IT Helpdesk. "
                "The IT team will add the correct "
                "staff printer to your device."
            ),
        )

    if (
        action == "add"
        and printer == "learning_commons"
    ):
        if device is None:
            return PrinterDecision(
                handled=True,
                answer=(
                    "Are you using a **Mac** or a **Chromebook**?"
                ),
            )

        if device == "unsupported_windows":
            return PrinterDecision(
                handled=True,
                answer=(
                    "Windows devices are not part of the school's supported "
                    "printing environment. Please contact the IT Helpdesk if this "
                    "is a school-managed device."
                ),
            )

        return PrinterDecision(
            handled=True,
            answer=(
                mac_setup_instructions()
                if device == "mac"
                else chromebook_setup_instructions()
            ),
        )

    if (
        action == "troubleshoot"
        and printer == "learning_commons"
        and device == "mac"
    ):
        return PrinterDecision(
            handled=True,
            answer=(
                "On your **Mac**, confirm you are on **SJK Wi-Fi** or **Student Wi-Fi**. "
                "Then open **System Settings → Printers & Scanners** and check whether the "
                "Learning Commons printer appears. If it appears, open its queue, resume it "
                "if paused, remove only your failed job, and try a one-page test print. If the "
                "printer is missing from the list, tell me that and I can give the setup steps."
            ),
        )

    if (
        action == "troubleshoot"
        and printer == "learning_commons"
    ):
        return PrinterDecision(
            handled=True,
            answer=(
                "Please confirm that your device is connected "
                "to either **SJK Wi-Fi** or "
                "**Student Wi-Fi**. Then:\n\n"
                "1. Open the document you want to print.\n"
                "2. Confirm that the Learning Commons printer "
                "is selected.\n"
                "3. Try printing again."
            ),
        )

    if (
        action == "troubleshoot"
        and printer == "other"
    ):
        return PrinterDecision(
            handled=True,
            answer=(
                "Please confirm that your device is connected "
                "to **SJK Wi-Fi**. Then:\n\n"
                "1. Open the document you want to print.\n"
                "2. Confirm that the correct school printer "
                "is selected.\n"
                "3. Try printing again."
            ),
        )

    return PrinterDecision(
        handled=True,
        answer=(
            "I could not determine the requested printer "
            "action. Please reply with **add** or "
            "**already added**."
        ),
    )