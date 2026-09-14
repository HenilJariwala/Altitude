from __future__ import annotations

from core.common_support_router import route_common_support_question
from core.extended_support_router import route_extended_support_question
from core.printer_router import route_printer_question
from core.support_router import is_google_password_request, route_security_or_account_question
from core.topic_context import build_topic_context
from core.wifi_router import route_wifi_question


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print(f"[PASS] {name}")


def main() -> int:
    monitor_history = [
        {
            "role": "user",
            "content": (
                "My laptop only detects one monitor when I connect two monitors "
                "through my USB-C docking station. How can I fix it?"
            ),
        },
        {
            "role": "assistant",
            "content": "To connect a laptop to the classroom display...",
        },
    ]

    ctx = build_topic_context(
        "I am talking about monitor, not for classroom",
        monitor_history,
    )
    check("correction blocks classroom routes", not ctx.allows("classroom_display"))
    check("correction blocks Google Classroom route", not ctx.allows("google_classroom"))
    check("correction keeps external monitor allowed", ctx.allows("external_monitor"))
    check("correction carries the original issue", "docking station" in ctx.effective_text)

    corrected = route_extended_support_question(
        "I am talking about monitor, not for classroom",
        monitor_history,
    )
    check("monitor correction returns hardware answer", corrected.handled and "USB-C dock" in corrected.answer)
    check("monitor correction does not drift to Classroom", "school Google account" not in corrected.answer)

    classroom = route_common_support_question(
        "Google Classroom will not open in Chrome",
        [],
    )
    check("explicit Google Classroom still routes correctly", classroom.handled and "Google Classroom" in classroom.answer)

    classroom_display = route_extended_support_question(
        "How do I connect my Chromebook to the classroom display?",
        [],
    )
    check("explicit classroom display still routes correctly", classroom_display.handled and "classroom display" in classroom_display.answer.lower())

    printer_history = [
        {"role": "user", "content": "My printer cannot connect and Wi-Fi is working."},
        {"role": "assistant", "content": "Which Wi-Fi network are you using?"},
    ]
    printer_ctx = build_topic_context("I mean the printer, not Wi-Fi", printer_history)
    check("printer correction blocks Wi-Fi", not printer_ctx.allows("wifi"))
    check("printer correction keeps printer", printer_ctx.allows("printer"))
    check("Wi-Fi router respects explicit negation", not route_wifi_question("I mean the printer, not Wi-Fi", printer_history).handled)

    wifi_history = [
        {"role": "user", "content": "My laptop cannot connect to Wi-Fi and the printer is nearby."},
        {"role": "assistant", "content": "Which printer are you using?"},
    ]
    wifi_ctx = build_topic_context("I mean Wi-Fi, not the printer", wifi_history)
    check("Wi-Fi correction blocks printer", not wifi_ctx.allows("printer"))
    check("Wi-Fi correction keeps Wi-Fi", wifi_ctx.allows("wifi"))
    check("printer router respects explicit negation", not route_printer_question("I mean Wi-Fi, not the printer", wifi_history).handled)

    check("Wi-Fi password is not a Google password reset", not is_google_password_request("What is the Wi-Fi password?"))
    check("school email password is a Google password reset", is_google_password_request("I forgot my email password"))

    password = route_security_or_account_question("I forgot my email password")
    check("password reset stays deterministic", password.handled and password.intent == "google_password_reset")
    check("password reset answer has four steps", all(f"{n}." in password.answer for n in range(1, 5)) and "5." not in password.answer)
    check("password reset answer has no repeated if-issue-continues footer", "if the issue continues" not in password.answer.lower())

    rag_ctx = build_topic_context(
        "I mean the monitor, not Google Classroom",
        monitor_history,
    )
    check("RAG correction query preserves original problem", "Original issue:" in rag_ctx.retrieval_text and "USB-C docking station" in rag_ctx.retrieval_text)
    check("RAG correction query carries exclusion", "Do not interpret as:" in rag_ctx.retrieval_text)

    print("\nAll universal topic-routing and password-reset checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
