from __future__ import annotations

from core.printer_router import route_printer_question
from core.topic_context import build_topic_context


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print(f"[PASS] {name}")


def main() -> None:
    first = route_printer_question("i want to print in library", [])
    check("library print request is handled", first.handled)
    check(
        "library print request skips redundant printer/action prompts",
        "mac" in first.answer.lower()
        and "chromebook" in first.answer.lower()
        and "which printer" not in first.answer.lower()
        and "clarify whether" not in first.answer.lower(),
    )

    mac_history = [
        {"role": "user", "content": "i want to print in library"},
        {"role": "assistant", "content": first.answer},
    ]
    mac = route_printer_question("Mac", mac_history)
    check("Mac follow-up returns setup instructions", "192.168.1.205" in mac.answer)

    chromebook = route_printer_question("Chromebook", mac_history)
    check(
        "Chromebook follow-up returns managed printer instructions",
        "school-managed" in chromebook.answer.lower(),
    )

    failed = "the library printer is not printing"
    context = build_topic_context(failed, [])
    check("not printing does not negate printer topic", context.allows("printer"))
    failed_answer = route_printer_question(failed, [])
    check("library printer failure is handled", failed_answer.handled)
    check(
        "library printer failure goes to troubleshooting",
        "try printing again" in failed_answer.answer.lower(),
    )

    nothing_came_out = route_printer_question(
        "i sent my essay to the library printer but nothing came out",
        [],
    )
    check(
        "nothing came out is treated as troubleshooting",
        "try printing again" in nothing_came_out.answer.lower()
        and "clarify whether" not in nothing_came_out.answer.lower(),
    )

    old_history = [
        {"role": "user", "content": "i want to print in library"},
        {
            "role": "assistant",
            "content": (
                "Which printer are you trying to use?\n\n"
                "- **Learning Commons / Library printer**\n"
                "- **Another school printer**"
            ),
        },
    ]
    continued = route_printer_question("library", old_history)
    check(
        "existing conversation can recover without restarting",
        "mac" in continued.answer.lower() and "chromebook" in continued.answer.lower(),
    )

    print("\nAll printer-flow regression checks passed.")


if __name__ == "__main__":
    main()
