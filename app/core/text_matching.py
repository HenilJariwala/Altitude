from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping

from rapidfuzz import fuzz


def normalize_text(text: str) -> str:
    """Normalize user text for predictable matching."""

    normalized = unicodedata.normalize(
        "NFKC",
        text,
    ).lower()

    normalized = (
        normalized
        .replace("wi-fi", "wifi")
        .replace("wi fi", "wifi")
        .replace("’", "'")
    )

    normalized = re.sub(
        r"[^a-z0-9.'\s-]",
        " ",
        normalized,
    )

    return " ".join(normalized.split())


def contains_phrase(
    text: str,
    phrase: str,
) -> bool:
    """Match a complete normalized word or phrase.

    Plain substring checks make values such as ``mac`` match words such
    as ``machine``. This helper prevents those false positives while
    still supporting multi-word phrases.
    """

    normalized_text = normalize_text(text)
    normalized_phrase = normalize_text(phrase)

    if not normalized_text or not normalized_phrase:
        return False

    return bool(
        re.search(
            rf"(?<![a-z0-9]){re.escape(normalized_phrase)}(?![a-z0-9])",
            normalized_text,
        )
    )


def contains_any_phrase(
    text: str,
    phrases: Iterable[str],
) -> bool:
    """Return whether any complete phrase occurs in *text*."""

    return any(
        contains_phrase(text, phrase)
        for phrase in phrases
    )


def similarity_score(
    text: str,
    phrase: str,
) -> float:
    """Return a typo-tolerant similarity score."""

    normalized_text = normalize_text(text)
    normalized_phrase = normalize_text(phrase)

    if not normalized_text or not normalized_phrase:
        return 0.0

    if contains_phrase(
        normalized_text,
        normalized_phrase,
    ):
        return 100.0

    return max(
        fuzz.partial_ratio(
            normalized_text,
            normalized_phrase,
        ),
        fuzz.token_set_ratio(
            normalized_text,
            normalized_phrase,
        ),
    )


def matches_any(
    text: str,
    phrases: Iterable[str],
    threshold: float = 80.0,
) -> bool:
    return any(
        similarity_score(text, phrase) >= threshold
        for phrase in phrases
    )


def classify_alias(
    text: str,
    aliases: Mapping[str, Iterable[str]],
    threshold: float = 80.0,
) -> str | None:
    best_label: str | None = None
    best_score = 0.0

    for label, phrases in aliases.items():
        for phrase in phrases:
            score = similarity_score(
                text,
                phrase,
            )

            if score > best_score:
                best_label = label
                best_score = score

    if best_score < threshold:
        return None

    return best_label
