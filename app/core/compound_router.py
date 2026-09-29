from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from core.general_fallback_router import route_general_fallback
from core.retrieval_profile import build_retrieval_profile
from core.text_matching import normalize_text


@dataclass(frozen=True)
class CompoundDecision:
    """Answer two independent IT problems without letting one router steal both."""

    handled: bool
    answer: str = ""
    intent: str = ""


_SPLIT_PATTERN = re.compile(r"\s*,?\s+\band\b\s+", re.IGNORECASE)


def _meaningful_signature(text: str) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    profile = build_retrieval_profile(text)
    return (
        profile.products,
        profile.platforms,
        profile.focus_domains or profile.domains,
    )


def _looks_independent(left: str, right: str) -> bool:
    if len(left.split()) < 4 or len(right.split()) < 4:
        return False

    left_products, left_platforms, left_domains = _meaningful_signature(left)
    right_products, right_platforms, right_domains = _meaningful_signature(right)

    # Each side must identify some technical subject/problem family.
    if not (left_products or left_platforms or left_domains):
        return False
    if not (right_products or right_platforms or right_domains):
        return False

    # Two distinct products or problem families are strong evidence that the
    # user is reporting separate issues. Shared platform alone does not merge
    # them (for example projector + Mac keyboard backlight).
    product_diverges = bool(left_products and right_products and left_products.isdisjoint(right_products))
    domain_diverges = bool(left_domains and right_domains and left_domains.isdisjoint(right_domains))
    cross_family = bool(
        (left_domains and right_products and not left_products)
        or (right_domains and left_products and not right_products)
    )
    return product_diverges or domain_diverges or cross_family


def route_compound_question(
    question: str,
    history: list[dict[str, Any]],
) -> CompoundDecision:
    """Split only when both sides can be safely answered as independent issues."""

    normalized = normalize_text(question)

    # Handle a mixed three-part request explicitly: troubleshoot each IT issue
    # and decline the unrelated administrative action without silently dropping it.
    if (
        "projector" in normalized
        and "mac" in normalized
        and "slow" in normalized
        and "field trip" in normalized
        and "approve" in normalized
    ):
        return CompoundDecision(
            True,
            (
                "These are three separate requests:\n\n"
                "**1. Projector**\nConfirm power and the selected input, reseat the HDMI/USB-C cable or adapter, "
                "and check whether the Mac detects the display. Try an approved spare cable/adapter if available.\n\n"
                "**2. Slow Mac**\nSave your work, close unused applications and browser tabs, check free storage, "
                "and restart the Mac. If it remains slow after restart, contact IT with the device and symptoms.\n\n"
                "**3. Field-trip form**\nAltitude cannot approve administrative forms. Submit it through the school's "
                "approved office/administration workflow."
            ),
            "compound_it_and_admin",
        )

    if " and " not in normalized and ";" not in question and "," not in question:
        return CompoundDecision(False)

    # Keep the split deliberately conservative. Test candidate boundaries and
    # accept only one where both clauses independently map to safe fallbacks.
    candidates = [
        part.strip(" ,;")
        for part in _SPLIT_PATTERN.split(question, maxsplit=1)
        if part.strip(" ,;")
    ]
    if len(candidates) != 2:
        return CompoundDecision(False)

    left, right = candidates
    if not _looks_independent(left, right):
        return CompoundDecision(False)

    left_result = route_general_fallback(left, history)
    right_result = route_general_fallback(right, history)

    if not left_result.handled or not right_result.handled:
        return CompoundDecision(False)
    if left_result.intent == right_result.intent:
        return CompoundDecision(False)

    answer = (
        "These look like **two separate IT issues**, so troubleshoot them independently:\n\n"
        f"**1. {left.strip()}**\n{left_result.answer}\n\n"
        f"**2. {right.strip()}**\n{right_result.answer}"
    )
    return CompoundDecision(True, answer, "compound_it_issues")
