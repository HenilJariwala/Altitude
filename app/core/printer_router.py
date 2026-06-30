from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.platform_context import detect_platform
from core.text_matching import normalize_text


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

    if any(
        marker in last_assistant
        for marker in (
            "are you using a mac or a windows laptop",
            "are you using a windows laptop or a mac",
            "reply with mac or windows",
        )
    ):
        return "device"

    return None


def is_printer_supply_request(
    question: str,
) -> bool:
    normalized = normalize_text(question)

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
        "print job",
        "printer unavailable",
        "printer is not responding",
        "offline",
    )

    if any(
        phrase in normalized
        for phrase in troubleshoot_phrases
    ):
        return "troubleshoot"

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
        or normalized in {
            "library",
            "kyocera",
        }
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

    if platform == "windows":
        return "windows"

    normalized = normalize_text(text)

    if normalized in {"mc", "mack"}:
        return "mac"

    if normalized in {"win", "window"}:
        return "windows"

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


def windows_setup_instructions() -> str:
    return (
        "Make sure your Windows laptop is connected "
        "to either **SJK Wi-Fi** or "
        "**Student Wi-Fi**.\n\n"
        "1. Open **Settings → Bluetooth & devices "
        "→ Printers & scanners**.\n"
        "2. Click **Add device**.\n"
        "3. If the printer does not appear, select "
        "**Add manually**.\n"
        "4. Choose **Add a printer using an IP "
        "address or hostname**.\n"
        "5. Set Device type to **TCP/IP Device**.\n"
        f"6. Enter **{LEARNING_COMMONS_IP}**.\n"
        "7. Allow Windows to detect the Kyocera "
        "printer.\n"
        "8. Complete setup and print a test page.\n\n"
        "If administrator credentials or an "
        "unapproved driver are requested, please "
        "visit the IT Helpdesk."
    )


def route_printer_question(
    question: str,
    history: list[dict[str, Any]],
) -> PrinterDecision:
    normalized = normalize_text(question)

    expected_step = get_expected_printer_step(
        history
    )

    if is_printer_supply_request(question):
        return PrinterDecision(
            handled=True,
            answer=(
                "Printer paper and supply locations vary "
                "by printer. Please contact the IT Helpdesk "
                "or the staff member responsible for that area."
            ),
        )

    explicit = has_explicit_printer_reference(
        question
    )

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
                    "**Windows**."
                ),
            )

    if (
        not explicit
        and not valid_workflow_reply(
            question,
            expected_step,
        )
    ):
        return PrinterDecision(
            handled=False
        )

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
        return PrinterDecision(
            handled=True,
            answer=(
                "Which printer are you trying to use?\n\n"
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
                    "Are you using a **Mac** or a "
                    "**Windows laptop**?"
                ),
            )

        return PrinterDecision(
            handled=True,
            answer=(
                mac_setup_instructions()
                if device == "mac"
                else windows_setup_instructions()
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