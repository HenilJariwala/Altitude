from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.text_matching import (
    contains_any_phrase,
    normalize_text,
)


OUT_OF_SCOPE_MESSAGE = (
    "I’m focused on SJK IT support, so I can’t complete that non-IT "
    "request. I can help with Wi-Fi, printers, school accounts, devices, "
    "classroom displays, software, loaner inventory, and helpdesk tickets."
)


UNSUPPORTED_IT_MESSAGE = (
    "I can help with IT-related issues, but I do not have an "
    "approved procedure for that request. Please contact the "
    "IT Helpdesk for further assistance."
)


CAPABILITIES_MESSAGE = (
    "I can help troubleshoot common SJK technology issues, including:\n\n"
    "- Wi-Fi and internet connection problems\n"
    "- Printers and print queues\n"
    "- School passwords, accounts, Gmail, Drive, and Classroom\n"
    "- MacBooks, Chromebooks, classroom displays, and AirPlay\n"
    "- Approved software and device troubleshooting\n"
    "- Live loaner inventory checks\n"
    "- Escalating unresolved problems to an IT helpdesk ticket"
)

IDENTITY_MESSAGE = (
    "I’m **Altitude**, the SJK IT Helpdesk AI assistant. I provide approved "
    "technology support, check loaner inventory, and help users escalate "
    "unresolved IT issues to the helpdesk team."
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
    "safari",
    "adobe",
    "acrobat",
    "creative cloud",
    "photoshop",
    "pdf",
    "camera",
    "webcam",
    "microphone",
    "audio",
    "speaker",
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
    "extension",
    "permissions",
    "admin rights",
    "administrator",
    "classroom tv",
    "testing browser",
    "lockdown browser",
    "install",
    "installed",
    "application",
    "app",
    "website",
    "portal",
    "file",
    "folder",
    "storage",
    "update",
    "smartboard",
    "smart board",
    "jamboard",
    "audacity",
    "powerschool",
    "icloud",
    "interactive whiteboard",
    "whiteboard",
    "promethean",
    "projected image",
    "keynote",
    "photo booth",
    "bookmarks",
    "cursor",
    "trackpad",
    "dock",
    "shared drive",
    "gradebook",
    "breakout room",
    "content blocker",
    "classroom",
    "assignment",
    "assignments",
    "submission",
    "submitted",
    "co-teacher",
    "co teacher",
    "class code",
    "stream",
    "announcement",
    "shared folder",
    "version history",
    "drive for desktop",
    "sync",
    "calendar",
    "meet",
    "forms",
    "bluetooth",
    "hotspot",
    "charging cart",
    "chromebook cart",
    "assessment platform",
    "quiz platform",
    "gradebook export",
    "downloads folder",
    "flash drive",
    "usb drive",
    "battery",
    "hinge",
    "kiosk",
    "developer mode",
    "ssl",
    "certificate",
    "error code",
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
    """Handle greetings, identity, scope, and requests needing clarification."""

    del history

    normalized = normalize_text(question).strip(" .")

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
            answer="Hello! What IT or technology issue can I help you with today?",
        )

    if normalized in {
        "what can you help me with",
        "what can you do",
        "how can you help",
        "how can you help me",
        "what do you support",
        "what services do you support",
    }:
        return ConversationDecision(handled=True, answer=CAPABILITIES_MESSAGE)

    if normalized in {
        "who are you",
        "what are you",
        "what is altitude",
        "tell me about yourself",
    }:
        return ConversationDecision(handled=True, answer=IDENTITY_MESSAGE)

    if normalized in {
        "can you help me with a school technology problem",
        "can you help with a school technology problem",
        "i need help with a technology problem",
        "i have a technology problem",
    }:
        return ConversationDecision(
            handled=True,
            answer=(
                "Yes. What technology issue are you experiencing? Please tell me "
                "the device or service involved and what is happening."
            ),
        )

    # Short requests without an identifiable subject should be clarified
    # instead of sent to semantic retrieval, where they can match a random topic.
    clarification_answers = {
        "it does not work": (
            "What device or service is not working, and what exactly happens when "
            "you try to use it?"
        ),
        "it doesn't work": (
            "What device or service is not working, and what exactly happens when "
            "you try to use it?"
        ),
        "help": (
            "What IT issue do you need help with? Please tell me the device or "
            "service and the problem you are seeing."
        ),
        "the screen": (
            "What screen or display are you using, and what problem are you seeing "
            "on it?"
        ),
        "i cannot connect": (
            "What are you trying to connect to: Wi-Fi, AirPlay, a printer, an "
            "account, or another service?"
        ),
        "i can't connect": (
            "What are you trying to connect to: Wi-Fi, AirPlay, a printer, an "
            "account, or another service?"
        ),
        "printer": (
            "What printer problem are you experiencing: adding the printer, an "
            "offline message, a stuck print queue, or something else?"
        ),
        "macbook": (
            "Do you need MacBook troubleshooting, or are you asking whether a "
            "MacBook is available to borrow?"
        ),
    }

    if normalized in clarification_answers:
        return ConversationDecision(
            handled=True,
            answer=clarification_answers[normalized],
        )

    # Contradictory statements need clarification, not a guessed procedure.
    if "chromebook" in normalized and "macos" in normalized:
        return ConversationDecision(
            handled=True,
            answer=(
                "Please clarify which device you are using. A Chromebook runs "
                "ChromeOS, while macOS runs on a Mac. Which one is affected?"
            ),
        )

    if "printer" in normalized and "offline" in normalized and any(
        phrase in normalized
        for phrase in ("can print", "print successfully", "printing successfully")
    ):
        return ConversationDecision(
            handled=True,
            answer=(
                "Please clarify: is the printer showing **Offline** even though "
                "printing is currently successful, or does a specific job still fail?"
            ),
        )

    if "wifi" in normalized and "only for me" in normalized and "everyone" in normalized:
        return ConversationDecision(
            handled=True,
            answer=(
                "Please clarify whether only your device is affected or everyone is "
                "disconnected. If multiple people are affected, this may be a Wi-Fi "
                "outage that should be reported to the IT team."
            ),
        )

    if "restarted it" in normalized and "did not restart" in normalized:
        return ConversationDecision(
            handled=True,
            answer=(
                "Please clarify what you restarted and whether the restart actually "
                "completed before we continue troubleshooting."
            ),
        )

    if normalized in {"bye", "goodbye", "see you"}:
        return ConversationDecision(
            handled=True,
            answer=(
                "Goodbye! Please contact the IT Helpdesk if you need further "
                "assistance."
            ),
        )

    if "weather" in normalized:
        return ConversationDecision(
            handled=True,
            answer=(
                "I’m focused on SJK IT support, so I can’t provide today’s weather. "
                "I can help with Wi-Fi, printers, accounts, devices, and other "
                "technology issues."
            ),
        )

    if any(
        phrase in normalized
        for phrase in (
            "tell me a joke",
            "do my math homework",
            "do my homework",
            "write my english essay",
            "write my essay",
        )
    ):
        return ConversationDecision(handled=True, answer=OUT_OF_SCOPE_MESSAGE)

    if normalized in {"you are useless", "this is useless"}:
        return ConversationDecision(
            handled=True,
            answer=(
                "I’m sorry the response was not useful. Tell me the IT problem and "
                "what you already tried, and I’ll focus on the next practical step."
            ),
        )

    if any(phrase in normalized for phrase in OUT_OF_SCOPE_PHRASES):
        return ConversationDecision(handled=True, answer=OUT_OF_SCOPE_MESSAGE)

    return ConversationDecision(handled=False)
