from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from core.text_matching import contains_any_phrase, contains_phrase, normalize_text


# Central topic vocabulary used only for routing/disambiguation.  The goal is
# not to answer the user here; it is to keep one word from hijacking a route.
TOPIC_ALIASES: dict[str, tuple[str, ...]] = {
    "external_monitor": (
        "external monitor",
        "external monitors",
        "second monitor",
        "second screen",
        "dual monitor",
        "dual monitors",
        "two monitors",
        "monitor",
        "monitors",
        "docking station",
        "usb-c dock",
        "usb c dock",
    ),
    "classroom_display": (
        "classroom display",
        "interactive classroom display",
        "smartboard",
        "smart board",
        "classroom tv",
        "projector",
    ),
    "google_classroom": (
        "google classroom",
    ),
    "airplay": (
        "airplay",
        "air play",
        "apple tv",
        "screen mirroring",
        "screen mirror",
    ),
    "printer": (
        "printer",
        "printers",
        "print queue",
        "printing",
    ),
    "wifi": (
        "wifi",
        "wireless network",
        "school network",
        "student wifi",
        "guest wifi",
    ),
    "google_password": (
        "google password",
        "gmail password",
        "school email password",
        "email password",
        "school account password",
        "google account password",
    ),
    "inventory": (
        "inventory",
        "loaner",
        "loaners",
        "borrow a laptop",
        "borrow laptop",
        "available laptop",
        "available laptops",
    ),
}

# A user may use a shorthand word in a correction that is too broad to be a
# normal positive alias.  "not classroom" should suppress both classroom web
# and classroom-display interpretations, without making bare "classroom" a
# high-confidence Google Classroom match everywhere else.
NEGATION_SHORTHANDS: dict[str, tuple[str, ...]] = {
    "classroom": ("google_classroom", "classroom_display"),
    "display": ("classroom_display",),
    "screen": ("classroom_display",),
    "monitor": ("external_monitor",),
    "printer": ("printer",),
    "wifi": ("wifi",),
    "wi-fi": ("wifi",),
    "airplay": ("airplay",),
}

CORRECTION_MARKERS = (
    "i mean",
    "i meant",
    "talking about",
    "i am talking about",
    "i'm talking about",
    "actually",
    "rather than",
    "instead of",
    "not for",
    "not about",
    "not the",
    "not google",
    "not classroom",
    "do not mean",
    "don't mean",
    "dont mean",
)


def _recent_user_issue(
    history: list[dict[str, Any]],
    current_question: str,
) -> str:
    current = normalize_text(current_question)

    for message in reversed(history[-12:]):
        if str(message.get("role", "")) != "user":
            continue

        content = str(message.get("content", "")).strip()
        if not content:
            continue

        # Streamlit history may already contain the current question.
        if normalize_text(content) == current:
            continue

        return content

    return ""


def _has_negation_pattern(text: str, phrase: str) -> bool:
    normalized = normalize_text(text)
    target = normalize_text(phrase)
    if not normalized or not target:
        return False

    escaped = re.escape(target)
    patterns = (
        rf"\bnot\s+(?:for\s+|about\s+|the\s+)?{escaped}\b",
        rf"\bdo\s+not\s+mean\s+(?:the\s+)?{escaped}\b",
        rf"\bdon't\s+mean\s+(?:the\s+)?{escaped}\b",
        rf"\bdont\s+mean\s+(?:the\s+)?{escaped}\b",
        rf"\binstead\s+of\s+(?:the\s+)?{escaped}\b",
        rf"\brather\s+than\s+(?:the\s+)?{escaped}\b",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def _has_affirmation_pattern(text: str, phrase: str) -> bool:
    normalized = normalize_text(text)
    target = normalize_text(phrase)
    if not normalized or not target:
        return False

    escaped = re.escape(target)
    patterns = (
        rf"\bi\s+mean\s+(?:the\s+)?{escaped}\b",
        rf"\bi\s+meant\s+(?:the\s+)?{escaped}\b",
        rf"\b(?:i\s+am|i'm)\s+talking\s+about\s+(?:the\s+)?{escaped}\b",
        rf"\btalking\s+about\s+(?:the\s+)?{escaped}\b",
        rf"\bactually\s+(?:the\s+)?{escaped}\b",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def _extract_negated_topics(text: str) -> set[str]:
    blocked: set[str] = set()

    for topic, aliases in TOPIC_ALIASES.items():
        if any(_has_negation_pattern(text, alias) for alias in aliases):
            blocked.add(topic)

    for shorthand, topics in NEGATION_SHORTHANDS.items():
        if _has_negation_pattern(text, shorthand):
            blocked.update(topics)

    return blocked


def _extract_affirmed_topics(text: str) -> set[str]:
    affirmed: set[str] = set()

    for topic, aliases in TOPIC_ALIASES.items():
        if any(_has_affirmation_pattern(text, alias) for alias in aliases):
            affirmed.add(topic)

    # For compact corrections like "monitor, not classroom", treat a clear
    # topic word as the intended subject when the message also has a correction
    # marker.  Bare occurrences outside a correction do not get this boost.
    normalized = normalize_text(text)
    has_correction_marker = any(marker in normalized for marker in CORRECTION_MARKERS)
    if has_correction_marker:
        for topic, aliases in TOPIC_ALIASES.items():
            if contains_any_phrase(normalized, aliases):
                affirmed.add(topic)

    return affirmed


@dataclass(frozen=True)
class TopicContext:
    current_text: str
    prior_issue: str
    effective_text: str
    retrieval_text: str
    negated_topics: frozenset[str]
    affirmed_topics: frozenset[str]
    is_correction: bool

    def allows(self, topic: str) -> bool:
        """Whether a deterministic route may claim *topic*."""
        return topic not in self.negated_topics or topic in self.affirmed_topics

    def mentions(self, topic: str) -> bool:
        aliases = TOPIC_ALIASES.get(topic, ())
        if not aliases:
            return False
        return contains_any_phrase(self.effective_text, aliases)

    def current_mentions(self, topic: str) -> bool:
        aliases = TOPIC_ALIASES.get(topic, ())
        if not aliases:
            return False
        return contains_any_phrase(self.current_text, aliases)


def build_topic_context(
    question: str,
    history: list[dict[str, Any]],
) -> TopicContext:
    """Resolve explicit corrections before deterministic routing and RAG.

    This is intentionally rule-light: it does not decide the final answer.  It
    only preserves the previous user issue for a short correction and records
    topics that the user explicitly rejected, so a word such as "classroom"
    cannot hijack the next route.
    """

    current = normalize_text(question)
    negated = _extract_negated_topics(question)
    affirmed = _extract_affirmed_topics(question)
    # Explicit negative evidence wins over a generic topic word appearing in
    # the same correction ("I mean printer, not Wi-Fi").
    affirmed.difference_update(negated)

    is_correction = bool(
        negated
        or affirmed
        or any(marker in current for marker in CORRECTION_MARKERS)
    )

    prior_issue = _recent_user_issue(history, question) if is_correction else ""

    if prior_issue:
        effective = f"{prior_issue} {question}".strip()
    else:
        effective = question

    clarification_lines: list[str] = []
    if affirmed:
        clarification_lines.append(
            "Intended topic: " + ", ".join(sorted(affirmed)) + "."
        )
    if negated:
        clarification_lines.append(
            "Do not interpret as: " + ", ".join(sorted(negated)) + "."
        )

    if prior_issue and clarification_lines:
        retrieval = (
            f"Original issue: {prior_issue}\n"
            f"User clarification: {question}\n"
            + " ".join(clarification_lines)
        )
    elif clarification_lines:
        retrieval = f"{question}\n" + " ".join(clarification_lines)
    else:
        retrieval = question

    return TopicContext(
        current_text=current,
        prior_issue=prior_issue,
        effective_text=normalize_text(effective),
        retrieval_text=retrieval,
        negated_topics=frozenset(negated),
        affirmed_topics=frozenset(affirmed),
        is_correction=is_correction,
    )


def topic_is_explicitly_negated(
    question: str,
    topic: str,
) -> bool:
    """Small convenience helper for routers without conversation context."""
    return topic in _extract_negated_topics(question)
