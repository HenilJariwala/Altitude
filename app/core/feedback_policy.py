from __future__ import annotations

import re


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


def is_feedback_eligible_response(
    response_text: str,
    *,
    route: str,
) -> bool:
    """Return whether Helpful/Not Helpful controls should be displayed.

    Feedback is shown for complete informational, troubleshooting, inventory,
    and policy answers. It stays hidden for greetings, short clarifying
    questions, out-of-scope redirects, security/privacy refusals, errors, and
    ticket-form transitions.
    """

    if route in {"greeting", "clarification", "error", "escalation"}:
        return False

    normalized = " ".join(response_text.lower().replace("’", "'").split())
    plain_normalized = re.sub(r"[*_`#]", "", normalized)

    if not normalized:
        return False

    if any(plain_normalized.startswith(prefix) for prefix in CLARIFICATION_PREFIXES):
        return False

    # These are complete answers the user can meaningfully rate even though
    # they may not contain numbered troubleshooting steps.
    explicit_feedback_answers = (
        "i can help troubleshoot common sjk technology issues",
        "for security reasons, the wi-fi password is not provided as plain text",
        "for security reasons, the wifi password is not provided as plain text",
    )
    if any(plain_normalized.startswith(prefix) for prefix in explicit_feedback_answers):
        return True

    hidden_prefixes = (
        "hello",
        "hi ",
        "i'm altitude",
        "i am altitude",
        "i'm focused on sjk it support",
        "i can help you create an it ticket",
        "i cannot provide",
        "i cannot reveal",
        "i cannot access",
        "i cannot perform",
        "i cannot help bypass",
        "i can't provide",
        "do not share your password",
        "administrator credentials are restricted",
        "passwords are private",
        "please clarify",
        "i'm sorry the response was not useful",
        "i am sorry the response was not useful",
    )

    if any(plain_normalized.startswith(prefix) for prefix in hidden_prefixes):
        return False

    hidden_markers = (
        "each support session must remain private",
        "sensitive secrets",
        "unverified claim of authorization",
        "non-it request",
        "what technology issue are you experiencing",
    )

    if any(marker in normalized for marker in hidden_markers):
        return False

    # A short question without resolution steps is a clarification, not a
    # completed answer. Feedback will be offered after the final response.
    if "?" in response_text and len(normalized.split()) <= 90:
        has_resolution_steps = bool(re.search(r"(?m)^\s*\d+[.)]\s+", response_text))
        if not has_resolution_steps:
            return False

    substantive_markers = (
        "1.",
        "2.",
        "available:",
        "currently unavailable",
        "current live availability",
        "not listed in the current live inventory",
        "contact the it helpdesk",
        "contact or visit the it helpdesk",
        "report it to the it helpdesk",
        "contact the it team",
        "qr code",
    )

    if any(marker in normalized for marker in substantive_markers):
        return True

    # Bulleted capability/policy answers and other complete direct answers are
    # also useful to rate. Very short acknowledgements remain hidden.
    has_bullets = bool(re.search(r"(?m)^\s*[-*•]\s+", response_text))
    if has_bullets:
        return True

    return len(normalized.split()) >= 12
