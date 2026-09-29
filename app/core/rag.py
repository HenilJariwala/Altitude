from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb
import frontmatter
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import (
    OllamaEmbeddings,
)

from core.app_logging import get_logger
from core.conversation_context import build_contextual_query
from core.platform_context import detect_platform
from core.retrieval_profile import (
    build_document_profile,
    build_retrieval_profile,
    issue_focus,
    profile_score,
    profiles_are_compatible,
)
from core.text_matching import normalize_text


load_dotenv()
LOGGER = get_logger("rag")


PROJECT_ROOT = Path(__file__).resolve().parents[2]

KNOWLEDGE_DIRECTORY = PROJECT_ROOT / "knowledge_base"

CHROMA_DIRECTORY = PROJECT_ROOT / "data" / "chroma"

COLLECTION_NAME = "sjk_public_knowledge"

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
)

OLLAMA_EMBED_MODEL = os.getenv(
    "OLLAMA_EMBED_MODEL",
    "all-minilm",
)

MICROSOFT_SUPPORT_ENABLED = os.getenv(
    "MICROSOFT_SUPPORT_ENABLED",
    "false",
).strip().lower() in {"1", "true", "yes", "on"}


def get_float_setting(
    name: str,
    default: float,
    minimum: float = 0.0,
) -> float:
    """Read a finite positive float without crashing at import time."""

    raw_value = os.getenv(
        name,
        str(default),
    ).strip()

    try:
        value = float(raw_value)
    except ValueError:
        return default

    if not math.isfinite(value) or value < minimum:
        return default

    return value


# Acceptance testing showed that semantic matches above roughly 0.66 are too
# unreliable for end-user support. Treat this as a code-level safety ceiling so
# an old/stale .env value (for example 0.95) cannot silently weaken retrieval.
RAG_HARD_DISTANCE_CEILING = 0.66

_configured_max_distance = get_float_setting(
    "RAG_MAX_DISTANCE",
    RAG_HARD_DISTANCE_CEILING,
)
RAG_MAX_DISTANCE = min(_configured_max_distance, RAG_HARD_DISTANCE_CEILING)

_configured_strong_distance = get_float_setting(
    "RAG_STRONG_DISTANCE",
    0.50,
)
RAG_STRONG_DISTANCE = min(_configured_strong_distance, RAG_MAX_DISTANCE)

# v10: distance-less lexical matches are never allowed to produce an end-user
# KB answer. They can still exist in the catalogue for diagnostics and future
# tooling, but retrieval must have a real semantic score before context is
# returned to the answer generator. Acceptance testing showed that None-distance
# answers were overwhelmingly wrong-topic.
ALLOW_DISTANCELESS_KB_ANSWERS = False


@dataclass(frozen=True)
class RagResult:
    context: str
    sources: tuple[str, ...]
    best_distance: float | None
    matched_chunks: int


@lru_cache(maxsize=1)
def get_vector_store() -> Chroma:
    if not CHROMA_DIRECTORY.exists():
        raise RuntimeError(
            "The Chroma database does not exist. Run scripts/ingest_knowledge.py first."
        )

    client = chromadb.PersistentClient(path=str(CHROMA_DIRECTORY))

    try:
        client.get_collection(name=COLLECTION_NAME)

    except Exception as error:
        raise RuntimeError(
            f"Chroma collection "
            f"'{COLLECTION_NAME}' was not found. "
            "Run scripts/ingest_knowledge.py first."
        ) from error

    embeddings = OllamaEmbeddings(
        model=OLLAMA_EMBED_MODEL,
        base_url=OLLAMA_BASE_URL,
    )

    return Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
    )


def _topic_sections(text: str) -> list[tuple[str, str]]:
    """Split an approved Markdown file into complete support topics."""

    matches = list(
        re.finditer(
            r"(?m)^## Topic:\s*(.+?)\s*$",
            text,
        )
    )

    if not matches:
        return []

    sections: list[tuple[str, str]] = []

    for index, match in enumerate(matches):
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )

        sections.append(
            (
                match.group(1).strip(),
                text[match.start() : end].strip(),
            )
        )

    return sections


@lru_cache(maxsize=1)
def get_lexical_documents() -> tuple[Document, ...]:
    """Load complete approved procedures for deterministic fallback search.

    Chroma remains the primary semantic retriever. This catalogue prevents
    exact support terms such as "force quit" from failing merely because
    the relevant topic was not returned in the vector search's top results.
    """

    documents: list[Document] = []

    if not KNOWLEDGE_DIRECTORY.exists():
        return ()

    for file_path in sorted(KNOWLEDGE_DIRECTORY.glob("*.md")):
        if not MICROSOFT_SUPPORT_ENABLED:
            source_name = file_path.name.lower()
            if "microsoft" in source_name or "windows" in source_name:
                continue

        post = frontmatter.load(file_path)
        content = post.content.strip()

        if not content:
            continue

        metadata = {
            str(key): (
                value
                if isinstance(value, (str, int, float, bool))
                else str(value)
            )
            for key, value in post.metadata.items()
        }

        audience = str(metadata.get("audience", "public")).lower()

        if audience != "public":
            continue

        for title, section in _topic_sections(content):
            keyword_match = re.search(
                r"\*\*Intent Keywords:\*\*\s*(.+)",
                section,
                flags=re.IGNORECASE,
            )

            section_metadata = metadata.copy()
            section_metadata.update(
                {
                    "source": file_path.name,
                    "audience": audience,
                    "document_title": str(
                        metadata.get("title", file_path.stem)
                    ),
                    "title": title,
                    "section_title": title,
                    "intent_keywords": (
                        keyword_match.group(1).strip()
                        if keyword_match
                        else ""
                    ),
                    "full_section": section,
                }
            )

            documents.append(
                Document(
                    page_content=section,
                    metadata=section_metadata,
                )
            )

    return tuple(documents)


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "could",
    "do",
    "does",
    "for",
    "from",
    "get",
    "has",
    "have",
    "help",
    "how",
    "i",
    "in",
    "is",
    "it",
    "my",
    "no",
    "not",
    "of",
    "on",
    "or",
    "please",
    "the",
    "to",
    "want",
    "what",
    "with",
    "working",
    "you",
}


TERM_ALIASES = {
    "macbook": "mac",
    "macos": "mac",
    "pc": "windows",
    "mic": "microphone",
    "audio": "sound",
    "emailed": "email",
    "emails": "email",
    "wifi": "wireless",
}


PRODUCT_ALIASES = {
    "google_chrome": (
        "google chrome",
        "chrome browser",
        "chrome",
    ),
    "safari": (
        "safari browser",
        "safari",
    ),
    "firefox": (
        "mozilla firefox",
        "firefox",
    ),
    "adobe_creative_cloud": (
        "adobe creative cloud",
        "creative cloud",
    ),
    "microsoft_word": (
        "microsoft word",
        "ms word",
        "word document",
        "word file",
        "using word",
        "in word",
        "with word",
    ),
    "microsoft_excel": (
        "microsoft excel",
        "ms excel",
        "excel workbook",
        "excel spreadsheet",
        "excel",
    ),
    "microsoft_powerpoint": (
        "microsoft powerpoint",
        "powerpoint presentation",
        "powerpoint",
        "power point",
    ),
    "microsoft_onedrive": (
        "microsoft onedrive",
        "one drive",
        "onedrive",
    ),
    "microsoft_outlook": (
        "microsoft outlook",
        "outlook",
    ),
    "adobe_acrobat": (
        "adobe acrobat",
        "acrobat",
        "adobe reader",
    ),
    "google_docs": (
        "google docs",
        "google doc",
    ),
    "google_sheets": (
        "google sheets",
        "google sheet",
    ),
    "google_slides": (
        "google slides",
        "google slide",
    ),
    "google_drive": ("google drive",),
    "google_classroom": ("google classroom",),
    "google_calendar": ("google calendar",),
    "google_meet": ("google meet",),
    "google_forms": (
        "google forms",
        "google form",
    ),
    "google_chat": ("google chat",),
    "gmail": ("gmail",),
}


PRODUCT_SUITES = {
    "google_chrome": "google",
    "safari": "apple",
    "firefox": "mozilla",
    "adobe_creative_cloud": "adobe",
    "microsoft_word": "microsoft",
    "microsoft_excel": "microsoft",
    "microsoft_powerpoint": "microsoft",
    "microsoft_onedrive": "microsoft",
    "microsoft_outlook": "microsoft",
    "adobe_acrobat": "adobe",
    "google_docs": "google",
    "google_sheets": "google",
    "google_slides": "google",
    "google_drive": "google",
    "google_classroom": "google",
    "google_calendar": "google",
    "google_meet": "google",
    "google_forms": "google",
    "google_chat": "google",
    "gmail": "google",
}


PRODUCTIVITY_CLARIFICATION_MARKERS = (
    "what would you like help with in",
    "which microsoft 365 service",
    "which google workspace service",
)


def contains_phrase(
    text: str,
    phrase: str,
) -> bool:
    return bool(
        re.search(
            rf"(?<!\w){re.escape(phrase)}(?!\w)",
            text,
        )
    )


def detect_product(
    text: str,
) -> str | None:
    normalized = normalize_text(text)

    for product, aliases in PRODUCT_ALIASES.items():
        for alias in sorted(
            aliases,
            key=len,
            reverse=True,
        ):
            if contains_phrase(
                normalized,
                alias,
            ):
                return product

    # Allow the short app name "word" only when the question
    # clearly treats it as an application.
    if contains_phrase(normalized, "word"):
        app_context_phrases = (
            "help me with word",
            "help with word",
            "use word",
            "word app",
            "word document",
            "word file",
            "in word",
            "using word",
            "microsoft",
        )

        if any(phrase in normalized for phrase in app_context_phrases):
            return "microsoft_word"

    return None


def detect_suite(
    text: str,
) -> str | None:
    normalized = normalize_text(text)

    product = detect_product(normalized)

    if product:
        return PRODUCT_SUITES.get(product)

    if any(
        phrase in normalized
        for phrase in (
            "microsoft 365",
            "office 365",
            "microsoft office",
            "sharepoint",
        )
    ):
        return "microsoft"

    if any(
        phrase in normalized
        for phrase in (
            "google workspace",
            "google",
            "gmail",
        )
    ):
        return "google"

    return None


def document_identity_text(
    document: Any,
) -> str:
    metadata = (
        getattr(
            document,
            "metadata",
            {},
        )
        or {}
    )

    return " ".join(
        [
            str(
                metadata.get(
                    "section_title",
                    "",
                )
            ),
            str(
                metadata.get(
                    "title",
                    "",
                )
            ),
            str(
                metadata.get(
                    "topic",
                    "",
                )
            ),
            str(
                metadata.get(
                    "workflow",
                    "",
                )
            ),
            str(
                metadata.get(
                    "source",
                    "",
                )
            ),
        ]
    )


def detect_document_product(
    document: Any,
) -> str | None:
    return detect_product(document_identity_text(document))


def detect_document_suite(
    document: Any,
) -> str | None:
    return detect_suite(document_identity_text(document))


def recent_assistant_requested_product_task(
    history: list[dict[str, Any]],
) -> bool:
    for message in reversed(history[-6:]):
        if message.get("role") != "assistant":
            continue

        content = normalize_text(
            str(
                message.get(
                    "content",
                    "",
                )
            )
        )

        return any(marker in content for marker in PRODUCTIVITY_CLARIFICATION_MARKERS)

    return False


def find_recent_user_product_question(
    history: list[dict[str, Any]],
) -> str:
    for message in reversed(history[-10:]):
        if message.get("role") != "user":
            continue

        content = str(
            message.get(
                "content",
                "",
            )
        ).strip()

        if content and detect_product(content):
            return content

    return ""


def build_retrieval_query(
    question: str,
    history: list[dict[str, Any]] | None,
) -> str:
    """Add prior context only when the current message is a follow-up."""

    cleaned_question = question.strip()

    if not history:
        return cleaned_question

    # A newly named product or suite starts a fresh topic. Do not attach it
    # to an earlier clarification for a different application.
    if detect_product(cleaned_question) or detect_suite(cleaned_question):
        return cleaned_question

    # The user answered the assistant's Microsoft or Google
    # clarification with a task such as "page numbers".
    if recent_assistant_requested_product_task(history):
        product_question = find_recent_user_product_question(history)

        if product_question:
            return f"{product_question}\nRequested task: {cleaned_question}"

    return build_contextual_query(
        cleaned_question,
        history,
    )


def extract_terms(
    text: str,
) -> set[str]:
    raw_words = re.findall(
        r"[a-z0-9-]+",
        text.lower(),
    )

    terms: set[str] = set()

    for word in raw_words:
        if word in STOP_WORDS or len(word) < 3:
            continue

        terms.add(word)

        alias = TERM_ALIASES.get(word)

        if alias:
            terms.add(alias)

        if len(word) > 5 and word.endswith("ed"):
            terms.add(word[:-2])

        if len(word) > 6 and word.endswith("ing"):
            terms.add(word[:-3])

        if len(word) > 5 and word.endswith("s"):
            terms.add(word[:-1])

    return terms


def detect_requested_platform(
    question: str,
) -> str | None:
    return detect_platform(question)


def document_platform(
    document: Any,
) -> str:
    return (
        str(
            document.metadata.get(
                "platform",
                "",
            )
        )
        .lower()
        .strip()
    )


def platform_is_compatible(
    requested_platform: str | None,
    candidate_platform: str,
) -> bool:
    """Reject knowledge written for the opposite operating system."""

    if requested_platform is None:
        return True

    normalized_candidate = (
        "macos" if candidate_platform == "mac" else candidate_platform
    )

    if normalized_candidate not in {
        "macos",
        "windows",
    }:
        return True

    return normalized_candidate == requested_platform


def document_topic_score(
    question: str,
    document: Any,
) -> int:
    """Rerank semantic results using product, title, and metadata."""

    focus_question = issue_focus(question)
    question_terms = extract_terms(focus_question)

    title = str(
        document.metadata.get(
            "section_title",
            document.metadata.get(
                "title",
                "",
            ),
        )
    )

    keywords = str(
        document.metadata.get(
            "intent_keywords",
            "",
        )
    )

    title_terms = extract_terms(title)

    keyword_terms = extract_terms(keywords)

    content_terms = extract_terms(document.page_content)

    score = 0

    score += len(question_terms.intersection(title_terms)) * 14

    score += len(question_terms.intersection(keyword_terms)) * 10

    score += len(question_terms.intersection(content_terms)) * 2

    normalized_question = normalize_text(question)
    normalized_focus = normalize_text(focus_question)

    for phrase in [part.strip() for part in keywords.split(",") if part.strip()]:
        normalized_phrase = normalize_text(phrase)
        if normalized_phrase in normalized_focus:
            score += 24
        elif normalized_phrase in normalized_question:
            score += 12

    requested_product = detect_product(question)

    document_product = detect_document_product(document)

    requested_suite = detect_suite(question)

    document_suite = detect_document_suite(document)

    if requested_product:
        if document_product == requested_product:
            score += 160

        elif document_product:
            if requested_suite and document_suite and requested_suite != document_suite:
                score -= 260
            else:
                score -= 150

        elif document_suite:
            if document_suite == requested_suite:
                score -= 20
            else:
                score -= 200

        else:
            # A generic Mac/Windows topic should not outrank a
            # specifically named Google or Microsoft product.
            score -= 110

    elif requested_suite:
        if document_suite == requested_suite:
            score += 45
        elif document_suite:
            score -= 140

    requested_platform = detect_requested_platform(question)

    candidate_platform = document_platform(document)

    os_specific_platforms = {
        "mac",
        "macos",
        "windows",
    }

    if requested_platform and candidate_platform in os_specific_platforms:
        matches = requested_platform == candidate_platform or (
            requested_platform == "macos" and candidate_platform == "mac"
        )

        score += 40 if matches else -120

    if any(
        term in normalized_question
        for term in (
            "weird email",
            "suspicious email",
            "phishing",
            "scam",
        )
    ):
        score += 30 if "phishing" in title.lower() else -20

    if "vendor" in normalized_question and any(
        term in normalized_question
        for term in (
            "missing",
            "not receiving",
            "can't find",
            "cant find",
        )
    ):
        score += 30 if "vendor" in title.lower() else 0

    return score


def _identity_parts(document: Any) -> tuple[str, str]:
    metadata = getattr(document, "metadata", {}) or {}
    title = str(metadata.get("section_title", metadata.get("title", "")))
    keywords = str(metadata.get("intent_keywords", ""))
    return title, keywords


def identity_overlap_count(question: str, document: Any) -> int:
    """Count non-trivial query terms that occur in topic identity metadata."""

    question_terms = extract_terms(issue_focus(question))
    title, keywords = _identity_parts(document)
    identity_terms = extract_terms(f"{title} {keywords}")
    generic = {
        "classroom", "screen", "display", "issue", "problem", "account",
        "school", "device", "computer", "laptop", "application", "user",
        "projector", "printer", "printing", "chromebook", "macbook", "macos",
        "google", "drive", "zoom", "adobe", "chrome", "safari", "wifi",
        "wireless", "keyboard", "camera", "audio", "sound", "website",
        "file", "folder", "student", "teacher", "help", "support",
    }
    return len({term for term in question_terms.intersection(identity_terms) if term not in generic})


def has_exact_intent_phrase(question: str, document: Any) -> bool:
    """Return whether a multi-word intent keyword appears in the query."""

    _, keywords = _identity_parts(document)
    normalized_question = normalize_text(question)
    for phrase in [part.strip() for part in keywords.split(",") if part.strip()]:
        normalized_phrase = normalize_text(phrase)
        if len(normalized_phrase.split()) >= 2 and normalized_phrase in normalized_question:
            return True
    return False


def semantic_match_is_acceptable(
    question: str,
    query_profile: Any,
    document: Any,
    distance: float,
) -> bool:
    """Final v10 semantic gate for product, task, symptom and identity.

    Embedding distance by itself is not enough. The remaining unseen-test
    failures were usually semantically close but operationally different topics
    inside the same suite. This gate gets progressively stricter as distance
    gets weaker.
    """

    if distance > RAG_MAX_DISTANCE:
        return False

    document_profile = build_document_profile(document)
    if not profiles_are_compatible(query_profile, document_profile):
        return False

    focus_domains = query_profile.focus_domains or query_profile.domains
    focus_symptoms = query_profile.focus_symptoms or query_profile.symptoms
    product_overlap = query_profile.products.intersection(document_profile.products)
    platform_overlap = query_profile.platforms.intersection(document_profile.platforms)
    domain_overlap = focus_domains.intersection(document_profile.domains)
    symptom_overlap = focus_symptoms.intersection(document_profile.symptoms)
    identity_count = identity_overlap_count(question, document)
    exact_intent = has_exact_intent_phrase(question, document)

    # Explicit products should remain in the same product when the topic has a
    # product identity. A suite-level generic topic may still be accepted at a
    # very strong distance, but not a weak one.
    if query_profile.products and document_profile.products and not product_overlap:
        return False

    # Explicit OS/device context must never cross to the opposite platform.
    if query_profile.platforms and document_profile.platforms and not platform_overlap:
        return False

    # A concrete task/problem family must agree whenever the topic itself has a
    # task identity. This catches Chrome extension -> accessibility, Gmail filter
    # -> spam, Meet attendance -> join-meeting, and mouse -> Wi-Fi.
    if focus_domains and document_profile.domains and not domain_overlap:
        return False

    if focus_symptoms and document_profile.symptoms and not (symptom_overlap or domain_overlap):
        return False

    # Very strong semantic matches can tolerate sparse metadata, but a product
    # name by itself is not enough when the user stated a concrete task. This
    # prevents same-product collisions such as Zoom licence -> New Meeting.
    structured_overlap = bool(product_overlap or platform_overlap or domain_overlap or symptom_overlap)
    task_identity = bool(domain_overlap or symptom_overlap or exact_intent or identity_count >= 1)
    has_task_signal = bool(focus_domains or focus_symptoms)

    if distance <= 0.42:
        if has_task_signal:
            return task_identity
        return exact_intent or identity_count >= 1 or structured_overlap

    if distance <= RAG_STRONG_DISTANCE:
        return task_identity and structured_overlap

    return (exact_intent or identity_count >= 2) and structured_overlap and task_identity


def has_meaningful_overlap(
    question: str,
    document: Any,
) -> bool:
    """Require overlap with the topic identity, not incidental procedure text."""

    question_terms = extract_terms(issue_focus(question))
    title = str(
        document.metadata.get(
            "section_title",
            document.metadata.get("title", ""),
        )
    )
    keywords = str(document.metadata.get("intent_keywords", ""))
    identity_terms = extract_terms(f"{title} {keywords}")
    overlap = question_terms.intersection(identity_terms)

    if len(overlap) >= 2:
        return True

    # One distinctive technical term can be enough, but generic words such as
    # "classroom", "screen", "issue", or "account" should not validate a topic.
    generic = {
        "classroom", "screen", "display", "issue", "problem", "account",
        "school", "device", "computer", "laptop", "application", "user",
        "projector", "printer", "printing", "chromebook", "macbook", "macos",
        "google", "drive", "zoom", "adobe", "chrome", "safari", "wifi",
        "wireless", "keyboard", "camera", "audio", "sound", "website",
    }
    return any(len(word) >= 7 and word not in generic for word in overlap)


def lexical_match_is_strong(
    question: str,
    query_profile: Any,
    document: Any,
) -> bool:
    """Require strong topic identity before using a no-distance lexical match.

    A lexical catalogue scan is useful for exact support terms, but unlike a
    semantic match it has no embedding distance. It therefore must prove a
    product/domain/symptom match and meaningful title/intent-keyword overlap.
    """

    document_profile = build_document_profile(document)
    focus_domains = query_profile.focus_domains or query_profile.domains
    focus_symptoms = query_profile.focus_symptoms or query_profile.symptoms

    product_overlap = query_profile.products.intersection(document_profile.products)
    domain_overlap = focus_domains.intersection(document_profile.domains)
    symptom_overlap = focus_symptoms.intersection(document_profile.symptoms)

    title = str(document.metadata.get("section_title", document.metadata.get("title", "")))
    keywords = str(document.metadata.get("intent_keywords", ""))
    question_terms = extract_terms(issue_focus(question))
    identity_terms = extract_terms(f"{title} {keywords}")
    overlap_count = len(question_terms.intersection(identity_terms))

    exact_intent_phrase = False
    normalized_question = normalize_text(question)
    for phrase in [part.strip() for part in keywords.split(",") if part.strip()]:
        normalized_phrase = normalize_text(phrase)
        if len(normalized_phrase.split()) >= 2 and contains_phrase(normalized_question, normalized_phrase):
            exact_intent_phrase = True
            break

    # If the question itself has no identifiable product/domain/symptom, a
    # lexical answer is too risky; let clarification/general fallback handle it.
    if not (query_profile.products or focus_domains or focus_symptoms):
        return False

    if query_profile.products and not product_overlap:
        return False

    if focus_domains and document_profile.domains and not domain_overlap:
        return False

    if focus_symptoms and document_profile.symptoms and not (symptom_overlap or domain_overlap):
        return False

    return exact_intent_phrase or overlap_count >= 2


def knowledge_document_is_enabled(document: Any) -> bool:
    """Return whether a KB document belongs to a supported school platform."""

    metadata = getattr(document, "metadata", {}) or {}
    source = str(metadata.get("source", "")).lower()

    if not MICROSOFT_SUPPORT_ENABLED:
        if "microsoft" in source or "windows" in source:
            return False

    return True


def retrieve_public_knowledge(
    question: str,
    history: list[dict[str, Any]] | None = None,
    result_count: int = 16,
) -> RagResult:
    """Retrieve one approved public support topic.

    Semantic Chroma results are combined with a deterministic lexical scan
    of the approved Markdown topics. The lexical fallback makes exact
    support requests reliable even when the embedding service is offline or
    the correct topic falls outside the vector search's top results.
    """

    cleaned_question = question.strip()

    if not cleaned_question:
        return RagResult(
            context="",
            sources=(),
            best_distance=None,
            matched_chunks=0,
        )

    retrieval_query = build_retrieval_query(
        cleaned_question,
        history,
    )

    query_profile = build_retrieval_profile(retrieval_query)

    vector_results: list[tuple[Any, float]] = []

    try:
        vector_store = get_vector_store()
        vector_results = [
            (document, float(distance))
            for document, distance in vector_store.similarity_search_with_score(
                query=retrieval_query,
                k=result_count,
                filter={
                    "audience": "public",
                },
            )
            if knowledge_document_is_enabled(document)
        ]
    except Exception as error:
        LOGGER.warning(
            "Semantic knowledge retrieval unavailable; using approved lexical "
            "fallback: %s: %s",
            type(error).__name__,
            error,
        )

    # Keep the best semantic instance for each topic, then add every approved
    # topic that was not already present. A full catalogue scan is small and
    # avoids arbitrary failures caused by a top-k cutoff.
    candidates: dict[str, tuple[Any, float, bool]] = {}

    def candidate_key(document: Any) -> str:
        metadata = getattr(document, "metadata", {}) or {}
        return "|".join(
            (
                str(metadata.get("source", "")),
                str(
                    metadata.get(
                        "section_title",
                        metadata.get("title", ""),
                    )
                ),
            )
        )

    for document, distance in vector_results:
        key = candidate_key(document)
        existing = candidates.get(key)

        if existing is None or distance < existing[1]:
            candidates[key] = (document, distance, True)

    if ALLOW_DISTANCELESS_KB_ANSWERS:
        for document in get_lexical_documents():
            if not knowledge_document_is_enabled(document):
                continue
            key = candidate_key(document)
            candidates.setdefault(
                key,
                (document, RAG_MAX_DISTANCE, False),
            )

    requested_platform = detect_requested_platform(retrieval_query)

    ranked: list[tuple[int, float, bool, Any]] = []

    for document, distance, semantic_match in candidates.values():
        candidate_platform = document_platform(document)

        if not platform_is_compatible(
            requested_platform,
            candidate_platform,
        ):
            continue

        document_profile = build_document_profile(document)

        if not profiles_are_compatible(
            query_profile,
            document_profile,
        ):
            continue

        topic_score = document_topic_score(
            retrieval_query,
            document,
        )
        topic_score += profile_score(
            query_profile,
            document_profile,
        )

        meaningful_overlap = has_meaningful_overlap(
            retrieval_query,
            document,
        )

        if semantic_match:
            if not semantic_match_is_acceptable(
                retrieval_query,
                query_profile,
                document,
                distance,
            ):
                continue
            if distance > RAG_STRONG_DISTANCE and topic_score < 90:
                continue
        else:
            # Production v10 does not answer from distance-less lexical matches.
            # Keep this branch for explicit diagnostic opt-in only.
            if not ALLOW_DISTANCELESS_KB_ANSWERS:
                continue
            if (
                not meaningful_overlap
                or topic_score < 90
                or not lexical_match_is_strong(
                    retrieval_query,
                    query_profile,
                    document,
                )
            ):
                continue

        ranked.append(
            (
                topic_score,
                distance,
                semantic_match,
                document,
            )
        )

    if not ranked:
        return RagResult(
            context="",
            sources=(),
            best_distance=(
                vector_results[0][1]
                if vector_results
                else None
            ),
            matched_chunks=0,
        )

    ranked.sort(
        key=lambda value: (
            -value[0],
            not value[2],
            value[1],
        )
    )

    (
        best_score,
        best_distance,
        best_is_semantic,
        best_document,
    ) = ranked[0]

    if best_score <= 0:
        return RagResult(
            context="",
            sources=(),
            best_distance=(
                best_distance
                if best_is_semantic
                else None
            ),
            matched_chunks=0,
        )

    # Final confidence gate. A vector result around 0.50+ was repeatedly shown
    # by acceptance testing to be unsafe unless the query and topic also match
    # on the actual problem family. This prevents a merely "closest" article
    # from being answered with full confidence.
    best_profile = build_document_profile(best_document)
    focus_domains = query_profile.focus_domains or query_profile.domains
    focus_symptoms = query_profile.focus_symptoms or query_profile.symptoms
    domain_overlap = focus_domains.intersection(best_profile.domains)
    symptom_overlap = focus_symptoms.intersection(best_profile.symptoms)
    identity_overlap = has_meaningful_overlap(retrieval_query, best_document)

    if best_is_semantic:
        if not semantic_match_is_acceptable(
            retrieval_query,
            query_profile,
            best_document,
            best_distance,
        ):
            return RagResult(
                context="",
                sources=(),
                best_distance=best_distance,
                matched_chunks=0,
            )
    else:
        # Distance-less knowledge is diagnostic-only in v10. Do not expose it to
        # the answer generator even when lexical identity appears strong.
        return RagResult(
            context="",
            sources=(),
            best_distance=None,
            matched_chunks=0,
        )

    source = str(
        best_document.metadata.get(
            "source",
            "Unknown source",
        )
    )

    full_section = str(
        best_document.metadata.get(
            "full_section",
            best_document.page_content,
        )
    ).strip()

    return RagResult(
        context=full_section,
        sources=(source,),
        best_distance=(
            best_distance
            if best_is_semantic
            else None
        ),
        matched_chunks=1,
    )
