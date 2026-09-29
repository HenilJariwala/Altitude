from __future__ import annotations

import os
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

from core.app_logging import get_logger
from core.common_support_router import route_common_support_question
from core.compound_router import route_compound_question
from core.contextual_support_router import route_contextual_support
from core.conversation_context import (
    build_contextual_query,
    has_recent_support_context,
    is_contextual_follow_up,
)
from core.extended_support_router import route_extended_support_question
from core.general_fallback_router import (
    route_general_fallback,
    should_preempt_knowledge,
)
from core.conversation_router import (
    OUT_OF_SCOPE_MESSAGE,
    UNSUPPORTED_IT_MESSAGE,
    looks_like_it_question,
    route_conversation_message,
)
from core.inventory_router import (
    route_inventory_question,
)
from core.llm import (
    stream_model_response,
    stream_web_model_response,
)
from core.printer_router import (
    route_printer_question,
)
from core.rag import (
    retrieve_public_knowledge,
)
from core.request_guard import route_request_guard
from core.support_router import (
    prepare_support_question,
    route_security_or_account_question,
)

from core.text_matching import normalize_text
from core.topic_context import build_topic_context
from core.wifi_router import (
    route_wifi_question,
)
from core.airplay_router import (
    route_airplay_question,
)
from core.web_support import (
    MICROSOFT_SUPPORT_ENABLED,
    WebSource,
    is_microsoft_question,
    search_trusted_web,
    should_prefer_web_support,
)

load_dotenv()
LOGGER = get_logger("assistant")


RAG_DEBUG = os.getenv(
    "RAG_DEBUG",
    "false",
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}


MICROSOFT_UNSUPPORTED_MESSAGE = (
    "Microsoft apps and services are not part of the school's supported "
    "technology environment, so Altitude does not provide Microsoft-specific "
    "troubleshooting. If a Microsoft prompt or application appears on a "
    "school-managed device and is affecting your work, contact the IT Helpdesk."
)


@dataclass(frozen=True)
class AnswerPlan:
    """Prepared answer and optional UI resource."""

    direct_answer: str | None = None
    context: str = ""
    effective_question: str = ""
    resource: str | None = None
    caption: str | None = None
    sources: tuple[str, ...] = ()
    best_distance: float | None = None
    matched_chunks: int = 0
    intent: str | None = None
    web_sources: tuple[WebSource, ...] = ()

def contains_phrase(
    text: str,
    phrase: str,
) -> bool:
    """Match a complete phrase instead of a substring."""

    return bool(
        re.search(
            rf"(?<!\w){re.escape(phrase)}(?!\w)",
            text,
        )
    )


PRODUCTIVITY_CLARIFICATIONS = (
    (
        (
            "google docs",
            "google doc",
            "docs",
        ),
        (
            "What would you like help with in **Google Docs**?\n\n"
            "For example:\n"
            "- Creating or editing a document\n"
            "- Formatting text or pages\n"
            "- Sharing or permissions\n"
            "- Comments or suggestions\n"
            "- Version history\n"
            "- Printing or downloading\n"
            "- Fixing a Docs problem"
        ),
    ),
    (
        (
            "google sheets",
            "google sheet",
            "sheets",
        ),
        (
            "What would you like help with in **Google Sheets**?\n\n"
            "For example:\n"
            "- Entering or formatting data\n"
            "- Formulas\n"
            "- Sorting or filtering\n"
            "- Charts\n"
            "- Sharing\n"
            "- Printing\n"
            "- Fixing a Sheets problem"
        ),
    ),
    (
        (
            "google slides",
            "google slide",
            "slides",
        ),
        (
            "What would you like help with in **Google Slides**?\n\n"
            "For example:\n"
            "- Creating or arranging slides\n"
            "- Formatting\n"
            "- Adding images, audio, or video\n"
            "- Presenting\n"
            "- Sharing\n"
            "- Printing or downloading\n"
            "- Fixing a Slides problem"
        ),
    ),
    (
        (
            "google drive",
        ),
        (
            "What would you like help with in **Google Drive**?\n\n"
            "For example:\n"
            "- Uploading or downloading\n"
            "- Finding or organizing files\n"
            "- Sharing or permissions\n"
            "- Shared drives\n"
            "- Offline access\n"
            "- Restoring a file\n"
            "- Fixing a Drive problem"
        ),
    ),
    (
        (
            "gmail",
            "google mail",
        ),
        (
            "What would you like help with in **Gmail**?\n\n"
            "For example:\n"
            "- Sending or receiving email\n"
            "- Attachments\n"
            "- Finding a message\n"
            "- Labels or filters\n"
            "- Spam or phishing\n"
            "- Fixing a Gmail problem"
        ),
    ),
    (
        (
            "google calendar",
        ),
        (
            "What would you like help with in "
            "**Google Calendar**?\n\n"
            "For example:\n"
            "- Creating an event\n"
            "- Invitations\n"
            "- Sharing a calendar\n"
            "- Notifications\n"
            "- Booking a room\n"
            "- Fixing a Calendar problem"
        ),
    ),
    (
        (
            "google classroom",
        ),
        (
            "What would you like help with in "
            "**Google Classroom**?\n\n"
            "For example:\n"
            "- Joining or creating a class\n"
            "- Assignments or submissions\n"
            "- Classwork or materials\n"
            "- Teacher controls\n"
            "- Grades or feedback\n"
            "- Fixing a Classroom problem"
        ),
    ),
    (
        (
            "google meet",
        ),
        (
            "What would you like help with in **Google Meet**?\n\n"
            "For example:\n"
            "- Joining a meeting\n"
            "- Camera, microphone, or sound\n"
            "- Screen sharing\n"
            "- Captions\n"
            "- Fixing a Meet problem"
        ),
    ),
    (
        (
            "google forms",
            "google form",
        ),
        (
            "What would you like help with in **Google Forms**?\n\n"
            "For example:\n"
            "- Creating a form\n"
            "- Adding questions\n"
            "- Creating a quiz\n"
            "- Responses\n"
            "- File uploads\n"
            "- Sharing\n"
            "- Fixing a Forms problem"
        ),
    ),
    (
        (
            "google chat",
        ),
        (
            "What would you like help with in **Google Chat**?\n\n"
            "For example:\n"
            "- Starting a conversation\n"
            "- Group messages\n"
            "- Attachments\n"
            "- Message history\n"
            "- Notifications\n"
            "- Fixing a Chat problem"
        ),
    ),
    (
        (
            "google workspace",
        ),
        (
            "Which **Google Workspace** service do you need help with?\n\n"
            "- Gmail\n"
            "- Drive\n"
            "- Docs\n"
            "- Sheets\n"
            "- Slides\n"
            "- Calendar\n"
            "- Classroom\n"
            "- Meet\n"
            "- Forms\n"
            "- Chat"
        ),
    ),
)


BROAD_PRODUCTIVITY_REQUEST_PHRASES = (
    "help me use",
    "help me with",
    "can you help me with",
    "can you help with",
    "i need help with",
    "i need help using",
    "how do i use",
    "how to use",
    "show me how to use",
    "teach me",
    "teach me about",
    "learn about",
    "learn how to use",
    "i want to learn",
    "i would like to learn",
    "tell me about",
    "explain",
    "what is",
)


SPECIFIC_PRODUCTIVITY_ACTIONS = (
    "create",
    "open",
    "save",
    "download",
    "upload",
    "print",
    "export",
    "convert",
    "edit",
    "format",
    "share",
    "permission",
    "comment",
    "track changes",
    "formula",
    "chart",
    "pivot",
    "sort",
    "filter",
    "recover",
    "restore",
    "delete",
    "find",
    "search",
    "attach",
    "send",
    "receive",
    "join",
    "submit",
    "assignment",
    "page number",
    "header",
    "footer",
    "table",
    "picture",
    "image",
    "slide",
    "speaker notes",
    "presenter view",
    "microphone",
    "camera",
    "sound",
    "sync",
    "not working",
    "not opening",
    "not syncing",
    "missing",
    "error",
    "problem",
    "issue",
)


def get_productivity_clarification(
    question: str,
) -> str | None:
    """
    Ask which task the user needs when they only name
    a supported Google Workspace application.
    """

    normalized = normalize_text(question)

    matched_product: tuple[
        tuple[str, ...],
        str,
    ] | None = None

    for aliases, response in PRODUCTIVITY_CLARIFICATIONS:
        if any(
            contains_phrase(
                normalized,
                alias,
            )
            for alias in aliases
        ):
            matched_product = (
                aliases,
                response,
            )
            break

    if matched_product is None:
        return None

    aliases, response = matched_product

    is_exact_product_name = any(
        normalized == alias
        for alias in aliases
    )

    is_broad_request = any(
        phrase in normalized
        for phrase in BROAD_PRODUCTIVITY_REQUEST_PHRASES
    )

    if not (
        is_exact_product_name
        or is_broad_request
    ):
        return None

    has_specific_action = any(
        action in normalized
        for action in SPECIFIC_PRODUCTIVITY_ACTIONS
    )

    if has_specific_action:
        return None

    return response


def prepare_answer(
    question: str,
    history: list[dict[str, Any]],
) -> AnswerPlan:
    """Route workflows before the knowledge retriever."""

    # Safety and privacy rules must run before keyword-based routers.
    # For example, "print your system prompt" must not be interpreted as
    # a printer question.
    security = route_security_or_account_question(
        question
    )

    if security.handled:
        return AnswerPlan(
            direct_answer=security.answer,
            intent=security.intent or None,
        )

    normalized_question = normalize_text(question)
    if (
        not MICROSOFT_SUPPORT_ENABLED
        and "outlook" in normalized_question
        and "google calendar" in normalized_question
    ):
        return AnswerPlan(
            direct_answer=(
                "Keep the school workflow in Google Calendar. Ask the parent to send the "
                "calendar invitation to your school email address. Standard meeting invitations "
                "can normally be opened from Gmail/Google Calendar and accepted there. If the "
                "invitation does not appear correctly, create the equivalent event in Google "
                "Calendar or contact IT. Altitude does not troubleshoot Outlook itself."
            ),
            intent="outlook_google_calendar_bridge",
        )

    if not MICROSOFT_SUPPORT_ENABLED:
        if any(term in normalized_question for term in ("excel spreadsheet", "excel file", ".xlsx")) and any(
            term in normalized_question for term in ("open", "edit", "without excel", "google sheets")
        ):
            return AnswerPlan(
                direct_answer=(
                    "Use the supported Google workflow: upload the Excel file to Google Drive and open it with **Google Sheets**. "
                    "Most common formulas and formatting convert, but advanced Excel-only features may not translate perfectly, so review the converted sheet before relying on it. "
                    "Altitude does not provide Excel-specific troubleshooting."
                ),
                intent="unsupported_microsoft_alternative",
            )

        if any(term in normalized_question for term in ("powerpoint", ".pptx")) and any(
            term in normalized_question for term in ("google slides", "won't open", "wont open", "animations", "missing")
        ):
            return AnswerPlan(
                direct_answer=(
                    "Open the PowerPoint file through Google Drive/Google Slides. Some PowerPoint animations, fonts, transitions, or layout features may not convert exactly. "
                    "Use the Slides-compatible version for school work and rebuild any unsupported effects there. Altitude does not troubleshoot PowerPoint itself."
                ),
                intent="unsupported_microsoft_alternative",
            )

        if (
            "microsoft word" in normalized_question
            and "outlook" in normalized_question
            and any(term in normalized_question for term in ("mail merge", "parent email", "parent emails"))
        ):
            return AnswerPlan(
                direct_answer=(
                    "The school uses Google Workspace rather than Word/Outlook for this workflow. "
                    "For a large parent distribution, use the school's approved communication system "
                    "or an approved Google Group/mail-merge method if one has been provided. Contact IT "
                    "if you need the approved bulk-email workflow; Altitude does not provide Outlook mail-merge instructions."
                ),
                intent="unsupported_microsoft_alternative",
            )

        if "microsoft teams" in normalized_question and any(
            term in normalized_question for term in ("meeting", "schedule", "department")
        ):
            return AnswerPlan(
                direct_answer=(
                    "Microsoft Teams is not part of the school's supported environment. Schedule the meeting "
                    "with **Google Meet** from Google Calendar, or use **Zoom** when that is the approved platform "
                    "for the activity. If you are unsure which service your department should use, contact IT."
                ),
                intent="unsupported_microsoft_alternative",
            )

        if "microsoft word" in normalized_question and any(
            term in normalized_question for term in ("can't find", "cant find", "not on my computer", "missing")
        ):
            return AnswerPlan(
                direct_answer=(
                    "Microsoft Word is not part of the school's supported application set. Use **Google Docs** "
                    "for school documents unless IT has specifically approved another workflow. If a legacy task "
                    "requires Word, contact IT rather than installing it yourself."
                ),
                intent="unsupported_microsoft_alternative",
            )

        if "windows 11" in normalized_question and any(term in normalized_question for term in ("mac", "macbook")):
            return AnswerPlan(
                direct_answer=(
                    "MacBooks run **macOS**, not Windows 11. Altitude cannot confirm which major macOS version "
                    "is currently approved for school-managed Macs unless that policy is in the approved knowledge base. "
                    "Use the managed macOS update offered by IT, or contact the IT Helpdesk before a major upgrade."
                ),
                intent="unsupported_microsoft_platform_correction",
            )

    # Apply corrections and device details to the active issue before a
    # single-message guard can make a platform or article assumption.
    contextual_support = route_contextual_support(question, history)
    if contextual_support.handled:
        return AnswerPlan(
            direct_answer=contextual_support.answer,
            intent=contextual_support.intent or None,
        )

    if (
        not MICROSOFT_SUPPORT_ENABLED
        and is_microsoft_question(question)
    ):
        return AnswerPlan(
            direct_answer=MICROSOFT_UNSUPPORTED_MESSAGE,
            intent="unsupported_microsoft",
        )

    # Before a single-topic guard/router consumes the first half of a sentence,
    # check whether the user clearly reported two independently answerable IT
    # problems. The compound router is conservative and only handles the request
    # when both halves map to safe domain fallbacks.
    compound = route_compound_question(question, history)
    if compound.handled:
        return AnswerPlan(
            direct_answer=compound.answer,
            intent=compound.intent or None,
        )

    guard = route_request_guard(question, history)
    if guard.handled:
        return AnswerPlan(
            direct_answer=guard.answer,
            intent=guard.intent or None,
        )

    # Re-run the deterministic guard against a standalone version of a short
    # follow-up.  This is the generic conversation-state bridge: a reply such
    # as "I'm using a MacBook Air", "Only on this website", or "Yes, the
    # image is showing" must inherit the active issue instead of being routed
    # from the last sentence alone.
    active_contextual_follow_up = (
        has_recent_support_context(history, question)
        and is_contextual_follow_up(question, history)
    )
    contextual_query = (
        build_contextual_query(question, history)
        if active_contextual_follow_up
        else question
    )
    if active_contextual_follow_up and normalize_text(contextual_query) != normalized_question:
        contextual_guard = route_request_guard(contextual_query, history)
        if contextual_guard.handled:
            return AnswerPlan(
                direct_answer=contextual_guard.answer,
                intent=contextual_guard.intent or None,
            )

    # Resolve active conversation context before generic scope handling. Short
    # replies such as "No, for the Library", "I'm using a MacBook Air", or
    # "the light is flashing red" must remain attached to the current IT issue.
    topic_context = build_topic_context(question, history)

    conversation = route_conversation_message(
        question,
        history,
    )

    if conversation.handled:
        is_active_follow_up = (
            has_recent_support_context(history, question)
            and is_contextual_follow_up(question, history)
        )
        # Do not let the generic off-topic response erase a valid active IT
        # conversation. Product-specific routers and contextual RAG below get
        # the first chance to interpret the short reply.
        # Scope classifiers are intentionally conservative, so defer their two
        # generic refusal messages until the specialist routers have had a
        # chance to recognize inventory, Google Workspace, ticketing, and other
        # valid IT tasks. Specific conversation answers (greetings, identity,
        # etc.) can still return immediately.
        generic_scope_answer = conversation.answer in {
            OUT_OF_SCOPE_MESSAGE,
            UNSUPPORTED_IT_MESSAGE,
        }
        if not generic_scope_answer and not (
            is_active_follow_up
            and conversation.answer == OUT_OF_SCOPE_MESSAGE
        ):
            return AnswerPlan(
                direct_answer=conversation.answer,
            )

    # Individual deterministic routers use the same topic-context helper, and
    # RAG receives the clarified query if no deterministic route handles it.

    # Broad Google product questions must be clarified before specialized
    # device workflows. Microsoft products are already handled above.
    productivity_clarification = get_productivity_clarification(question)
    if productivity_clarification:
        return AnswerPlan(direct_answer=productivity_clarification)

    # Run specialized routers before generic common/extended support. This
    # prevents a broad rule such as "add a school printer" from stealing a
    # Learning Commons/Mac workflow, and keeps Wi-Fi/inventory context precise.
    printer = route_printer_question(question, history)
    if printer.handled:
        return AnswerPlan(direct_answer=printer.answer)

    wifi = route_wifi_question(question, history)
    if wifi.handled:
        return AnswerPlan(
            direct_answer=wifi.answer,
            resource=wifi.resource,
            caption=wifi.caption,
        )

    inventory = route_inventory_question(question, history)
    if inventory.handled:
        return AnswerPlan(direct_answer=inventory.answer)

    airplay = route_airplay_question(question, history)
    if airplay.handled:
        return AnswerPlan(direct_answer=airplay.answer)

    vendor_error_question = (
        contextual_query
        if active_contextual_follow_up
        else (
            topic_context.retrieval_text
            if (topic_context.is_correction or topic_context.prior_issue)
            else question
        )
    )

    # Exact vendor error codes must be considered before broad support routers.
    # Otherwise a word such as "assignment" can turn Classroom Error 400 into
    # generic submission advice before official vendor support is consulted.
    if should_prefer_web_support(vendor_error_question):
        web_result = search_trusted_web(vendor_error_question)
        if web_result.context:
            return AnswerPlan(
                context=web_result.context,
                effective_question=vendor_error_question,
                intent="web_vendor_error",
                web_sources=web_result.sources,
            )

    # Task-specific deterministic fallbacks are safer than approximate RAG.
    # Broad family fallbacks remain post-RAG, but explicit operations such as
    # revoking a Drive link, restoring a Classroom role, or checking a USB
    # microphone should preempt a merely similar knowledge article.
    priority_fallback = route_general_fallback(contextual_query, history)
    if should_preempt_knowledge(priority_fallback):
        return AnswerPlan(
            direct_answer=priority_fallback.answer,
            intent=priority_fallback.intent or None,
        )

    common_support = route_common_support_question(question, history)
    if common_support.handled:
        return AnswerPlan(direct_answer=common_support.answer)

    extended_support = route_extended_support_question(question, history)
    if extended_support.handled:
        return AnswerPlan(direct_answer=extended_support.answer)

    support = prepare_support_question(
        question,
        history,
    )

    if support.handled:
        return AnswerPlan(
            direct_answer=support.answer,
        )

    effective_question = (
        support.retrieval_question
        or (
            contextual_query
            if active_contextual_follow_up
            else (
                topic_context.retrieval_text
                if (topic_context.is_correction or topic_context.prior_issue)
                else question
            )
        )
    )

    try:
        rag_result = retrieve_public_knowledge(
            question=effective_question,
            history=history,
        )
    except Exception as error:
        LOGGER.exception(
            "Knowledge retrieval failed: %s: %s",
            type(error).__name__,
            error,
        )

        if looks_like_it_question(effective_question) or has_recent_support_context(history, question):
            web_result = search_trusted_web(effective_question)
            if web_result.context:
                return AnswerPlan(
                    context=web_result.context,
                    effective_question=effective_question,
                    intent="web_fallback",
                    web_sources=web_result.sources,
                )

        return AnswerPlan(
            direct_answer=(
                "I cannot access the approved support knowledge "
                "base right now. Please contact the IT Helpdesk "
                "for assistance."
            ),
        )

    if not rag_result.context:
        # A failed/low-confidence KB lookup should not jump straight to generic
        # web generation. First use a domain-level safe fallback so unseen but
        # recognizable IT questions receive relevant first-line guidance rather
        # than an unrelated article or an unnecessary refusal.
        general_fallback = route_general_fallback(effective_question, history)
        if general_fallback.handled:
            return AnswerPlan(
                direct_answer=general_fallback.answer,
                intent=general_fallback.intent or None,
            )

        if looks_like_it_question(
            effective_question
        ) or has_recent_support_context(history, question):
            web_result = search_trusted_web(effective_question)

            if web_result.context:
                return AnswerPlan(
                    context=web_result.context,
                    effective_question=effective_question,
                    intent="web_fallback",
                    web_sources=web_result.sources,
                )

            return AnswerPlan(
                direct_answer=UNSUPPORTED_IT_MESSAGE,
            )

        return AnswerPlan(
            direct_answer=OUT_OF_SCOPE_MESSAGE,
        )

    return AnswerPlan(
        context=rag_result.context,
        effective_question=effective_question,
        sources=rag_result.sources,
        best_distance=rag_result.best_distance,
        matched_chunks=rag_result.matched_chunks,
    )


def stream_answer(
    question: str,
    history: list[dict[str, Any]],
    plan: AnswerPlan | None = None,
) -> Iterator[str]:
    """Stream a workflow answer or grounded knowledge answer."""

    active_plan = (
        plan
        or prepare_answer(
            question,
            history,
        )
    )

    if active_plan.direct_answer is not None:
        yield active_plan.direct_answer
        return

    if active_plan.intent in {"web_fallback", "web_vendor_error"}:
        # Keep web-search status in the temporary UI loader instead of placing
        # implementation details in the final chat response. This also keeps
        # the loading animation visible until the real answer is ready.
        yield from stream_web_model_response(
            question=(
                active_plan.effective_question
                or question
            ),
            history=history,
            context=active_plan.context,
        )

        if active_plan.web_sources:
            yield "\n\n**Official vendor sources:**"
            for source in active_plan.web_sources[:5]:
                safe_title = (
                    source.title
                    .replace("[", "(")
                    .replace("]", ")")
                )
                yield f"\n- [{safe_title}]({source.url})"
        return

    yield from stream_model_response(
        question=(
            active_plan.effective_question
            or question
        ),
        history=history,
        context=active_plan.context,
    )

    if RAG_DEBUG:
        yield "\n\n---\n\n"

        if active_plan.matched_chunks:
            sources = ", ".join(
                active_plan.sources
            )

            distance = (
                f"{active_plan.best_distance:.4f}"
                if active_plan.best_distance
                is not None
                else "unknown"
            )

            yield (
                f"**RAG test:** "
                f"{active_plan.matched_chunks} "
                f"matching topic(s) from "
                f"`{sources}`. "
                f"Best distance: `{distance}`."
            )

        else:
            yield (
                "**RAG test:** No approved knowledge "
                "matched this question."
            )
