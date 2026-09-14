from __future__ import annotations

import os
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

from core.common_support_router import route_common_support_question
from core.extended_support_router import route_extended_support_question
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
)
from core.printer_router import (
    route_printer_question,
)
from core.rag import (
    retrieve_public_knowledge,
)
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

load_dotenv()


RAG_DEBUG = os.getenv(
    "RAG_DEBUG",
    "false",
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}


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

MICROSOFT_ACCOUNT_TERMS = (
    "microsoft account",
    "microsoft password",
    "office 365 password",
    "microsoft 365 password",
    "outlook password",
    "onedrive password",
)


MICROSOFT_PASSWORD_RECOVERY_SIGNALS = (
    "forgot my password",
    "forgot password",
    "forgotten password",
    "reset my password",
    "reset password",
    "password not working",
    "password is not working",
    "cannot sign in",
    "can't sign in",
    "cant sign in",
)


MICROSOFT_DOCUMENT_PASSWORD_TERMS = (
    "password protect",
    "password protected document",
    "document password",
    "workbook password",
    "file password",
    "protected workbook",
    "protected document",
)


def get_microsoft_password_recovery_answer(
    question: str,
) -> str | None:
    """
    Handle Microsoft account password recovery separately
    because SJK manages Google accounts, not Microsoft
    accounts.
    """

    normalized = normalize_text(
        question
    )

    if any(
        term in normalized
        for term in MICROSOFT_DOCUMENT_PASSWORD_TERMS
    ):
        return None

    has_microsoft_account = any(
        term in normalized
        for term in MICROSOFT_ACCOUNT_TERMS
    )

    has_recovery_request = any(
        signal in normalized
        for signal in MICROSOFT_PASSWORD_RECOVERY_SIGNALS
    )

    if not (
        has_microsoft_account
        and has_recovery_request
    ):
        return None

    return (
        "SJK does not manage Microsoft account passwords. "
        "You can reset the password directly through Microsoft:\n\n"
        "1. Open the Microsoft sign-in page.\n"
        "2. Enter the email address connected to the "
        "Microsoft account.\n"
        "3. Select **Forgot password?**\n"
        "4. Choose an available identity-verification method.\n"
        "5. Enter the verification code sent by Microsoft.\n"
        "6. Create and confirm a new password.\n"
        "7. Sign in again using the new password.\n\n"
        "If you no longer have access to the recovery email, "
        "phone number, or verification method, use Microsoft's "
        "account-recovery or sign-in help process.\n\n"
        "Never share your password or verification code with "
        "the chatbot or another person. SJK IT can help with "
        "Word, Excel, PowerPoint, or device problems, but it "
        "cannot reset or access a personal Microsoft account."
    )

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
            "microsoft word",
            "ms word",
            "word",
        ),
        (
            "**Microsoft Word** is used to create, edit, format, "
            "print, and share written documents.\n\n"
            "What would you like to learn or get help with?\n\n"
            "For example:\n"
            "- Creating or opening a document\n"
            "- Saving or converting to PDF\n"
            "- Formatting text or pages\n"
            "- Adding tables, pictures, or page numbers\n"
            "- Sharing or permissions\n"
            "- Comments or Track Changes\n"
            "- Printing\n"
            "- Recovering a document\n"
            "- Fixing a Word problem"
        ),
    ),
    (
        (
            "microsoft excel",
            "ms excel",
            "excel",
        ),
        (
            "What would you like help with in **Microsoft Excel**?\n\n"
            "For example:\n"
            "- Entering or formatting data\n"
            "- Formulas or formula errors\n"
            "- Sorting or filtering\n"
            "- Charts or PivotTables\n"
            "- Worksheets\n"
            "- Sharing\n"
            "- Printing\n"
            "- Recovering a workbook\n"
            "- Fixing an Excel problem"
        ),
    ),
    (
        (
            "microsoft powerpoint",
            "ms powerpoint",
            "powerpoint",
            "power point",
        ),
        (
            "What would you like help with in "
            "**Microsoft PowerPoint**?\n\n"
            "For example:\n"
            "- Creating or arranging slides\n"
            "- Themes and slide layouts\n"
            "- Pictures, charts, audio, or video\n"
            "- Animations or transitions\n"
            "- Speaker notes or Presenter View\n"
            "- Sharing\n"
            "- Printing or exporting\n"
            "- Fixing a PowerPoint problem"
        ),
    ),
    (
        (
            "microsoft onedrive",
            "one drive",
            "onedrive",
        ),
        (
            "What would you like help with in **OneDrive**?\n\n"
            "For example:\n"
            "- Uploading or downloading\n"
            "- Finding a file\n"
            "- Sharing or permissions\n"
            "- Syncing files\n"
            "- Restoring a deleted file\n"
            "- Version history\n"
            "- Offline access\n"
            "- Fixing a OneDrive problem"
        ),
    ),
    (
        (
            "microsoft 365",
            "office 365",
            "microsoft office",
        ),
        (
            "Which **Microsoft 365** service do you need help with?\n\n"
            "- Word\n"
            "- Excel\n"
            "- PowerPoint\n"
            "- OneDrive"
        ),
    ),
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
            "classroom",
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
    a Microsoft or Google application.
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

    conversation = route_conversation_message(
        question,
        history,
    )

    if conversation.handled:
        return AnswerPlan(
            direct_answer=conversation.answer,
        )

    # Resolve explicit corrections (for example, "monitor, not Classroom")
    # once for the rest of the routing pipeline. Individual deterministic
    # routers use the same topic-context helper, and RAG receives the clarified
    # query if no deterministic route handles it.
    topic_context = build_topic_context(question, history)

    extended_support = route_extended_support_question(
        question,
        history,
    )

    if extended_support.handled:
        return AnswerPlan(
            direct_answer=extended_support.answer,
        )

    common_support = route_common_support_question(
        question,
        history,
    )

    if common_support.handled:
        return AnswerPlan(
            direct_answer=common_support.answer,
        )

    airplay = route_airplay_question(
        question,
        history,
    )

    if airplay.handled:
        return AnswerPlan(
            direct_answer=airplay.answer,
        )

    microsoft_password_recovery = (
        get_microsoft_password_recovery_answer(
            question
        )
    )

    if microsoft_password_recovery:
        return AnswerPlan(
            direct_answer=microsoft_password_recovery,
            intent="microsoft_password_recovery",
        )

    # Broad Google or Microsoft product questions must be
    # clarified before any OS-dependent support routing.
    productivity_clarification = (
        get_productivity_clarification(
            question
        )
    )

    if productivity_clarification:
        return AnswerPlan(
            direct_answer=productivity_clarification,
        )

    printer = route_printer_question(
        question,
        history,
    )

    if printer.handled:
        return AnswerPlan(
            direct_answer=printer.answer,
        )

    wifi = route_wifi_question(
        question,
        history,
    )

    if wifi.handled:
        return AnswerPlan(
            direct_answer=wifi.answer,
            resource=wifi.resource,
            caption=wifi.caption,
        )

    inventory = route_inventory_question(
        question,
        history,
    )

    if inventory.handled:
        return AnswerPlan(
            direct_answer=inventory.answer,
        )

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
            topic_context.retrieval_text
            if topic_context.is_correction
            else question
        )
    )

    try:
        rag_result = retrieve_public_knowledge(
            question=effective_question,
            history=history,
        )
    except Exception as error:
        print(
            "Knowledge retrieval failed: "
            f"{type(error).__name__}: {error}"
        )

        return AnswerPlan(
            direct_answer=(
                "I cannot access the approved support knowledge "
                "base right now. Please contact the IT Helpdesk "
                "for assistance."
            ),
        )

    if not rag_result.context:
        if looks_like_it_question(
            effective_question
        ):
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
