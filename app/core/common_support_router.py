from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.text_matching import contains_any_phrase, normalize_text
from core.topic_context import build_topic_context


@dataclass(frozen=True)
class CommonSupportDecision:
    """Deterministic response for high-frequency or safety-critical issues."""

    handled: bool
    answer: str = ""


def _has(text: str, *phrases: str) -> bool:
    return contains_any_phrase(text, phrases)


def _recent_topic(history: list[dict[str, Any]], *terms: str) -> bool:
    for message in reversed(history[-10:]):
        content = normalize_text(str(message.get("content", "")))
        if any(term in content for term in terms):
            return True
    return False


def route_common_support_question(
    question: str,
    history: list[dict[str, Any]],
) -> CommonSupportDecision:
    """Handle issues where a wrong RAG match would be confusing or unsafe.

    These responses intentionally run before semantic retrieval. They cover
    safety-critical device conditions and common support requests whose answer
    is stable enough to be deterministic.
    """

    topic_context = build_topic_context(question, history)
    normalized = topic_context.effective_text.strip(" .")

    if not normalized:
        return CommonSupportDecision(False)

    # Account lockouts should never be mistaken for a personal Microsoft
    # account or an unrelated knowledge topic.
    if _has(
        normalized,
        "account is locked",
        "account locked",
        "locked after too many login attempts",
        "too many login attempts",
        "locked out of my account",
    ):
        return CommonSupportDecision(
            True,
            (
                "Your account may be temporarily locked after repeated sign-in "
                "attempts.\n\n"
                "1. Stop trying to sign in for a few minutes so the lockout is "
                "not extended.\n"
                "2. Confirm that you are using the correct school email address.\n"
                "3. Try one sign-in from a private browser window.\n"
                "4. If the account is still locked, visit the IT Helpdesk so the "
                "team can verify your identity and reset or unlock the school "
                "account.\n\n"
                "Do not share your password or verification codes in chat."
            ),
        )

    # Managed-device application installation and policy restrictions.
    if _has(
        normalized,
        "install software on my school laptop",
        "install an app on my school laptop",
        "install application on my school laptop",
        "install software on school device",
        "install software on a school laptop",
    ):
        return CommonSupportDecision(
            True,
            (
                "Software on a school-managed laptop must use the approved "
                "installation process.\n\n"
                "1. Tell the IT Helpdesk the name of the application and why it "
                "is needed.\n"
                "2. IT will confirm that the software is approved and licensed.\n"
                "3. If administrator access is required, an authorized technician "
                "must complete the installation.\n"
                "4. Do not download installers from unapproved websites or try to "
                "bypass device restrictions.\n\n"
                "Which application do you need installed?"
            ),
        )

    # Google Drive sync has safe cross-platform checks. Avoid asking Mac or
    # Windows before giving the useful first-line steps.
    if "google drive" in normalized and _has(
        normalized,
        "not syncing",
        "will not sync",
        "won't sync",
        "sync problem",
        "syncing problem",
    ):
        return CommonSupportDecision(
            True,
            (
                "Try these Google Drive sync checks:\n\n"
                "1. Confirm that the laptop has a working internet connection.\n"
                "2. Open Google Drive in a browser and confirm that the correct "
                "school account can access the files.\n"
                "3. Check that the device and Google account have available "
                "storage.\n"
                "4. Quit and reopen Google Drive for desktop, then confirm that it "
                "is signed in.\n"
                "5. Restart the laptop.\n"
                "6. Record any sync error shown by the Drive icon.\n\n"
                "If syncing still fails, contact the IT Helpdesk with the exact "
                "error message."
            ),
        )

    if (
        topic_context.allows("google_classroom")
        and "google classroom" in normalized
        and _has(
            normalized,
        "will not open",
        "won't open",
        "cannot open",
        "can't open",
            "not opening",
        )
    ):
        return CommonSupportDecision(
            True,
            (
                "Try these Google Classroom checks:\n\n"
                "1. Confirm that you are signed in with the correct school Google "
                "account.\n"
                "2. Open Classroom in a supported browser such as Chrome.\n"
                "3. Refresh the page and try a private/incognito browser window.\n"
                "4. Clear the browser cache for Google Classroom if the page still "
                "does not load.\n"
                "5. Disable only nonessential browser extensions and try again.\n"
                "6. Restart the browser or device.\n\n"
                "If other Google services work but Classroom still will not open, "
                "contact the IT Helpdesk with the exact error message."
            ),
        )

    # Classroom display and source-selection issues.
    if (
        topic_context.allows("classroom_display")
        and _has(normalized, "smartboard", "smart board")
        and _has(
            normalized,
        "screen is black",
        "black screen",
        "screen black",
            "display is black",
        )
    ):
        return CommonSupportDecision(
            True,
            (
                "Check the Smartboard display path in this order:\n\n"
                "1. Confirm that the Smartboard and the connected computer are on.\n"
                "2. Select the correct input or source on the Smartboard.\n"
                "3. Reseat the HDMI, USB-C, or display cable at both ends.\n"
                "4. Confirm that the laptop detects an external display.\n"
                "5. Restart the connected laptop.\n"
                "6. Try an approved spare cable or adapter if one is available.\n\n"
                "If the screen remains black, contact the IT Helpdesk with the "
                "classroom location and connection type."
            ),
        )

    if (
        topic_context.allows("classroom_display")
        and not topic_context.current_mentions("external_monitor")
        and _has(normalized, "tv", "classroom display", "display")
        and "no signal" in normalized
    ):
        return CommonSupportDecision(
            True,
            (
                "A **No Signal** message usually means the TV is on the wrong "
                "input or is not receiving video.\n\n"
                "1. Confirm that the connected laptop or Apple TV is powered on.\n"
                "2. Use the TV remote or controls to select the correct input/source.\n"
                "3. Reseat the HDMI or display cable at both ends.\n"
                "4. If an adapter is used, disconnect and reconnect it.\n"
                "5. Try an approved spare cable or adapter when available.\n\n"
                "If the TV still shows No Signal, contact the IT Helpdesk with the "
                "classroom location and selected input."
            ),
        )

    if (
        topic_context.allows("classroom_display")
        and not topic_context.current_mentions("external_monitor")
        and _has(normalized, "classroom display", "display", "screen", "tv")
        and _has(
            normalized,
            "sound but no picture",
            "audio but no picture",
            "sound but no video",
            "can hear but cannot see",
        )
    ):
        return CommonSupportDecision(
            True,
            (
                "Because sound is working, check the video input and display "
                "connection:\n\n"
                "1. Confirm that the classroom display is on the correct input.\n"
                "2. Reseat the HDMI, USB-C, or display cable at both ends.\n"
                "3. Open the laptop's display settings and confirm the external "
                "screen is detected.\n"
                "4. Try mirror/duplicate display mode.\n"
                "5. Restart the connected device and test an approved spare cable "
                "or adapter.\n\n"
                "If there is still no picture, contact the IT Helpdesk with the "
                "classroom and device details."
            ),
        )

    # AirPlay stability can be answered without first asking for a platform.
    if "airplay" in normalized and _has(
        normalized,
        "disconnects",
        "disconnecting",
        "keeps disconnecting",
        "drops",
        "stops after",
    ):
        return CommonSupportDecision(
            True,
            (
                "For AirPlay that connects and then disconnects:\n\n"
                "1. Confirm that the Mac and Apple TV are on the same approved "
                "school Wi-Fi network.\n"
                "2. Move closer to the classroom access point and disconnect any "
                "VPN.\n"
                "3. Turn Wi-Fi off and back on, then reconnect through **Control "
                "Center → Screen Mirroring**.\n"
                "4. Restart the Mac and wake or restart the Apple TV only if you are "
                "authorized to do so.\n"
                "5. Install approved macOS updates when available.\n\n"
                "If AirPlay continues dropping, contact the IT Helpdesk with the "
                "classroom and Apple TV name."
            ),
        )

    # Hardware safety must always take precedence over normal troubleshooting.
    if _has(
        normalized,
        "battery is swelling",
        "battery swelling",
        "swollen battery",
        "battery is bulging",
        "battery bulging",
    ):
        return CommonSupportDecision(
            True,
            (
                "Stop using the laptop immediately. A swelling battery is a safety "
                "hazard.\n\n"
                "1. Shut the laptop down if it is safe to do so.\n"
                "2. Disconnect the charger and all accessories.\n"
                "3. Do not press on, damage, bend, or continue charging the device.\n"
                "4. Place it on a hard, nonflammable surface away from heat.\n"
                "5. Contact the IT Helpdesk immediately and do not transport it in a "
                "tightly packed bag."
            ),
        )

    if _has(
        normalized,
        "spilled water on my laptop",
        "spilled liquid on my laptop",
        "water on my laptop",
        "liquid spill",
        "drink on my laptop",
    ):
        return CommonSupportDecision(
            True,
            (
                "Stop using the laptop immediately to reduce electrical and data "
                "damage.\n\n"
                "1. Power it off; do not keep testing it.\n"
                "2. Disconnect the charger and all accessories.\n"
                "3. Do not apply heat, compressed air, or place the device in rice.\n"
                "4. Keep the device still and place it on a dry surface.\n"
                "5. Contact the IT Helpdesk immediately and describe what was spilled."
            ),
        )

    if "chromebook" in normalized and _has(
        normalized,
        "screen is frozen",
        "screen frozen",
        "is frozen",
        "not responding",
    ):
        return CommonSupportDecision(
            True,
            (
                "Try these Chromebook restart steps:\n\n"
                "1. Wait briefly and try **Refresh** once.\n"
                "2. If the Chromebook is still frozen, hold the **Power** button until "
                "it turns off.\n"
                "3. Wait ten seconds, then press Power to start it again.\n"
                "4. Reopen only the tabs or applications you need.\n\n"
                "If it freezes again, contact the IT Helpdesk and note which page or "
                "application was open."
            ),
        )

    # A short failure follow-up should retain the recent printer context even
    # before the specialized printer router chooses a specific device.
    if normalized in {
        "i already restarted it",
        "already restarted it",
        "i restarted it already",
    } and _recent_topic(history, "printer", "printing", "print queue"):
        return CommonSupportDecision(
            True,
            (
                "Since the printer or device has already been restarted, try the "
                "next checks:\n\n"
                "1. Confirm that the correct printer is selected.\n"
                "2. Open the print queue and remove only your failed print job.\n"
                "3. Confirm that the queue is not paused.\n"
                "4. Verify that the device is connected to the approved school Wi-Fi.\n"
                "5. Send a one-page test print.\n\n"
                "If it still fails, contact the IT Helpdesk or create a ticket."
            ),
        )

    if normalized in {
        "it still does not work",
        "it still doesn't work",
        "still does not work",
        "still not working",
    } and _recent_topic(history, "printer", "printing", "print queue"):
        return CommonSupportDecision(
            True,
            (
                "The printer issue is still unresolved after the approved checks. "
                "The next step is to contact the IT Helpdesk or create a ticket with "
                "the printer name, device type, and any error shown."
            ),
        )

    return CommonSupportDecision(False)
