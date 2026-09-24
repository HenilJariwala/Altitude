from __future__ import annotations

import sys
import types

from core.request_guard import route_request_guard


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print(f"[PASS] {name}")


def guarded(question: str, expected_intent: str) -> str:
    decision = route_request_guard(question, [])
    check(f"{expected_intent}: handled", decision.handled)
    check(f"{expected_intent}: intent", decision.intent == expected_intent)
    check(f"{expected_intent}: answer", bool(decision.answer.strip()))
    return decision.answer


def main() -> int:
    guarded("Adobe Acrobat won't open PDF files", "adobe_acrobat_pdf_open")
    guarded("Photoshop keeps crashing on my Mac", "adobe_photoshop_crash")

    adobe_license = guarded(
        "Adobe says 'Licensing for this product has stopped working'",
        "adobe_licensing",
    )
    check("Adobe licensing explicitly blocks Keychain reset", "do not reset keychain" in adobe_license.lower())
    check("Adobe licensing restricts reinstall", "reinstall adobe unless it specifically directs you to" in adobe_license.lower() or "reinstall adobe unless it specifically" in adobe_license.lower())

    zoom_5003 = guarded(
        "Zoom says 'Error 5003' when I try to start a meeting",
        "zoom_error_5003",
    )
    check("Zoom 5003 explicitly blocks firewall changes", "do not disable the firewall" in zoom_5003.lower())

    dns = guarded(
        "Chrome says 'This site can't be reached, DNS_PROBE_FINISHED_NXDOMAIN'",
        "chrome_dns_nxdomain",
    )
    check("Chrome DNS keeps managed network settings unchanged", "do not change dns" in dns.lower())

    guarded(
        "A student says they submitted but I don't see it, is that a Classroom bug?",
        "classroom_submission",
    )
    guarded(
        "My screen won't mirror to the TV and I have a lesson pulled up",
        "classroom_screen_mirroring",
    )
    guarded("My display isn't working", "clarification")
    guarded("Can you unlock my Mac, I forgot the login password", "mac_login_recovery")

    zoom_signin = guarded("I can't sign into Zoom with my school account", "zoom_signin")
    check("Zoom sign-in does not assume SSO", "sign in with sso" not in zoom_signin.lower())

    outage = guarded(
        "The whole class can't log into Classroom right now, is something down?",
        "possible_service_outage",
    )
    check("Status Dashboard wording does not imply Altitude checked it", "not claiming that it checked" in outage.lower())

    guarded("My microphone isn't being picked up in calls", "generic_microphone")
    guarded("Camera shows black screen in video calls", "generic_camera")

    # llm.py imports ollama at module import time. A tiny local stub lets this
    # regression test exercise the pure response-quality validator without
    # requiring a running Ollama service.
    if "ollama" not in sys.modules:
        fake_ollama = types.ModuleType("ollama")

        class DummyClient:
            def __init__(self, *args: object, **kwargs: object) -> None:
                del args, kwargs

        fake_ollama.Client = DummyClient
        sys.modules["ollama"] = fake_ollama

    from core.llm import web_answer_looks_low_quality

    repeated = (
        "1. Check for updates and install them if available.\n"
        "2. Check for updates and install them if available."
    )
    unsafe = "Temporarily disable your firewall and try the meeting again."
    safe = "1. Restart the app.\n2. Confirm the internet connection.\n3. Contact IT if the error continues."

    check("web validator rejects repeated instructions", web_answer_looks_low_quality(repeated))
    check("web validator rejects unsafe managed-network changes", web_answer_looks_low_quality(unsafe))
    check("web validator accepts concise safe answer", not web_answer_looks_low_quality(safe))

    print("\nAll Run 2 hardening checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
