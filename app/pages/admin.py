from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from html import escape
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import streamlit as st

try:
    from streamlit_cookies_controller import CookieController
except ImportError:  # The dashboard still works, but refresh persistence is disabled.
    CookieController = None  # type: ignore[assignment,misc]

from core.admin_auth import (
    authenticate_admin,
    get_admin_auth_fingerprint,
    get_admin_configuration_error,
    get_admin_identity,
    get_configured_admin_username,
    is_admin_authenticated,
    logout_admin,
    set_admin_authenticated,
)
from core.analytics_db import (
    apply_ticket_status_updates,
    create_announcement,
    delete_announcement,
    get_announcement_summary,
    get_database_health,
    get_feedback_filter_options,
    get_feedback_summary,
    get_knowledge_queue_summary,
    get_recent_knowledge_gaps,
    get_security_summary,
    get_ticket_summary,
    get_tickets_for_status_sync,
    initialize_database,
    list_announcements,
    list_feedback_records,
    list_knowledge_drafts,
    list_security_findings,
    list_ticket_audits,
    record_ticket_status_sync_error,
    set_announcement_active,
    update_announcement,
    update_knowledge_draft,
    update_security_finding_review,
)
from core.knowledge_queue import (
    publish_knowledge_draft,
    reject_knowledge_draft,
    sync_resolved_tickets_to_knowledge_queue,
)
from core.resolution_notifications import process_pending_resolution_notifications
from core.system_health import run_system_health_checks
from core.time_utils import get_local_timezone, local_now
from core.ticketing_client import TicketingClientError, fetch_ticket_statuses
from ui.layout import image_data_uri


ADMIN_STYLES_FILE = Path(__file__).resolve().parents[1] / "ui" / "admin_styles.css"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCK_SECONDS = 30
ADMIN_SESSION_COOKIE = "sjk_altitude_admin_session"
ADMIN_SESSION_LIFETIME = timedelta(days=7)
ADMIN_SESSION_SECRET_FILE = PROJECT_ROOT / "data" / ".admin_session_secret"

ADMIN_SECTIONS: tuple[tuple[str, str], ...] = (
    ("Overview", "overview"),
    ("Feedback", "feedback"),
    ("Tickets", "tickets"),
    ("Security", "security"),
    ("Knowledge Queue", "knowledge"),
    ("Announcements", "announcements"),
    ("System Health", "health"),
)

SECTION_DESCRIPTIONS: dict[str, str] = {
    "overview": (
        "Monitor support activity, user feedback, ticket volume and the "
        "knowledge-review pipeline."
    ),
    "feedback": (
        "Review satisfaction results and identify responses that may need "
        "better support documentation."
    ),
    "tickets": (
        "Track tickets created by Altitude and synchronize their live status."
    ),
    "security": (
        "Review non-school email attempts and high-confidence chatbot misuse flags."
    ),
    "knowledge": (
        "Review resolved-ticket drafts before publishing them to the approved "
        "knowledge base."
    ),
    "announcements": (
        "Create and schedule notices that will appear in the support interface."
    ),
    "health": (
        "Check the status of Altitude data stores and connected services."
    ),
}


def _load_admin_styles() -> None:
    """Load CSS used only by the administrator portal."""
    if ADMIN_STYLES_FILE.exists():
        st.html(ADMIN_STYLES_FILE)


def _get_time_greeting() -> str:
    hour = local_now().hour

    if hour < 12:
        return "Good Morning"

    if hour < 17:
        return "Good Afternoon"

    return "Good Evening"



def _urlsafe_encode(value: bytes) -> str:
    """Return URL-safe base64 without padding."""
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _urlsafe_decode(value: str) -> bytes:
    """Decode URL-safe base64 with restored padding."""
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


@st.cache_resource(show_spinner=False)
def _get_admin_session_secret() -> bytes:
    """Load a stable secret used to sign persistent admin sessions."""
    for environment_name in (
        "ALTITUDE_ADMIN_SESSION_SECRET",
        "ADMIN_SESSION_SECRET",
    ):
        configured_secret = os.getenv(environment_name, "").strip()
        if configured_secret:
            return configured_secret.encode("utf-8")

    try:
        for secret_name in (
            "ALTITUDE_ADMIN_SESSION_SECRET",
            "ADMIN_SESSION_SECRET",
        ):
            configured_secret = str(st.secrets.get(secret_name, "")).strip()
            if configured_secret:
                return configured_secret.encode("utf-8")
    except (FileNotFoundError, KeyError, TypeError):
        pass

    # Local/on-prem fallback: create one private secret and reuse it across
    # Streamlit restarts. Do not commit this generated file to source control.
    ADMIN_SESSION_SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)

    if ADMIN_SESSION_SECRET_FILE.exists():
        saved_secret = ADMIN_SESSION_SECRET_FILE.read_text(encoding="utf-8").strip()
        if saved_secret:
            return saved_secret.encode("utf-8")

    generated_secret = secrets.token_urlsafe(48)
    ADMIN_SESSION_SECRET_FILE.write_text(generated_secret, encoding="utf-8")

    try:
        ADMIN_SESSION_SECRET_FILE.chmod(0o600)
    except OSError:
        pass

    return generated_secret.encode("utf-8")


def _create_admin_session_token(username: str) -> str:
    """Create a signed, expiring browser-session token."""
    expires_at = int((datetime.now(timezone.utc) + ADMIN_SESSION_LIFETIME).timestamp())
    canonical_username = get_configured_admin_username() or username.strip()
    payload = json.dumps(
        {
            "username": canonical_username,
            "expires_at": expires_at,
            "auth_fingerprint": get_admin_auth_fingerprint(),
            "version": 2,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    encoded_payload = _urlsafe_encode(payload)
    signature = hmac.new(
        _get_admin_session_secret(),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{encoded_payload}.{_urlsafe_encode(signature)}"


def _validate_admin_session_token(token: str | None) -> str | None:
    """Return the authenticated username when a signed token is valid."""
    if not token or "." not in token:
        return None

    encoded_payload, encoded_signature = token.split(".", 1)

    try:
        supplied_signature = _urlsafe_decode(encoded_signature)
        expected_signature = hmac.new(
            _get_admin_session_secret(),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()

        if not hmac.compare_digest(supplied_signature, expected_signature):
            return None

        payload = json.loads(_urlsafe_decode(encoded_payload).decode("utf-8"))
        username = str(payload.get("username", "")).strip()
        expires_at = int(payload.get("expires_at", 0))
        token_version = int(payload.get("version", 0))
        auth_fingerprint = str(payload.get("auth_fingerprint", "")).strip()
    except (ValueError, TypeError, json.JSONDecodeError):
        return None

    if (
        not username
        or token_version != 2
        or expires_at <= int(datetime.now(timezone.utc).timestamp())
    ):
        return None

    configured_username = get_configured_admin_username()
    if configured_username and not hmac.compare_digest(
        username.casefold(),
        configured_username.casefold(),
    ):
        return None

    expected_fingerprint = get_admin_auth_fingerprint()
    if not auth_fingerprint or not hmac.compare_digest(
        auth_fingerprint,
        expected_fingerprint,
    ):
        return None

    return configured_username or username


def _create_cookie_controller() -> Any | None:
    """Create one cookie controller for the current Streamlit rerun."""
    if CookieController is None:
        return None

    try:
        return CookieController(key="sjk_admin_cookie_controller")
    except Exception as error:
        print(
            "Admin cookie controller failed: "
            f"{type(error).__name__}: {error}"
        )
        return None


def _read_admin_session_cookie(cookie_controller: Any | None) -> str | None:
    """Read the persistent token from the initial request or component cache."""
    try:
        context_token = st.context.cookies.get(ADMIN_SESSION_COOKIE)
        if context_token:
            return str(context_token)
    except (AttributeError, KeyError, TypeError):
        pass

    if cookie_controller is None:
        return None

    try:
        component_token = cookie_controller.get(ADMIN_SESSION_COOKIE)
    except Exception as error:
        print(
            "Admin cookie read failed: "
            f"{type(error).__name__}: {error}"
        )
        return None

    return str(component_token) if component_token else None


def _restore_admin_session(cookie_controller: Any | None) -> None:
    """Restore server-side authentication from a valid signed cookie."""
    if is_admin_authenticated():
        return

    username = _validate_admin_session_token(
        _read_admin_session_cookie(cookie_controller)
    )
    if username:
        set_admin_authenticated(username)


def _save_admin_session(cookie_controller: Any | None, username: str) -> bool:
    """Persist a signed login token in the current browser."""
    if cookie_controller is None:
        return False

    try:
        cookie_controller.set(
            ADMIN_SESSION_COOKIE,
            _create_admin_session_token(username),
            path="/",
            expires=datetime.now(timezone.utc) + ADMIN_SESSION_LIFETIME,
            max_age=int(ADMIN_SESSION_LIFETIME.total_seconds()),
            same_site="lax",
        )
        return True
    except Exception as error:
        print(
            "Admin cookie save failed: "
            f"{type(error).__name__}: {error}"
        )
        return False


def _clear_admin_session_cookie(cookie_controller: Any | None) -> None:
    """Remove the persistent login token from the browser."""
    if cookie_controller is None:
        return

    try:
        cookie_controller.remove(
            ADMIN_SESSION_COOKIE,
            path="/",
            same_site="lax",
        )
    except (KeyError, ValueError):
        pass
    except Exception as error:
        print(
            "Admin cookie removal failed: "
            f"{type(error).__name__}: {error}"
        )


def _render_admin_login() -> str | None:
    """Render sign-in and return the username after a successful login.

    The caller persists the browser cookie after the login placeholder has
    been cleared. This avoids calling ``st.rerun()`` immediately after the
    cookie component is mounted, which could cancel the browser-side write.
    """
    crest_uri = image_data_uri("sjk_crest.png")
    configured_username = get_configured_admin_username()
    configuration_error = get_admin_configuration_error()

    locked_until = float(st.session_state.get("admin_locked_until", 0.0))
    now = time.time()
    remaining_lock_seconds = max(0, int(locked_until - now))

    if remaining_lock_seconds == 0 and locked_until:
        st.session_state.pop("admin_locked_until", None)
        st.session_state["admin_failed_login_attempts"] = 0

    crest_html = (
        f'<img src="{crest_uri}" class="sjk-admin-login-crest" alt="SJK">'
        if crest_uri
        else '<div class="sjk-admin-login-crest-fallback">SJK</div>'
    )

    with st.container(key="admin_login_page", border=False):
        with st.container(key="admin_login_card", border=False):
            st.html(
                f"""
<div class="sjk-admin-login-heading">
    {crest_html}
    <div>
        <div class="sjk-admin-login-eyebrow">ALTITUDE ADMIN</div>
        <h1>IT Control Center</h1>
        <p>Secure access for authorized SJK IT staff.</p>
    </div>
</div>
"""
            )

            if configuration_error:
                st.error(configuration_error)
                st.code(
                    "PYTHONPATH=app python scripts/generate_admin_password.py",
                    language="bash",
                )
                return

            if remaining_lock_seconds > 0:
                st.warning(
                    "Too many unsuccessful attempts. "
                    f"Try again in approximately {remaining_lock_seconds} seconds."
                )

            with st.form("admin_login_form", clear_on_submit=False):
                username = st.text_input(
                    "Username",
                    value=configured_username,
                    autocomplete="username",
                    disabled=remaining_lock_seconds > 0,
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    autocomplete="current-password",
                    disabled=remaining_lock_seconds > 0,
                )
                submitted = st.form_submit_button(
                    "Sign in",
                    type="primary",
                    width="stretch",
                    disabled=remaining_lock_seconds > 0,
                )

            st.caption(
                "Administrator credentials are separate from the "
                "ticketing-service account."
            )

            if not submitted:
                return

            if authenticate_admin(username, password):
                clean_username = get_configured_admin_username()
                set_admin_authenticated(clean_username)
                st.session_state["admin_failed_login_attempts"] = 0
                st.session_state.pop("admin_locked_until", None)
                return clean_username

            failed_attempts = int(
                st.session_state.get("admin_failed_login_attempts", 0)
            ) + 1
            st.session_state["admin_failed_login_attempts"] = failed_attempts

            if failed_attempts >= MAX_LOGIN_ATTEMPTS:
                st.session_state["admin_locked_until"] = (
                    time.time() + LOGIN_LOCK_SECONDS
                )
                st.error(
                    "Too many unsuccessful attempts. "
                    "Sign-in is temporarily locked."
                )
            else:
                attempts_remaining = MAX_LOGIN_ATTEMPTS - failed_attempts
                st.error(
                    "The username or password is incorrect. "
                    f"{attempts_remaining} attempts remaining."
                )

            return None


def _safe_admin_summary() -> dict[str, Any]:
    """Return available overview metrics without breaking the dashboard."""
    summary: dict[str, Any] = {
        "conversation_count": 0,
        "message_count": 0,
        "total_votes": 0,
        "helpful_votes": 0,
        "not_helpful_votes": 0,
        "helpful_rate": 0.0,
        "eligible_responses": 0,
        "feedback_coverage": 0.0,
        "database_status": "Unavailable",
    }

    try:
        initialize_database()
        health = get_database_health()
        feedback = get_feedback_summary()
    except Exception as error:
        print(
            "Admin overview metrics failed: "
            f"{type(error).__name__}: {error}"
        )
        return summary

    summary.update(health)
    summary.update(feedback)
    summary["database_status"] = (
        "Healthy" if health.get("quick_check") == "ok" else "Attention"
    )
    return summary


def _metric_card(
    label: str,
    value: str,
    detail: str,
    *,
    tone: str = "blue",
) -> str:
    """Return one branded metric card without decorative emoji."""
    return f"""
<article class="sjk-admin-metric sjk-admin-metric-{escape(tone)}">
    <span class="sjk-admin-metric-label">{escape(label)}</span>
    <strong>{escape(value)}</strong>
    <span class="sjk-admin-metric-detail">{escape(detail)}</span>
</article>
"""


def _dashboard_panel_html(
    *,
    title: str,
    badge: str,
    body: str,
    empty_label: str,
) -> str:
    """Return one overview panel for the responsive dashboard grid."""
    return f"""
<section class="sjk-admin-dashboard-panel">
    <div class="sjk-admin-dashboard-panel-heading">
        <h3>{escape(title)}</h3>
        <span class="sjk-admin-panel-badge">{escape(badge)}</span>
    </div>
    <p>{escape(body)}</p>
    <div class="sjk-admin-empty-state">{escape(empty_label)}</div>
</section>
"""




def _format_feedback_datetime(value: str | None) -> str:
    """Format a stored UTC feedback timestamp in local server time."""
    if not value:
        return "Unknown"

    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(_local_timezone()).strftime("%b %d, %Y %I:%M %p")


def _short_text(value: Any, maximum: int = 110) -> str:
    """Return compact single-line text for dashboard summaries."""
    clean_value = " ".join(str(value or "").split())

    if not clean_value:
        return "Not available"

    if len(clean_value) <= maximum:
        return clean_value

    return clean_value[: maximum - 1].rstrip() + "…"


def _source_display_name(value: Any) -> str:
    """Return a short source label without exposing local file paths."""
    clean_value = str(value or "").strip()

    if not clean_value:
        return "Not recorded"

    return Path(clean_value).name


def _safe_recent_knowledge_gaps(limit: int = 4) -> list[dict[str, Any]]:
    """Load recent negative-feedback rows without breaking Overview."""
    try:
        return get_recent_knowledge_gaps(limit=limit)
    except Exception as error:
        print(
            "Recent knowledge gaps failed: "
            f"{type(error).__name__}: {error}"
        )
        return []


def _knowledge_gap_panel_html(records: list[dict[str, Any]]) -> str:
    """Return the live Recent Knowledge Gaps overview panel."""
    if not records:
        content = (
            '<div class="sjk-admin-empty-state">'
            "No Not Helpful feedback has been submitted yet"
            "</div>"
        )
    else:
        rows: list[str] = []

        for record in records:
            question = _short_text(record.get("user_question"), 95)
            reason = str(record.get("reason") or "No reason provided")
            created_at = _format_feedback_datetime(
                str(record.get("feedback_created_at") or "")
            )
            rows.append(
                f"""
<article class="sjk-admin-gap-row">
    <div>
        <strong>{escape(question)}</strong>
        <span>{escape(reason)}</span>
    </div>
    <time>{escape(created_at)}</time>
</article>
"""
            )

        content = (
            '<div class="sjk-admin-gap-list">'
            + "".join(rows)
            + "</div>"
        )

    return f"""
<section class="sjk-admin-dashboard-panel">
    <div class="sjk-admin-dashboard-panel-heading">
        <h3>Recent Knowledge Gaps</h3>
        <span class="sjk-admin-panel-badge">Live</span>
    </div>
    <p>Latest Not Helpful responses that may need documentation review.</p>
    {content}
</section>
"""




TICKET_CATEGORY_LABELS_ADMIN: dict[str, str] = {
    "Wifi-Network": "Wifi / Network",
    "AudioVideo": "Audio / Video",
    "GoogleApps": "Google Apps",
    "OnSJK": "onSJK",
    "Reset_Password": "Reset Password",
    "DeviceHardwareIssue": "Device / Hardware Issue",
    "AirplayScreenMirror": "Airplay / Screen Mirror",
    "Other": "Other",
}


def _ticket_category_label(value: Any) -> str:
    """Return a readable category label for one local ticket record."""
    clean_value = str(value or "").strip()
    return TICKET_CATEGORY_LABELS_ADMIN.get(clean_value, clean_value or "Unknown")


def _safe_ticket_summary() -> dict[str, int]:
    """Load ticket totals without allowing an audit error to break Admin."""
    empty_summary = {
        "total_tickets": 0,
        "open_tickets": 0,
        "in_progress_tickets": 0,
        "closed_tickets": 0,
        "pending_sync_tickets": 0,
    }

    try:
        initialize_database()
        return get_ticket_summary()
    except Exception as error:
        print(
            "Admin ticket summary failed: "
            f"{type(error).__name__}: {error}"
        )
        return empty_summary


def _safe_ticket_rows(limit: int = 250) -> list[dict[str, Any]]:
    """Load recent local ticket audits without breaking the dashboard."""
    try:
        initialize_database()
        return list_ticket_audits(limit=limit)
    except Exception as error:
        print(
            "Admin ticket records failed: "
            f"{type(error).__name__}: {error}"
        )
        return []


def _safe_knowledge_summary() -> dict[str, int]:
    """Load knowledge queue totals without breaking the administrator page."""
    empty_summary = {
        "total": 0,
        "pending": 0,
        "approved": 0,
        "rejected": 0,
    }
    try:
        initialize_database()
        return get_knowledge_queue_summary()
    except Exception as error:
        print(
            "Admin knowledge summary failed: "
            f"{type(error).__name__}: {error}"
        )
        return empty_summary


def _safe_knowledge_rows(
    *,
    review_status: str | None = None,
    limit: int = 250,
) -> list[dict[str, Any]]:
    """Load knowledge drafts safely for the administrator review screen."""
    try:
        initialize_database()
        return list_knowledge_drafts(
            review_status=review_status,
            limit=limit,
        )
    except Exception as error:
        print(
            "Admin knowledge records failed: "
            f"{type(error).__name__}: {error}"
        )
        return []


def _synchronize_ticket_statuses() -> tuple[int, int]:
    """Fetch current Django ticket statuses and update local audit rows."""
    initialize_database()
    local_tickets = get_tickets_for_status_sync(limit=1_000)
    if not local_tickets:
        st.session_state["admin_ticket_last_sync"] = datetime.now(
            timezone.utc
        ).isoformat(timespec="seconds")
        return 0, 0

    try:
        remote_matches = fetch_ticket_statuses(local_tickets)
    except (TicketingClientError, ValueError) as error:
        record_ticket_status_sync_error(str(error))
        raise

    updates = [
        {
            "local_ticket_id": match.local_ticket_id,
            "status": match.status,
            "external_ticket_id": match.external_ticket_id,
            "remote_ticket_url": match.remote_ticket_url,
            "resolution_comment": match.resolution_comment,
        }
        for match in remote_matches
    ]
    updated_count = apply_ticket_status_updates(updates)
    sync_resolved_tickets_to_knowledge_queue(limit=1_000)
    email_result = process_pending_resolution_notifications(limit=1_000)
    st.session_state["admin_resolution_email_last_sent_count"] = int(
        email_result.get("sent", 0)
    )
    st.session_state["admin_resolution_email_last_failed_count"] = int(
        email_result.get("failed", 0)
    )
    st.session_state["admin_resolution_email_disabled"] = bool(
        email_result.get("disabled", False)
    )
    st.session_state["admin_resolution_email_config_error"] = (
        email_result.get("configuration_error")
    )
    st.session_state["admin_ticket_last_sync"] = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")
    st.session_state["admin_ticket_last_sync_count"] = updated_count
    return updated_count, len(local_tickets)


def _format_ticket_sync_time() -> str:
    value = st.session_state.get("admin_ticket_last_sync")
    if not value:
        return "Not synchronized in this admin session"
    return _format_feedback_datetime(str(value))


def _auto_sync_ticket_statuses() -> None:
    """Synchronize once when Tickets opens, then at most every five minutes."""
    last_attempt = float(
        st.session_state.get("admin_ticket_sync_attempt_epoch", 0.0)
    )
    if time.time() - last_attempt < 300:
        return

    st.session_state["admin_ticket_sync_attempt_epoch"] = time.time()
    try:
        _synchronize_ticket_statuses()
        st.session_state.pop("admin_ticket_sync_error", None)
    except Exception as error:
        print(
            "Ticket status synchronization failed: "
            f"{type(error).__name__}: {error}"
        )
        st.session_state["admin_ticket_sync_error"] = str(error)


def _ticket_status_class(value: Any) -> str:
    """Return a safe CSS class suffix for a local ticket status."""
    status = str(value or "Unknown").strip().lower()
    return {
        "open": "open",
        "new": "open",
        "pending": "open",
        "in progress": "in-progress",
        "in-progress": "in-progress",
        "working": "in-progress",
        "assigned": "in-progress",
        "processing": "in-progress",
        "reopened": "in-progress",
        "closed": "closed",
        "resolved": "closed",
        "completed": "closed",
        "complete": "closed",
        "cancelled": "cancelled",
        "canceled": "cancelled",
        "submitting": "pending",
    }.get(status, "other")


def _recent_tickets_panel_html(records: list[dict[str, Any]]) -> str:
    """Return the Overview card containing recently created AI tickets."""
    visible_records = records[:4]

    if not visible_records:
        content = (
            '<div class="sjk-admin-empty-state">'
            "No tickets have been created by Altitude yet"
            "</div>"
        )
    else:
        rows: list[str] = []
        for record in visible_records:
            status = str(record.get("status") or "Unknown")
            title = _short_text(record.get("title"), 78)
            requester = str(record.get("contact_email") or "Not recorded")
            created_at = _format_feedback_datetime(
                str(record.get("created_at") or "")
            )
            rows.append(
                f"""
<article class="sjk-admin-ticket-preview-row">
    <div>
        <strong>{escape(title)}</strong>
        <span>{escape(requester)}</span>
    </div>
    <div class="sjk-admin-ticket-preview-meta">
        <span class="sjk-admin-ticket-status sjk-admin-ticket-status-{_ticket_status_class(status)}">
            {escape(status)}
        </span>
        <time>{escape(created_at)}</time>
    </div>
</article>
"""
            )

        content = (
            '<div class="sjk-admin-ticket-preview-list">'
            + "".join(rows)
            + "</div>"
        )

    return f"""
<section class="sjk-admin-dashboard-panel sjk-admin-recent-tickets-panel">
    <div class="sjk-admin-dashboard-panel-heading">
        <h3>Recent AI Tickets</h3>
        <span class="sjk-admin-panel-badge">Live</span>
    </div>
    <p>Latest ticket submissions created through the Altitude chat.</p>
    {content}
</section>
"""


def _overview_announcements_panel_html() -> str:
    """Return the Overview card containing currently active announcements."""
    try:
        announcements = list_announcements(include_inactive=True)
    except Exception as error:
        print(
            "Admin overview announcements failed: "
            f"{type(error).__name__}: {error}"
        )
        announcements = []

    active_announcements: list[dict[str, Any]] = []

    for announcement in announcements:
        status_label, _ = _announcement_status(announcement)
        if status_label == "Active":
            active_announcements.append(announcement)

    visible_announcements = active_announcements[:3]

    if visible_announcements:
        announcement_items = []

        for announcement in visible_announcements:
            severity = str(announcement.get("severity", "info"))
            severity_label = ANNOUNCEMENT_TYPE_LABELS.get(
                severity,
                "Information",
            )
            title = escape(
                str(announcement.get("title", "Announcement"))
            )
            message = escape(str(announcement.get("message", "")))

            announcement_items.append(
                f"""
<article class="sjk-admin-overview-announcement sjk-admin-overview-announcement-{escape(severity)}">
    <div class="sjk-admin-overview-announcement-heading">
        <span>{escape(severity_label)}</span>
        <strong>{title}</strong>
    </div>
    <p>{message}</p>
</article>
"""
            )

        remaining_count = len(active_announcements) - len(visible_announcements)
        more_label = (
            f'<div class="sjk-admin-overview-announcement-more">'
            f'+{remaining_count} more active announcement'
            f'{"s" if remaining_count != 1 else ""}</div>'
            if remaining_count > 0
            else ""
        )

        content_html = (
            '<div class="sjk-admin-overview-announcement-list">'
            + "".join(announcement_items)
            + more_label
            + "</div>"
        )
    else:
        content_html = (
            '<div class="sjk-admin-empty-state">'
            "No active announcements right now"
            "</div>"
        )

    badge = (
        f"{len(active_announcements)} Active"
        if active_announcements
        else "None Active"
    )

    return f"""
<section class="sjk-admin-dashboard-panel sjk-admin-overview-announcements-panel">
    <div class="sjk-admin-dashboard-panel-heading">
        <h3>Active Announcements</h3>
        <span class="sjk-admin-panel-badge">{escape(badge)}</span>
    </div>
    <p>Notices currently visible in the chatbot's Announcements panel.</p>
    {content_html}
</section>
"""


def _render_overview() -> None:
    summary = _safe_admin_summary()
    ticket_summary = _safe_ticket_summary()
    knowledge_summary = _safe_knowledge_summary()
    recent_tickets = _safe_ticket_rows(limit=4)
    helpful_rate = float(summary.get("helpful_rate", 0.0))
    coverage = float(summary.get("feedback_coverage", 0.0))
    knowledge_gaps = _safe_recent_knowledge_gaps(limit=4)

    st.html(
        "".join(
            (
                '<div class="sjk-admin-metric-grid">',
                _metric_card(
                    "Conversations",
                    f"{int(summary.get('conversation_count', 0)):,}",
                    "Logged support sessions",
                ),
                _metric_card(
                    "Helpful Rate",
                    f"{helpful_rate:.1f}%",
                    (
                        f"{int(summary.get('total_votes', 0)):,} votes · "
                        f"{coverage:.1f}% coverage"
                    ),
                    tone="green",
                ),
                _metric_card(
                    "AI Tickets",
                    f"{int(ticket_summary.get('total_tickets', 0)):,}",
                    (
                        f"{int(ticket_summary.get('open_tickets', 0)):,} open · "
                        f"{int(ticket_summary.get('closed_tickets', 0)):,} closed"
                    ),
                    tone="gold",
                ),
                _metric_card(
                    "Pending Knowledge",
                    f"{int(knowledge_summary.get('pending', 0)):,}",
                    (
                        f"{int(knowledge_summary.get('approved', 0)):,} approved · "
                        f"{int(knowledge_summary.get('rejected', 0)):,} rejected"
                    ),
                    tone="purple",
                ),
                "</div>",
            )
        )
    )

    st.html(
        "".join(
            (
                '<div class="sjk-admin-panel-grid">',
                _knowledge_gap_panel_html(knowledge_gaps),
                _dashboard_panel_html(
                    title="Pending Knowledge Reviews",
                    badge="Live",
                    body=(
                        "Resolved-ticket notes are converted into editable "
                        "drafts and held for IT approval before they become live."
                    ),
                    empty_label=(
                        "Knowledge queue is empty"
                        if int(knowledge_summary.get("pending", 0)) == 0
                        else f"{int(knowledge_summary.get('pending', 0))} draft(s) awaiting review"
                    ),
                ),
                _recent_tickets_panel_html(recent_tickets),
                _overview_announcements_panel_html(),
                "</div>",
            )
        )
    )


def _render_dashboard_panel(
    *,
    title: str,
    badge: str,
    body: str,
    empty_label: str,
) -> None:
    st.html(
        f"""
<section class="sjk-admin-dashboard-panel">
    <div class="sjk-admin-dashboard-panel-heading">
        <h3>{escape(title)}</h3>
        <span class="sjk-admin-panel-badge">{escape(badge)}</span>
    </div>
    <p>{escape(body)}</p>
    <div class="sjk-admin-empty-state">{escape(empty_label)}</div>
</section>
"""
    )


def _render_placeholder_section(
    *,
    title: str,
    description: str,
    next_feature: str,
) -> None:
    st.html(
        f"""
<section class="sjk-admin-placeholder">
    <div class="sjk-admin-placeholder-marker" aria-hidden="true"></div>
    <div>
        <span class="sjk-admin-placeholder-kicker">{escape(next_feature)}</span>
        <h2>{escape(title)}</h2>
        <p>{escape(description)}</p>
    </div>
</section>
"""
    )


def _render_feedback_section() -> None:
    feedback = _safe_admin_summary()
    helpful_rate = float(feedback.get("helpful_rate", 0.0))

    st.html(
        "".join(
            (
                '<div class="sjk-admin-metric-grid sjk-admin-metric-grid-three">',
                _metric_card(
                    "Helpful",
                    f"{int(feedback.get('helpful_votes', 0)):,}",
                    "Positive responses",
                    tone="green",
                ),
                _metric_card(
                    "Not Helpful",
                    f"{int(feedback.get('not_helpful_votes', 0)):,}",
                    "Potential knowledge gaps",
                    tone="red",
                ),
                _metric_card(
                    "Helpful Rate",
                    f"{helpful_rate:.1f}%",
                    f"{int(feedback.get('total_votes', 0)):,} submitted votes",
                ),
                "</div>",
            )
        )
    )

    try:
        filter_options = get_feedback_filter_options()
    except Exception as error:
        print(
            "Feedback filter options failed: "
            f"{type(error).__name__}: {error}"
        )
        filter_options = {"reasons": [], "platforms": [], "sources": []}

    with st.container(key="admin_feedback_filters", border=False):
        st.html(
            """
<div class="sjk-admin-feedback-heading">
    <div>
        <span>Feedback records</span>
        <h2>Feedback and Knowledge Gaps</h2>
        <p>Search and filter the responses rated by chatbot users.</p>
    </div>
</div>
"""
        )

        search_column, vote_column = st.columns([2.4, 1.0], gap="small")
        with search_column:
            search_value = st.text_input(
                "Search",
                key="admin_feedback_search",
                placeholder="Search questions, answers, reasons or comments",
            )
        with vote_column:
            vote_value = st.selectbox(
                "Vote",
                options=("All", "Helpful", "Not Helpful"),
                key="admin_feedback_vote",
            )

        reason_column, platform_column, source_column = st.columns(
            3,
            gap="small",
        )
        with reason_column:
            reason_value = st.selectbox(
                "Reason",
                options=("All", *filter_options.get("reasons", [])),
                key="admin_feedback_reason",
            )
        with platform_column:
            platform_value = st.selectbox(
                "Platform",
                options=("All", *filter_options.get("platforms", [])),
                key="admin_feedback_platform",
            )
        with source_column:
            source_options = ["All", *filter_options.get("sources", [])]
            source_value = st.selectbox(
                "Source",
                options=source_options,
                format_func=(
                    lambda value: value
                    if value == "All"
                    else _source_display_name(value)
                ),
                key="admin_feedback_source",
            )

    helpful_filter: bool | None
    if vote_value == "Helpful":
        helpful_filter = True
    elif vote_value == "Not Helpful":
        helpful_filter = False
    else:
        helpful_filter = None

    try:
        records = list_feedback_records(
            helpful=helpful_filter,
            search=search_value,
            reason=None if reason_value == "All" else reason_value,
            platform=None if platform_value == "All" else platform_value,
            source_document=None if source_value == "All" else source_value,
            limit=1_000,
        )
    except Exception as error:
        print(
            "Feedback table load failed: "
            f"{type(error).__name__}: {error}"
        )
        records = []
        st.error("Feedback records could not be loaded from the database.")

    with st.container(key="admin_feedback_table_panel", border=False):
        st.caption(
            f"Showing {len(records):,} feedback "
            + ("record" if len(records) == 1 else "records")
        )

        if not records:
            st.html(
                """
<div class="sjk-admin-empty-state sjk-admin-feedback-empty">
    No feedback records match the selected filters.
</div>
"""
            )
            return

        table_rows = [
            {
                "Date": _format_feedback_datetime(
                    str(record.get("feedback_created_at") or "")
                ),
                "Vote": (
                    "Helpful"
                    if bool(record.get("helpful"))
                    else "Not Helpful"
                ),
                "User question": str(
                    record.get("user_question") or "Not available"
                ),
                "Bot answer": str(
                    record.get("bot_answer") or "Not available"
                ),
                "Reason": str(record.get("reason") or "—"),
                "Comment": str(record.get("comment") or "—"),
                "Platform": str(record.get("platform") or "Not recorded"),
                "Source": _source_display_name(record.get("source_document")),
            }
            for record in records
        ]
        feedback_frame = pd.DataFrame(table_rows)

        st.dataframe(
            feedback_frame,
            hide_index=True,
            width="stretch",
            height=420,
            column_config={
                "Date": st.column_config.TextColumn("Date", width="medium"),
                "Vote": st.column_config.TextColumn("Vote", width="small"),
                "User question": st.column_config.TextColumn(
                    "User question",
                    width="large",
                ),
                "Bot answer": st.column_config.TextColumn(
                    "Bot answer",
                    width="large",
                ),
                "Reason": st.column_config.TextColumn("Reason", width="medium"),
                "Comment": st.column_config.TextColumn(
                    "Comment",
                    width="medium",
                ),
                "Platform": st.column_config.TextColumn(
                    "Platform",
                    width="small",
                ),
                "Source": st.column_config.TextColumn(
                    "Source",
                    width="medium",
                ),
            },
        )


def _render_tickets_section() -> None:
    """Render live ticket statuses synchronized from the Django dashboard."""
    _auto_sync_ticket_statuses()
    ticket_summary = _safe_ticket_summary()
    ticket_rows = _safe_ticket_rows(limit=1_000)

    st.html(
        "".join(
            (
                '<div class="sjk-admin-metric-grid">',
                _metric_card(
                    "Total Tickets",
                    f"{int(ticket_summary.get('total_tickets', 0)):,}",
                    "Tickets accepted by the ticketing system",
                ),
                _metric_card(
                    "Open",
                    f"{int(ticket_summary.get('open_tickets', 0)):,}",
                    "Open or awaiting IT action",
                    tone="green",
                ),
                _metric_card(
                    "In Progress",
                    f"{int(ticket_summary.get('in_progress_tickets', 0)):,}",
                    "Assigned or actively being worked",
                    tone="gold",
                ),
                _metric_card(
                    "Closed",
                    f"{int(ticket_summary.get('closed_tickets', 0)):,}",
                    "Closed or resolved remotely",
                    tone="purple",
                ),
                "</div>",
            )
        )
    )

    with st.container(key="admin_ticket_filters", border=False):
        heading_column, refresh_column, action_column = st.columns(
            [1.0, 0.2, 0.22],
            gap="small",
            vertical_alignment="bottom",
        )

        with heading_column:
            st.html(
                """
<div class="sjk-admin-ticket-heading">
    <span>Live ticket records</span>
    <h2>AI-Created Tickets</h2>
    <p>
        Statuses are synchronized from the authenticated ticketing dashboard.
        A ticket can move from Open to In Progress and then Closed.
    </p>
</div>
"""
            )

        with refresh_column:
            refresh_requested = st.button(
                "Refresh statuses",
                key="admin_refresh_ticket_statuses",
                width="stretch",
            )

        with action_column:
            base_url = os.getenv("TICKETING_BASE_URL", "").strip().rstrip("/")
            dashboard_url = os.getenv("TICKETING_DASHBOARD_URL", "").strip()
            if not dashboard_url and base_url:
                dashboard_url = f"{base_url}/faculty/dashboard/"

            if dashboard_url:
                st.link_button(
                    "Open ticketing system",
                    dashboard_url,
                    width="stretch",
                )

        if refresh_requested:
            st.session_state["admin_ticket_sync_attempt_epoch"] = time.time()
            try:
                with st.spinner("Synchronizing ticket statuses..."):
                    updated_count, total_count = _synchronize_ticket_statuses()
            except Exception as error:
                st.session_state["admin_ticket_sync_error"] = str(error)
                st.error(f"Ticket status synchronization failed: {error}")
            else:
                st.session_state.pop("admin_ticket_sync_error", None)
                st.toast(
                    f"Synchronized {updated_count} of {total_count} tickets."
                )
                st.rerun()

        sync_error = str(
            st.session_state.get("admin_ticket_sync_error", "")
        ).strip()
        if sync_error:
            st.warning(
                "Live status could not be refreshed. Existing local statuses "
                f"are still shown. {sync_error}"
            )

        st.caption(f"Last status check: {_format_ticket_sync_time()}")

        search_column, status_column, priority_column = st.columns(
            [2.0, 1.0, 1.0],
            gap="small",
        )
        with search_column:
            search_value = st.text_input(
                "Search",
                key="admin_ticket_search",
                placeholder="Search title, requester, category or reference",
            )
        with status_column:
            status_options = sorted(
                {
                    str(row.get("status") or "Unknown")
                    for row in ticket_rows
                },
                key=str.casefold,
            )
            status_value = st.selectbox(
                "Status",
                options=("All", *status_options),
                key="admin_ticket_status",
            )
        with priority_column:
            priority_options = sorted(
                {
                    str(row.get("priority") or "Unknown")
                    for row in ticket_rows
                },
                key=str.casefold,
            )
            priority_value = st.selectbox(
                "Priority",
                options=("All", *priority_options),
                key="admin_ticket_priority",
            )

    clean_search = search_value.strip().casefold()
    filtered_rows: list[dict[str, Any]] = []
    for row in ticket_rows:
        if status_value != "All" and str(row.get("status")) != status_value:
            continue
        if priority_value != "All" and str(row.get("priority")) != priority_value:
            continue
        if clean_search:
            searchable = " ".join(
                str(row.get(field) or "")
                for field in (
                    "title",
                    "contact_email",
                    "category",
                    "altitude_reference",
                    "external_ticket_id",
                    "status",
                )
            ).casefold()
            if clean_search not in searchable:
                continue
        filtered_rows.append(row)

    with st.container(key="admin_ticket_table_panel", border=False):
        st.caption(
            f"Showing {len(filtered_rows):,} of {len(ticket_rows):,} ticket "
            + ("record" if len(ticket_rows) == 1 else "records")
        )

        if not filtered_rows:
            st.html(
                """
<div class="sjk-admin-empty-state sjk-admin-ticket-empty">
    No ticket records match the selected filters.
</div>
"""
            )
            return

        table_rows = [
            {
                "Created": _format_feedback_datetime(
                    str(row.get("created_at") or "")
                ),
                "Status": str(row.get("status") or "Unknown"),
                "Title": str(row.get("title") or "Untitled ticket"),
                "Requester": str(
                    row.get("contact_email") or "Not recorded"
                ),
                "Category": _ticket_category_label(row.get("category")),
                "Priority": str(row.get("priority") or "Unknown"),
                "Altitude reference": str(
                    row.get("altitude_reference") or "Pending"
                ),
                "Ticketing ID": str(
                    row.get("external_ticket_id") or "Pending"
                ),
                "Last synced": _format_feedback_datetime(
                    str(row.get("last_synced_at") or "")
                ) if row.get("last_synced_at") else "Not synced",
                "Ticket link": str(row.get("remote_ticket_url") or ""),
            }
            for row in filtered_rows
        ]

        st.dataframe(
            pd.DataFrame(table_rows),
            hide_index=True,
            width="stretch",
            height=440,
            column_config={
                "Created": st.column_config.TextColumn(
                    "Created",
                    width="medium",
                ),
                "Status": st.column_config.TextColumn(
                    "Live status",
                    width="small",
                ),
                "Title": st.column_config.TextColumn(
                    "Title",
                    width="large",
                ),
                "Requester": st.column_config.TextColumn(
                    "Requester",
                    width="medium",
                ),
                "Category": st.column_config.TextColumn(
                    "Category",
                    width="medium",
                ),
                "Priority": st.column_config.TextColumn(
                    "Priority",
                    width="small",
                ),
                "Reference": st.column_config.TextColumn(
                    "Reference",
                    width="small",
                ),
                "Last synced": st.column_config.TextColumn(
                    "Last synced",
                    width="medium",
                ),
                "Ticket link": st.column_config.LinkColumn(
                    "Open",
                    display_text="View ticket",
                    width="small",
                ),
            },
        )



def _safe_security_summary() -> dict[str, int]:
    """Load Security-page counts without breaking the admin portal."""
    empty = {
        "total_findings": 0,
        "open_findings": 0,
        "unauthorized_email_findings": 0,
        "misuse_findings": 0,
        "high_severity_findings": 0,
    }
    try:
        initialize_database()
        return get_security_summary()
    except Exception as error:
        print(
            "Admin security summary failed: "
            f"{type(error).__name__}: {error}"
        )
        return empty


def _safe_security_rows(limit: int = 1_000) -> list[dict[str, Any]]:
    """Load security findings without breaking the admin portal."""
    try:
        initialize_database()
        return list_security_findings(limit=limit)
    except Exception as error:
        print(
            "Admin security findings failed: "
            f"{type(error).__name__}: {error}"
        )
        return []


def _security_actor_label(row: dict[str, Any]) -> str:
    actor = str(row.get("actor") or "Not recorded")
    if str(row.get("finding_id", "")).startswith("event:") and len(actor) > 18:
        return f"Session {actor[:8]}…"
    return actor


def _render_security_section() -> None:
    """Render unauthorized-email and misuse findings for IT review."""
    summary = _safe_security_summary()
    findings = _safe_security_rows(limit=1_000)

    st.html(
        "".join(
            (
                '<div class="sjk-admin-metric-grid">',
                _metric_card(
                    "Open Flags",
                    f"{int(summary.get('open_findings', 0)):,}",
                    "Findings waiting for IT review",
                    tone="red",
                ),
                _metric_card(
                    "Unauthorized Emails",
                    f"{int(summary.get('unauthorized_email_findings', 0)):,}",
                    "Non-school addresses used in escalation",
                    tone="gold",
                ),
                _metric_card(
                    "Misuse Signals",
                    f"{int(summary.get('misuse_findings', 0)):,}",
                    "High-confidence abuse or bypass patterns",
                ),
                _metric_card(
                    "High Severity",
                    f"{int(summary.get('high_severity_findings', 0)):,}",
                    "Open High or Critical findings",
                    tone="purple",
                ),
                "</div>",
            )
        )
    )

    with st.container(key="admin_security_filters", border=False):
        st.html(
            """
<div class="sjk-admin-security-heading">
    <span>Security review</span>
    <h2>Flagged Activity</h2>
    <p>
        Review non-school ticket emails and high-confidence attempts to bypass,
        misuse, damage, or extract protected information from Altitude.
    </p>
</div>
"""
        )

        search_column, type_column, severity_column, review_column = st.columns(
            [2.0, 1.15, 0.9, 0.9],
            gap="small",
        )
        with search_column:
            search_value = st.text_input(
                "Search",
                key="admin_security_search",
                placeholder="Search email, type, summary or session",
            )
        with type_column:
            type_options = sorted(
                {str(row.get("event_type") or "Unknown") for row in findings},
                key=str.casefold,
            )
            type_value = st.selectbox(
                "Event type",
                options=("All", *type_options),
                key="admin_security_type",
            )
        with severity_column:
            severity_options = sorted(
                {str(row.get("severity") or "Unknown") for row in findings},
                key=str.casefold,
            )
            severity_value = st.selectbox(
                "Severity",
                options=("All", *severity_options),
                key="admin_security_severity",
            )
        with review_column:
            review_value = st.selectbox(
                "Review status",
                options=("All", "Open", "Reviewed", "Dismissed"),
                key="admin_security_review",
            )

    clean_search = search_value.strip().casefold()
    filtered: list[dict[str, Any]] = []
    for row in findings:
        if type_value != "All" and str(row.get("event_type")) != type_value:
            continue
        if severity_value != "All" and str(row.get("severity")) != severity_value:
            continue
        if review_value != "All" and str(row.get("review_status")) != review_value:
            continue
        if clean_search:
            searchable = " ".join(
                str(row.get(field) or "")
                for field in (
                    "event_type",
                    "severity",
                    "summary",
                    "actor",
                    "context",
                    "review_status",
                )
            ).casefold()
            if clean_search not in searchable:
                continue
        filtered.append(row)

    with st.container(key="admin_security_table_panel", border=False):
        st.caption(
            f"Showing {len(filtered):,} of {len(findings):,} security "
            + ("finding" if len(findings) == 1 else "findings")
        )

        if not filtered:
            st.html(
                """
<div class="sjk-admin-empty-state sjk-admin-security-empty">
    No security findings match the selected filters.
</div>
"""
            )
            return

        table_rows = [
            {
                "Date": _format_feedback_datetime(
                    str(row.get("updated_at") or row.get("created_at") or "")
                ),
                "Severity": str(row.get("severity") or "Unknown"),
                "Type": str(row.get("event_type") or "Unknown"),
                "Email / Session": _security_actor_label(row),
                "Summary": str(row.get("summary") or "Not available"),
                "Occurrences": int(row.get("occurrence_count") or 1),
                "Review": str(row.get("review_status") or "Open"),
            }
            for row in filtered
        ]
        st.dataframe(
            pd.DataFrame(table_rows),
            hide_index=True,
            width="stretch",
            height=390,
            column_config={
                "Date": st.column_config.TextColumn("Date", width="medium"),
                "Severity": st.column_config.TextColumn(
                    "Severity", width="small"
                ),
                "Type": st.column_config.TextColumn("Type", width="medium"),
                "Email / Session": st.column_config.TextColumn(
                    "Email / Session", width="medium"
                ),
                "Summary": st.column_config.TextColumn(
                    "Summary", width="large"
                ),
                "Occurrences": st.column_config.NumberColumn(
                    "Count", width="small"
                ),
                "Review": st.column_config.TextColumn(
                    "Review", width="small"
                ),
            },
        )

        finding_options = [str(row.get("finding_id")) for row in filtered]
        labels = {
            str(row.get("finding_id")): (
                f"{row.get('severity', 'Unknown')} — "
                f"{row.get('event_type', 'Unknown')} — "
                f"{_security_actor_label(row)}"
            )
            for row in filtered
        }
        
        def _format_security_finding(value: object) -> str:
            value_text = str(value)
            return labels.get(value_text, value_text)
        
        selected_finding = st.selectbox(
            "Selected finding",
            options=finding_options,
            format_func=_format_security_finding,
            key="admin_security_selected_finding",
        )

        reviewed_column, dismissed_column, reopen_column = st.columns(3)
        identity = get_admin_identity()
        reviewer = identity.username if identity is not None else "administrator"

        with reviewed_column:
            mark_reviewed = st.button(
                "Mark reviewed",
                key="admin_security_mark_reviewed",
                width="stretch",
            )
        with dismissed_column:
            mark_dismissed = st.button(
                "Dismiss",
                key="admin_security_mark_dismissed",
                width="stretch",
            )
        with reopen_column:
            mark_open = st.button(
                "Reopen",
                key="admin_security_mark_open",
                width="stretch",
            )

        requested_status = (
            "Reviewed" if mark_reviewed
            else "Dismissed" if mark_dismissed
            else "Open" if mark_open
            else None
        )
        if requested_status is not None:
            try:
                update_security_finding_review(
                    selected_finding,
                    review_status=requested_status,
                    reviewed_by=reviewer,
                )
            except (RuntimeError, ValueError) as error:
                st.error(str(error))
            else:
                st.toast(f"Security finding marked {requested_status}.")
                st.rerun()


def _scroll_admin_content_to_top() -> None:
    """Move the admin section scrollbar to the top after a queue action."""
    trigger_id = time.time_ns()
    st.html(
        f"""
<script data-admin-scroll-top="{trigger_id}">
(() => {{
    const scrollToTop = () => {{
        const container = document.querySelector(
            ".st-key-admin_content_scroll"
        );

        if (!container) {{
            return;
        }}

        container.scrollTo({{
            top: 0,
            left: 0,
            behavior: "auto"
        }});
    }};

    requestAnimationFrame(scrollToTop);
    setTimeout(scrollToTop, 75);
    setTimeout(scrollToTop, 250);
}})();
</script>
""",
        unsafe_allow_javascript=True,
    )


def _finish_knowledge_review_action(message: str) -> None:
    """Prepare a clean, obvious Knowledge Queue state after review."""
    st.session_state["admin_knowledge_action_flash"] = message
    st.session_state["admin_knowledge_scroll_top"] = True
    # Do not leave the next pending draft selected under the same buttons.
    st.session_state.pop("admin_knowledge_selected_draft", None)
    st.rerun()


def _render_knowledge_section() -> None:
    """Review resolved-ticket learning drafts before publishing them to RAG."""
    initialize_database()

    # Keep initial navigation fast. A live Django ticket sync can involve many
    # HTTP requests, so it runs only when the administrator explicitly presses
    # "Sync resolved tickets" (or via the standalone scheduled sync script).
    # Locally stored resolved tickets are still converted to drafts immediately.

    if st.session_state.pop("admin_knowledge_scroll_top", False):
        _scroll_admin_content_to_top()

    action_flash = st.session_state.pop("admin_knowledge_action_flash", None)
    if action_flash:
        st.success(str(action_flash), icon="✅")

    # Convert any resolved tickets already stored locally into pending drafts.
    # Remote ticket synchronization is rate-limited separately below.
    try:
        sync_resolved_tickets_to_knowledge_queue(limit=1_000)
    except Exception as error:
        print(
            "Knowledge queue generation failed: "
            f"{type(error).__name__}: {error}"
        )

    summary = _safe_knowledge_summary()

    st.html(
        "".join(
            (
                '<div class="sjk-admin-metric-grid sjk-admin-metric-grid-three">',
                _metric_card(
                    "Pending Review",
                    f"{int(summary.get('pending', 0)):,}",
                    "Resolved-ticket drafts awaiting IT approval",
                    tone="gold",
                ),
                _metric_card(
                    "Approved",
                    f"{int(summary.get('approved', 0)):,}",
                    "Published to Altitude knowledge",
                    tone="green",
                ),
                _metric_card(
                    "Rejected",
                    f"{int(summary.get('rejected', 0)):,}",
                    "Kept out of the live knowledge base",
                    tone="red",
                ),
                "</div>",
            )
        )
    )

    with st.container(key="admin_knowledge_toolbar", border=False):
        toolbar_columns = st.columns(
            [2.2, 1.0],
            gap="medium",
            vertical_alignment="bottom",
        )
        with toolbar_columns[0]:
            status_filter = st.selectbox(
                "Queue status",
                options=("Pending", "Approved", "Rejected", "All"),
                key="admin_knowledge_status_filter",
            )
        with toolbar_columns[1]:
            force_sync = st.button(
                "Sync resolved tickets",
                key="admin_knowledge_force_sync",
                type="primary",
                width="stretch",
            )

    if force_sync:
        try:
            with st.spinner("Checking resolved tickets and resolution notes..."):
                updated_count, checked_count = _synchronize_ticket_statuses()
                queue_result = sync_resolved_tickets_to_knowledge_queue(limit=1_000)
            sent_count = int(
                st.session_state.get("admin_resolution_email_last_sent_count", 0)
            )
            failed_count = int(
                st.session_state.get("admin_resolution_email_last_failed_count", 0)
            )
            email_suffix = f", sent {sent_count} resolution email(s)"
            if failed_count:
                email_suffix += f", {failed_count} email(s) failed"
            st.toast(
                f"Checked {checked_count} ticket(s), updated {updated_count}, "
                f"created {queue_result.get('created', 0)} draft(s){email_suffix}.",
                icon="✅",
            )
            config_error = st.session_state.get(
                "admin_resolution_email_config_error"
            )
            if config_error:
                st.warning(f"Resolution email is not configured correctly: {config_error}")
            st.rerun()
        except Exception as error:
            st.error(f"Ticket synchronization failed: {error}")

    selected_status = None if status_filter == "All" else status_filter
    drafts = _safe_knowledge_rows(
        review_status=selected_status,
        limit=500,
    )

    if not drafts:
        st.info(
            "There are no knowledge drafts in this view. A draft is created "
            "when an Altitude-created ticket is Closed/Resolved and has a "
            "meaningful technician resolution note."
        )
        return

    labels = {
        str(row["draft_id"]): (
            f"#{row['draft_id']} — {row.get('draft_title', 'Untitled')} "
            f"({row.get('review_status', 'Pending')})"
        )
        for row in drafts
    }

    def _format_knowledge_draft(value: object) -> str:
        value_text = str(value)
        return labels.get(value_text, value_text)

    selected_value = st.selectbox(
        "Knowledge draft",
        options=tuple(labels),
        format_func=_format_knowledge_draft,
        key="admin_knowledge_selected_draft",
    )
    selected = next(
        row for row in drafts if str(row["draft_id"]) == str(selected_value)
    )
    draft_id = int(selected["draft_id"])
    is_pending = str(selected.get("review_status")) == "Pending"

    source_ticket = (
        selected.get("external_ticket_id")
        or selected.get("altitude_reference")
        or f"Local #{selected.get('local_ticket_id')}"
    )
    st.html(
        f"""
<section class="sjk-admin-dashboard-panel">
    <div class="sjk-admin-dashboard-panel-heading">
        <h3>Source Ticket</h3>
        <span class="sjk-admin-panel-badge">{escape(str(selected.get('review_status', 'Pending')))}</span>
    </div>
    <p><strong>{escape(str(source_ticket))}</strong> · {escape(_ticket_category_label(selected.get('source_category')))} · {escape(str(selected.get('source_device') or 'Device not provided'))}</p>
</section>
"""
    )

    source_columns = st.columns(2, gap="medium")
    with source_columns[0]:
        st.text_area(
            "Original problem",
            value=str(selected.get("source_problem") or selected.get("source_title") or ""),
            height=145,
            disabled=True,
            key=f"knowledge_source_problem_{draft_id}",
        )
    with source_columns[1]:
        st.text_area(
            "Technician resolution note",
            value=str(selected.get("source_resolution") or ""),
            height=145,
            disabled=True,
            key=f"knowledge_source_resolution_{draft_id}",
        )

    title_value = st.text_input(
        "Documentation title",
        value=str(selected.get("draft_title") or ""),
        disabled=not is_pending,
        key=f"knowledge_title_{draft_id}",
    )
    keywords_value = st.text_input(
        "Intent keywords",
        value=str(selected.get("intent_keywords") or ""),
        help="Comma-separated phrases Altitude can match against future questions.",
        disabled=not is_pending,
        key=f"knowledge_keywords_{draft_id}",
    )
    audience_value = st.text_input(
        "Target audience",
        value=str(selected.get("target_audience") or "Staff, Faculty, Students"),
        disabled=not is_pending,
        key=f"knowledge_audience_{draft_id}",
    )
    direct_answer_value = st.text_area(
        "Direct answer",
        value=str(selected.get("direct_answer") or ""),
        height=115,
        disabled=not is_pending,
        key=f"knowledge_answer_{draft_id}",
    )

    existing_steps = selected.get("troubleshooting_steps") or []
    steps_value = st.text_area(
        "Troubleshooting steps — one step per line",
        value="\n".join(str(step) for step in existing_steps),
        height=190,
        disabled=not is_pending,
        key=f"knowledge_steps_{draft_id}",
    )
    bot_instruction_value = st.text_area(
        "Private bot instruction",
        value=str(selected.get("bot_instruction") or ""),
        height=105,
        help=(
            "Internal guidance used by Altitude. It is removed before the "
            "procedure is shown to a user."
        ),
        disabled=not is_pending,
        key=f"knowledge_instruction_{draft_id}",
    )
    review_notes_value = st.text_area(
        "IT review notes",
        value=str(selected.get("review_notes") or ""),
        height=90,
        disabled=not is_pending,
        key=f"knowledge_review_notes_{draft_id}",
    )

    if not is_pending:
        published_filename = str(selected.get("published_filename") or "").strip()
        if published_filename:
            st.success(
                f"Published as `{published_filename}` and available to Altitude retrieval."
            )
        else:
            st.caption(
                f"Reviewed by {selected.get('reviewed_by') or 'administrator'} · "
                f"Status: {selected.get('review_status')}"
            )
        return

    steps = [
        " ".join(line.split()).strip()
        for line in steps_value.splitlines()
        if " ".join(line.split()).strip()
    ]

    identity = get_admin_identity()
    reviewer = identity.username if identity is not None else "administrator"

    action_columns = st.columns([1.0, 1.0, 1.0], gap="small")
    with action_columns[0]:
        save_requested = st.button(
            "Save Draft",
            key=f"knowledge_save_{draft_id}",
            width="stretch",
        )
    with action_columns[1]:
        approve_requested = st.button(
            "Approve & Publish",
            key=f"knowledge_approve_{draft_id}",
            type="primary",
            width="stretch",
        )
    with action_columns[2]:
        reject_requested = st.button(
            "Reject",
            key=f"knowledge_reject_{draft_id}",
            width="stretch",
        )

    if save_requested or approve_requested:
        try:
            update_knowledge_draft(
                draft_id,
                draft_title=title_value,
                intent_keywords=keywords_value,
                target_audience=audience_value,
                direct_answer=direct_answer_value,
                troubleshooting_steps=steps,
                bot_instruction=bot_instruction_value,
                review_notes=review_notes_value,
            )
        except ValueError as error:
            st.error(str(error))
            return

        if save_requested:
            st.toast("Knowledge draft saved.", icon="✅")
            st.rerun()

        try:
            with st.spinner("Publishing and indexing approved knowledge..."):
                filename = publish_knowledge_draft(
                    draft_id,
                    reviewed_by=reviewer,
                    review_notes=review_notes_value,
                )
        except Exception as error:
            st.error(
                "The draft was saved but could not be published to live "
                f"knowledge: {error}"
            )
            return

        _finish_knowledge_review_action(
            f"Knowledge draft #{draft_id} approved and published as {filename}."
        )

    if reject_requested:
        try:
            reject_knowledge_draft(
                draft_id,
                reviewed_by=reviewer,
                review_notes=review_notes_value,
            )
        except ValueError as error:
            st.error(str(error))
            return
        _finish_knowledge_review_action(
            f"Knowledge draft #{draft_id} rejected and kept out of live knowledge."
        )


ANNOUNCEMENT_TYPE_LABELS: dict[str, str] = {
    "info": "Information",
    "maintenance": "Maintenance",
    "warning": "Warning",
    "outage": "Service outage",
    "resolved": "Resolved",
}


def _local_timezone():
    """Return Altitude's configured local timezone."""
    return get_local_timezone()


def _combine_local_datetime(
    selected_date: date,
    selected_time: datetime_time,
) -> str:
    """Convert local date/time inputs into a UTC ISO timestamp."""
    local_value = datetime.combine(
        selected_date,
        selected_time,
        tzinfo=_local_timezone(),
    )
    return local_value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _format_announcement_time(value: str | None) -> str:
    """Display a stored UTC timestamp in the server's local timezone."""
    if not value:
        return "No limit"

    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(_local_timezone()).strftime("%b %d, %Y at %I:%M %p")


def _announcement_status(announcement: dict[str, Any]) -> tuple[str, str]:
    """Return a display label and CSS status class for an announcement."""
    if not bool(announcement.get("is_active")):
        return "Inactive", "inactive"

    now = datetime.now(timezone.utc)
    starts_at = announcement.get("starts_at")
    ends_at = announcement.get("ends_at")

    try:
        start_value = (
            datetime.fromisoformat(str(starts_at).replace("Z", "+00:00"))
            if starts_at
            else None
        )
        end_value = (
            datetime.fromisoformat(str(ends_at).replace("Z", "+00:00"))
            if ends_at
            else None
        )
    except ValueError:
        return "Active", "active"

    if start_value is not None and start_value.tzinfo is None:
        start_value = start_value.replace(tzinfo=timezone.utc)

    if end_value is not None and end_value.tzinfo is None:
        end_value = end_value.replace(tzinfo=timezone.utc)

    if start_value is not None and start_value > now:
        return "Scheduled", "scheduled"

    if end_value is not None and end_value < now:
        return "Expired", "expired"

    return "Active", "active"


def _clear_announcement_form_state() -> None:
    for key in (
        "announcement_edit_id",
        "announcement_form_title",
        "announcement_form_message",
        "announcement_form_type",
        "announcement_form_publish_now",
        "announcement_form_start_date",
        "announcement_form_start_time",
        "announcement_form_has_end",
        "announcement_form_end_date",
        "announcement_form_end_time",
        "announcement_form_active",
    ):
        st.session_state.pop(key, None)


def _request_announcement_form_reset() -> None:
    """Request a clean editor state before the next Streamlit rerun."""
    st.session_state["announcement_form_reset_requested"] = True


def _load_announcement_for_edit(announcement: dict[str, Any]) -> None:
    """Populate form session state from one stored announcement."""
    start_value = announcement.get("starts_at")
    end_value = announcement.get("ends_at")

    start_local = (
        datetime.fromisoformat(str(start_value).replace("Z", "+00:00"))
        .astimezone(_local_timezone())
        if start_value
        else local_now()
    )
    end_local = (
        datetime.fromisoformat(str(end_value).replace("Z", "+00:00"))
        .astimezone(_local_timezone())
        if end_value
        else local_now().replace(microsecond=0)
    )

    st.session_state["announcement_edit_id"] = int(
        announcement["announcement_id"]
    )
    st.session_state["announcement_form_title"] = str(
        announcement.get("title", "")
    )
    st.session_state["announcement_form_message"] = str(
        announcement.get("message", "")
    )
    st.session_state["announcement_form_type"] = str(
        announcement.get("severity", "info")
    )
    st.session_state["announcement_form_publish_now"] = not bool(start_value)
    st.session_state["announcement_form_start_date"] = start_local.date()
    st.session_state["announcement_form_start_time"] = start_local.time().replace(
        second=0,
        microsecond=0,
    )
    st.session_state["announcement_form_has_end"] = bool(end_value)
    st.session_state["announcement_form_end_date"] = end_local.date()
    st.session_state["announcement_form_end_time"] = end_local.time().replace(
        second=0,
        microsecond=0,
    )
    st.session_state["announcement_form_active"] = bool(
        announcement.get("is_active")
    )


def _render_announcement_form(username: str) -> None:
    """Render live create/edit controls for administrator announcements.

    The controls intentionally do not use ``st.form``. Streamlit forms batch
    widget changes until submit, which prevented the schedule date and time
    fields from appearing immediately when "Publish immediately" was cleared.
    """
    if st.session_state.pop("announcement_form_reset_requested", False):
        _clear_announcement_form_state()

    now_local = local_now().replace(second=0, microsecond=0)
    default_end = now_local.replace(hour=23, minute=59)

    st.session_state.setdefault("announcement_form_title", "")
    st.session_state.setdefault("announcement_form_message", "")
    st.session_state.setdefault("announcement_form_type", "info")
    st.session_state.setdefault("announcement_form_publish_now", True)
    st.session_state.setdefault("announcement_form_start_date", now_local.date())
    st.session_state.setdefault("announcement_form_start_time", now_local.time())
    st.session_state.setdefault("announcement_form_has_end", False)
    st.session_state.setdefault("announcement_form_end_date", default_end.date())
    st.session_state.setdefault("announcement_form_end_time", default_end.time())
    st.session_state.setdefault("announcement_form_active", True)

    edit_id = st.session_state.get("announcement_edit_id")

    with st.container(key="announcement_editor_controls", border=False):
        title = st.text_input(
            "Title",
            key="announcement_form_title",
            max_chars=120,
            placeholder="Example: Wi-Fi maintenance",
        )
        message = st.text_area(
            "Announcement",
            key="announcement_form_message",
            max_chars=1500,
            height=110,
            placeholder=(
                "Enter the message that students and staff should see in the "
                "chatbot's left panel."
            ),
        )

        type_options = list(ANNOUNCEMENT_TYPE_LABELS)
        selected_type = st.selectbox(
            "Type",
            options=type_options,
            format_func=lambda value: ANNOUNCEMENT_TYPE_LABELS[value],
            key="announcement_form_type",
        )

        publish_now = st.checkbox(
            "Publish immediately",
            key="announcement_form_publish_now",
        )

        if publish_now:
            start_date = now_local.date()
            start_time = now_local.time()
        else:
            st.caption("Choose the date and time when this notice should appear.")
            start_columns = st.columns(2)
            with start_columns[0]:
                start_date = st.date_input(
                    "Start date",
                    key="announcement_form_start_date",
                )
            with start_columns[1]:
                start_time = st.time_input(
                    "Start time",
                    step=300,
                    key="announcement_form_start_time",
                )

        has_end = st.checkbox(
            "Set an automatic end time",
            key="announcement_form_has_end",
        )

        if has_end:
            end_columns = st.columns(2)
            with end_columns[0]:
                end_date = st.date_input(
                    "End date",
                    key="announcement_form_end_date",
                )
            with end_columns[1]:
                end_time = st.time_input(
                    "End time",
                    step=300,
                    key="announcement_form_end_time",
                )
        else:
            end_date = default_end.date()
            end_time = default_end.time()

        is_active = st.checkbox(
            "Enabled",
            key="announcement_form_active",
            help=(
                "Disabled announcements remain in the dashboard but are hidden "
                "from the chatbot."
            ),
        )

        submit_label = "Save changes" if edit_id else "Create announcement"
        submitted = st.button(
            submit_label,
            key="save_announcement",
            type="primary",
            width="stretch",
        )

        if edit_id:
            st.button(
                "Cancel editing",
                key="cancel_announcement_edit",
                width="stretch",
                on_click=_request_announcement_form_reset,
            )

    if not submitted:
        return

    clean_title = title.strip()
    clean_message = message.strip()

    if not clean_title:
        st.error("Enter an announcement title.")
        return

    if not clean_message:
        st.error("Enter an announcement message.")
        return

    starts_at = (
        None
        if publish_now
        else _combine_local_datetime(start_date, start_time)
    )
    ends_at = (
        _combine_local_datetime(end_date, end_time)
        if has_end
        else None
    )

    if ends_at is not None:
        start_reference = starts_at or datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        )
        start_value = datetime.fromisoformat(start_reference.replace("Z", "+00:00"))
        end_value = datetime.fromisoformat(ends_at.replace("Z", "+00:00"))

        if end_value <= start_value:
            st.error("The automatic end time must be after the start time.")
            return

    try:
        if edit_id:
            update_announcement(
                int(edit_id),
                title=clean_title,
                message=clean_message,
                severity=selected_type,
                starts_at=starts_at,
                ends_at=ends_at,
                is_active=is_active,
            )
            success_message = "Announcement updated."
        else:
            create_announcement(
                title=clean_title,
                message=clean_message,
                severity=selected_type,
                starts_at=starts_at,
                ends_at=ends_at,
                is_active=is_active,
                created_by=username,
            )
            success_message = "Announcement created."
    except (RuntimeError, ValueError) as error:
        st.error(str(error))
        return
    except Exception as error:
        print(
            "Announcement save failed: "
            f"{type(error).__name__}: {error}"
        )
        st.error("The announcement could not be saved. Try again.")
        return

    st.session_state["announcement_form_reset_requested"] = True
    st.session_state["announcement_success_message"] = success_message
    st.rerun()

def _render_announcement_card(announcement: dict[str, Any]) -> None:
    announcement_id = int(announcement["announcement_id"])
    status_label, status_class = _announcement_status(announcement)
    severity = str(announcement.get("severity", "info"))
    severity_label = ANNOUNCEMENT_TYPE_LABELS.get(severity, "Information")

    st.html(
        f"""
<article class="sjk-admin-announcement-card sjk-admin-announcement-{escape(severity)}">
    <div class="sjk-admin-announcement-card-heading">
        <div>
            <span class="sjk-admin-announcement-type">{escape(severity_label)}</span>
            <h3>{escape(str(announcement.get('title', 'Announcement')))}</h3>
        </div>
        <span class="sjk-admin-announcement-status sjk-admin-announcement-status-{status_class}">
            {escape(status_label)}
        </span>
    </div>
    <p>{escape(str(announcement.get('message', '')))}</p>
    <dl class="sjk-admin-announcement-meta">
        <div>
            <dt>Starts</dt>
            <dd>{escape(_format_announcement_time(announcement.get('starts_at')))}</dd>
        </div>
        <div>
            <dt>Ends</dt>
            <dd>{escape(_format_announcement_time(announcement.get('ends_at')))}</dd>
        </div>
    </dl>
</article>
"""
    )

    actions = st.columns([1, 1, 1.1])

    with actions[0]:
        st.button(
            "Edit",
            key=f"edit_announcement_{announcement_id}",
            width="stretch",
            on_click=_load_announcement_for_edit,
            args=(announcement,),
        )

    with actions[1]:
        currently_active = bool(announcement.get("is_active"))
        if st.button(
            "Disable" if currently_active else "Enable",
            key=f"toggle_announcement_{announcement_id}",
            width="stretch",
        ):
            try:
                set_announcement_active(
                    announcement_id,
                    is_active=not currently_active,
                )
            except (RuntimeError, ValueError) as error:
                st.error(str(error))
            else:
                st.rerun()

    with actions[2]:
        confirm_key = f"confirm_delete_announcement_{announcement_id}"

        if not st.session_state.get(confirm_key):
            if st.button(
                "Delete",
                key=f"delete_announcement_{announcement_id}",
                width="stretch",
            ):
                st.session_state[confirm_key] = True
                st.rerun()
        else:
            confirm_columns = st.columns(2)
            with confirm_columns[0]:
                if st.button(
                    "Confirm",
                    key=f"confirm_delete_yes_{announcement_id}",
                    type="primary",
                    width="stretch",
                ):
                    try:
                        delete_announcement(announcement_id)
                    except (RuntimeError, ValueError) as error:
                        st.error(str(error))
                    else:
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
            with confirm_columns[1]:
                if st.button(
                    "Cancel",
                    key=f"confirm_delete_no_{announcement_id}",
                    width="stretch",
                ):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()


def _render_announcements_section() -> None:
    """Create, schedule, list, and manage chatbot announcements."""
    identity = get_admin_identity()
    username = identity.username if identity is not None else "administrator"

    success_message = st.session_state.pop(
        "announcement_success_message",
        None,
    )
    if success_message:
        # A toast does not consume layout height, so the two announcement
        # panels keep a stable viewport-relative size after a save.
        st.toast(str(success_message), icon="✅")

    try:
        announcement_rows = list_announcements(include_inactive=True)
        summary = get_announcement_summary()
    except Exception as error:
        print(
            "Announcement dashboard load failed: "
            f"{type(error).__name__}: {error}"
        )
        announcement_rows = []
        summary = {
            "active_announcements": 0,
            "scheduled_announcements": 0,
            "total_announcements": 0,
        }
        st.error("Announcements could not be loaded from the database.")

    st.html(
        "".join(
            (
                '<div class="sjk-admin-metric-grid sjk-admin-metric-grid-three">',
                _metric_card(
                    "Active",
                    f"{int(summary.get('active_announcements', 0)):,}",
                    "Currently shown in the chatbot",
                    tone="green",
                ),
                _metric_card(
                    "Scheduled",
                    f"{int(summary.get('scheduled_announcements', 0)):,}",
                    "Will appear automatically",
                    tone="gold",
                ),
                _metric_card(
                    "Total",
                    f"{int(summary.get('total_announcements', 0)):,}",
                    "Active and inactive records",
                ),
                "</div>",
            )
        )
    )

    # The stable key lets CSS size the two-column area without depending on
    # Streamlit's generated emotion-cache class names.
    with st.container(key="announcement_workspace", border=False):
        editor_column, list_column = st.columns(
            [0.9, 1.35],
            gap="medium",
            vertical_alignment="top",
        )

        with editor_column:
            with st.container(
                key="announcement_editor_panel",
                border=True,
            ):
                edit_id = st.session_state.get("announcement_edit_id")
                editor_title = (
                    "Edit announcement" if edit_id else "Create announcement"
                )

                st.html(
                    f"""
<div class="sjk-admin-section-heading">
    <div>
        <span>Announcement editor</span>
        <h2>{escape(editor_title)}</h2>
        <p>Publish a notice to the chatbot's Announcements panel.</p>
    </div>
</div>
"""
                )

                # This keyed region owns scrolling. Its content keeps its
                # natural height, allowing the last control to remain reachable.
                with st.container(
                    key="announcement_editor_scroll",
                    height=320,
                    border=False,
                ):
                    _render_announcement_form(username)

        with list_column:
            with st.container(
                key="announcement_list_panel",
                border=True,
            ):
                st.html(
                    """
<div class="sjk-admin-section-heading">
    <div>
        <span>Published notices</span>
        <h2>Current announcements</h2>
        <p>
            The list scrolls only when its content exceeds the available space.
        </p>
    </div>
</div>
"""
                )

                # The card list scrolls independently from the editor.
                with st.container(
                    key="announcement_list_scroll",
                    height=320,
                    border=False,
                ):
                    if not announcement_rows:
                        st.html(
                            """
<div class="sjk-admin-empty-state sjk-admin-announcement-empty">
    No announcements have been created yet.
</div>
"""
                        )
                    else:
                        for announcement in announcement_rows:
                            _render_announcement_card(announcement)

def _display_database_path(raw_path: str) -> str:
    """Return a short, non-sensitive project-relative database path."""
    if not raw_path or raw_path == "Not available":
        return "Not available"

    path = Path(raw_path).expanduser()

    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except (OSError, ValueError):
        return path.name


def _health_report_checked_at(report: dict[str, Any]) -> str:
    """Return a readable timestamp for one system-health report."""
    display_value = str(report.get("checked_at_display", "")).strip()
    if display_value:
        return display_value

    raw_value = str(report.get("checked_at", "")).strip()
    if not raw_value:
        return "Not checked yet"

    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return raw_value

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(_local_timezone()).strftime("%b %d, %Y at %I:%M:%S %p")


def _health_summary_html(report: dict[str, Any]) -> str:
    """Return the overall operational-status banner."""
    status = str(report.get("overall_status", "warning"))
    label = str(report.get("overall_label", "Health status unavailable"))
    message = str(
        report.get(
            "overall_message",
            "Run the health checks to inspect Altitude services.",
        )
    )
    checked_at = _health_report_checked_at(report)
    counts = report.get("counts", {})
    healthy_count = int(counts.get("healthy", 0))
    warning_count = int(counts.get("warning", 0))
    unavailable_count = int(counts.get("unavailable", 0))
    unconfigured_count = int(counts.get("not_configured", 0))

    return f"""
<section class="sjk-health-summary sjk-health-summary-{escape(status)}">
    <div class="sjk-health-summary-indicator" aria-hidden="true"></div>
    <div class="sjk-health-summary-copy">
        <span class="sjk-health-eyebrow">Current operational status</span>
        <h2>{escape(label)}</h2>
        <p>{escape(message)}</p>
        <time>Last checked: {escape(checked_at)}</time>
    </div>
    <dl class="sjk-health-summary-counts">
        <div>
            <dt>Healthy</dt>
            <dd>{healthy_count:,}</dd>
        </div>
        <div>
            <dt>Warning</dt>
            <dd>{warning_count:,}</dd>
        </div>
        <div>
            <dt>Unavailable</dt>
            <dd>{unavailable_count:,}</dd>
        </div>
        <div>
            <dt>Not configured</dt>
            <dd>{unconfigured_count:,}</dd>
        </div>
    </dl>
</section>
"""


def _health_check_details_html(check: dict[str, Any]) -> str:
    """Return one expandable technical diagnostic row."""
    status = str(check.get("status", "warning"))
    status_label = str(check.get("status_label", status.title()))
    name = str(check.get("name", "Service"))
    message = str(check.get("message", "No diagnostic message is available."))
    metric = str(check.get("metric", "—"))
    detail_rows = check.get("details", [])
    recommendation = str(check.get("recommendation") or "").strip()

    details_html = "".join(
        (
            '<div class="sjk-health-detail-row">'
            f"<dt>{escape(str(label))}</dt>"
            f"<dd>{escape(str(value))}</dd>"
            "</div>"
        )
        for label, value in detail_rows
    )

    recommendation_html = (
        f"""
<div class="sjk-health-recommendation">
    <strong>Recommended action</strong>
    <p>{escape(recommendation)}</p>
</div>
"""
        if recommendation
        else ""
    )

    return f"""
<details class="sjk-health-row sjk-health-row-{escape(status)}">
    <summary>
        <span class="sjk-health-status-dot" aria-hidden="true"></span>
        <span class="sjk-health-service-copy">
            <strong>{escape(name)}</strong>
            <span>{escape(message)}</span>
        </span>
        <span class="sjk-health-service-metric">{escape(metric)}</span>
        <span class="sjk-health-status-badge">{escape(status_label)}</span>
        <span class="sjk-health-disclosure" aria-hidden="true"></span>
    </summary>
    <div class="sjk-health-row-details">
        <dl>{details_html}</dl>
        {recommendation_html}
    </div>
</details>
"""


def _health_group_html(group: dict[str, Any]) -> str:
    """Return one grouped set of health checks."""
    label = str(group.get("label", "Services"))
    description = str(group.get("description", ""))
    checks = group.get("checks", [])
    checks_html = "".join(
        _health_check_details_html(check)
        for check in checks
        if isinstance(check, dict)
    )

    return f"""
<section class="sjk-health-group">
    <header class="sjk-health-group-header">
        <div>
            <span>Service group</span>
            <h3>{escape(label)}</h3>
            <p>{escape(description)}</p>
        </div>
        <strong>{len(checks):,} checks</strong>
    </header>
    <div class="sjk-health-service-list">
        {checks_html}
    </div>
</section>
"""


def _record_health_events(report: dict[str, Any]) -> None:
    """Store recent health-check results for the current admin session."""
    checked_at = str(report.get("checked_at", "")).strip()
    if not checked_at:
        return

    if st.session_state.get("system_health_last_recorded_at") == checked_at:
        return

    previous_statuses = dict(
        st.session_state.get("system_health_previous_statuses", {})
    )
    events = list(st.session_state.get("system_health_events", []))
    current_statuses: dict[str, str] = {}

    for group in report.get("groups", []):
        for check in group.get("checks", []):
            key = str(check.get("key", "")).strip()
            if not key:
                continue

            status = str(check.get("status", "warning"))
            current_statuses[key] = status
            old_status = previous_statuses.get(key)

            if old_status == status:
                continue

            events.insert(
                0,
                {
                    "checked_at": checked_at,
                    "service": str(check.get("name", key)),
                    "status": status,
                    "status_label": str(
                        check.get("status_label", status.title())
                    ),
                    "message": str(check.get("message", "")),
                    "change": (
                        "Initial check"
                        if old_status is None
                        else (
                            f"{old_status.replace('_', ' ').title()} to "
                            f"{status.replace('_', ' ').title()}"
                        )
                    ),
                },
            )

    st.session_state["system_health_events"] = events[:50]
    st.session_state["system_health_previous_statuses"] = current_statuses
    st.session_state["system_health_last_recorded_at"] = checked_at


def _health_events_html() -> str:
    """Return recent health-status changes for the current browser session."""
    events = list(st.session_state.get("system_health_events", []))[:12]

    if not events:
        rows_html = (
            '<div class="sjk-health-events-empty">'
            "No health events have been recorded in this admin session."
            "</div>"
        )
    else:
        rows: list[str] = []

        for event in events:
            checked_at = _format_feedback_datetime(
                str(event.get("checked_at", ""))
            )
            status = str(event.get("status", "warning"))
            rows.append(
                f"""
<div class="sjk-health-event-row">
    <time>{escape(checked_at)}</time>
    <strong>{escape(str(event.get('service', 'Service')))}</strong>
    <span class="sjk-health-event-status sjk-health-event-status-{escape(status)}">
        {escape(str(event.get('status_label', status.title())))}
    </span>
    <p>{escape(str(event.get('change', 'Health check')))}</p>
</div>
"""
            )

        rows_html = "".join(rows)

    return f"""
<section class="sjk-health-events">
    <header>
        <div>
            <span>Session history</span>
            <h3>Recent health events</h3>
            <p>
                Status changes recorded while this administrator session is open.
            </p>
        </div>
    </header>
    <div class="sjk-health-event-list">
        {rows_html}
    </div>
</section>
"""


def _run_health_report() -> dict[str, Any]:
    """Run health checks while keeping failures inside a safe report."""
    try:
        return run_system_health_checks()
    except Exception as error:
        print(
            "System health checks failed: "
            f"{type(error).__name__}: {error}"
        )
        checked_at = datetime.now(timezone.utc)
        return {
            "checked_at": checked_at.isoformat(timespec="seconds"),
            "checked_at_display": checked_at.astimezone(_local_timezone()).strftime(
                "%b %d, %Y at %I:%M:%S %p"
            ),
            "overall_status": "critical",
            "overall_label": "Health checks could not complete",
            "overall_message": (
                "The health-check service encountered an unexpected error."
            ),
            "counts": {
                "healthy": 0,
                "warning": 0,
                "unavailable": 1,
                "not_configured": 0,
            },
            "groups": [
                {
                    "key": "health_service",
                    "label": "Health-check service",
                    "description": "Internal diagnostic execution.",
                    "checks": [
                        {
                            "key": "health_service",
                            "name": "Health-check service",
                            "status": "unavailable",
                            "status_label": "Unavailable",
                            "message": "The checks could not be completed.",
                            "metric": "Failed",
                            "details": [
                                (
                                    "Safe error",
                                    f"{type(error).__name__}: {error}",
                                )
                            ],
                            "recommendation": (
                                "Review the server log and validate the "
                                "system-health module."
                            ),
                        }
                    ],
                }
            ],
        }


def _render_health_section() -> None:
    """Render an operations console for current Altitude service health."""
    with st.container(key="admin_health_console", border=False):
        toolbar_columns = st.columns(
            [1.0, 0.24],
            gap="medium",
            vertical_alignment="center",
        )

        with toolbar_columns[0]:
            st.html(
                """
<div class="sjk-health-toolbar-copy">
    <span>Live diagnostics</span>
    <strong>Altitude operations console</strong>
    <p>
        Run on-demand checks for the application, AI services, knowledge
        system and connected school services.
    </p>
</div>
"""
            )

        with toolbar_columns[1]:
            refresh_requested = st.button(
                "Run health checks",
                key="run_system_health_checks",
                type="primary",
                width="stretch",
            )

        report = st.session_state.get("system_health_report")

        if refresh_requested or not isinstance(report, dict):
            with st.spinner("Running Altitude health checks..."):
                report = _run_health_report()
            st.session_state["system_health_report"] = report
            _record_health_events(report)

        if not isinstance(report, dict):
            report = _run_health_report()
            st.session_state["system_health_report"] = report
            _record_health_events(report)

        st.html(_health_summary_html(report))

        for group in report.get("groups", []):
            if isinstance(group, dict):
                st.html(_health_group_html(group))

        st.html(_health_events_html())


SECTION_RENDERERS: dict[str, Callable[[], None]] = {
    "overview": _render_overview,
    "feedback": _render_feedback_section,
    "tickets": _render_tickets_section,
    "security": _render_security_section,
    "knowledge": _render_knowledge_section,
    "announcements": _render_announcements_section,
    "health": _render_health_section,
}


def _render_admin_navigation(
    username: str,
    cookie_controller: Any | None,
) -> None:
    crest_uri = image_data_uri("sjk_crest.png")
    crest_html = (
        f'<img src="{crest_uri}" class="sjk-admin-nav-crest" alt="SJK">'
        if crest_uri
        else '<div class="sjk-admin-nav-crest-fallback">SJK</div>'
    )

    st.html(
        f"""
<div class="sjk-admin-nav-brand">
    {crest_html}
    <div>
        <span>ALTITUDE</span>
        <strong>IT ADMIN</strong>
    </div>
</div>
"""
    )

    current_section = str(
        st.session_state.get("admin_active_section", "overview")
    )

    with st.container(key="admin_navigation", border=False):
        for label, section_key in ADMIN_SECTIONS:
            is_active = current_section == section_key
            button_key = (
                f"admin_nav_active_{section_key}"
                if is_active
                else f"admin_nav_{section_key}"
            )

            if st.button(
                label,
                key=button_key,
                width="stretch",
                disabled=is_active,
            ):
                st.session_state["admin_active_section"] = section_key
                st.rerun()

    st.html(
        f"""
<div class="sjk-admin-user-summary">
    <span>Signed in as</span>
    <strong>{escape(username)}</strong>
</div>
"""
    )

    if st.button(
        "Sign out",
        key="admin_logout_button",
        width="stretch",
    ):
        _clear_admin_session_cookie(cookie_controller)
        logout_admin()
        st.rerun()


def _render_admin_content() -> None:
    active_section = str(
        st.session_state.get("admin_active_section", "overview")
    )
    section_label = next(
        (
            label
            for label, section_key in ADMIN_SECTIONS
            if section_key == active_section
        ),
        "Overview",
    )
    section_description = SECTION_DESCRIPTIONS.get(
        active_section,
        SECTION_DESCRIPTIONS["overview"],
    )

    st.html(
        f"""
<div class="sjk-admin-content-header">
    <div>
        <span class="sjk-admin-greeting">
            {_get_time_greeting()}, IT Team
        </span>
        <h1>{escape(section_label)}</h1>
        <p>{escape(section_description)}</p>
    </div>
</div>
"""
    )

    with st.container(key="admin_content_scroll", border=False):
        renderer = SECTION_RENDERERS.get(active_section, _render_overview)
        renderer()


def render_admin() -> None:
    """Render the secure Altitude IT administrator portal."""
    _load_admin_styles()

    cookie_controller = _create_cookie_controller()
    _restore_admin_session(cookie_controller)

    if not is_admin_authenticated():
        login_placeholder = st.empty()

        with login_placeholder.container():
            authenticated_username = _render_admin_login()

        if authenticated_username is None:
            if CookieController is None:
                st.warning(
                    "Persistent login is unavailable because "
                    "streamlit-cookies-controller is not installed."
                )
            return

        # Clear the login UI first, then mount the cookie-writing component in
        # the live page and continue directly to the dashboard. Do not call
        # st.rerun() here: an immediate rerun can destroy the client component
        # before it writes the browser cookie.
        login_placeholder.empty()
        _save_admin_session(cookie_controller, authenticated_username)

    identity = get_admin_identity()

    if identity is None:
        logout_admin()
        st.rerun()

    st.session_state.setdefault("admin_active_section", "overview")

    with st.container(key="admin_page", border=False):
        navigation_column, content_column = st.columns(
            [1.0, 5.1],
            gap="small",
            vertical_alignment="top",
        )

        with navigation_column:
            with st.container(
                key="admin_nav_shell",
                border=False,
            ):
                _render_admin_navigation(identity.username, cookie_controller)

        with content_column:
            with st.container(
                key="admin_content_shell",
                border=False,
            ):
                _render_admin_content()