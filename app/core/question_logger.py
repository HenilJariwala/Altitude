from __future__ import annotations

import re
import threading
from datetime import datetime
from pathlib import Path

from core.time_utils import get_local_timezone


PROJECT_ROOT = Path(__file__).resolve().parents[2]

LOG_DIRECTORY = PROJECT_ROOT / "logs"
QUESTION_LOG_FILE = LOG_DIRECTORY / "user_questions.txt"
MAX_LOG_BYTES = 5 * 1024 * 1024
MAX_LOG_LINE_CHARACTERS = 2_000

FILE_LOCK = threading.Lock()


def redact_sensitive_information(text: str) -> str:
    """Remove common credentials and personal identifiers before logging."""

    cleaned = text.strip()

    patterns = (
        (
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
            "[EMAIL REDACTED]",
        ),
        (
            r"(?i)\b(password|passcode|verification\s+code|otp|"
            r"api\s*key|access\s*token|token|secret)\b"
            r"\s*(?:is|was|:|=)\s*[\"']?[^\s,;\"']+",
            r"\1: [REDACTED]",
        ),
        (
            r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]+=*",
            "Bearer [REDACTED]",
        ),
        (
            r"(?<!\d)(?:\+?1[ .-]?)?(?:\(?\d{3}\)?[ .-]?)"
            r"\d{3}[ .-]?\d{4}(?!\d)",
            "[PHONE REDACTED]",
        ),
        (
            r"(?<!\d)(?:\d[ -]*?){13,19}(?!\d)",
            "[NUMBER REDACTED]",
        ),
    )

    for pattern, replacement in patterns:
        cleaned = re.sub(pattern, replacement, cleaned)

    # Keep each question on one bounded line.
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned) > MAX_LOG_LINE_CHARACTERS:
        cleaned = cleaned[: MAX_LOG_LINE_CHARACTERS - 1].rstrip() + "…"

    return cleaned


def _rotate_log_if_needed() -> None:
    if not QUESTION_LOG_FILE.exists():
        return

    if QUESTION_LOG_FILE.stat().st_size < MAX_LOG_BYTES:
        return

    rotated_file = QUESTION_LOG_FILE.with_suffix(".previous.txt")
    rotated_file.unlink(missing_ok=True)
    QUESTION_LOG_FILE.replace(rotated_file)


def log_user_question(question: str) -> None:
    """Append one redacted user question to the local text log."""

    cleaned_question = redact_sensitive_information(question)

    if not cleaned_question:
        return

    timestamp = datetime.now(get_local_timezone()).strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {cleaned_question}\n"

    with FILE_LOCK:
        LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
        _rotate_log_if_needed()
        with QUESTION_LOG_FILE.open("a", encoding="utf-8") as log_file:
            log_file.write(log_line)
