#!/usr/bin/env python3
"""Regression tests for Altitude's resolved-ticket follow-up email workflow."""

from __future__ import annotations

import os
import sys
import tempfile
from email.message import EmailMessage
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


class FakeSMTP:
    messages: list[EmailMessage] = []
    login_calls: list[tuple[str, str]] = []

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.tls_started = False

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def ehlo(self) -> None:
        return None

    def starttls(self) -> None:
        self.tls_started = True

    def login(self, username: str, password: str) -> None:
        self.login_calls.append((username, password))

    def send_message(self, message: EmailMessage) -> None:
        self.messages.append(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"[PASS] {message}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="altitude-resolution-email-") as temp_dir:
        os.environ["ALTITUDE_DB_PATH"] = str(Path(temp_dir) / "altitude.db")
        os.environ["ALTITUDE_RESOLUTION_EMAIL_ENABLED"] = "true"
        os.environ["ALTITUDE_SMTP_HOST"] = "smtp.test.local"
        os.environ["ALTITUDE_SMTP_PORT"] = "587"
        os.environ["ALTITUDE_SMTP_USERNAME"] = ""
        os.environ["ALTITUDE_SMTP_PASSWORD"] = ""
        os.environ["ALTITUDE_SMTP_FROM_EMAIL"] = "altitude@sjkschool.org"
        os.environ["ALTITUDE_SMTP_FROM_NAME"] = "Altitude IT Support"
        os.environ["ALTITUDE_SMTP_USE_TLS"] = "true"
        os.environ["ALTITUDE_SMTP_USE_SSL"] = "false"

        from core.analytics_db import (
            apply_ticket_status_updates,
            create_ticket_audit,
            ensure_ticket_altitude_reference,
            get_tickets_pending_resolution_email,
            initialize_database,
            mark_ticket_submitted,
        )
        import core.resolution_notifications as notifications

        notifications.smtplib.SMTP = FakeSMTP  # type: ignore[assignment]
        FakeSMTP.messages.clear()

        initialize_database()
        local_id = create_ticket_audit(
            session_id="resolution-email-test-session",
            title="Second monitor not detected through USB-C dock",
            contact_email="tester@sjkschool.org",
            category="DeviceHardwareIssue",
            device="Laptop",
            priority="Medium",
            payload={"description": "Only one of two external monitors is detected."},
        )
        reference = ensure_ticket_altitude_reference(local_id)
        mark_ticket_submitted(local_id, external_ticket_id="75", status="Open")

        resolution_note = (
            "Disconnected the USB-C cable and dock power for 30 seconds. "
            "Reconnected dock power first, then USB-C, and restarted the laptop. "
            "Both external monitors were detected successfully."
        )
        apply_ticket_status_updates(
            [
                {
                    "local_ticket_id": local_id,
                    "status": "Resolved",
                    "external_ticket_id": "75",
                    "remote_ticket_url": "http://ticketing.local/ticket/75/",
                    "resolution_comment": resolution_note,
                }
            ]
        )

        pending = get_tickets_pending_resolution_email()
        require(len(pending) == 1, "newly resolved ticket becomes email-eligible")
        require(pending[0]["altitude_reference"] == reference, "email keeps Altitude reference")

        subject, text_body, html_body = notifications.build_resolution_email(pending[0])
        require("resolution details" in subject.lower(), "email subject identifies resolution details")
        require(resolution_note in text_body, "plain-text email contains technician resolution note")
        require("How it was resolved" in html_body, "HTML email has a How it was resolved section")
        require("USB-C" in html_body, "HTML email contains the actual fix")

        first = notifications.process_pending_resolution_notifications()
        require(first["sent"] == 1 and first["failed"] == 0, "first sync sends one resolution email")
        require(len(FakeSMTP.messages) == 1, "SMTP receives exactly one message")
        require(FakeSMTP.messages[0]["To"] == "tester@sjkschool.org", "email goes to ticket requester")

        second = notifications.process_pending_resolution_notifications()
        require(second["sent"] == 0, "second sync does not resend the same resolution email")
        require(len(FakeSMTP.messages) == 1, "duplicate resolution email is prevented")

    print("\nAll Altitude resolution-notification regression checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
