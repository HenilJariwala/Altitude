from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.conversation_context import (
    find_recent_user_issue,
    recent_user_messages as context_recent_user_messages,
)
from core.platform_context import (
    detect_platform,
    is_platform_only_reply,
    platform_display_name,
)
from core.text_matching import (
    contains_any_phrase,
    normalize_text,
)


@dataclass(frozen=True)
class SupportPreparation:
    """Security handling and device-context preparation."""

    handled: bool = False
    answer: str = ""
    retrieval_question: str = ""


CLOUD_AND_WEB_SERVICES = (
    "google docs",
    "google sheets",
    "google slides",
    "google drive",
    "google classroom",
    "google calendar",
    "google forms",
    "gmail",
    "sharepoint",
    "microsoft 365",
    "office 365",
)

DESKTOP_PRODUCTIVITY_APPS = (
    "microsoft word",
    "word",
    "microsoft excel",
    "excel",
    "microsoft powerpoint",
    "powerpoint",
    "microsoft outlook",
    "outlook",
    "microsoft teams",
    "teams",
    "onedrive",
)

DEVICE_COMPONENTS = (
    "laptop",
    "computer",
    "desktop",
    "macbook",
    "microphone",
    "mic",
    "camera",
    "speaker",
    "sound",
    "audio",
    "keyboard",
    "mouse",
    "trackpad",
    "monitor",
    "display",
    "screen",
    "usb",
    "external drive",
    "flash drive",
    "printer",
    "bluetooth",
    "battery",
    "charger",
)

DESKTOP_CLIENT_SIGNALS = (
    "desktop app",
    "desktop application",
    "application",
    "sync client",
    "file explorer",
    "finder",
    "launch",
    "opening",
    "crashing",
    "freezing",
    "syncing",
)

PROBLEM_SIGNALS = (
    "not working",
    "does not work",
    "doesn't work",
    "doesnt work",
    "not opening",
    "won't open",
    "wont open",
    "cannot open",
    "can't open",
    "cant open",
    "not responding",
    "not syncing",
    "sync failed",
    "not detected",
    "not showing",
    "no sound",
    "no audio",
    "microphone not working",
    "camera not working",
    "crashing",
    "freezing",
    "frozen",
    "running slow",
    "very slow",
    "disconnecting",
    "failed",
    "error",
    "problem",
    "issue",
)

OS_DEPENDENT_ACTION_SIGNALS = (
    "force quit",
    "force close",
    "end task",
    "app will not close",
    "app won't close",
    "application will not close",
    "application won't close",
    "program will not close",
    "program won't close",
    "restart my computer",
    "restart the computer",
    "reboot my computer",
    "reboot the computer",
    "shut down my computer",
    "shut down the computer",
    "shutdown my computer",
    "shutdown the computer",
)

SPECIFIC_SYMPTOMS = (
    "no sound",
    "no audio",
    "not working",
    "not responding",
    "not showing",
    "not detected",
    "will not turn on",
    "won't turn on",
    "wont turn on",
    "will not start",
    "won't start",
    "wont start",
    "not charging",
    "draining",
    "running slow",
    "very slow",
    "freezing",
    "frozen",
    "crashing",
    "stuck",
    "disconnecting",
    "wrong characters",
    "blurry",
    "missing",
    "cannot open",
    "can't open",
    "cant open",
    "cannot delete",
    "can't delete",
    "cant delete",
    "update failed",
    "update stuck",
    "error",
)


VAGUE_DEVICE_PHRASES = (
    "laptop is not working",
    "laptop not working",
    "computer is not working",
    "computer not working",
    "device is not working",
    "device not working",
    "my laptop broke",
    "my computer broke",
    "laptop has a problem",
    "computer has a problem",
    "something is wrong with my laptop",
    "something is wrong with my computer",
)


FAILED_FOLLOW_UPS = (
    "still not working",
    "that did not work",
    "that didn't work",
    "it did not work",
    "it didn't work",
    "same issue",
    "problem continues",
    "issue continues",
)


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


def recent_user_messages(
    history: list[dict[str, Any]],
    current_question: str,
) -> list[str]:
    """Return recent user messages excluding the current question."""

    return context_recent_user_messages(
        history,
        current_question,
    )


def detect_operating_system(
    text: str,
) -> str | None:
    platform = detect_platform(text)

    if platform is None:
        return None

    return platform_display_name(platform)


def is_os_only_reply(
    text: str,
) -> bool:
    return is_platform_only_reply(text)


def is_vague_device_problem(
    text: str,
) -> bool:
    normalized = normalize_text(text)

    return any(phrase in normalized for phrase in VAGUE_DEVICE_PHRASES)


def has_specific_symptom(
    text: str,
) -> bool:
    normalized = normalize_text(text)

    return any(phrase in normalized for phrase in SPECIFIC_SYMPTOMS)


def needs_operating_system(
    text: str,
) -> bool:
    """
    Ask Mac or Windows only when the issue is genuinely
    device or desktop-application dependent.
    """

    if detect_operating_system(text):
        return False

    normalized = normalize_text(text)

    has_problem = contains_any_phrase(
        normalized,
        (
            *PROBLEM_SIGNALS,
            *OS_DEPENDENT_ACTION_SIGNALS,
        ),
    )

    # Instructional questions never require an OS.
    if not has_problem:
        return False

    has_device_component = contains_any_phrase(
        normalized,
        DEVICE_COMPONENTS,
    )

    has_desktop_app = contains_any_phrase(
        normalized,
        DESKTOP_PRODUCTIVITY_APPS,
    )

    has_desktop_client_signal = contains_any_phrase(
        normalized,
        DESKTOP_CLIENT_SIGNALS,
    )

    has_cloud_service = contains_any_phrase(
        normalized,
        CLOUD_AND_WEB_SERVICES,
    )

    # Browser/cloud problems normally use cross-platform steps.
    if has_cloud_service and not has_device_component and not has_desktop_client_signal:
        return False

    return has_device_component or (has_desktop_app and has_desktop_client_signal)


def is_google_password_request(
    text: str,
) -> bool:
    normalized = normalize_text(text)

    account_context = any(
        term in normalized
        for term in (
            "google",
            "gmail",
            "school email",
            "email",
            "email account",
            "school account",
        )
    )

    password_context = "password" in normalized and any(
        term in normalized
        for term in (
            "forgot",
            "reset",
            "not working",
            "incorrect",
            "expired",
            "change",
            "new password",
        )
    )

    sign_in_context = any(
        term in normalized
        for term in (
            "cannot sign in",
            "can't sign in",
            "cant sign in",
            "cannot log in",
            "can't log in",
            "cant log in",
            "locked out",
        )
    )

    return account_context and (password_context or sign_in_context)


def route_security_or_account_question(
    text: str,
) -> SupportPreparation:
    normalized = normalize_text(text)

    suspicious_terms = (
        "phishing",
        "suspicious email",
        "weird email",
        "fake email",
        "scam email",
        "gift card email",
        "unknown sender",
        "impersonating",
        "spam email",
    )

    interaction_terms = (
        "clicked the link",
        "clicked a link",
        "opened the link",
        "opened the attachment",
        "downloaded the attachment",
        "downloaded a file",
        "entered my password",
        "submitted my password",
        "entered credentials",
        "gave my password",
    )

    suspicious = any(term in normalized for term in suspicious_terms)

    interacted = any(term in normalized for term in interaction_terms)

    if suspicious and interacted:
        return SupportPreparation(
            handled=True,
            answer=(
                "Because you interacted with a suspicious email, "
                "please contact the IT Helpdesk immediately. "
                "Do not continue using the message, and do not "
                "enter any additional information."
            ),
        )

    if suspicious:
        return SupportPreparation(
            handled=True,
            answer=(
                "Do not click any links or download attachments. "
                "If the message is obvious spam, delete it. If it "
                "impersonates someone at the school or asks for "
                "passwords, money, or gift cards, report it to "
                "the IT Helpdesk immediately."
            ),
        )

    if is_google_password_request(text):
        return SupportPreparation(
            handled=True,
            answer=(
                "Please visit the IT Helpdesk so the IT team can "
                "verify your request and assist with your school "
                "Google account password. Do not share your "
                "current password or verification codes in chat."
            ),
        )

    return SupportPreparation()


def _last_prompt_asked_for_os(
    history: list[dict[str, Any]],
) -> bool:
    last_assistant = get_last_assistant_message(history)

    if not (
        contains_any_phrase(last_assistant, ("mac", "macos"))
        and contains_any_phrase(last_assistant, ("windows", "pc"))
    ):
        return False

    return any(
        marker in last_assistant
        for marker in (
            "are you using",
            "please reply",
            "which operating system",
            "mac or windows",
            "windows device or a mac",
        )
    )


def _last_answer_used_opposite_platform(
    history: list[dict[str, Any]],
    platform: str,
) -> bool:
    """Detect a short platform correction after OS-specific steps."""

    last_assistant = get_last_assistant_message(history)

    windows_markers = (
        "task manager",
        "end task",
        "windows update",
        "file explorer",
        "start menu",
    )
    mac_markers = (
        "force quit",
        "option command escape",
        "system settings",
        "finder",
        "activity monitor",
    )

    if platform == "macos":
        return contains_any_phrase(last_assistant, windows_markers)

    if platform == "windows":
        return contains_any_phrase(last_assistant, mac_markers)

    return False


def _last_prompt_asked_for_symptom(
    history: list[dict[str, Any]],
) -> bool:
    last_assistant = get_last_assistant_message(history)

    return "what exactly is happening" in last_assistant


def _recent_os(
    history: list[dict[str, Any]],
    current_question: str,
) -> str | None:
    for content in recent_user_messages(
        history,
        current_question,
    ):
        os_name = detect_operating_system(content)

        if os_name:
            return os_name

    return None


def _recent_problem(
    history: list[dict[str, Any]],
    current_question: str,
) -> str:
    return find_recent_user_issue(
        history,
        current_question,
    )


def _recent_assistant_had_steps(
    history: list[dict[str, Any]],
) -> bool:
    last_assistant = get_last_assistant_message(history)

    return (
        "1." in last_assistant
        or "troubleshooting steps" in last_assistant
        or "try these steps" in last_assistant
    )


def prepare_support_question(
    question: str,
    history: list[dict[str, Any]],
) -> SupportPreparation:
    """Prepare a platform-aware query or clarification response."""

    normalized = normalize_text(question)

    if any(
        phrase in normalized for phrase in FAILED_FOLLOW_UPS
    ) and _recent_assistant_had_steps(history):
        return SupportPreparation(
            handled=True,
            answer=(
                "The approved troubleshooting steps did not "
                "resolve the issue. Please contact or visit "
                "the IT Helpdesk for further assistance."
            ),
        )

    platform_reply = (
        detect_platform(question) if is_platform_only_reply(question) else None
    )

    if platform_reply is not None:
        os_name = platform_display_name(platform_reply)
        has_issue_context = (
            _last_prompt_asked_for_os(history)
            or _last_answer_used_opposite_platform(
                history,
                platform_reply,
            )
        )

        if has_issue_context:
            previous_problem = _recent_problem(
                history,
                question,
            )

            if previous_problem:
                if is_vague_device_problem(previous_problem):
                    return SupportPreparation(
                        handled=True,
                        answer=(
                            f"Thanks — you are using a **{os_name}**. "
                            "What exactly is happening?\n\n"
                            "For example:\n"
                            "- It will not turn on\n"
                            "- It is frozen or running slowly\n"
                            "- It has no sound or internet\n"
                            "- It is not charging\n"
                            "- A monitor, USB device, file, or "
                            "application is not working"
                        ),
                    )

                return SupportPreparation(
                    retrieval_question=(
                        f"{previous_problem}\n"
                        f"Operating system: {os_name}"
                    ),
                )

        # A platform name by itself is not enough to choose a random
        # procedure. Ask for the actual issue when no OS prompt or clear
        # platform correction preceded it.
        return SupportPreparation(
            handled=True,
            answer=(
                f"Thanks — you are using a **{os_name}**. "
                "What IT issue do you need help with?"
            ),
        )

    if _last_prompt_asked_for_symptom(history):
        os_name = _recent_os(
            history,
            question,
        )

        if os_name and not is_os_only_reply(question):
            return SupportPreparation(
                retrieval_question=(f"{question}\nOperating system: {os_name}"),
            )

    if is_vague_device_problem(question):
        os_name = detect_operating_system(question)

        if os_name:
            return SupportPreparation(
                handled=True,
                answer=(
                    f"I understand that you are using a "
                    f"**{os_name}**. What exactly is happening?\n\n"
                    "For example:\n"
                    "- It will not turn on\n"
                    "- It is frozen or running slowly\n"
                    "- It has no sound or internet\n"
                    "- It is not charging\n"
                    "- A monitor, USB device, file, or "
                    "application is not working"
                ),
            )

        return SupportPreparation(
            handled=True,
            answer=(
                "Please provide two details so I can give the "
                "correct troubleshooting steps:\n\n"
                "1. Are you using a **Mac** or a "
                "**Windows device**?\n"
                "2. What exactly is happening? For example, "
                "it will not turn on, it is frozen, it has no "
                "sound, it is not charging, or a device is "
                "not detected."
            ),
        )

    if needs_operating_system(question):
        return SupportPreparation(
            handled=True,
            answer=("Are you using a **Mac** or a **Windows device**?"),
        )

    return SupportPreparation(retrieval_question=question)
