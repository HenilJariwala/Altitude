from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.text_matching import normalize_text


@dataclass(frozen=True)
class WifiDecision:
    handled: bool
    answer: str = ""
    resource: str | None = None
    caption: str | None = None


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


def detect_role(
    text: str,
) -> str | None:
    normalized = normalize_text(text)

    if any(
        term in normalized
        for term in (
            "student",
            "student wifi",
            "student network",
        )
    ):
        return "student"

    if any(
        term in normalized
        for term in (
            "guest",
            "visitor",
            "guest wifi",
            "guest network",
            "contractor",
        )
    ):
        return "guest"

    return None


def contains_wifi_topic(
    text: str,
) -> bool:
    normalized = normalize_text(text)

    terms = (
        "wifi",
        "wireless",
        "school network",
        "guest network",
        "student network",
        "wifi qr",
        "network password",
        "internet connection",
        "no internet",
    )

    return any(
        term in normalized
        for term in terms
    )


def detect_connection_problem(
    text: str,
) -> bool:
    normalized = normalize_text(text)

    terms = (
        "not connecting",
        "cannot connect",
        "can't connect",
        "cant connect",
        "unable to connect",
        "not working",
        "does not work",
        "doesn't work",
        "keeps disconnecting",
        "connection failed",
        "no internet",
        "connected but no internet",
        "not showing",
        "network is not appearing",
        "network is not visible",
        "cannot find network",
        "can't find network",
        "cant find network",
        "keeps dropping",
        "weak signal",
        "offline",
    )

    return any(
        term in normalized
        for term in terms
    )


def detect_password_or_access_request(
    text: str,
) -> bool:
    normalized = normalize_text(text)

    terms = (
        "wifi password",
        "network password",
        "connect to wifi",
        "join wifi",
        "wifi qr",
        "wireless access",
        "school wifi",
    )

    return any(
        term in normalized
        for term in terms
    )


def waiting_for_role(
    history: list[dict[str, Any]],
) -> bool:
    last_assistant = get_last_assistant_message(
        history
    )

    markers = (
        "connecting as a student or as a guest",
        "student or as a guest",
        "student wifi or guest wifi",
        "student or guest",
    )

    return any(
        marker in last_assistant
        for marker in markers
    )


def recent_wifi_mode(
    history: list[dict[str, Any]],
    current_question: str,
) -> str:
    current = normalize_text(
        current_question
    )

    for message in reversed(
        history[-10:]
    ):
        if message.get("role") != "user":
            continue

        content = str(
            message.get(
                "content",
                "",
            )
        )

        if normalize_text(content) == current:
            continue

        if detect_connection_problem(content):
            return "troubleshoot"

        if (
            detect_password_or_access_request(
                content
            )
            or contains_wifi_topic(content)
        ):
            return "access"

    return "access"


def unresolved_wifi_follow_up(
    question: str,
    history: list[dict[str, Any]],
) -> bool:
    normalized = normalize_text(question)

    failure_terms = (
        "still not working",
        "still cannot connect",
        "still can't connect",
        "that did not work",
        "that didn't work",
        "same issue",
    )

    if not any(
        term in normalized
        for term in failure_terms
    ):
        return False

    last_assistant = get_last_assistant_message(
        history
    )

    return (
        "forget this network"
        in last_assistant
        or "scan the"
        in last_assistant
    )


def route_wifi_question(
    question: str,
    history: list[dict[str, Any]],
) -> WifiDecision:
    """Handle Student and Guest Wi-Fi without the LLM."""

    if unresolved_wifi_follow_up(
        question,
        history,
    ):
        return WifiDecision(
            handled=True,
            answer=(
                "The approved Wi-Fi troubleshooting steps "
                "did not resolve the issue. Please visit or "
                "contact the IT Helpdesk for further assistance."
            ),
        )

    role = detect_role(question)

    explicit_wifi = contains_wifi_topic(
        question
    )

    role_follow_up = (
        role is not None
        and waiting_for_role(history)
    )

    if (
        not explicit_wifi
        and not role_follow_up
    ):
        return WifiDecision(
            handled=False
        )

    mode = (
        "troubleshoot"
        if detect_connection_problem(question)
        else "access"
    )

    if role_follow_up:
        mode = recent_wifi_mode(
            history,
            question,
        )

    if role is None:
        prompt = (
            "Are you connecting to "
            "**Student Wi-Fi** or **Guest Wi-Fi**?"
            if mode == "troubleshoot"
            else (
                "Are you connecting as a "
                "**student** or as a **guest**?"
            )
        )

        return WifiDecision(
            handled=True,
            answer=prompt,
        )

    if role == "student":
        network_name = "Student Wi-Fi"
        resource = "student_wifi_qr.png"
        caption = "Student Wi-Fi QR Code"

    else:
        network_name = "Guest Wi-Fi"
        resource = "guest_wifi_qr.png"
        caption = "Guest Wi-Fi QR Code"

    if mode == "troubleshoot":
        return WifiDecision(
            handled=True,
            answer=(
                f"Try these approved steps for "
                f"**{network_name}**:\n\n"
                "1. Open the Wi-Fi settings on the device.\n"
                "2. Confirm that Wi-Fi is turned on.\n"
                "3. Select the existing school Wi-Fi network.\n"
                "4. Choose **Forget This Network** or "
                "**Forget Network**.\n"
                "5. Turn Wi-Fi off and then back on.\n"
                "6. Restart the device.\n"
                "7. Confirm that the date, time, and time "
                "zone are correct.\n"
                f"8. Scan the **{network_name} QR code** "
                "below again.\n"
                "9. Accept the connection prompt and "
                "try again.\n\n"
                "If the issue continues, please contact "
                "the IT Helpdesk."
            ),
            resource=resource,
            caption=caption,
        )

    return WifiDecision(
        handled=True,
        answer=(
            "For security reasons, the Wi-Fi password is "
            "not provided as plain text.\n\n"
            f"Please scan the **{network_name} QR code** "
            "below to connect."
        ),
        resource=resource,
        caption=caption,
    )