from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.extended_support_router import route_extended_support_question
from core.retrieval_profile import (
    build_document_profile,
    build_retrieval_profile,
    profiles_are_compatible,
)
from core.support_router import route_security_or_account_question
from core.wifi_router import route_wifi_question


@dataclass
class FakeDocument:
    page_content: str
    metadata: dict[str, Any]


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print(f"[PASS] {name}")


def direct(question: str) -> str:
    decision = route_extended_support_question(question, [])
    check(f"direct route handled: {question[:45]}", decision.handled)
    return decision.answer.lower()


def main() -> None:
    profile = build_retrieval_profile(
        "My laptop connects to Wi-Fi just fine, but every website shows an invalid security certificate."
    )
    check("contrast focus keeps certificate problem", "certificate" in profile.focus_text)
    check("certificate symptom detected", "certificate_warning" in profile.focus_symptoms)

    charge = build_retrieval_profile(
        "My Chromebook won't charge even when the power adapter is plugged in."
    )
    zoom_doc = FakeDocument(
        "Chromebooks can use the Zoom Web App to join meetings.",
        {
            "source": "zoom_workplace_school_support.md",
            "section_title": "Join with the Zoom Web App",
            "intent_keywords": "zoom, chromebook, web app",
        },
    )
    check(
        "Chromebook charging rejects Zoom article",
        not profiles_are_compatible(charge, build_document_profile(zoom_doc)),
    )

    popup = build_retrieval_profile(
        "My browser keeps opening random pop-up tabs that I cannot close."
    )
    learned_monitor = FakeDocument(
        "Disconnect the USB-C dock and reconnect the external monitors.",
        {
            "source": "learned_support.md",
            "section_title": "External Monitors Not Detected Through a USB-C Dock",
            "intent_keywords": "external monitor, usb-c dock, not detected",
        },
    )
    check(
        "browser pop-ups reject learned monitor fix",
        not profiles_are_compatible(popup, build_document_profile(learned_monitor)),
    )

    monitor_question = build_retrieval_profile(
        "My USB-C dock works for Ethernet, but neither external monitor is detected."
    )
    check(
        "monitor problem accepts learned monitor fix",
        profiles_are_compatible(
            monitor_question,
            build_document_profile(learned_monitor),
        ),
    )

    wifi = route_wifi_question(
        "My laptop connects to Wi-Fi just fine, but every website shows a privacy warning about an invalid security certificate.",
        [],
    )
    check("certificate warning is not hijacked by Wi-Fi access router", not wifi.handled)

    admin = route_security_or_account_question(
        "I need to install a required program but it asks for an administrator password."
    )
    check("software install admin prompt has approved support answer", admin.handled)
    check("admin prompt answer explains IT approval", "it" in admin.answer.lower())

    lockout_security = route_security_or_account_question(
        "I changed my network password and now the laptop keeps locking my account because of too many failed login attempts."
    )
    check("network lockout is not misclassified as credential reveal", not lockout_security.handled)

    answer = direct("The classroom projector image has a strange purple tint and the text looks fuzzy.")
    check("projector quality answer mentions cable/resolution", "resolution" in answer and "cable" in answer)

    answer = direct("Every time I open my browser it opens random pop-up tabs that I cannot close.")
    check("browser pop-up answer is security/browser focused", "extension" in answer and "pop-up" in answer)

    answer = direct("The stylus pen for my touchscreen is no longer drawing on the screen.")
    check("stylus answer is device focused", "stylus" in answer and "touchscreen" in answer)

    answer = direct("The scanner on the main office copier is no longer sending documents to my email address.")
    check("scan-to-email answer is copier focused", "copier" in answer and "recipient" in answer)

    answer = direct("The smartboard ink appears three inches away from where the pen touches.")
    check("smartboard answer recommends calibration", "calibration" in answer)

    answer = direct("My math software says Cannot connect to local database server even though internet works.")
    check("local database answer avoids Wi-Fi reset", "local database" in answer and "wifi" not in answer)

    answer = direct("My USB microphone says it is currently in use by another application.")
    check("microphone-in-use answer closes competing apps", "another application" in answer and "close" in answer)

    answer = direct("The VPN connects successfully but I still cannot access internal network drives.")
    check("VPN drive answer stays on VPN/network-drive problem", "vpn" in answer and "drive" in answer)

    answer = direct("The cursor keeps jumping on its own even after I disconnect my external mouse.")
    check("ghost cursor answer checks built-in input", "touchpad" in answer or "trackpad" in answer)

    answer = direct("Adobe Acrobat prints my PDF as pages of weird symbols even though Google Docs prints fine.")
    check("Acrobat garbled print answer uses Print as Image", "print as image" in answer)

    answer = direct("The video is smooth but classroom speaker audio is three seconds out of sync.")
    check("audio sync answer treats delay, not missing output", "delayed" in answer and "output device alone" in answer)

    answer = direct("My Chromebook keeps connecting to the guest network instead of staff and it will not let me forget it.")
    check("managed Chromebook Wi-Fi answer does not demand forgetting", "managed" in answer and "do not try to remove management" in answer)

    print("\nAll domain-aware routing regression checks passed.")


if __name__ == "__main__":
    main()
