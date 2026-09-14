from __future__ import annotations

import re


EXPLICIT_ESCALATION_PHRASES = (
    "create a ticket",
    "create a helpdesk ticket",
    "create an it ticket",
    "create it ticket",
    "create IT ticket",
    "help me create it ticket",
    "help me create an it ticket",
    "help me create IT ticket",
    "want to create a helpdesk ticket",
    "want to create a ticket",
    "create ticket",
    "open a ticket",
    "submit a ticket",
    "escalate this",
    "escalate to it",
    "talk to it",
    "talk to the it team",
    "contact it",
    "contact the helpdesk",
    "human support",
    "need to talk to it",
    "does not know how to fix",
    "doesn't know how to fix",
    "cannot resolve",
    "can't resolve",
)


def user_requests_escalation(text: str) -> bool:
    normalized = " ".join(str(text).lower().split())

    if not normalized:
        return False

    negative_phrases = (
        "do not create a ticket",
        "don't create a ticket",
        "dont create a ticket",
        "no ticket",
    )

    if any(phrase in normalized for phrase in negative_phrases):
        return False

    # Questions about ticket policy, status, reopening, response time, or
    # whether a user is allowed to submit a ticket should receive an
    # informational answer first. They should not immediately open the
    # escalation form, because the user has not yet supplied an issue to
    # submit.
    informational_ticket_starts = (
        "how do i ",
        "how can i ",
        "where do i ",
        "what's ",
        "what is ",
        "why ",
        "can i ",
        "could i ",
        "who do i ",
        "is there ",
    )
    informational_ticket_terms = (
        "submit a ticket",
        "ticket status",
        "status of a ticket",
        "reopen",
        "response time",
        "assigned",
        "on behalf",
        "high priority",
        "attach",
        "screenshot",
        "closed",
        "resolved",
        "not urgent",
    )

    if (
        normalized.startswith(informational_ticket_starts)
        and "ticket" in normalized
        and any(term in normalized for term in informational_ticket_terms)
    ):
        return False

    if re.search(
        r"\b(?:help me|can you help me|please)?\s*(?:create|open|submit|make)\s+(?:an?\s+)?i\s*t\s+ticket\b",
        normalized,
    ):
        return True

    if (
        "ticket" in normalized
        and any(phrase in normalized for phrase in ("help me", "can you help", "please"))
        and any(verb in normalized for verb in ("create", "open", "submit", "make"))
    ):
        return True

    return any(phrase in normalized for phrase in EXPLICIT_ESCALATION_PHRASES)
