from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.text_matching import (
    contains_any_phrase,
    normalize_text,
)


OUT_OF_SCOPE_MESSAGE = (
    "I can only help with IT-related questions. "
    "For this request, please contact your respective "
    "supervisor or the appropriate department."
)


UNSUPPORTED_IT_MESSAGE = (
    "I can help with IT-related issues, but I do not have an "
    "approved procedure for that request. Please contact the "
    "IT Helpdesk for further assistance."
)


@dataclass(frozen=True)
class ConversationDecision:
    """A direct conversational response."""

    handled: bool
    answer: str = ""


ACKNOWLEDGEMENT_REPLIES = {
    "ok": (
        "Sounds good. Let me know if you need help with "
        "another IT issue."
    ),
    "appreciate it": (
        "Great. Let me know if you need help with another "
        "IT issue."
    ),
    "okay": (
        "Sounds good. Let me know if you need help with "
        "another IT issue."
    ),
    "alright": (
        "Sounds good. Let me know if you need help with "
        "another IT issue."
    ),
    "got it": (
        "Great. Let me know if you need help with another "
        "IT issue."
    ),
    "thank you": (
        "You're welcome! Let me know if you need help with "
        "another IT issue."
    ),
    "thanks": (
        "You're welcome! Let me know if you need help with "
        "another IT issue."
    ),
    "thanks a lot": (
        "You're welcome! Let me know if you need help with "
        "another IT issue."
    ),
    "perfect": (
        "Great! Let me know if you need help with another "
        "IT issue."
    ),
    "cool": (
        "Great! Let me know if you need help with another "
        "IT issue."
    ),
    "done": (
        "Great! Let me know if you need help with another "
        "IT issue."
    ),
    "that worked": (
        "Great! I'm glad the issue is resolved. Let me know "
        "if you need help with another IT issue."
    ),
    "it works now": (
        "Great! I'm glad the issue is resolved. Let me know "
        "if you need help with another IT issue."
    ),
    "solved": (
        "Great! I'm glad the issue is resolved. Let me know "
        "if you need help with another IT issue."
    ),
    # Extended Gratitude Variations
    "thank you so much": (
        "You're welcome! Let me know if you need help with "
        "another IT issue."
    ),
    "thx": (
        "You're welcome! Let me know if you need help with "
        "another IT issue."
    ),
    "many thanks": (
        "You're welcome! Let me know if you need help with "
        "another IT issue."
    ),
    "cheers": (
        "You're welcome! Let me know if you need help with "
        "another IT issue."
    ),

    # Extended Success & Resolution Indicators
    "fixed": (
        "Great! I'm glad the issue is resolved. Let me know "
        "if you need help with another IT issue."
    ),
    "works perfectly": (
        "Great! I'm glad the issue is resolved. Let me know "
        "if you need help with another IT issue."
    ),
    "it's working": (
        "Great! I'm glad the issue is resolved. Let me know "
        "if you need help with another IT issue."
    ),
    "that did the trick": (
        "Great! I'm glad the issue is resolved. Let me know "
        "if you need help with another IT issue."
    ),
    "that fixed it": (
        "Great! I'm glad the issue is resolved. Let me know "
        "if you need help with another IT issue."
    ),
    "awesome": (
        "Great! Let me know if you need help with another "
        "IT issue."
    ),
    "sweet": (
        "Great! Let me know if you need help with another "
        "IT issue."
    ),
    "great": (
        "Great! Let me know if you need help with another "
        "IT issue."
    ),
    "all good": (
        "Sounds good. Let me know if you need help with "
        "another IT issue."
    ),
    "all set": (
        "Sounds good. Let me know if you need help with "
        "another IT issue."
    ),
    "makes sense": (
        "Sounds good. Let me know if you need help with "
        "another IT issue."
    ),
    "that's all": (
        "Sounds good. Let me know if you need help with "
        "another IT issue."
    ),
    "i'm good": (
        "Sounds good. Let me know if you need help with "
        "another IT issue."
    ),
    "yup": (
        "Sounds good. Let me know if you need help with "
        "another IT issue."
    ),
    "yeah": (
        "Sounds good. Let me know if you need help with "
        "another IT issue."
    ),
}


GREETING_REPLIES = {
    "hi",
    "hello",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
}


OUT_OF_SCOPE_PHRASES = (
    "paid time off",
    "direct deposit",
    "payroll",
    "salary",
    "benefits",
    "vacation request",
    "leave request",
    "human resources",
    "hr request",
    "tax form",
    "tuition",
    "school admission",
    "admissions",
    "course registration",
    "student grades",
    "transcript request",
    "cafeteria menu",
)


IT_TERMS = (
    "wifi",
    "internet",
    "network",
    "email",
    "gmail",
    "password",
    "account",
    "login",
    "log in",
    "sign in",
    "printer",
    "printing",
    "laptop",
    "computer",
    "macbook",
    "windows",
    "mac",
    "chromebook",
    "ipad",
    "monitor",
    "screen",
    "display",
    "software",
    "browser",
    "chrome",
    "hardware",
    "device",
    "usb",
    "cable",
    "charger",
    "adapter",
    "mouse",
    "keyboard",
    "projector",
    "inventory",
    "borrow",
    "loaner",
    "phishing",
    "spam",
    "suspicious email",
    "vendor email",
    "airplay",
    "air play",
    "apple tv",
    "screen mirroring",
    "screen mirror",
    "wireless display",
    "miracast",
    "projector",
    "external display",
    "force quit",
    "force close",
    "end task",
    "not responding",
    "microsoft",
    "microsoft 365",
    "office 365",
    "microsoft office",
    "microsoft word",
    "word document",
    "excel",
    "powerpoint",
    "onedrive",
    "outlook",
    "teams",
    "google workspace",
    "google docs",
    "google sheets",
    "google slides",
    "google drive",
    "google classroom",
    "google calendar",
    "google meet",
    "google forms",
    "google chat",
    "zoom",
    "spreadsheet",
)

def looks_like_it_question(
    question: str,
) -> bool:
    """Determine whether a question appears IT-related."""

    normalized = normalize_text(question)

    return contains_any_phrase(
        normalized,
        IT_TERMS,
    )


def route_conversation_message(
    question: str,
    history: list[dict[str, Any]],
) -> ConversationDecision:
    """Handle greetings, acknowledgements, and non-IT requests."""

    del history

    normalized = normalize_text(question)

    if not normalized:
        return ConversationDecision(
            handled=True,
            answer="Please enter an IT support question.",
        )

    if normalized in ACKNOWLEDGEMENT_REPLIES:
        return ConversationDecision(
            handled=True,
            answer=ACKNOWLEDGEMENT_REPLIES[normalized],
        )

    if normalized in GREETING_REPLIES:
        return ConversationDecision(
            handled=True,
            answer=(
                "Hello! How can I help you with an IT issue today?"
            ),
        )

    if normalized in {
        "bye",
        "goodbye",
        "see you",
    }:
        return ConversationDecision(
            handled=True,
            answer=(
                "Goodbye! Please contact the IT Helpdesk if "
                "you need further assistance."
            ),
        )

    if any(
        phrase in normalized
        for phrase in OUT_OF_SCOPE_PHRASES
    ):
        return ConversationDecision(
            handled=True,
            answer=OUT_OF_SCOPE_MESSAGE,
        )

    return ConversationDecision(
        handled=False,
    )