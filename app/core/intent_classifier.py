from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from ollama import Client

from core.app_logging import get_logger


load_dotenv()
LOGGER = get_logger("intent_classifier")


OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:1.5b",
)

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
)


client = Client(
    host=OLLAMA_BASE_URL,
)


INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "enum": [
                "printer",
                "wifi",
                "google_password",
                "other",
            ],
        },
        "action": {
            "type": "string",
            "enum": [
                "add",
                "troubleshoot",
                "access",
                "reset",
                "unknown",
            ],
        },
        "printer": {
            "type": "string",
            "enum": [
                "learning_commons",
                "other",
                "unknown",
            ],
        },
        "device": {
            "type": "string",
            "enum": [
                "mac",
                "windows",
                "unknown",
            ],
        },
        "role": {
            "type": "string",
            "enum": [
                "student",
                "guest",
                "unknown",
            ],
        },
        "failure_follow_up": {
            "type": "boolean",
        },
    },
    "required": [
        "topic",
        "action",
        "printer",
        "device",
        "role",
        "failure_follow_up",
    ],
}


@dataclass(frozen=True)
class IntentResult:
    topic: str
    action: str
    printer: str
    device: str
    role: str
    failure_follow_up: bool


def unknown_intent() -> IntentResult:
    """Return a safe fallback when local classification fails."""

    return IntentResult(
        topic="other",
        action="unknown",
        printer="unknown",
        device="unknown",
        role="unknown",
        failure_follow_up=False,
    )


def classify_intent(
    question: str,
    history: list[dict[str, Any]],
) -> IntentResult:
    """Use Ollama to interpret unclear or misspelled input."""

    recent_messages = history[-6:]

    conversation = "\n".join(
        f"{message.get('role')}: "
        f"{message.get('content', '')}"
        for message in recent_messages
    )

    prompt = f"""
Classify the current IT-helpdesk message.

Correctly interpret ordinary spelling mistakes and incomplete
follow-up answers.

Do not answer the user. Return only the requested JSON fields.

Recent conversation:
{conversation}

Current message:
{question}
""".strip()

    try:
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You classify SJK IT-helpdesk requests. "
                        "Infer likely intent despite minor spelling "
                        "mistakes, but do not invent missing facts."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            format=INTENT_SCHEMA,
            stream=False,
            keep_alive="30m",
            options={
                "temperature": 0,
                "num_predict": 120,
            },
        )
    except Exception as error:
        LOGGER.exception(
            "Intent classification failed: %s: %s",
            type(error).__name__,
            error,
        )
        return unknown_intent()

    raw_content = response.message.content

    if not isinstance(raw_content, str) or not raw_content.strip():
        return unknown_intent()

    try:
        data = json.loads(raw_content)
    except (json.JSONDecodeError, TypeError):
        return unknown_intent()

    if not isinstance(data, dict):
        return unknown_intent()

    topic = data.get("topic")
    action = data.get("action")
    printer = data.get("printer")
    device = data.get("device")
    role = data.get("role")
    failure_follow_up = data.get("failure_follow_up")

    if (
        topic not in {"printer", "wifi", "google_password", "other"}
        or action not in {
            "add",
            "troubleshoot",
            "access",
            "reset",
            "unknown",
        }
        or printer not in {
            "learning_commons",
            "other",
            "unknown",
        }
        or device not in {"mac", "windows", "unknown"}
        or role not in {"student", "guest", "unknown"}
        or not isinstance(failure_follow_up, bool)
    ):
        return unknown_intent()

    return IntentResult(
        topic=topic,
        action=action,
        printer=printer,
        device=device,
        role=role,
        failure_follow_up=failure_follow_up,
    )
