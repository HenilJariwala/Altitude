from __future__ import annotations

import base64
import re
import time
import uuid
from datetime import datetime, timezone
from dataclasses import asdict
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st

from core.analytics_db import (
    apply_ticket_status_updates,
    close_conversation,
    create_conversation,
    create_ticket_audit,
    ensure_ticket_altitude_reference,
    get_feedback_for_session,
    get_ticket_by_altitude_reference,
    log_security_event,
    log_unauthorized_ticket_attempt,
    initialize_database,
    normalize_altitude_reference,
    mark_ticket_submission_failed,
    mark_ticket_submitted,
    record_ticket_status_sync_error,
    save_feedback,
    save_message,
)
from core.assistant import prepare_answer, stream_answer
from core.escalation_router import user_requests_escalation as _core_user_requests_escalation
from core.feedback_policy import is_feedback_eligible_response as _core_feedback_eligible
from core.knowledge_queue import sync_resolved_tickets_to_knowledge_queue
from core.resolution_notifications import process_pending_resolution_notifications
from core.platform_context import detect_platform
from core.question_logger import redact_sensitive_information
from core.time_utils import get_local_timezone, local_now
from core.ticketing_client import (
    TicketPayload,
    TicketingClientError,
    fetch_ticket_statuses,
    is_authorized_school_email,
    parse_email_address,
    payload_with_altitude_reference,
    submit_ticket,
    validate_school_email,
)
from ui.layout import STATIC_DIRECTORY, image_data_uri


MAX_CHAT_MESSAGES = 80
OPENING_MESSAGE = (
    "👋 Hi! I’m Altitude — your IT Support Assistant.\n\n"
    "How can I help you?"
)

LOADING_GIF_PATH = (
    Path(__file__).resolve().parents[1]
    / "static"
    / "ai-loading.gif"
)

# Assistant responses that ask the user for missing information should not
# receive Helpful / Not Helpful controls in Feature 2.
CLARIFICATION_PREFIXES = (
    "are you using",
    "are you connecting",
    "for this wi-fi issue, are you",
    "can you tell me",
    "could you tell me",
    "please tell me",
    "please clarify",
    "what would you like",
    "what device",
    "what service",
    "what screen",
    "what printer",
    "what are you trying",
    "which device",
    "which service",
    "which operating system",
    "which printer",
    "which approved wi-fi",
    "which inventory item",
    "do you need",
    "yes. what technology",
    "thanks — you are using",
)

NEGATIVE_FEEDBACK_REASONS = (
    "Did not understand my question",
    "Incorrect instructions",
    "Wrong device or platform",
    "Steps did not work",
    "Missing information",
    "Other",
)



NON_TICKET_FEEDBACK_INTENTS = {
    "google_password_reset",
    "microsoft_password_recovery",
}

TICKET_ESCALATION_PREFIXES = (
    "i can help with it-related issues, but i do not have an approved procedure",
    "i could not complete that request",
)

EXPLICIT_ESCALATION_PHRASES = (
    "create a ticket",
    "create a helpdesk ticket",
    "create an it ticket",
    "want to create a helpdesk ticket",
    "want to create a ticket",
    "create ticket",
    "open a ticket",
    "submit a ticket",
    "escalate this",
    "escalate to it",
    "talk to it",
    "contact it",
    "contact the helpdesk",
    "human support",
    "does not know how to fix",
    "doesn't know how to fix",
    "cannot resolve",
    "can't resolve",
)

SCHOOL_EMAIL_HELP = (
    "Use your @sjkeagles.com or @sjkschool.org email address."
)

SECURITY_MISUSE_RULES: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    (
        "Prompt manipulation",
        "High",
        "Attempt to bypass or reveal assistant instructions",
        (
            "ignore previous instructions",
            "ignore all instructions",
            "reveal your system prompt",
            "show your system prompt",
            "show the developer message",
            "reveal the developer message",
            "jailbreak",
            "bypass your rules",
            "disable your safeguards",
        ),
    ),
    (
        "Credential access",
        "Critical",
        "Attempt to obtain passwords, tokens, or service credentials",
        (
            "show me the password",
            "give me the password",
            "reveal the password",
            "show me the api key",
            "give me the api key",
            "reveal the api key",
            "show me the api token",
            "give me the api token",
            "reveal the api token",
            "database password",
            "login credentials",
            "admin credentials",
        ),
    ),
    (
        "Destructive request",
        "Critical",
        "Potential request to damage, disable, or flood school systems",
        (
            "delete the database",
            "drop table",
            "wipe the database",
            "disable security",
            "ddos",
            "denial of service",
            "spam tickets",
            "flood tickets",
            "create hundreds of tickets",
        ),
    ),
    (
        "Unauthorized access",
        "High",
        "Potential attempt to bypass access controls or impersonate another user",
        (
            "bypass login",
            "bypass authentication",
            "impersonate",
            "use someone else's account",
            "use someone elses account",
            "use someone else's email",
            "access another user's",
        ),
    ),
    (
        "Bulk data request",
        "High",
        "Potential attempt to extract protected school or user information",
        (
            "dump all student",
            "export all student",
            "list all passwords",
            "download all user data",
            "show all student records",
            "give me everyone email",
        ),
    ),
)


# ---------------------------------------------------------------------------
# Analytics and conversation-session helpers
# ---------------------------------------------------------------------------


def _print_analytics_error(action: str, error: Exception) -> None:
    """Log an analytics failure without breaking the support chat."""
    print(
        f"Analytics {action} failed: "
        f"{type(error).__name__}: {error}"
    )


def _ensure_analytics_database() -> bool:
    """Initialize SQLite once per Streamlit browser session."""
    if st.session_state.get("analytics_database_ready"):
        return True

    try:
        initialize_database()
    except Exception as error:
        _print_analytics_error("database initialization", error)
        return False

    st.session_state.analytics_database_ready = True
    return True


def _ensure_session_id() -> str:
    """Return one stable analytics session ID for the current chat."""
    session_id = st.session_state.get("session_id")

    if not isinstance(session_id, str) or not session_id.strip():
        session_id = str(uuid.uuid4())
        st.session_state.session_id = session_id
        st.session_state.analytics_conversation_registered = False

    return session_id


def _ensure_conversation_record() -> bool:
    """Create the current conversation row once."""
    if not _ensure_analytics_database():
        return False

    if st.session_state.get("analytics_conversation_registered"):
        return True

    session_id = _ensure_session_id()

    try:
        create_conversation(session_id)
    except Exception as error:
        _print_analytics_error("conversation creation", error)
        return False

    st.session_state.analytics_conversation_registered = True
    return True


def _save_message_safely(message: dict[str, Any]) -> bool:
    """Persist one chat message without allowing analytics to stop chat."""
    if message.get("analytics_saved") is True:
        return True

    if not _ensure_conversation_record():
        return False

    try:
        save_message(
            message_id=str(message["message_id"]),
            session_id=str(st.session_state.session_id),
            role=str(message.get("role", "assistant")),
            content=str(message.get("content", "")),
            route=_optional_string(message.get("route")),
            intent=_optional_string(message.get("intent")),
            platform=_optional_string(message.get("platform")),
            source_document=_optional_string(
                message.get("source_document")
            ),
            feedback_eligible=bool(
                message.get("feedback_eligible", False)
            ),
        )
    except Exception as error:
        _print_analytics_error("message save", error)
        return False

    message["analytics_saved"] = True
    return True


def _optional_string(value: Any) -> str | None:
    """Convert a non-empty value to text for SQLite metadata fields."""
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _prepare_legacy_messages() -> None:
    """
    Upgrade messages already present in Streamlit session state.

    This is useful when the code is deployed while a browser session from the
    previous chat implementation is still open.
    """
    messages = st.session_state.get("chat_messages")

    if not isinstance(messages, list):
        st.session_state.chat_messages = []
        return

    for message in messages:
        if not isinstance(message, dict):
            continue

        message.setdefault("message_id", str(uuid.uuid4()))
        message.setdefault("route", None)
        message.setdefault("intent", None)
        message.setdefault("platform", None)
        message.setdefault("source_document", None)
        message.setdefault("feedback_eligible", False)
        message.setdefault("analytics_saved", False)


def _sync_unsaved_messages() -> None:
    """Retry any message writes that previously failed."""
    messages = st.session_state.get("chat_messages", [])

    if not isinstance(messages, list):
        return

    for message in messages:
        if isinstance(message, dict):
            _save_message_safely(message)


def _ensure_feedback_cache() -> dict[str, dict[str, Any]]:
    """Load feedback for the current conversation once per session."""
    session_id = _ensure_session_id()
    cached_session_id = st.session_state.get(
        "feedback_cache_session_id"
    )
    cached_feedback = st.session_state.get("feedback_by_message")

    if (
        cached_session_id == session_id
        and isinstance(cached_feedback, dict)
    ):
        return cached_feedback

    feedback_by_message: dict[str, dict[str, Any]] = {}

    if _ensure_conversation_record():
        try:
            feedback_by_message = get_feedback_for_session(session_id)
        except Exception as error:
            _print_analytics_error("feedback load", error)

    st.session_state.feedback_cache_session_id = session_id
    st.session_state.feedback_by_message = feedback_by_message
    return feedback_by_message


def _save_feedback_safely(
    *,
    message: dict[str, Any],
    helpful: bool,
    reason: str | None = None,
    comment: str | None = None,
) -> bool:
    """Persist feedback and update the in-memory feedback cache."""
    if not _save_message_safely(message):
        return False

    message_id = str(message.get("message_id", "")).strip()
    session_id = str(st.session_state.get("session_id", "")).strip()

    if not message_id or not session_id:
        return False

    try:
        feedback_record = save_feedback(
            message_id=message_id,
            session_id=session_id,
            helpful=helpful,
            reason=reason,
            comment=comment,
        )
    except Exception as error:
        _print_analytics_error("feedback save", error)
        st.session_state.feedback_error_for = message_id
        return False

    feedback_cache = _ensure_feedback_cache()
    feedback_cache[message_id] = feedback_record
    st.session_state.feedback_by_message = feedback_cache
    st.session_state.feedback_error_for = None
    return True


def add_chat_message(
    role: str,
    content: str,
    *,
    message_id: str | None = None,
    route: str | None = None,
    intent: str | None = None,
    platform: str | None = None,
    source_document: str | None = None,
    feedback_eligible: bool = False,
    resource: str | None = None,
    caption: str | None = None,
) -> dict[str, Any]:
    """
    Add a message to Streamlit history and the analytics database.

    A stable message ID makes this safe against Streamlit reruns. If a message
    with the same ID is already in memory, it is returned instead of appended
    again.
    """
    final_message_id = message_id or str(uuid.uuid4())

    for existing_message in st.session_state.chat_messages:
        if (
            isinstance(existing_message, dict)
            and existing_message.get("message_id") == final_message_id
        ):
            _save_message_safely(existing_message)
            return existing_message

    message: dict[str, Any] = {
        "message_id": final_message_id,
        "role": role,
        "content": content,
        "route": route,
        "intent": intent,
        "platform": platform,
        "source_document": source_document,
        "feedback_eligible": feedback_eligible,
        "resource": resource,
        "caption": caption,
        "analytics_saved": False,
    }

    st.session_state.chat_messages.append(message)
    _save_message_safely(message)

    return message


def start_new_chat(*, outcome: str = "closed") -> None:
    """
    Close the current analytics conversation and start a fresh chat.

    This function can also be called from another navigation or sidebar
    component later.
    """
    previous_session_id = st.session_state.get("session_id")

    if isinstance(previous_session_id, str) and previous_session_id:
        try:
            close_conversation(
                previous_session_id,
                outcome=outcome,
            )
        except Exception as error:
            _print_analytics_error("conversation close", error)

    # Clear chat-specific state while preserving global application caches.
    for key in (
        "chat_messages",
        "pending_question",
        "pending_ticket_status_query",
        "pending_assistant_message_id",
        "conversation_context",
        "active_issue",
        "platform",
        "escalation_state",
        "feedback_by_message",
        "feedback_cache_session_id",
        "feedback_reason_for",
        "feedback_error_for",
        "ticket_escalation_message_id",
    ):
        st.session_state.pop(key, None)

    for state_key in list(st.session_state):
        if str(state_key).startswith("ticket_"):
            st.session_state.pop(state_key, None)

    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.analytics_conversation_registered = False

    initialize_chat()


# ---------------------------------------------------------------------------
# Chat-state and metadata helpers
# ---------------------------------------------------------------------------


def initialize_chat() -> None:
    """Initialize analytics and create the opening message once."""
    _ensure_session_id()
    _ensure_conversation_record()

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    _prepare_legacy_messages()

    if not st.session_state.chat_messages:
        add_chat_message(
            role="assistant",
            content=OPENING_MESSAGE,
            route="greeting",
            feedback_eligible=False,
        )

    if "pending_question" not in st.session_state:
        st.session_state.pending_question = None

    if "pending_ticket_status_query" not in st.session_state:
        st.session_state.pending_ticket_status_query = None

    if "pending_assistant_message_id" not in st.session_state:
        st.session_state.pending_assistant_message_id = None

    # If SQLite was temporarily unavailable, retry unsaved messages on rerun.
    _sync_unsaved_messages()
    _ensure_feedback_cache()


def trim_chat_history() -> None:
    """Bound in-memory history while preserving the opening greeting."""
    messages = list(st.session_state.chat_messages)

    if len(messages) <= MAX_CHAT_MESSAGES:
        return

    opening_message = messages[0]
    recent_messages = messages[-(MAX_CHAT_MESSAGES - 1) :]
    st.session_state.chat_messages = [opening_message, *recent_messages]


def build_assistant_history() -> list[dict[str, str]]:
    """Return only role/content fields to the conversation router and LLM."""
    history: list[dict[str, str]] = []

    for message in st.session_state.chat_messages:
        if not isinstance(message, dict):
            continue

        role = str(message.get("role", "")).strip()
        content = str(message.get("content", "")).strip()

        if role and content:
            history.append(
                {
                    "role": role,
                    "content": content,
                }
            )

    return history


def detect_platform_from_conversation(
    question: str,
    history: list[dict[str, Any]],
) -> str | None:
    """Find the most recent explicit Mac or Windows reference."""
    current_platform = detect_platform(question)

    if current_platform is not None:
        return current_platform

    for message in reversed(history):
        content = str(message.get("content", ""))
        platform = detect_platform(content)

        if platform is not None:
            return platform

    return None


def get_plan_sources(plan: Any) -> tuple[str, ...]:
    """Safely obtain document-source names from an AnswerPlan."""
    raw_sources = getattr(plan, "sources", ())

    if not isinstance(raw_sources, (list, tuple, set)):
        return ()

    return tuple(
        str(source).strip()
        for source in raw_sources
        if str(source).strip()
    )


def get_response_route(plan: Any, *, had_error: bool) -> str:
    """Classify the response route for analytics."""
    if had_error:
        return "error"

    if get_plan_sources(plan):
        return "knowledge"

    if getattr(plan, "direct_answer", None) is not None:
        return "direct"

    if getattr(plan, "context", ""):
        return "knowledge"

    return "generated"


def is_feedback_eligible_response(
    response_text: str,
    *,
    route: str,
) -> bool:
    """Delegate to the shared feedback policy used by tests and the UI."""
    return _core_feedback_eligible(response_text, route=route)


# ---------------------------------------------------------------------------
# Feedback controls
# ---------------------------------------------------------------------------


def display_feedback_controls(message: dict[str, Any]) -> None:
    """Render one-time Helpful / Not Helpful controls for a final answer."""
    if message.get("role") != "assistant":
        return

    if not bool(message.get("feedback_eligible", False)):
        return

    message_id = str(message.get("message_id", "")).strip()

    if not message_id:
        return

    feedback_cache = _ensure_feedback_cache()
    existing_feedback = feedback_cache.get(message_id)

    with st.container(
        key=f"feedback_controls_{message_id}",
        border=False,
    ):
        # Once feedback is saved, the Yes/No controls are intentionally hidden.
        # This prevents a user from changing the vote after submitting it.
        if existing_feedback is not None:
            if bool(existing_feedback.get("helpful")):
                st.success("Thanks for your feedback — marked Helpful.")
            else:
                reason = str(existing_feedback.get("reason") or "").strip()
                status_text = "Thanks for your feedback — marked Not Helpful."

                if reason:
                    status_text += f" Reason: {reason}."

                st.warning(status_text)
            return

        reason_form_open = (
            st.session_state.get("feedback_reason_for") == message_id
        )

        if not reason_form_open:
            st.html(
                '<div class="sjk-feedback-prompt">'
                'Was this response helpful?'
                '</div>'
            )

            with st.container(
                key=f"feedback_button_row_{message_id}",
                border=False,
            ):
                yes_column, no_column = st.columns(
                    2,
                    gap="small",
                    vertical_alignment="center",
                )

                with yes_column:
                    if st.button(
                        "👍 Yes",
                        key=f"feedback_yes_{message_id}",
                        width="stretch",
                    ):
                        if _save_feedback_safely(
                            message=message,
                            helpful=True,
                        ):
                            st.session_state.feedback_reason_for = None
                            st.session_state.pop(
                                _ticket_state_key(
                                    message_id,
                                    "offer_dismissed",
                                ),
                                None,
                            )
                            st.rerun()

                with no_column:
                    if st.button(
                        "👎 No",
                        key=f"feedback_no_{message_id}",
                        width="stretch",
                    ):
                        # Hide both vote buttons while the reason form is open.
                        st.session_state.feedback_reason_for = message_id
                        st.rerun()

        if st.session_state.get("feedback_error_for") == message_id:
            st.error(
                "Your feedback could not be saved. Please try again."
            )

        if st.session_state.get("feedback_reason_for") != message_id:
            return

        with st.form(
            key=f"negative_feedback_form_{message_id}",
            clear_on_submit=False,
        ):
            selected_reason = st.selectbox(
                "What was wrong?",
                options=NEGATIVE_FEEDBACK_REASONS,
                index=0,
                key=f"feedback_reason_{message_id}",
            )

            feedback_comment = st.text_area(
                "Additional details (optional)",
                max_chars=1000,
                placeholder=(
                    "Tell us what was missing or what happened when "
                    "you followed the steps."
                ),
                key=f"feedback_comment_{message_id}",
            )

            submit_column, cancel_column = st.columns(2)

            with submit_column:
                submitted = st.form_submit_button(
                    "Submit feedback",
                    width="stretch",
                )

            with cancel_column:
                cancelled = st.form_submit_button(
                    "Cancel",
                    width="stretch",
                )

            if cancelled:
                st.session_state.feedback_reason_for = None
                st.rerun()

            if submitted:
                cleaned_comment = feedback_comment.strip()

                if selected_reason == "Other" and not cleaned_comment:
                    st.error(
                        "Please add a short explanation when selecting Other."
                    )
                elif _save_feedback_safely(
                    message=message,
                    helpful=False,
                    reason=selected_reason,
                    comment=cleaned_comment or None,
                ):
                    st.session_state.feedback_reason_for = None
                    st.session_state[
                        _ticket_state_key(message_id, "offer_dismissed")
                    ] = False
                    st.rerun()


# ---------------------------------------------------------------------------
# Security-event detection
# ---------------------------------------------------------------------------


def _contains_security_signal(normalized: str, signal: str) -> bool:
    """Match a signal as a complete phrase instead of a loose substring."""
    pattern = rf"(?<!\w){re.escape(signal)}(?!\w)"
    return re.search(pattern, normalized) is not None


def _is_benign_credential_support_request(normalized: str) -> bool:
    """Avoid flagging normal password-reset and policy questions."""
    support_phrases = (
        "password reset",
        "reset my password",
        "reset a password",
        "change my password",
        "change a password",
        "forgot my password",
        "password policy",
        "password requirement",
        "password requirements",
        "password reset page",
        "password reset link",
        "password reset steps",
        "password reset instructions",
    )
    return any(phrase in normalized for phrase in support_phrases)


def _detect_security_misuse(text: str) -> dict[str, str] | None:
    """Return the first high-confidence misuse rule matched by user text."""
    normalized = " ".join(str(text).casefold().split())
    if not normalized:
        return None

    support_exempt_signals = {
        "show me the password",
        "give me the password",
        "reveal the password",
    }

    for event_type, severity, summary, signals in SECURITY_MISUSE_RULES:
        for signal in signals:
            if not _contains_security_signal(normalized, signal):
                continue

            if (
                event_type == "Credential access"
                and signal in support_exempt_signals
                and _is_benign_credential_support_request(normalized)
            ):
                continue

            return {
                "event_type": event_type,
                "severity": severity,
                "summary": summary,
                "matched_signal": signal,
            }
    return None


def _audit_security_misuse(text: str, platform: str | None) -> None:
    """Record high-confidence misuse without interrupting normal chat."""
    finding = _detect_security_misuse(text)
    if finding is None or not _ensure_conversation_record():
        return

    try:
        log_security_event(
            session_id=_ensure_session_id(),
            event_type=finding["event_type"],
            severity=finding["severity"],
            summary=finding["summary"],
            details={
                "matched_signal": finding["matched_signal"],
                "message_excerpt": redact_sensitive_information(str(text))[:1000],
                "platform": str(platform or ""),
            },
        )
    except Exception as error:
        _print_analytics_error("security event logging", error)


# ---------------------------------------------------------------------------
# Ticket escalation helpers
# ---------------------------------------------------------------------------


TICKET_CATEGORY_LABELS: dict[str, str] = {
    "Wifi-Network": "Wifi / Network",
    "AudioVideo": "Audio / Video",
    "GoogleApps": "Google Apps",
    "OnSJK": "onSJK",
    "Reset_Password": "Reset Password",
    "DeviceHardwareIssue": "Device / Hardware Issue",
    "AirplayScreenMirror": "Airplay / Screen Mirror",
    "Other": "Other",
}

TICKET_ROLE_LABELS: dict[str, str] = {
    "": "Not provided",
    "faculty": "Faculty",
    "staff": "Staff",
    "supply_teacher": "Supply Teacher",
}

TICKET_DEVICE_LABELS: dict[str, str] = {
    "": "Not provided",
    "Smartboard": "Smartboard",
    "TV": "TV",
    "Laptop": "Laptop",
    "Tablet": "Tablet / iPad",
    "Printer": "Printer",
    "Other": "Other",
}

TICKET_PRIORITY_OPTIONS = ("Low", "Medium", "High")
TICKET_OPTIONAL_DETAIL_OPTIONS = (
    "No, create the ticket with these details only",
    "Yes, I want to add more details",
)



def _format_ticket_timestamp(value: str) -> str:
    """Format stored UTC timestamps in Altitude's local timezone."""
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""

    normalized = raw_value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return raw_value

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    local_value = parsed.astimezone(get_local_timezone())
    date_text = local_value.strftime("%Y-%m-%d")
    time_text = local_value.strftime("%I:%M %p").lstrip("0")
    timezone_text = local_value.tzname() or "local time"
    return f"{date_text} {time_text} {timezone_text}"

def _user_requests_escalation(text: str) -> bool:
    """Return True when the user explicitly asks for human/ticket support."""
    return _core_user_requests_escalation(text)



def _extract_school_email_from_text(text: str) -> str | None:
    """Return an authorized school email found in free text, if present."""
    for candidate in re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+", str(text), re.I):
        if is_authorized_school_email(candidate):
            return parse_email_address(candidate)[0]
    return None


def _is_ticket_status_query(text: str) -> bool:
    """Return True when the user is asking about an ALT ticket reference."""
    if normalize_altitude_reference(text) is None:
        return False

    normalized = " ".join(str(text).lower().split())
    status_words = (
        "status",
        "open",
        "closed",
        "resolved",
        "assigned",
        "update",
        "updates",
        "ticket",
        "sticktet",
        "sticket",
        "reference",
    )
    return any(word in normalized for word in status_words)


def _ticket_status_query_answer(text: str) -> str | None:
    """Answer ALT reference status requests before normal RAG routing."""
    altitude_reference = normalize_altitude_reference(text)
    if altitude_reference is None or not _is_ticket_status_query(text):
        return None

    if not _ensure_analytics_database():
        return (
            "I found the Altitude reference, but I cannot access the local "
            "ticket receipt database right now. Please contact the IT Helpdesk "
            f"and mention **{altitude_reference}**."
        )

    session_id = _ensure_session_id()
    contact_email = _extract_school_email_from_text(text)

    row = get_ticket_by_altitude_reference(
        altitude_reference,
        session_id=session_id,
    )
    if row is None and contact_email:
        row = get_ticket_by_altitude_reference(
            altitude_reference,
            contact_email=contact_email,
        )

    if row is None:
        email_note = (
            " You can also include the school email used on the ticket in the "
            "same message so I can verify it."
            if contact_email is None
            else ""
        )
        return (
            f"I could not find **{altitude_reference}** in this chat session. "
            "Check that the reference number is correct."
            f"{email_note} For privacy, I can only show ticket status when the "
            "reference matches this chat or the verified school email."
        )

    sync_note = ""
    try:
        updates = fetch_ticket_statuses([row])
        if updates:
            apply_ticket_status_updates([update.__dict__ for update in updates])
            sync_resolved_tickets_to_knowledge_queue(limit=50)
            process_pending_resolution_notifications(limit=50)
            refreshed = get_ticket_by_altitude_reference(
                altitude_reference,
                session_id=session_id,
            )
            if refreshed is None and contact_email:
                refreshed = get_ticket_by_altitude_reference(
                    altitude_reference,
                    contact_email=contact_email,
                )
            if refreshed is not None:
                row = refreshed
        else:
            sync_note = (
                "\n\nI could not find a newer matching status on the ticketing "
                "dashboard, so I am showing the last status saved by Altitude."
            )
    except Exception as error:
        record_ticket_status_sync_error(str(error))
        sync_note = (
            "\n\nI could not refresh the ticketing dashboard right now, so I am "
            "showing the last status saved by Altitude."
        )
        print(
            "Ticket status lookup failed: "
            f"{type(error).__name__}: {error}"
        )

    status = str(row.get("status") or "Submitted").strip() or "Submitted"
    title = str(row.get("title") or "").strip()
    external_id = str(row.get("external_ticket_id") or "").strip()
    last_synced_at = str(row.get("last_synced_at") or "").strip()
    resolution_comment = " ".join(
        str(row.get("resolution_comment") or "").split()
    ).strip()
    if len(resolution_comment) > 700:
        resolution_comment = resolution_comment[:700].rsplit(" ", 1)[0].rstrip() + "…"

    is_closed_status = status.lower() in {
        "closed",
        "resolved",
        "completed",
        "complete",
    }

    lines = [
        f"Ticket **{altitude_reference}** is currently marked **{status}**.",
    ]
    if external_id:
        lines.append(f"Ticketing ID: **{external_id}**.")
    if title:
        lines.append(f"Issue: {title}.")
    if resolution_comment:
        if is_closed_status:
            lines.append(f"Resolution comment: {resolution_comment}")
        else:
            lines.append(f"Latest IT note: {resolution_comment}")
    if last_synced_at:
        display_time = _format_ticket_timestamp(last_synced_at)
        lines.append(f"Last checked: {display_time}.")

    if is_closed_status:
        lines.append(
            "If the problem is still happening, create a new IT ticket and "
            "mention this Altitude reference so the IT Helpdesk can review the "
            "earlier request."
        )
    else:
        lines.append(
            "For urgent or repeated issues, contact the IT Helpdesk directly "
            "and mention this Altitude reference."
        )

    return "\n\n".join(lines) + sync_note


def _is_ticket_escalation_candidate(message: dict[str, Any]) -> bool:
    """Return True when an assistant response should offer ticket escalation."""
    if str(message.get("role", "")) != "assistant":
        return False

    route = str(message.get("route", "")).strip().lower()
    intent = str(message.get("intent", "")).strip().lower()
    normalized = " ".join(str(message.get("content", "")).lower().split())

    # Password-reset responses are policy/helpdesk procedures, not issues that
    # should create a ticket from a Not Helpful vote. Keep feedback available,
    # but never offer the ticket workflow for these intents.
    if intent in NON_TICKET_FEEDBACK_INTENTS:
        return False

    if route in {"error", "escalation"}:
        return True

    if any(
        normalized.startswith(prefix)
        for prefix in TICKET_ESCALATION_PREFIXES
    ):
        return True

    # A submitted Not Helpful vote means the user says the proposed solution
    # did not resolve the issue. Offer the same ticket workflow immediately.
    message_id = str(message.get("message_id", "")).strip()
    if message_id:
        feedback = _ensure_feedback_cache().get(message_id)
        if feedback is not None and not bool(feedback.get("helpful")):
            return True

    return False


def _latest_ticket_candidate_id() -> str | None:
    """Return the newest unresolved assistant message eligible for escalation."""
    for message in reversed(st.session_state.get("chat_messages", [])):
        if not isinstance(message, dict):
            continue
        if _is_ticket_escalation_candidate(message):
            return str(message.get("message_id", "")) or None
    return None


def _user_only_text() -> str:
    """Return normalized text from user messages for deterministic extraction."""
    parts = [
        str(message.get("content", "")).strip()
        for message in st.session_state.get("chat_messages", [])
        if isinstance(message, dict)
        and str(message.get("role", "")) == "user"
        and str(message.get("content", "")).strip()
    ]
    return "\n".join(parts)


def _latest_user_question() -> str:
    for message in reversed(st.session_state.get("chat_messages", [])):
        if (
            isinstance(message, dict)
            and str(message.get("role", "")) == "user"
            and str(message.get("content", "")).strip()
        ):
            return str(message["content"]).strip()
    return "IT support request"


def _build_ticket_title(question: str) -> str:
    clean = " ".join(question.split()).strip(" .!?\n\t")
    if not clean:
        clean = "IT support request"
    title = f"Altitude: {clean}"
    return title[:255]


def _normalized_ticket_text(text: str) -> str:
    """Return lower-case ticket text with punctuation normalized to spaces."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(text).lower()).split())


def _infer_ticket_category(text: str) -> str:
    """Suggest the best Django category from the current issue title."""
    normalized = _normalized_ticket_text(text)
    padded = f" {normalized} "

    category_signals: dict[str, tuple[tuple[str, int], ...]] = {
        "Wifi-Network": (
            ("wifi", 6), ("wi fi", 6), ("wireless", 5),
            ("internet", 4), ("network", 4), ("ethernet", 5),
            ("no connection", 5), ("cannot connect", 3),
        ),
        "AudioVideo": (
            ("audio", 5), ("sound", 4), ("speaker", 5),
            ("microphone", 5), ("projector", 5), ("smartboard", 4),
            ("television", 4), ("video", 3), ("camera", 4),
        ),
        "GoogleApps": (
            ("google docs", 7), ("google sheets", 7),
            ("google slides", 7), ("google drive", 7),
            ("google classroom", 7), ("gmail", 7),
            ("google app", 5), ("google account", 5),
        ),
        "OnSJK": (
            ("onsjk", 8), ("on sjk", 8), ("school portal", 5),
        ),
        "Reset_Password": (
            ("reset password", 8), ("forgot password", 8),
            ("password reset", 8), ("locked out", 5),
            ("password", 3),
        ),
        "DeviceHardwareIssue": (
            ("device", 5), ("hardware", 6), ("laptop", 6),
            ("macbook", 6), ("chromebook", 6), ("computer", 5),
            ("desktop", 5), ("ipad", 5), ("tablet", 5),
            ("printer", 6), ("keyboard", 5), ("mouse", 5),
            ("monitor", 5), ("screen", 3), ("frozen", 5),
            ("freeze", 5), ("force quit", 6), ("not turning on", 6),
            ("broken", 4), ("not working", 3),
        ),
        "AirplayScreenMirror": (
            ("airplay", 8), ("screen mirror", 8),
            ("screen mirroring", 8), ("mirror screen", 7),
            ("cast screen", 6),
        ),
    }

    scores = {category: 0 for category in category_signals}
    for category, signals in category_signals.items():
        for phrase, weight in signals:
            if f" {phrase} " in padded or phrase in normalized:
                scores[category] += weight

    best_category, best_score = max(scores.items(), key=lambda item: item[1])
    return best_category if best_score >= 4 else "Other"


def _infer_custom_category(text: str) -> str:
    """Return a reusable 1-3 word label when the main category is Other."""
    normalized = _normalized_ticket_text(text)
    suggestions = (
        (("website", "web page", "browser page"), "Website Issue"),
        (("software", "application", " app "), "Software Issue"),
        (("login", "sign in", "access"), "Account Access"),
        (("file", "folder", "document"), "File Access"),
        (("classroom", "room"), "Classroom Issue"),
        (("email", "message"), "Email Issue"),
        (("calendar", "schedule"), "Calendar Issue"),
    )
    padded = f" {normalized} "
    for signals, label in suggestions:
        if any(signal in padded or signal in normalized for signal in signals):
            return label
    return "General IT Issue"


def _infer_ticket_priority(text: str) -> str:
    """Suggest priority from operational impact described in the title."""
    normalized = _normalized_ticket_text(text)
    high_signals = (
        "urgent", "emergency", "outage", "school wide", "all users",
        "everyone", "cannot teach", "class in progress", "lesson in progress",
        "account compromised", "phishing", "security incident",
        "multiple classrooms", "entire class",
    )
    low_signals = (
        "how do i", "how can i", "request", "when you have time",
        "not urgent", "question", "would like", "minor",
    )
    medium_signals = (
        "not working", "cannot", "cant", "unable", "broken", "problem",
        "error", "failed", "disconnect", "frozen", "stopped",
    )

    if any(signal in normalized for signal in high_signals):
        return "High"
    if any(signal in normalized for signal in low_signals):
        return "Low"
    if any(signal in normalized for signal in medium_signals):
        return "Medium"
    return "Medium"


def _ticket_state_key(message_id: str, field_name: str) -> str:
    return f"ticket_{field_name}_{message_id}"


def _refresh_ticket_suggestions_from_title(message_id: str) -> None:
    """Refresh category, priority, and custom category after title edits."""
    title = str(
        st.session_state.get(_ticket_state_key(message_id, "title"), "")
    )
    category = _infer_ticket_category(title)
    st.session_state[_ticket_state_key(message_id, "category")] = category
    st.session_state[_ticket_state_key(message_id, "priority")] = (
        _infer_ticket_priority(title)
    )
    custom_key = _ticket_state_key(message_id, "custom_category")
    if category == "Other":
        st.session_state[custom_key] = _infer_custom_category(title)
    else:
        st.session_state[custom_key] = ""


def _initialize_ticket_form_state(message_id: str) -> None:
    """Initialize editable ticket values once for this escalation."""
    issue_text = _latest_user_question()
    suggested_title = _build_ticket_title(issue_text)
    suggested_category = _infer_ticket_category(issue_text)
    defaults: dict[str, Any] = {
        "stage": "edit",
        "email": "",
        "title": suggested_title,
        "category": suggested_category,
        "priority": _infer_ticket_priority(issue_text),
        "optional_choice": TICKET_OPTIONAL_DETAIL_OPTIONS[0],
        "location": "",
        "description": "",
        "role": "",
        "device": "",
        "custom_device": "",
        "custom_category": (
            _infer_custom_category(issue_text)
            if suggested_category == "Other"
            else ""
        ),
        "besttimetocontact": "",
        "image_url": "",
    }

    for field_name, default_value in defaults.items():
        st.session_state.setdefault(
            _ticket_state_key(message_id, field_name),
            default_value,
        )


def _clear_ticket_form_state(message_id: str) -> None:
    for field_name in (
        "stage",
        "email",
        "title",
        "category",
        "priority",
        "optional_choice",
        "location",
        "description",
        "role",
        "device",
        "custom_device",
        "custom_category",
        "besttimetocontact",
        "image_url",
        "review_payload",
        "non_school_email_captured",
    ):
        st.session_state.pop(_ticket_state_key(message_id, field_name), None)


def _ticket_form_snapshot(message_id: str) -> dict[str, Any]:
    """Return the current ticket editor values without validating the email."""
    field_names = (
        "email",
        "title",
        "category",
        "priority",
        "optional_choice",
        "location",
        "description",
        "role",
        "device",
        "custom_device",
        "custom_category",
        "besttimetocontact",
        "image_url",
    )
    return {
        field_name: st.session_state.get(
            _ticket_state_key(message_id, field_name),
            "",
        )
        for field_name in field_names
    }


def _ticket_transcript_snapshot() -> list[dict[str, Any]]:
    """Return a compact chat transcript for the disclosed security audit."""
    transcript: list[dict[str, Any]] = []

    for message in st.session_state.get("chat_messages", []):
        if not isinstance(message, dict):
            continue

        role = str(message.get("role", "")).strip()
        content = str(message.get("content", "")).strip()
        if not role or not content:
            continue

        transcript.append(
            {
                "role": role,
                "content": content[:50_000],
                "route": str(message.get("route", "") or ""),
                "platform": str(message.get("platform", "") or ""),
                "created_at": str(message.get("created_at", "") or ""),
            }
        )

    return transcript[-80:]


def _capture_non_school_email_attempt(message_id: str) -> None:
    """Automatically record a valid non-school email after clear disclosure."""
    raw_email = str(
        st.session_state.get(_ticket_state_key(message_id, "email"), "")
    )

    try:
        normalized_email, email_domain = parse_email_address(raw_email)
    except ValueError:
        return

    if is_authorized_school_email(normalized_email):
        st.session_state.pop(
            _ticket_state_key(message_id, "non_school_email_captured"),
            None,
        )
        return

    snapshot = _ticket_form_snapshot(message_id)
    session_id = _ensure_session_id()

    try:
        log_unauthorized_ticket_attempt(
            session_id=session_id,
            assistant_message_id=message_id,
            contact_email=normalized_email,
            email_domain=email_domain,
            title=str(snapshot.get("title", "")),
            category=str(snapshot.get("category", "")),
            priority=str(snapshot.get("priority", "")),
            form_data=snapshot,
            transcript=_ticket_transcript_snapshot(),
        )
    except Exception as error:
        _print_analytics_error("non-school email audit", error)
        return

    st.session_state[
        _ticket_state_key(message_id, "non_school_email_captured")
    ] = normalized_email


def _payload_from_review_snapshot(message_id: str) -> TicketPayload:
    """Load the validated payload saved before Streamlit hides edit widgets."""
    snapshot = st.session_state.get(
        _ticket_state_key(message_id, "review_payload")
    )

    if not isinstance(snapshot, dict):
        payload = _build_ticket_payload_from_state(message_id)
        st.session_state[
            _ticket_state_key(message_id, "review_payload")
        ] = asdict(payload)
        return payload

    payload = TicketPayload(**snapshot)
    payload.validate()
    return payload


def _restore_ticket_editor_from_payload(
    message_id: str,
    payload: TicketPayload,
) -> None:
    """Restore widget keys before returning from review to edit mode."""
    values = asdict(payload)
    optional_fields = (
        payload.location,
        payload.description,
        payload.role,
        payload.device,
        payload.custom_device,
        payload.besttimetocontact,
        payload.image_url,
    )
    values["email"] = payload.contact_email
    values["optional_choice"] = (
        TICKET_OPTIONAL_DETAIL_OPTIONS[1]
        if any(str(value).strip() for value in optional_fields)
        else TICKET_OPTIONAL_DETAIL_OPTIONS[0]
    )

    for field_name in (
        "email",
        "title",
        "category",
        "priority",
        "optional_choice",
        "location",
        "description",
        "role",
        "device",
        "custom_device",
        "custom_category",
        "besttimetocontact",
        "image_url",
    ):
        st.session_state[_ticket_state_key(message_id, field_name)] = values.get(
            field_name,
            "",
        )


def _build_ticket_payload_from_state(message_id: str) -> TicketPayload:
    """Build a payload from the user's confirmed values."""
    email = validate_school_email(
        str(st.session_state.get(_ticket_state_key(message_id, "email"), ""))
    )
    title = str(
        st.session_state.get(_ticket_state_key(message_id, "title"), "")
    ).strip()
    category = str(
        st.session_state.get(_ticket_state_key(message_id, "category"), "")
    )
    priority = str(
        st.session_state.get(_ticket_state_key(message_id, "priority"), "")
    )
    optional_choice = str(
        st.session_state.get(
            _ticket_state_key(message_id, "optional_choice"),
            TICKET_OPTIONAL_DETAIL_OPTIONS[0],
        )
    )
    include_optional = optional_choice == TICKET_OPTIONAL_DETAIL_OPTIONS[1]

    payload = TicketPayload(
        title=title,
        category=category,
        priority=priority,
        contact_email=email,
        location=(
            str(st.session_state.get(_ticket_state_key(message_id, "location"), ""))
            if include_optional
            else ""
        ),
        description=(
            str(st.session_state.get(_ticket_state_key(message_id, "description"), ""))
            if include_optional
            else ""
        ),
        role=(
            str(st.session_state.get(_ticket_state_key(message_id, "role"), ""))
            if include_optional
            else ""
        ),
        device=(
            str(st.session_state.get(_ticket_state_key(message_id, "device"), ""))
            if include_optional
            else ""
        ),
        custom_device=(
            str(st.session_state.get(_ticket_state_key(message_id, "custom_device"), ""))
            if include_optional
            else ""
        ),
        custom_category=(
            (
                str(
                    st.session_state.get(
                        _ticket_state_key(message_id, "custom_category"),
                        "",
                    )
                ).strip()
                or _infer_custom_category(title)
            )
            if category == "Other"
            else (
                str(
                    st.session_state.get(
                        _ticket_state_key(message_id, "custom_category"),
                        "",
                    )
                ).strip()
                if include_optional
                else ""
            )
        ),
        bestwaytocontact="email",
        besttimetocontact=(
            str(
                st.session_state.get(
                    _ticket_state_key(message_id, "besttimetocontact"),
                    "",
                )
            )
            if include_optional
            else ""
        ),
        image_url=(
            str(st.session_state.get(_ticket_state_key(message_id, "image_url"), ""))
            if include_optional
            else ""
        ),
        status="",
        assignedto="",
    )
    payload.validate()
    return payload


def _render_optional_ticket_fields(message_id: str, category: str) -> None:
    """Render fields that the user may choose to provide."""
    if category == "Other":
        custom_key = _ticket_state_key(message_id, "custom_category")
        if not str(st.session_state.get(custom_key, "")).strip():
            current_title = str(
                st.session_state.get(
                    _ticket_state_key(message_id, "title"),
                    "",
                )
            )
            st.session_state[custom_key] = _infer_custom_category(current_title)
        st.text_input(
            "Custom category (required)",
            key=custom_key,
            max_chars=60,
            placeholder="Example: Website Issue",
            help="Use a short category between 1 and 3 words.",
        )

    optional_choice = st.radio(
        "Would you like to provide any other details?",
        options=TICKET_OPTIONAL_DETAIL_OPTIONS,
        key=_ticket_state_key(message_id, "optional_choice"),
    )

    if optional_choice != TICKET_OPTIONAL_DETAIL_OPTIONS[1]:
        return

    st.text_input(
        "Location (optional)",
        key=_ticket_state_key(message_id, "location"),
        placeholder="Example: Room 101 or Staff Room",
    )
    st.text_area(
        "Description (optional)",
        key=_ticket_state_key(message_id, "description"),
        placeholder="Add any extra context that would help the IT team.",
        height=110,
    )

    role_column, device_column = st.columns(2, gap="small")
    with role_column:
        st.selectbox(
            "Role (optional)",
            options=tuple(TICKET_ROLE_LABELS),
            format_func=lambda value: TICKET_ROLE_LABELS[value],
            key=_ticket_state_key(message_id, "role"),
        )
    with device_column:
        selected_device = st.selectbox(
            "Device (optional)",
            options=tuple(TICKET_DEVICE_LABELS),
            format_func=lambda value: TICKET_DEVICE_LABELS[value],
            key=_ticket_state_key(message_id, "device"),
        )

    if selected_device == "Other":
        st.text_input(
            "Custom device (optional)",
            key=_ticket_state_key(message_id, "custom_device"),
            placeholder="Describe the device",
        )

    st.text_input(
        "Best time to contact (optional)",
        key=_ticket_state_key(message_id, "besttimetocontact"),
        placeholder="Example: 10 AM or afternoon",
    )
    st.text_input(
        "Screenshot or Google Drive link (optional)",
        key=_ticket_state_key(message_id, "image_url"),
        placeholder="Paste a shareable link",
    )


def _render_ticket_edit_step(message_id: str) -> None:
    """Render editable generated fields and optional details."""
    st.html(
        """
<div class="sjk-ticket-privacy-warning">
    <strong>Privacy and security notice</strong>
    <span>
        Only authorized school email addresses can create tickets. If a valid
        non-school email address is entered, Altitude automatically records
        the email, current ticket fields, and chat context for IT security
        review, even if the ticket is not reviewed or submitted.
    </span>
</div>
"""
    )

    st.markdown(
        "I generated the ticket title, category, and priority from your "
        "question. Please review them and change anything that is not correct."
    )

    st.text_input(
        "School email",
        key=_ticket_state_key(message_id, "email"),
        placeholder="name@sjkeagles.com",
        help=SCHOOL_EMAIL_HELP,
        on_change=_capture_non_school_email_attempt,
        args=(message_id,),
    )
    st.caption(SCHOOL_EMAIL_HELP)

    captured_email = st.session_state.get(
        _ticket_state_key(message_id, "non_school_email_captured")
    )
    if captured_email:
        st.warning(
            "This non-school email attempt was recorded for IT security "
            "review. Enter an authorized school email to continue."
        )

    st.text_input(
        "Title",
        key=_ticket_state_key(message_id, "title"),
        max_chars=255,
        on_change=_refresh_ticket_suggestions_from_title,
        args=(message_id,),
    )

    selected_category = st.selectbox(
        "Category",
        options=tuple(TICKET_CATEGORY_LABELS),
        format_func=lambda value: TICKET_CATEGORY_LABELS[value],
        key=_ticket_state_key(message_id, "category"),
    )
    st.caption("Suggested from the ticket title. You can change it.")

    st.selectbox(
        "Priority",
        options=TICKET_PRIORITY_OPTIONS,
        key=_ticket_state_key(message_id, "priority"),
    )
    st.caption("Suggested from the impact described in the ticket title.")

    _render_optional_ticket_fields(message_id, selected_category)

    review_column, cancel_column = st.columns(2, gap="small")
    with review_column:
        review_requested = st.button(
            "Review ticket",
            key=f"review_ticket_{message_id}",
            type="primary",
            width="stretch",
        )
    with cancel_column:
        cancel_requested = st.button(
            "Not now",
            key=f"cancel_ticket_{message_id}",
            width="stretch",
        )

    if cancel_requested:
        _clear_ticket_form_state(message_id)
        st.session_state.pop("ticket_escalation_message_id", None)
        st.rerun()

    if not review_requested:
        return

    # The on-change callback normally captures a non-school address before the
    # button event. Calling it again here guarantees the audit is written even
    # when the browser submits the button event without first blurring input.
    _capture_non_school_email_attempt(message_id)

    try:
        payload = _build_ticket_payload_from_state(message_id)
    except ValueError as error:
        st.error(str(error))
        return

    # Streamlit may remove widget state when the edit controls are hidden on
    # the review rerun. Preserve a validated snapshot so the school email and
    # all reviewed values remain available during confirmation.
    st.session_state[
        _ticket_state_key(message_id, "review_payload")
    ] = asdict(payload)
    st.session_state[_ticket_state_key(message_id, "stage")] = "review"
    st.rerun()

def _render_ticket_review_step(
    message_id: str,
    session_id: str,
) -> None:
    """Show the final confirmation and create the ticket after approval."""
    try:
        payload = _payload_from_review_snapshot(message_id)
    except (TypeError, ValueError) as error:
        st.error(str(error))
        st.session_state[_ticket_state_key(message_id, "stage")] = "edit"
        return

    category_label = TICKET_CATEGORY_LABELS.get(
        payload.category,
        payload.category,
    )
    if payload.category == "Other" and payload.custom_category.strip():
        category_label = f"Other — {payload.custom_category.strip()}"
    st.markdown(
        "I will create the IT ticket with the following details:"
    )
    st.markdown(
        f"**Title:** {payload.title}\n\n"
        f"**Category:** {category_label}\n\n"
        f"**Priority:** {payload.priority}\n\n"
        f"**Contact email:** {payload.contact_email}"
    )

    optional_values = (
        payload.location,
        payload.description,
        payload.role,
        payload.device,
        payload.custom_device,
        payload.custom_category,
        payload.besttimetocontact,
        payload.image_url,
    )
    if any(str(value).strip() for value in optional_values):
        st.caption("The optional details you provided will also be included.")
    else:
        st.caption("No optional details will be included.")

    create_column, edit_column, cancel_column = st.columns(
        [1.25, 1.0, 0.85],
        gap="small",
    )
    with create_column:
        create_requested = st.button(
            "Confirm and create ticket",
            key=f"confirm_create_ticket_{message_id}",
            type="primary",
            width="stretch",
        )
    with edit_column:
        edit_requested = st.button(
            "Edit details",
            key=f"edit_ticket_details_{message_id}",
            width="stretch",
        )
    with cancel_column:
        cancel_requested = st.button(
            "Cancel",
            key=f"cancel_confirm_ticket_{message_id}",
            width="stretch",
        )

    if edit_requested:
        _restore_ticket_editor_from_payload(message_id, payload)
        st.session_state.pop(
            _ticket_state_key(message_id, "review_payload"),
            None,
        )
        st.session_state[_ticket_state_key(message_id, "stage")] = "edit"
        st.rerun()

    if cancel_requested:
        _clear_ticket_form_state(message_id)
        st.session_state.pop("ticket_escalation_message_id", None)
        st.rerun()

    if not create_requested:
        return

    payload_data = payload.as_form_data()
    try:
        local_ticket_id = create_ticket_audit(
            session_id=session_id,
            title=payload.title,
            contact_email=payload.contact_email,
            category=payload.category,
            device=payload.device,
            priority=payload.priority,
            payload=payload_data,
        )
    except Exception as error:
        _print_analytics_error("ticket audit creation", error)
        st.error("The ticket could not be prepared. Try again.")
        return

    try:
        altitude_reference = ensure_ticket_altitude_reference(local_ticket_id)
    except Exception as error:
        _print_analytics_error("ticket reference creation", error)
        altitude_reference = f"ALT-{local_ticket_id:06d}"

    remote_payload = payload_with_altitude_reference(
        payload,
        altitude_reference,
    )

    try:
        with st.spinner("Creating your IT ticket..."):
            result = submit_ticket(remote_payload)
    except (TicketingClientError, ValueError) as error:
        try:
            mark_ticket_submission_failed(
                local_ticket_id,
                error_message=str(error),
            )
        except Exception as audit_error:
            _print_analytics_error("ticket failure update", audit_error)
        st.error(str(error))
        return
    except Exception as error:
        try:
            mark_ticket_submission_failed(
                local_ticket_id,
                error_message="Unexpected ticket submission error",
            )
        except Exception as audit_error:
            _print_analytics_error("ticket failure update", audit_error)
        print(
            "Ticket submission failed: "
            f"{type(error).__name__}: {error}"
        )
        st.error("The ticketing system could not create the ticket.")
        return

    try:
        mark_ticket_submitted(
            local_ticket_id,
            external_ticket_id=result.external_ticket_id,
            status="Open",
            remote_ticket_url=result.remote_ticket_url,
        )
    except Exception as error:
        _print_analytics_error("ticket success update", error)

    st.session_state[
        _ticket_state_key(message_id, "created_result")
    ] = {
        "external_ticket_id": result.external_ticket_id or "",
        "altitude_reference": altitude_reference,
    }
    _clear_ticket_form_state(message_id)
    st.session_state.pop("ticket_escalation_message_id", None)
    st.rerun()


def _display_ticket_escalation_controls(
    message: dict[str, Any],
) -> None:
    """Offer a reviewable, user-confirmed ticket escalation workflow."""
    if not _is_ticket_escalation_candidate(message):
        return

    message_id = str(message.get("message_id", ""))
    if not message_id or message_id != _latest_ticket_candidate_id():
        return

    feedback = _ensure_feedback_cache().get(message_id)
    is_negative_feedback = (
        feedback is not None
        and not bool(feedback.get("helpful"))
    )
    selected_message = st.session_state.get(
        "ticket_escalation_message_id"
    )
    offer_dismissed = bool(
        st.session_state.get(
            _ticket_state_key(message_id, "offer_dismissed"),
            False,
        )
    )

    if offer_dismissed and selected_message != message_id:
        return

    session_id = _ensure_session_id()
    created_result = st.session_state.get(
        _ticket_state_key(message_id, "created_result")
    )

    if isinstance(created_result, dict):
        external_id = str(
            created_result.get("external_ticket_id") or ""
        ).strip()
        altitude_reference = str(
            created_result.get("altitude_reference") or ""
        ).strip()

        message_lines = [
            "Your IT ticket was created successfully.",
        ]
        if altitude_reference:
            message_lines.append(
                f"**Altitude reference:** {altitude_reference}"
            )
        if external_id:
            message_lines.append(
                f"**Ticketing ID:** {external_id}"
            )
        message_lines.append(
            "Save this reference number. You can ask me for the status later "
            "using the Altitude reference, or follow up with the IT Helpdesk "
            "and mention the same reference."
        )
        st.success("\n\n".join(message_lines))
        return

    with st.container(
        key=f"ticket_escalation_panel_{message_id}",
        border=True,
    ):
        if selected_message != message_id:
            offer_text = (
                "That response was marked Not Helpful. Would you like me to "
                "create an IT ticket for this issue?"
                if is_negative_feedback
                else "Would you like me to create an IT ticket for this issue?"
            )
            st.html(
                '<div class="sjk-ticket-offer-prompt">'
                f'{escape(offer_text)}'
                '</div>'
            )

            with st.container(
                key=f"ticket_offer_actions_{message_id}",
                border=False,
            ):
                create_column, dismiss_column, spacer_column = st.columns(
                    [0.26, 0.18, 0.56],
                    gap="small",
                    vertical_alignment="center",
                )

                with create_column:
                    if st.button(
                        "Create IT ticket",
                        key=f"open_ticket_form_{message_id}",
                        type="primary",
                        width="stretch",
                    ):
                        st.session_state.ticket_escalation_message_id = message_id
                        st.session_state[
                            _ticket_state_key(message_id, "offer_dismissed")
                        ] = False
                        _initialize_ticket_form_state(message_id)
                        st.rerun()

                with dismiss_column:
                    if st.button(
                        "Not now",
                        key=f"dismiss_ticket_offer_{message_id}",
                        width="stretch",
                    ):
                        st.session_state[
                            _ticket_state_key(message_id, "offer_dismissed")
                        ] = True
                        st.rerun()

                with spacer_column:
                    st.empty()
            return

        _initialize_ticket_form_state(message_id)
        stage = str(
            st.session_state.get(
                _ticket_state_key(message_id, "stage"),
                "edit",
            )
        )

        if stage == "review":
            _render_ticket_review_step(message_id, session_id)
        else:
            _render_ticket_edit_step(message_id)


def _inject_ticket_feedback_styles() -> None:
    """Apply scoped layout fixes for feedback and ticket controls."""
    st.html(
        """
<style>
.sjk-feedback-prompt {
    position: relative !important;
    z-index: 2 !important;
    display: block !important;
    min-height: 0 !important;
    margin: 0 0 6px !important;
    padding: 0 2px !important;
    color: #6b7785 !important;
    font-size: 0.92rem !important;
    line-height: 1.45 !important;
}

[class*="st-key-feedback_controls_"] {
    position: relative !important;
    z-index: 2 !important;
    width: 100% !important;
    height: auto !important;
    min-height: 0 !important;
    margin-top: 4px !important;
    padding-top: 2px !important;
    overflow: visible !important;
}

[class*="st-key-feedback_controls_"]
> [data-testid="stVerticalBlock"] {
    display: flex !important;
    flex-direction: column !important;
    height: auto !important;
    min-height: 0 !important;
    gap: 6px !important;
    overflow: visible !important;
}

.st-key-chat_scroll_area
[class*="st-key-assistant_message_"]
> [data-testid="stVerticalBlock"] {
    display: flex !important;
    flex-direction: column !important;
    height: auto !important;
    min-height: 0 !important;
    gap: 4px !important;
}

.st-key-chat_scroll_area
[class*="st-key-assistant_message_"]
[data-testid="stElementContainer"]:has([class*="st-key-feedback_controls_"]),
.st-key-chat_scroll_area
[class*="st-key-assistant_message_"]
[data-testid="stLayoutWrapper"]:has([class*="st-key-feedback_controls_"]) {
    flex: 0 0 auto !important;
    width: 100% !important;
    height: auto !important;
    min-height: 0 !important;
    margin: 2px 0 0 !important;
    padding: 0 !important;
    overflow: visible !important;
}

[class*="st-key-feedback_button_row_"] {
    width: min(100%, 300px) !important;
    max-width: 300px !important;
    margin: 0 !important;
    padding: 0 !important;
}

[class*="st-key-feedback_button_row_"]
> [data-testid="stVerticalBlock"] {
    gap: 0 !important;
}

[class*="st-key-feedback_button_row_"]
[data-testid="stHorizontalBlock"] {
    width: 100% !important;
    max-width: 300px !important;
    gap: 8px !important;
}

[class*="st-key-feedback_button_row_"]
[data-testid="stColumn"] {
    min-width: 0 !important;
}

[class*="st-key-feedback_button_row_"] .stButton > button {
    width: 100% !important;
    min-width: 120px !important;
    min-height: 42px !important;
    padding: 0.5rem 0.9rem !important;
    white-space: nowrap !important;
    line-height: 1.2 !important;
}

[class*="st-key-ticket_escalation_panel_"] {
    width: 100% !important;
    margin-top: 8px !important;
    padding: clamp(12px, 1.6vw, 18px) !important;
    background: #f8fbfd !important;
    border: 1px solid #cbdce8 !important;
    border-radius: 14px !important;
    box-sizing: border-box !important;
    overflow: visible !important;
}

[class*="st-key-ticket_escalation_panel_"]
> [data-testid="stVerticalBlock"] {
    gap: 10px !important;
}

.sjk-ticket-offer-prompt {
    margin: 0 0 2px;
    color: #243542;
    font-size: 0.9rem;
    font-weight: 700;
    line-height: 1.45;
}


[class*="st-key-ticket_offer_actions_"] {
    width: 100% !important;
    max-width: 100% !important;
    margin: 4px 0 0 !important;
    padding: 0 !important;
    overflow: visible !important;
}

[class*="st-key-ticket_offer_actions_"]
> [data-testid="stVerticalBlock"] {
    width: 100% !important;
    gap: 0 !important;
    overflow: visible !important;
}

[class*="st-key-ticket_offer_actions_"]
[data-testid="stHorizontalBlock"],
[class*="st-key-ticket_offer_actions_"]
[data-testid="stHorizontalBlock"] {
    display: flex !important;
    width: 100% !important;
    max-width: 100% !important;
    gap: 10px !important;
    align-items: center !important;
    overflow: visible !important;
}

[class*="st-key-ticket_offer_actions_"]
[data-testid="stColumn"] {
    min-width: 0 !important;
}

[class*="st-key-ticket_offer_actions_"]
[data-testid="stColumn"]:nth-child(1) {
    flex: 0 0 190px !important;
    width: 190px !important;
    min-width: 190px !important;
    max-width: 190px !important;
}

[class*="st-key-ticket_offer_actions_"]
[data-testid="stColumn"]:nth-child(2) {
    flex: 0 0 116px !important;
    width: 116px !important;
    min-width: 116px !important;
    max-width: 116px !important;
}

[class*="st-key-ticket_offer_actions_"]
[data-testid="stColumn"]:nth-child(3) {
    flex: 1 1 auto !important;
    width: auto !important;
    min-width: 0 !important;
    max-width: none !important;
}

[class*="st-key-ticket_offer_actions_"] .stButton > button {
    width: 100% !important;
    min-width: 0 !important;
    min-height: 44px !important;
    padding: 0.55rem 0.9rem !important;
    white-space: nowrap !important;
    word-break: normal !important;
    overflow-wrap: normal !important;
    line-height: 1.2 !important;
}

[class*="st-key-ticket_offer_actions_"] .stButton > button p {
    margin: 0 !important;
    white-space: nowrap !important;
    word-break: normal !important;
    overflow-wrap: normal !important;
}

@media (max-width: 560px) {
    [class*="st-key-ticket_offer_actions_"]
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }

    [class*="st-key-ticket_offer_actions_"]
    [data-testid="stColumn"]:nth-child(1),
    [class*="st-key-ticket_offer_actions_"]
    [data-testid="stColumn"]:nth-child(2) {
        flex: 1 1 100% !important;
        width: 100% !important;
        min-width: 100% !important;
        max-width: 100% !important;
    }

    [class*="st-key-ticket_offer_actions_"]
    [data-testid="stColumn"]:nth-child(3) {
        display: none !important;
    }
}

.sjk-ticket-privacy-warning {
    display: flex;
    flex-direction: column;
    gap: 5px;
    margin: 0 0 4px;
    padding: 12px 14px;
    background: #FFF8E1;
    border: 1px solid #FFE082;
    border-left: 4px solid #FFC107;
    border-radius: 10px;
    color: #5F4500;
    font-size: 0.82rem;
    line-height: 1.45;
}

.sjk-ticket-privacy-warning strong {
    color: #4B3A00;
    font-size: 0.86rem;
}

[class*="st-key-ticket_escalation_panel_"] [data-testid="stSelectbox"],
[class*="st-key-ticket_escalation_panel_"] [data-testid="stTextInput"],
[class*="st-key-ticket_escalation_panel_"] [data-testid="stTextArea"] {
    width: 100% !important;
    min-width: 0 !important;
}

[class*="st-key-ticket_escalation_panel_"] [data-baseweb="input"],
[class*="st-key-ticket_escalation_panel_"] [data-baseweb="textarea"],
[class*="st-key-ticket_escalation_panel_"] [data-baseweb="select"] > div {
    background: #ffffff !important;
    border: 1px solid #aebdca !important;
    border-radius: 10px !important;
    box-shadow: none !important;
}

[class*="st-key-ticket_escalation_panel_"] [data-baseweb="input"]:focus-within,
[class*="st-key-ticket_escalation_panel_"] [data-baseweb="textarea"]:focus-within,
[class*="st-key-ticket_escalation_panel_"] [data-baseweb="select"]:focus-within > div {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 1px #2563EB !important;
}

[class*="st-key-ticket_escalation_panel_"] .stButton > button,
[class*="st-key-ticket_escalation_panel_"] [data-testid="stFormSubmitButton"] button {
    min-height: 44px !important;
    border-radius: 10px !important;
}

@media (max-width: 780px) {
    [class*="st-key-ticket_escalation_panel_"]
    [data-testid="stHorizontalBlock"]:has([data-testid="stSelectbox"]) {
        display: flex !important;
        flex-direction: column !important;
    }

    [class*="st-key-ticket_escalation_panel_"]
    [data-testid="stHorizontalBlock"]:has([data-testid="stSelectbox"])
    > [data-testid="stColumn"] {
        width: 100% !important;
        min-width: 100% !important;
        max-width: 100% !important;
        flex: 1 1 100% !important;
    }
}
</style>
"""
    )


# ---------------------------------------------------------------------------
# Existing UI helpers
# ---------------------------------------------------------------------------


def get_greeting() -> str:
    """Return a greeting based on the current local time."""
    hour = local_now().hour

    if hour < 12:
        return "Good Morning"

    if hour < 17:
        return "Good Afternoon"

    return "Good Evening"


def display_greeting(animate: bool) -> None:
    """Display the time-based greeting."""
    greeting = get_greeting()
    eagle_uri = image_data_uri("eagle.png")

    if eagle_uri:
        eagle_html = (
            f'<img src="{eagle_uri}" '
            'class="sjk-eagle" alt="SJK Eagle">'
        )
    else:
        eagle_html = '<span class="sjk-eagle-fallback">🦅</span>'

    if animate:
        time_html = f"""
<span
    class="sjk-typewriter-shell"
    style="--sjk-character-count: {len(greeting)};"
>
    <span
        class="sjk-typewriter-reserve"
        aria-hidden="true"
    >
        {greeting}
    </span>

    <span class="sjk-greeting-time sjk-typewriter-text">
        {greeting}
    </span>
</span>
"""
    else:
        time_html = f'<span class="sjk-greeting-time">{greeting}</span>'

    st.html(
        f"""
<div class="sjk-greeting">
    {time_html}
    <span class="sjk-greeting-eagles">Eagles</span>
    {eagle_html}
</div>
"""
    )


def display_assistant_avatar() -> None:
    """Render the SJK crest beside assistant messages."""
    crest_uri = image_data_uri("sjk_crest.png")

    if crest_uri:
        st.html(
            f"""
<div class="sjk-message-avatar-wrapper">
    <img
        src="{crest_uri}"
        class="sjk-message-avatar-image"
        alt="SJK Altitude"
    >
</div>
"""
        )
    else:
        st.html(
            """
<div class="sjk-message-avatar-wrapper">
    <div class="sjk-fallback-avatar">🤖</div>
</div>
"""
        )


def display_student_avatar() -> None:
    """Render the student avatar beside user messages."""
    st.html(
        """
<div class="sjk-message-avatar-wrapper sjk-user-avatar-wrapper">
    <div class="sjk-student-avatar">👤</div>
</div>
"""
    )


def display_message(
    message: dict[str, Any],
    message_index: int,
) -> None:
    """Render an assistant or user message."""
    role = message.get("role", "assistant")
    content = str(message.get("content", ""))

    if role == "assistant":
        avatar_column, bubble_column = st.columns(
            [0.045, 0.955],
            gap="small",
            vertical_alignment="top",
        )

        with avatar_column:
            display_assistant_avatar()

        with bubble_column:
            with st.container(
                key=f"assistant_message_{message_index}",
                height="content",
                border=False,
            ):
                st.markdown(content)

                resource = message.get("resource")

                if resource:
                    resource_path = STATIC_DIRECTORY / str(resource)

                    if resource_path.exists():
                        st.image(
                            str(resource_path),
                            caption=message.get("caption"),
                            width=320,
                        )

                display_feedback_controls(message)
                _display_ticket_escalation_controls(message)

    else:
        bubble_column, avatar_column = st.columns(
            [0.955, 0.045],
            gap="small",
            vertical_alignment="top",
        )

        with bubble_column:
            with st.container(
                key=f"user_message_{message_index}",
                height="content",
                border=False,
            ):
                st.markdown(content)

        with avatar_column:
            display_student_avatar()


def render_loading_animation(placeholder: Any) -> None:
    """Render the local loading GIF or fallback dots."""
    if not LOADING_GIF_PATH.exists():
        placeholder.markdown(
            """
<div class="sjk-thinking-loader">
    <span></span>
    <span></span>
    <span></span>
    <strong>ALTITUDE is thinking...</strong>
</div>
""",
            unsafe_allow_html=True,
        )
        return

    gif_bytes = LOADING_GIF_PATH.read_bytes()
    encoded_gif = base64.b64encode(gif_bytes).decode("utf-8")

    placeholder.markdown(
        f"""
<div class="sjk-thinking-loader">
    <img
        src="data:image/gif;base64,{encoded_gif}"
        alt=""
    />
    <strong></strong>
</div>
""",
        unsafe_allow_html=True,
    )


def display_streaming_assistant(
    question: str,
    history: list[dict[str, Any]],
    message_index: int,
) -> dict[str, Any]:
    """Display loading, prepare the answer, and stream the response."""
    avatar_column, bubble_column = st.columns(
        [0.045, 0.955],
        gap="small",
        vertical_alignment="top",
    )

    plan = None
    response_text = ""
    had_error = False

    with avatar_column:
        display_assistant_avatar()

    with bubble_column:
        with st.container(
            key=f"assistant_message_{message_index}",
            height="content",
            border=False,
        ):
            loading_placeholder = st.empty()
            render_loading_animation(loading_placeholder)
            time.sleep(0.15)

            try:
                plan = prepare_answer(
                    question=question,
                    history=history,
                )

                if plan.direct_answer is not None:
                    time.sleep(0.20)
                    loading_placeholder.empty()
                    response_text = plan.direct_answer
                    st.markdown(response_text)
                else:

                    def response_with_loading():
                        first_chunk_received = False

                        try:
                            for chunk in stream_answer(
                                question=question,
                                history=history,
                                plan=plan,
                            ):
                                if chunk and not first_chunk_received:
                                    loading_placeholder.empty()
                                    first_chunk_received = True

                                yield chunk
                        finally:
                            loading_placeholder.empty()

                    response_text = st.write_stream(
                        response_with_loading(),
                        cursor="▌",
                    )

            except Exception as error:
                had_error = True
                loading_placeholder.empty()

                print(
                    "Chat response error: "
                    f"{type(error).__name__}: {error}"
                )

                response_text = (
                    "I could not complete that request. "
                    "Please contact the IT Helpdesk."
                )

                st.markdown(response_text)

            if plan is not None and plan.resource:
                resource_path = STATIC_DIRECTORY / plan.resource

                if resource_path.exists():
                    st.image(
                        str(resource_path),
                        caption=plan.caption,
                        width=320,
                    )
                else:
                    st.error(
                        "The requested support resource could not be found."
                    )
                    print("Missing support resource:", resource_path)

            scroll_chat_to_bottom()

    if not isinstance(response_text, str):
        response_text = str(response_text)

    route = get_response_route(plan, had_error=had_error)
    sources = get_plan_sources(plan)
    source_document = " | ".join(sources)[:1000] or None
    platform = detect_platform_from_conversation(
        question,
        history,
    )

    return {
        "role": "assistant",
        "content": response_text,
        "route": route,
        "intent": _optional_string(getattr(plan, "intent", None)),
        "platform": platform,
        "source_document": source_document,
        "feedback_eligible": is_feedback_eligible_response(
            response_text,
            route=route,
        ),
        "resource": (plan.resource if plan is not None else None),
        "caption": (plan.caption if plan is not None else None),
    }


def display_ticket_status_assistant(
    question: str,
    message_index: int,
) -> dict[str, Any]:
    """Display the local loading GIF while checking ticket status."""
    avatar_column, bubble_column = st.columns(
        [0.045, 0.955],
        gap="small",
        vertical_alignment="top",
    )

    response_text = ""
    had_error = False

    with avatar_column:
        display_assistant_avatar()

    with bubble_column:
        with st.container(
            key=f"assistant_ticket_status_{message_index}",
            height="content",
            border=False,
        ):
            loading_placeholder = st.empty()
            render_loading_animation(loading_placeholder)
            time.sleep(0.20)

            try:
                response_text = _ticket_status_query_answer(question) or (
                    "I could not read that Altitude ticket reference. "
                    "Please check the reference number and try again."
                )
            except Exception as error:
                had_error = True
                print(
                    "Ticket status response error: "
                    f"{type(error).__name__}: {error}"
                )
                response_text = (
                    "I could not check that ticket status right now. "
                    "Please contact the IT Helpdesk and mention the "
                    "Altitude reference."
                )
            finally:
                loading_placeholder.empty()

            st.markdown(response_text)
            scroll_chat_to_bottom()

    return {
        "role": "assistant",
        "content": response_text,
        "route": "ticket_status_error" if had_error else "ticket_status",
        "intent": "ticket_status_lookup",
        "platform": None,
        "source_document": None,
        "feedback_eligible": not had_error,
        "resource": None,
        "caption": None,
    }


def scroll_chat_to_bottom() -> None:
    """Scroll the custom chat container to its newest content."""
    trigger_id = time.time_ns()

    st.html(
        f"""
<script data-scroll-trigger="{trigger_id}">
(() => {{
    const findScrollableContainer = () => {{
        const root = document.querySelector(
            ".st-key-chat_scroll_area"
        );

        if (!root) {{
            return null;
        }}

        const candidates = [
            root,
            ...root.querySelectorAll("div")
        ];

        return candidates.find((element) => {{
            const style = window.getComputedStyle(element);

            const canScroll =
                style.overflowY === "auto" ||
                style.overflowY === "scroll";

            return (
                canScroll &&
                element.scrollHeight >
                    element.clientHeight + 4
            );
        }}) || root;
    }};

    const scrollToBottom = () => {{
        const container = findScrollableContainer();

        if (!container) {{
            return;
        }}

        container.scrollTo({{
            top: container.scrollHeight,
            behavior: "smooth"
        }});
    }};

    requestAnimationFrame(scrollToBottom);
    setTimeout(scrollToBottom, 100);
    setTimeout(scrollToBottom, 350);
    setTimeout(scrollToBottom, 750);

    const chatRoot = document.querySelector(
        ".st-key-chat_scroll_area"
    );

    if (!chatRoot) {{
        return;
    }}

    const observer = new MutationObserver(() => {{
        scrollToBottom();
    }});

    observer.observe(chatRoot, {{
        childList: true,
        subtree: true,
        characterData: true
    }});

    setTimeout(() => {{
        observer.disconnect();
        scrollToBottom();
    }}, 30000);
}})();
</script>
""",
        unsafe_allow_javascript=True,
    )


# ---------------------------------------------------------------------------
# Main page renderer
# ---------------------------------------------------------------------------


def render_chat() -> None:
    """Render chat, persist messages, and show user input immediately."""
    _inject_ticket_feedback_styles()
    initialize_chat()
    trim_chat_history()

    is_new_conversation = len(st.session_state.chat_messages) == 1

    with st.container(
        key="chat_page",
        height="stretch",
        gap="small",
    ):
        # A small built-in control makes the Feature 1 session lifecycle
        # complete. This can later be moved to the left panel if preferred.
        toolbar_spacer, toolbar_button = st.columns(
            [0.84, 0.16],
            gap="small",
            vertical_alignment="center",
        )

        with toolbar_spacer:
            st.empty()

        with toolbar_button:
            if st.button(
                "New Chat",
                key="sjk_new_chat_button",
                width="stretch",
            ):
                start_new_chat()
                st.rerun()

        with st.container(
            key="chat_scroll_area",
            height="stretch",
            border=False,
            autoscroll=True,
        ):
            display_greeting(animate=is_new_conversation)

            for index, message in enumerate(
                st.session_state.chat_messages
            ):
                display_message(
                    message=message,
                    message_index=index,
                )

            scroll_chat_to_bottom()

            pending_ticket_status_query = st.session_state.get(
                "pending_ticket_status_query"
            )

            if pending_ticket_status_query:
                pending_message_id = (
                    st.session_state.pending_assistant_message_id
                    or str(uuid.uuid4())
                )
                st.session_state.pending_assistant_message_id = (
                    pending_message_id
                )

                assistant_message = display_ticket_status_assistant(
                    question=str(pending_ticket_status_query),
                    message_index=len(
                        st.session_state.chat_messages
                    ),
                )

                add_chat_message(
                    role="assistant",
                    content=str(assistant_message["content"]),
                    message_id=pending_message_id,
                    route=_optional_string(
                        assistant_message.get("route")
                    ),
                    intent=_optional_string(
                        assistant_message.get("intent")
                    ),
                    platform=_optional_string(
                        assistant_message.get("platform")
                    ),
                    source_document=_optional_string(
                        assistant_message.get("source_document")
                    ),
                    feedback_eligible=bool(
                        assistant_message.get(
                            "feedback_eligible",
                            False,
                        )
                    ),
                )

                st.session_state.pending_ticket_status_query = None
                st.session_state.pending_question = None
                st.session_state.pending_assistant_message_id = None
                trim_chat_history()
                st.rerun()

            pending_question = st.session_state.pending_question

            if pending_question:
                pending_message_id = (
                    st.session_state.pending_assistant_message_id
                    or str(uuid.uuid4())
                )
                st.session_state.pending_assistant_message_id = (
                    pending_message_id
                )

                assistant_message = display_streaming_assistant(
                    question=pending_question,
                    history=build_assistant_history(),
                    message_index=len(
                        st.session_state.chat_messages
                    ),
                )

                add_chat_message(
                    role="assistant",
                    content=str(assistant_message["content"]),
                    message_id=pending_message_id,
                    route=_optional_string(
                        assistant_message.get("route")
                    ),
                    intent=_optional_string(
                        assistant_message.get("intent")
                    ),
                    platform=_optional_string(
                        assistant_message.get("platform")
                    ),
                    source_document=_optional_string(
                        assistant_message.get("source_document")
                    ),
                    feedback_eligible=bool(
                        assistant_message.get(
                            "feedback_eligible",
                            False,
                        )
                    ),
                    resource=_optional_string(
                        assistant_message.get("resource")
                    ),
                    caption=_optional_string(
                        assistant_message.get("caption")
                    ),
                )

                st.session_state.pending_question = None
                st.session_state.pending_assistant_message_id = None
                trim_chat_history()
                st.rerun()

        user_question = st.chat_input(
            "Describe your IT issue...",
            key="sjk_support_chat",
            max_chars=1000,
        )

    if user_question:
        cleaned_question = user_question.strip()

        if not cleaned_question:
            return

        detected_platform = detect_platform(cleaned_question)

        add_chat_message(
            role="user",
            content=cleaned_question,
            route="user_input",
            platform=detected_platform,
            feedback_eligible=False,
        )
        _audit_security_misuse(cleaned_question, detected_platform)

        if _is_ticket_status_query(cleaned_question):
            st.session_state.pending_ticket_status_query = cleaned_question
            st.session_state.pending_question = None
            st.session_state.pending_assistant_message_id = str(
                uuid.uuid4()
            )
            trim_chat_history()
            st.rerun()

        if _user_requests_escalation(cleaned_question):
            add_chat_message(
                role="assistant",
                content="I can help you create an IT ticket for this issue.",
                route="escalation",
                platform=detected_platform,
                feedback_eligible=False,
            )
            st.session_state.pending_question = None
            st.session_state.pending_assistant_message_id = None
            trim_chat_history()
            st.rerun()

        trim_chat_history()
        st.session_state.pending_question = cleaned_question
        st.session_state.pending_assistant_message_id = str(
            uuid.uuid4()
        )

        st.rerun()
