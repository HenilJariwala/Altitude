from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from core.analytics_db import (
    create_knowledge_draft,
    get_knowledge_draft,
    get_resolved_tickets_without_knowledge_drafts,
    set_knowledge_draft_review_status,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIRECTORY = PROJECT_ROOT / "knowledge_base"
LEARNED_KNOWLEDGE_FILENAME = "learned_support.md"
LEARNED_KNOWLEDGE_PATH = KNOWLEDGE_DIRECTORY / LEARNED_KNOWLEDGE_FILENAME
LEARNED_KNOWLEDGE_HEADER = """---
title: "Altitude Learned Support Knowledge"
topic: learned_support
audience: public
document_type: support_procedure_collection
workflow: resolved_ticket_learning
version: 1.0
---"""

GENERIC_RESOLUTION_NOTES = {
    "done",
    "fixed",
    "resolved",
    "complete",
    "completed",
    "closed",
    "issue fixed",
    "issue resolved",
    "problem fixed",
    "problem resolved",
    "working",
    "working now",
    "all good",
}

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "can",
    "for",
    "from",
    "has",
    "have",
    "how",
    "i",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "user",
    "with",
    "won",
    "wont",
    "not",
}

SENSITIVE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
        "[school email removed]",
    ),
    (
        re.compile(r"\bALT\s*-?\s*20\d{2}\s*-?\s*\d{1,8}\b", re.IGNORECASE),
        "[ticket reference removed]",
    ),
    (
        re.compile(
            r"(?i)\b(password|passcode|api\s*key|token|secret)\s*[:=]\s*[^\s,;]+"
        ),
        r"\1: [removed]",
    ),
)


def _normalize_space(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _sanitize_text(value: Any, *, maximum_length: int = 6000) -> str:
    text = str(value or "").replace("\x00", " ")
    for pattern, replacement in SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    text = re.sub(r"(?im)^\s*Requester Email\s*:\s*.*$", "", text)
    text = re.sub(r"(?im)^\s*Altitude Reference\s*:\s*.*$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:maximum_length].strip()


def _clean_ticket_title(value: Any) -> str:
    title = _sanitize_text(value, maximum_length=255)
    title = re.sub(r"^\s*\[[^\]]*ALT[^\]]*\]\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"^\s*(?:ticket|issue|problem)\s*[:\-]\s*", "", title, flags=re.IGNORECASE)
    return _normalize_space(title) or "Resolved IT issue"


def _extract_problem_from_payload(payload_json: Any, fallback_title: str) -> str:
    try:
        payload = json.loads(str(payload_json or "{}"))
    except (TypeError, json.JSONDecodeError):
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    description = _sanitize_text(payload.get("description"), maximum_length=5000)
    if description:
        return description

    location = _normalize_space(payload.get("location"))
    if location:
        return f"{fallback_title} at {location}."

    return fallback_title


def _resolution_is_useful(value: str) -> bool:
    normalized = _normalize_space(value).casefold().strip(" .!:-")
    if not normalized:
        return False
    if normalized in GENERIC_RESOLUTION_NOTES:
        return False
    # A short but actionable note such as "Restarted Chromebook" is useful.
    return len(normalized) >= 10


def _split_steps(resolution: str) -> list[str]:
    text = _sanitize_text(resolution, maximum_length=5000)
    if not text:
        return []

    # Normalize common technician note styles: numbered lines, bullets,
    # semicolon-separated actions, and compact sentence sequences.
    pieces = re.split(
        r"(?:\r?\n)+|\s*;\s*|(?<=\.)\s+(?=[A-Z0-9])|\s+->\s+",
        text,
    )

    steps: list[str] = []
    for piece in pieces:
        cleaned = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", piece).strip()
        cleaned = _normalize_space(cleaned).strip(" -")
        if not cleaned:
            continue
        if cleaned.casefold() in GENERIC_RESOLUTION_NOTES:
            continue
        if cleaned not in steps:
            steps.append(cleaned[:1200])

    if not steps and _resolution_is_useful(text):
        steps.append(_normalize_space(text)[:1200])

    return steps[:12]


def _keywords_for_ticket(
    *,
    title: str,
    category: str,
    device: str,
    problem: str,
) -> str:
    source = " ".join((title, category, device, problem[:700])).lower()
    tokens = re.findall(r"[a-z0-9][a-z0-9+._-]{2,}", source)

    keywords: list[str] = []
    title_phrase = _normalize_space(title).lower()
    if title_phrase:
        keywords.append(title_phrase[:120])

    for token in tokens:
        normalized = token.replace("_", " ").replace("-", " ").strip()
        if not normalized or normalized in STOP_WORDS:
            continue
        if normalized.isdigit():
            continue
        if normalized not in keywords:
            keywords.append(normalized)
        if len(keywords) >= 14:
            break

    for extra in (category, device):
        normalized = _normalize_space(extra).lower().replace("_", " ")
        if normalized and normalized not in {"not provided", "other"} and normalized not in keywords:
            keywords.append(normalized)

    return ", ".join(keywords[:16])


def _direct_answer_from_resolution(resolution: str, steps: list[str]) -> str:
    if len(steps) == 1:
        return steps[0]
    return "Use the troubleshooting steps below to apply the fix that resolved this issue."


def build_ticket_draft(ticket: dict[str, Any]) -> dict[str, Any] | None:
    """Convert one resolved ticket into a conservative structured draft."""
    resolution = _sanitize_text(ticket.get("resolution_comment"), maximum_length=5000)
    if not _resolution_is_useful(resolution):
        return None

    title = _clean_ticket_title(ticket.get("title"))
    problem = _extract_problem_from_payload(ticket.get("payload_json"), title)
    steps = _split_steps(resolution)
    if not steps:
        return None

    category = _normalize_space(ticket.get("category"))
    device = _normalize_space(ticket.get("device"))

    return {
        "local_ticket_id": int(ticket["local_ticket_id"]),
        "external_ticket_id": _normalize_space(ticket.get("external_ticket_id")) or None,
        "altitude_reference": _normalize_space(ticket.get("altitude_reference")) or None,
        "source_status": _normalize_space(ticket.get("status")) or "Resolved",
        "source_title": title,
        "source_category": category,
        "source_device": device,
        "source_problem": problem,
        "source_resolution": resolution,
        "draft_title": title,
        "intent_keywords": _keywords_for_ticket(
            title=title,
            category=category,
            device=device,
            problem=problem,
        ),
        "target_audience": "Staff, Faculty, Students",
        "direct_answer": _direct_answer_from_resolution(resolution, steps),
        "troubleshooting_steps": steps,
        "bot_instruction": (
            "Use this procedure only when the user's symptoms match this resolved issue. "
            "Do not invent missing steps, credentials, permissions, or administrator actions."
        ),
    }


def sync_resolved_tickets_to_knowledge_queue(*, limit: int = 250) -> dict[str, int]:
    """Create pending drafts for newly resolved tickets with useful notes."""
    tickets = get_resolved_tickets_without_knowledge_drafts(limit=limit)
    created = 0
    skipped = 0

    for ticket in tickets:
        draft = build_ticket_draft(ticket)
        if draft is None:
            skipped += 1
            continue
        create_knowledge_draft(**draft)
        created += 1

    return {
        "resolved_candidates": len(tickets),
        "created": created,
        "skipped": skipped,
    }



def build_published_topic_section(draft: dict[str, Any]) -> str:
    """Build one approved support topic for the shared learned-knowledge file."""
    title = _normalize_space(draft.get("draft_title"))
    keywords = _normalize_space(draft.get("intent_keywords"))
    audience = _normalize_space(draft.get("target_audience")) or "Staff, Faculty, Students"
    direct_answer = _sanitize_text(draft.get("direct_answer"), maximum_length=5000)
    bot_instruction = _sanitize_text(draft.get("bot_instruction"), maximum_length=2500)
    problem = _sanitize_text(draft.get("source_problem"), maximum_length=5000)
    steps = [
        _sanitize_text(step, maximum_length=1200)
        for step in draft.get("troubleshooting_steps", [])
        if _sanitize_text(step, maximum_length=1200)
    ]

    if not title or not direct_answer or not steps:
        raise ValueError("The knowledge draft is missing required publication fields")

    lines = [
        f"## Topic: {title}",
        f"**Intent Keywords:** {keywords}",
        f"**Target Audience:** {audience}",
        "",
    ]

    if bot_instruction:
        lines.extend((f"**Bot Instruction:** {bot_instruction}", ""))

    if problem:
        lines.extend(("**Use this procedure when:**", problem, ""))

    lines.extend(("**Direct Answer:**", direct_answer, "", "**Troubleshooting Steps:**"))
    for index, step in enumerate(steps, start=1):
        lines.append(f"{index}. {step}")

    lines.extend(
        (
            "",
            "**Escalation:**",
            "If these approved steps do not resolve the issue, contact the IT Helpdesk.",
        )
    )
    return "\n".join(lines).strip()


def build_published_markdown(draft: dict[str, Any]) -> str:
    """Build a complete one-topic learned knowledge document.

    This function is retained for compatibility with existing tests/tools. Live
    publishing appends only the topic section to the shared learned_support.md.
    """
    section = build_published_topic_section(draft)
    return f"{LEARNED_KNOWLEDGE_HEADER}\n\n{section}\n"


def _shared_file_content(existing: str, new_section: str) -> str:
    """Return the complete shared knowledge file after appending one topic."""
    current = str(existing or "").strip()
    section = str(new_section or "").strip()

    if not section:
        raise ValueError("The published knowledge section is empty")

    if not current:
        return f"{LEARNED_KNOWLEDGE_HEADER}\n\n{section}\n"

    # A valid shared file has one YAML header at the beginning and any number
    # of `## Topic:` sections. New approvals are appended as another section.
    if not current.startswith("---"):
        current = f"{LEARNED_KNOWLEDGE_HEADER}\n\n{current}"

    return f"{current.rstrip()}\n\n{section}\n"


def _write_text_atomic(path: Path, content: str) -> None:
    """Replace a text file atomically so a failed write cannot truncate it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    temporary_path.write_text(content, encoding="utf-8")
    temporary_path.replace(path)


def _vector_document_for_markdown(
    *,
    markdown: str,
    filename: str,
    title: str,
    keywords: str,
) -> Any:
    # Keep vector/RAG imports lazy so the administrator can still inspect and
    # edit queued drafts if the embedding service is temporarily unavailable.
    from langchain_core.documents import Document

    section_match = re.search(r"(?ms)^## Topic:.*\Z", markdown)
    section = section_match.group(0).strip() if section_match else markdown.strip()
    return Document(
        page_content=section,
        metadata={
            "source": filename,
            "audience": "public",
            "document_title": title,
            "title": title,
            "section_title": title,
            "intent_keywords": keywords,
            "full_section": section,
            "document_type": "support_procedure",
            "workflow": "resolved_ticket_learning",
        },
    )


def publish_knowledge_draft(
    draft_id: int,
    *,
    reviewed_by: str,
    review_notes: str | None = None,
) -> str:
    """Append one approved draft to learned_support.md and index that topic."""
    from core.rag import get_lexical_documents, get_vector_store

    draft = get_knowledge_draft(int(draft_id))
    if draft is None:
        raise ValueError("Knowledge draft was not found")
    if str(draft.get("review_status")) != "Pending":
        raise ValueError("Only pending knowledge drafts can be published")

    section = build_published_topic_section(draft)
    title = _normalize_space(draft.get("draft_title"))
    keywords = _normalize_space(draft.get("intent_keywords"))
    filename = LEARNED_KNOWLEDGE_FILENAME
    final_path = LEARNED_KNOWLEDGE_PATH

    original_content = final_path.read_text(encoding="utf-8") if final_path.exists() else ""
    updated_content = _shared_file_content(original_content, section)

    vector_document = _vector_document_for_markdown(
        markdown=section,
        filename=filename,
        title=title,
        keywords=keywords,
    )
    vector_id = hashlib.sha256(
        f"knowledge-draft:{draft_id}:{filename}:{section}".encode("utf-8")
    ).hexdigest()

    vector_store = get_vector_store()
    indexed = False
    file_written = False

    try:
        # Index only this new topic. The rest of the shared file is already in
        # Chroma, so approving one item does not re-embed every learned topic.
        vector_store.add_documents([vector_document], ids=[vector_id])
        indexed = True

        _write_text_atomic(final_path, updated_content)
        file_written = True

        set_knowledge_draft_review_status(
            int(draft_id),
            review_status="Approved",
            reviewed_by=reviewed_by,
            review_notes=review_notes,
            published_filename=filename,
        )
    except Exception:
        if file_written:
            try:
                if original_content:
                    _write_text_atomic(final_path, original_content)
                else:
                    final_path.unlink(missing_ok=True)
            except Exception:
                pass

        if indexed:
            try:
                vector_store.delete(ids=[vector_id])
            except Exception:
                pass
        raise

    # Clear lexical fallback cache so the appended topic is immediately usable.
    get_lexical_documents.cache_clear()
    return filename

def reject_knowledge_draft(
    draft_id: int,
    *,
    reviewed_by: str,
    review_notes: str | None = None,
) -> None:
    """Keep an audit trail for a draft that should not become live knowledge."""
    set_knowledge_draft_review_status(
        int(draft_id),
        review_status="Rejected",
        reviewed_by=reviewed_by,
        review_notes=review_notes,
    )
