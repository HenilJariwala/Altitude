from __future__ import annotations

from core.common_support_router import route_common_support_question
from core.extended_support_router import route_extended_support_question


def _check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print(f"[PASS] {name}")


def main() -> int:
    monitor_question = (
        "My laptop only detects one monitor when I connect two monitors "
        "through my USB-C docking station. How can I fix it?"
    )
    monitor_result = route_extended_support_question(monitor_question, [])

    _check("USB-C monitor question is handled", monitor_result.handled)
    _check(
        "USB-C monitor question stays on external-monitor topic",
        "USB-C docking station" in monitor_result.answer
        and "classroom display" not in monitor_result.answer.lower()
        and "google classroom" not in monitor_result.answer.lower(),
    )

    correction_history = [
        {"role": "user", "content": monitor_question},
        {
            "role": "assistant",
            "content": "To connect a laptop to the classroom display...",
        },
    ]
    correction = route_extended_support_question(
        "i am talking about monitor not for classroom",
        correction_history,
    )
    _check("Monitor correction is handled", correction.handled)
    _check(
        "Monitor correction does not become Google Classroom",
        "external monitor / USB-C dock" in correction.answer
        and "not Google Classroom" in correction.answer,
    )

    classroom = route_extended_support_question(
        "How do I connect my laptop to the classroom display?",
        [],
    )
    _check("Real classroom-display question still works", classroom.handled)
    _check(
        "Real classroom-display question keeps classroom answer",
        "classroom display" in classroom.answer.lower(),
    )

    google_classroom_question = "Google Classroom won't open"
    google_extended = route_extended_support_question(
        google_classroom_question,
        [],
    )
    google_common = route_common_support_question(
        google_classroom_question,
        [],
    )
    _check(
        "Google Classroom is not captured by monitor/display routing",
        not google_extended.handled,
    )
    _check(
        "Google Classroom support still works",
        google_common.handled and "Google Classroom" in google_common.answer,
    )

    print("\nAll monitor/classroom routing regression tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
