from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from html import escape
from typing import Any

from dotenv import load_dotenv

from core.analytics_db import (
    get_tickets_pending_resolution_email,
    mark_resolution_email_error,
    mark_resolution_email_sent,
)
from core.ticketing_client import is_authorized_school_email


load_dotenv()


class ResolutionEmailConfigurationError(RuntimeError):
    """Raised when Altitude resolution email is enabled but incomplete."""


@dataclass(frozen=True)
class ResolutionEmailConfig:
    enabled: bool
    host: str
    port: int
    username: str
    password: str
    from_email: str
    from_name: str
    reply_to: str
    use_tls: bool
    use_ssl: bool
    timeout_seconds: float

    @classmethod
    def from_environment(cls) -> "ResolutionEmailConfig":
        enabled = _env_bool("ALTITUDE_RESOLUTION_EMAIL_ENABLED", default=False)
        host = os.getenv("ALTITUDE_SMTP_HOST", "").strip()
        username = os.getenv("ALTITUDE_SMTP_USERNAME", "").strip()
        password = os.getenv("ALTITUDE_SMTP_PASSWORD", "")
        from_email = os.getenv("ALTITUDE_SMTP_FROM_EMAIL", "").strip() or username
        from_name = os.getenv(
            "ALTITUDE_SMTP_FROM_NAME", "Altitude IT Support"
        ).strip() or "Altitude IT Support"
        reply_to = os.getenv("ALTITUDE_SMTP_REPLY_TO", "").strip()

        try:
            port = int(os.getenv("ALTITUDE_SMTP_PORT", "587"))
        except ValueError as error:
            raise ResolutionEmailConfigurationError(
                "ALTITUDE_SMTP_PORT must be an integer"
            ) from error

        try:
            timeout_seconds = float(
                os.getenv("ALTITUDE_SMTP_TIMEOUT_SECONDS", "12")
            )
        except ValueError as error:
            raise ResolutionEmailConfigurationError(
                "ALTITUDE_SMTP_TIMEOUT_SECONDS must be numeric"
            ) from error

        use_ssl = _env_bool("ALTITUDE_SMTP_USE_SSL", default=False)
        use_tls = _env_bool("ALTITUDE_SMTP_USE_TLS", default=not use_ssl)

        config = cls(
            enabled=enabled,
            host=host,
            port=port,
            username=username,
            password=password,
            from_email=from_email,
            from_name=from_name,
            reply_to=reply_to,
            use_tls=use_tls,
            use_ssl=use_ssl,
            timeout_seconds=max(3.0, min(timeout_seconds, 60.0)),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if not self.enabled:
            return
        if not self.host:
            raise ResolutionEmailConfigurationError(
                "ALTITUDE_SMTP_HOST is required when resolution email is enabled"
            )
        if not self.from_email:
            raise ResolutionEmailConfigurationError(
                "ALTITUDE_SMTP_FROM_EMAIL or ALTITUDE_SMTP_USERNAME is required"
            )
        if self.port <= 0 or self.port > 65535:
            raise ResolutionEmailConfigurationError(
                "ALTITUDE_SMTP_PORT must be between 1 and 65535"
            )
        if self.username and not self.password:
            raise ResolutionEmailConfigurationError(
                "ALTITUDE_SMTP_PASSWORD is required when ALTITUDE_SMTP_USERNAME is set"
            )
        if self.use_ssl and self.use_tls:
            raise ResolutionEmailConfigurationError(
                "Enable only one of ALTITUDE_SMTP_USE_SSL or ALTITUDE_SMTP_USE_TLS"
            )


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().casefold() in {"1", "true", "yes", "on"}


def _clean_single_line(value: object, *, maximum_length: int) -> str:
    return " ".join(str(value or "").split()).strip()[:maximum_length]


def _clean_multiline(value: object, *, maximum_length: int) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.split()).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()[:maximum_length]


def build_resolution_email(ticket: dict[str, Any]) -> tuple[str, str, str]:
    """Return subject, plain text, and HTML for one resolved ticket."""
    title = _clean_single_line(ticket.get("title"), maximum_length=220) or "IT support issue"
    resolution = _clean_multiline(
        ticket.get("resolution_comment"), maximum_length=5000
    )
    if not resolution:
        raise ValueError("A resolution note is required before sending the email")

    reference = _clean_single_line(
        ticket.get("altitude_reference"), maximum_length=80
    )
    external_id = _clean_single_line(
        ticket.get("external_ticket_id"), maximum_length=80
    )
    status = _clean_single_line(ticket.get("status"), maximum_length=80) or "Resolved"

    display_reference = reference
    if not display_reference and external_id:
        display_reference = f"Ticket #{external_id}"
    if not display_reference:
        display_reference = "your IT ticket"

    subject = f"Altitude resolution details — {display_reference}"[:240]

    text_lines = [
        "Your IT support ticket has been resolved.",
        "",
        f"Ticket: {display_reference}",
        f"Issue: {title}",
        f"Status: {status}",
        "",
        "How it was resolved:",
        resolution,
        "",
        "If the issue returns, open Altitude and ask for help again. If the approved steps do not resolve it, you can create a new IT ticket.",
        "",
        "Altitude IT Support",
    ]
    text_body = "\n".join(text_lines)

    resolution_html = "<br>".join(escape(line) for line in resolution.split("\n"))
    html_body = f"""<!doctype html>
<html>
<body style="margin:0;padding:0;background:#F4F6F8;font-family:Arial,Helvetica,sans-serif;color:#1F2937;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#F4F6F8;padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:680px;background:#FFFFFF;border:1px solid #E5E7EB;border-radius:12px;overflow:hidden;">
        <tr>
          <td style="background:#002B4F;padding:22px 28px;color:#FFFFFF;">
            <div style="font-size:22px;font-weight:700;">Altitude IT Support</div>
            <div style="font-size:14px;margin-top:4px;color:#DCEBFA;">Resolution details</div>
          </td>
        </tr>
        <tr>
          <td style="padding:28px;">
            <p style="margin:0 0 18px 0;font-size:16px;line-height:1.6;">Your IT support ticket has been resolved.</p>
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:20px;">
              <tr><td style="padding:5px 0;color:#6B7280;width:90px;">Ticket</td><td style="padding:5px 0;font-weight:600;">{escape(display_reference)}</td></tr>
              <tr><td style="padding:5px 0;color:#6B7280;">Issue</td><td style="padding:5px 0;">{escape(title)}</td></tr>
              <tr><td style="padding:5px 0;color:#6B7280;">Status</td><td style="padding:5px 0;">{escape(status)}</td></tr>
            </table>
            <div style="background:#F4F6F8;border-left:4px solid #2563EB;border-radius:8px;padding:18px 20px;">
              <div style="font-size:16px;font-weight:700;margin-bottom:9px;">How it was resolved</div>
              <div style="font-size:15px;line-height:1.65;">{resolution_html}</div>
            </div>
            <p style="margin:20px 0 0 0;font-size:14px;line-height:1.6;color:#6B7280;">If the issue returns, open Altitude and ask for help again. If the approved steps do not resolve it, you can create a new IT ticket.</p>
          </td>
        </tr>
        <tr><td style="height:5px;background:#FFC107;"></td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    return subject, text_body, html_body


def send_resolution_email(
    ticket: dict[str, Any],
    *,
    config: ResolutionEmailConfig | None = None,
) -> None:
    """Send one resolved-ticket follow-up email using Altitude SMTP settings."""
    config = config or ResolutionEmailConfig.from_environment()
    if not config.enabled:
        raise ResolutionEmailConfigurationError(
            "Altitude resolution email is disabled"
        )

    recipient = _clean_single_line(
        ticket.get("contact_email"), maximum_length=254
    ).lower()
    if not is_authorized_school_email(recipient):
        raise ValueError(
            "Resolution email recipient must be an authorized school email"
        )

    subject, text_body, html_body = build_resolution_email(ticket)
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((config.from_name, config.from_email))
    message["To"] = recipient
    if config.reply_to:
        message["Reply-To"] = config.reply_to
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    smtp_class = smtplib.SMTP_SSL if config.use_ssl else smtplib.SMTP
    with smtp_class(
        config.host,
        config.port,
        timeout=config.timeout_seconds,
    ) as smtp:
        if not config.use_ssl and config.use_tls:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
        if config.username:
            smtp.login(config.username, config.password)
        smtp.send_message(message)


def process_pending_resolution_notifications(
    *,
    limit: int = 250,
) -> dict[str, Any]:
    """Send unsent resolution-detail emails and safely record their outcome."""
    tickets = get_tickets_pending_resolution_email(limit=limit)
    result: dict[str, Any] = {
        "eligible": len(tickets),
        "sent": 0,
        "failed": 0,
        "disabled": False,
        "configuration_error": None,
    }
    if not tickets:
        return result

    try:
        config = ResolutionEmailConfig.from_environment()
    except ResolutionEmailConfigurationError as error:
        result["configuration_error"] = str(error)
        return result

    if not config.enabled:
        result["disabled"] = True
        return result

    for ticket in tickets:
        local_ticket_id = int(ticket["local_ticket_id"])
        try:
            send_resolution_email(ticket, config=config)
        except Exception as error:
            mark_resolution_email_error(
                local_ticket_id,
                f"{type(error).__name__}: {error}",
            )
            result["failed"] += 1
            continue
        mark_resolution_email_sent(local_ticket_id)
        result["sent"] += 1

    return result
