from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from core.support_router import route_security_or_account_question


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"[PASS] {label}")


def main() -> None:
    routed = route_security_or_account_question("I forgot my email password")
    check(routed.handled, "forgot-email-password request is handled directly")
    check(
        routed.intent == "google_password_reset",
        "school password reset receives a dedicated intent",
    )
    check(
        "1. Stop repeated sign-in attempts." in routed.answer
        and "4. After IT resets the password" in routed.answer,
        "password answer contains four concise steps",
    )
    check(
        "If the issue continues" not in routed.answer
        and "All school Google password resets" not in routed.answer,
        "password answer has no repeated closing instruction",
    )

    assistant_source = (APP_ROOT / "core" / "assistant.py").read_text(encoding="utf-8")
    chat_source = (APP_ROOT / "pages" / "chat.py").read_text(encoding="utf-8")

    check(
        "intent=security.intent or None" in assistant_source,
        "password-reset intent is propagated to the assistant message",
    )
    check(
        '"google_password_reset"' in chat_source
        and "if intent in NON_TICKET_FEEDBACK_INTENTS" in chat_source,
        "negative password-reset feedback cannot trigger a ticket offer",
    )

    print("\nAll password-reset flow regression checks passed.")


if __name__ == "__main__":
    main()
