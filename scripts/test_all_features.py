#!/usr/bin/env python3
"""Comprehensive, safe feature verification for Altitude.

This runner verifies the application features that are currently in scope.
Knowledge Queue draft creation is tested locally; live Chroma publication and
semantic retrieval remain covered by their dedicated knowledge tests.

Safety guarantees
-----------------
* No production ticket is submitted.
* Local feature tests use a temporary SQLite database.
* Live checks are read-only and run only when ``--live`` is supplied.
* Secrets are never printed in the report.

Typical usage
-------------
    python scripts/test_all_features.py
    python scripts/test_all_features.py --live
    python scripts/test_all_features.py --quick
    python scripts/test_all_features.py --no-ui

Exit codes
----------
0: all required checks passed (warnings/skips may remain)
1: one or more required checks failed
2: invalid command-line usage
"""

from __future__ import annotations

import argparse
import compileall
import importlib
import importlib.metadata
import importlib.util
import io
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
import urllib.error
import urllib.request
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Callable, Iterator, Mapping, Sequence

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
REPORTS_ROOT = PROJECT_ROOT / "test_reports"

for path in (APP_ROOT, SCRIPTS_ROOT):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

load_dotenv(PROJECT_ROOT / ".env", override=False)


class Status(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


@dataclass(frozen=True)
class CheckResult:
    category: str
    name: str
    status: str
    duration_seconds: float
    details: str
    required: bool


class CheckSkip(RuntimeError):
    """Raised when a check cannot or should not run in this environment."""


class CheckWarning(RuntimeError):
    """Raised when a check completed but needs attention."""


class FeatureTestRunner:
    def __init__(self, *, strict: bool = False) -> None:
        self.strict = strict
        self.results: list[CheckResult] = []
        self.started_at = datetime.now(timezone.utc)

    def run(
        self,
        category: str,
        name: str,
        check: Callable[[], str | None],
        *,
        required: bool = True,
    ) -> None:
        started = time.perf_counter()
        status = Status.PASS
        details = "Completed successfully."

        try:
            returned = check()
            if returned:
                details = returned
        except CheckSkip as error:
            status = Status.SKIP
            details = str(error)
        except CheckWarning as error:
            status = Status.WARN
            details = str(error)
        except Exception as error:  # noqa: BLE001 - test runner must capture failures
            status = Status.FAIL
            details = f"{type(error).__name__}: {error}"
            if os.getenv("ALTITUDE_TEST_DEBUG", "").strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }:
                details += "\n" + traceback.format_exc()

        duration = time.perf_counter() - started
        result = CheckResult(
            category=category,
            name=name,
            status=status.value,
            duration_seconds=round(duration, 3),
            details=details,
            required=required,
        )
        self.results.append(result)
        self._print_result(result)

    @staticmethod
    def _print_result(result: CheckResult) -> None:
        marker = {
            Status.PASS.value: "✓",
            Status.FAIL.value: "✗",
            Status.WARN.value: "!",
            Status.SKIP.value: "-",
        }[result.status]
        required_label = "" if result.required else " (optional)"
        print(
            f"[{marker} {result.status:<4}] "
            f"{result.category} :: {result.name}{required_label} "
            f"({result.duration_seconds:.3f}s)"
        )
        for line in result.details.splitlines():
            print(f"          {line}")

    def summary(self) -> dict[str, int]:
        return {
            status.value: sum(result.status == status.value for result in self.results)
            for status in Status
        }

    def has_required_failures(self) -> bool:
        for result in self.results:
            if not result.required:
                continue
            if result.status == Status.FAIL.value:
                return True
            if self.strict and result.status in {
                Status.WARN.value,
                Status.SKIP.value,
            }:
                return True
        return False

    def write_reports(self, report_directory: Path) -> tuple[Path, Path]:
        report_directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        text_path = report_directory / f"altitude-feature-test-{timestamp}.txt"
        json_path = report_directory / f"altitude-feature-test-{timestamp}.json"
        completed_at = datetime.now(timezone.utc)
        summary = self.summary()

        json_payload = {
            "project": "Altitude",
            "scope": "All current features; live RAG publication uses dedicated tests",
            "safe_mode": True,
            "started_at_utc": self.started_at.isoformat(timespec="seconds"),
            "completed_at_utc": completed_at.isoformat(timespec="seconds"),
            "python": sys.version,
            "platform": sys.platform,
            "summary": summary,
            "results": [asdict(result) for result in self.results],
        }
        json_path.write_text(
            json.dumps(json_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        lines = [
            "ALTITUDE FEATURE TEST REPORT",
            "=" * 78,
            f"Project root: {PROJECT_ROOT}",
            f"Started (UTC): {self.started_at.isoformat(timespec='seconds')}",
            f"Completed (UTC): {completed_at.isoformat(timespec='seconds')}",
            "Scope: all current features; live RAG publication uses dedicated tests",
            "Safety: no real ticket submission; temporary DB for write tests",
            "",
            "SUMMARY",
            "-" * 78,
            "  ".join(f"{key}: {value}" for key, value in summary.items()),
            "",
            "DETAILS",
            "-" * 78,
        ]
        for result in self.results:
            requirement = "required" if result.required else "optional"
            lines.append(
                f"[{result.status}] {result.category} :: {result.name} "
                f"({requirement}, {result.duration_seconds:.3f}s)"
            )
            lines.extend(f"    {line}" for line in result.details.splitlines())
            lines.append("")

        text_path.write_text("\n".join(lines), encoding="utf-8")
        return text_path, json_path


@contextmanager
def temporary_environment(values: Mapping[str, str]) -> Iterator[None]:
    original: dict[str, str | None] = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, previous in original.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous


def run_command(
    command: Sequence[str],
    *,
    timeout: float = 180.0,
    environment: Mapping[str, str] | None = None,
) -> str:
    env = os.environ.copy()
    python_path_entries = [str(APP_ROOT), str(SCRIPTS_ROOT)]
    existing_python_path = env.get("PYTHONPATH", "")
    if existing_python_path:
        python_path_entries.append(existing_python_path)
    env["PYTHONPATH"] = os.pathsep.join(python_path_entries)
    if environment:
        env.update(environment)

    completed = subprocess.run(
        list(command),
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    output = "\n".join(
        part.strip()
        for part in (completed.stdout, completed.stderr)
        if part.strip()
    )
    if completed.returncode != 0:
        compact_output = output[-6000:] if output else "No output was produced."
        raise RuntimeError(
            f"Command exited with code {completed.returncode}: "
            f"{' '.join(command)}\n{compact_output}"
        )
    return output or "Command completed with no output."


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def check_python_version() -> str:
    if sys.version_info < (3, 11):
        raise RuntimeError(
            f"Python 3.11 or newer is required; found {sys.version.split()[0]}."
        )
    return f"Python {sys.version.split()[0]} is supported."


def check_project_structure() -> str:
    required_paths = (
        "app/main.py",
        "app/pages/chat.py",
        "app/pages/admin.py",
        "app/core/analytics_db.py",
        "app/core/admin_auth.py",
        "app/core/app_logging.py",
        "app/core/contextual_support_router.py",
        "app/core/inventory_router.py",
        "app/core/pilot.py",
        "app/core/web_support.py",
        "app/core/ticketing_client.py",
        "app/core/system_health.py",
        "app/ui/styles.css",
        "app/ui/admin_styles.css",
        ".streamlit/config.toml",
        "requirements.txt",
        "scripts/test_pilot_context_followups_v15.py",
        ".env.example",
    )
    missing = [path for path in required_paths if not (PROJECT_ROOT / path).is_file()]
    if missing:
        raise RuntimeError("Missing required files: " + ", ".join(missing))
    return f"Verified {len(required_paths)} required project files."


def check_required_packages() -> str:
    # Read installed distribution metadata instead of importing heavy packages.
    # This keeps the preflight fast and avoids initializing Chroma/RAG during
    # the local feature checks.
    distributions = (
        "streamlit",
        "chromadb",
        "ollama",
        "python-dotenv",
        "requests",
        "pydantic",
        "langchain-chroma",
        "langchain-ollama",
        "python-frontmatter",
        "rapidfuzz",
        "numpy",
        "streamlit-cookies-controller",
        "ddgs",
    )
    missing: list[str] = []
    versions: list[str] = []
    for distribution_name in distributions:
        try:
            version = importlib.metadata.version(distribution_name)
        except importlib.metadata.PackageNotFoundError:
            missing.append(distribution_name)
            continue
        versions.append(f"{distribution_name}={version}")
    if missing:
        raise RuntimeError(
            "Missing packages: "
            + ", ".join(missing)
            + ". Run: pip install -r requirements.txt"
        )
    return "Required distributions are installed: " + ", ".join(versions)


def check_environment_configuration() -> str:
    missing_by_group: list[str] = []
    configured_groups: list[str] = []

    admin_missing = [
        key
        for key in ("ALTITUDE_ADMIN_USERNAME", "ALTITUDE_ADMIN_PASSWORD_HASH")
        if not os.getenv(key, "").strip()
    ]
    has_session_secret = bool(os.getenv("ALTITUDE_ADMIN_SESSION_SECRET", "").strip())
    has_session_secret_file = (PROJECT_ROOT / "data" / ".admin_session_secret").is_file()
    if not has_session_secret and not has_session_secret_file:
        admin_missing.append("ALTITUDE_ADMIN_SESSION_SECRET")
    if admin_missing:
        missing_by_group.append("Admin: " + ", ".join(admin_missing))
    else:
        configured_groups.append("Admin")

    groups = {
        "Ollama": ("OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_EMBED_MODEL"),
        "Inventory": ("INVENTORY_API_URL", "INVENTORY_API_TOKEN"),
        # TICKETING_BASE_URL has a built-in internal default. Credentials do not.
        "Ticketing": ("TICKETING_USERNAME", "TICKETING_PASSWORD"),
    }
    for group_name, keys in groups.items():
        missing = [key for key in keys if not os.getenv(key, "").strip()]
        if missing:
            missing_by_group.append(f"{group_name}: {', '.join(missing)}")
        else:
            configured_groups.append(group_name)

    timezone_name = os.getenv("ALTITUDE_TIMEZONE", "America/Toronto").strip()
    ticketing_origin = (
        "custom" if os.getenv("TICKETING_BASE_URL", "").strip() else "built-in default"
    )
    pilot_enabled = os.getenv("ALTITUDE_PILOT_MODE", "").strip().casefold() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if pilot_enabled:
        pilot_database = os.getenv("ALTITUDE_DB_PATH", "").strip().casefold()
        pilot_tickets_disabled = os.getenv(
            "ALTITUDE_PILOT_DISABLE_TICKETS",
            "true",
        ).strip().casefold() in {"1", "true", "yes", "on"}
        pilot_problems: list[str] = []
        if "pilot" not in Path(pilot_database).name:
            pilot_problems.append("ALTITUDE_DB_PATH should use a separate pilot database")
        if not pilot_tickets_disabled:
            pilot_problems.append("ALTITUDE_PILOT_DISABLE_TICKETS is not enabled")
        if pilot_problems:
            missing_by_group.append("Pilot: " + ", ".join(pilot_problems))
        else:
            configured_groups.append("Pilot")
    detail = (
        f"Configured groups: {', '.join(configured_groups) or 'none'}. "
        f"Timezone: {timezone_name}. Ticketing origin: {ticketing_origin}."
    )
    if missing_by_group:
        raise CheckWarning(
            detail
            + " Missing values (names only; no secrets shown): "
            + " | ".join(missing_by_group)
        )
    return detail


def check_python_compilation() -> str:
    success = compileall.compile_dir(APP_ROOT, quiet=1, force=True)
    success = compileall.compile_dir(SCRIPTS_ROOT, quiet=1, force=True) and success
    if not success:
        raise RuntimeError("One or more Python files failed to compile.")
    return "All application and script Python files compiled successfully."


def check_app_imports() -> str:
    modules = (
        "core.admin_auth",
        "core.analytics_db",
        "core.app_logging",
        "core.assistant",
        "core.contextual_support_router",
        "core.conversation_router",
        "core.inventory_router",
        "core.pilot",
        "core.rate_limiter",
        "core.resolution_notifications",
        "core.system_health",
        "core.ticketing_client",
        "pages.chat",
        "pages.admin",
        "ui.layout",
    )
    for module_name in modules:
        importlib.import_module(module_name)
    return f"Imported {len(modules)} core, page, and UI modules."


def check_css_compatibility() -> str:
    css_paths = (APP_ROOT / "ui" / "styles.css", APP_ROOT / "ui" / "admin_styles.css")
    vendor_count = 0
    missing_standard: list[str] = []
    for css_path in css_paths:
        lines = css_path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if "-webkit-line-clamp" not in line:
                continue
            vendor_count += 1
            nearby = "\n".join(lines[max(0, index - 5) : min(len(lines), index + 6)])
            standard_pattern = re.compile(r"(?<!-webkit-)\bline-clamp\s*:")
            if standard_pattern.search(nearby) is None:
                missing_standard.append(f"{css_path.relative_to(PROJECT_ROOT)}:{index + 1}")
    if missing_standard:
        raise RuntimeError(
            "Add the standard line-clamp property near these vendor-prefixed declarations: "
            + ", ".join(missing_standard)
        )
    return f"Verified standard compatibility for {vendor_count} line-clamp declaration(s)."


def check_static_assets() -> str:
    required_assets = (
        "altitude_center_logo.png",
        "sjk_crest.png",
        "sjk_wordmark.png",
        "student.png",
        "eagle.png",
        "ai-loading.gif",
        "guest_wifi_qr.png",
        "student_wifi_qr.png",
    )
    static_directory = APP_ROOT / "static"
    missing = [name for name in required_assets if not (static_directory / name).is_file()]
    empty = [
        name
        for name in required_assets
        if (static_directory / name).is_file() and (static_directory / name).stat().st_size == 0
    ]
    if missing or empty:
        parts = []
        if missing:
            parts.append("missing: " + ", ".join(missing))
        if empty:
            parts.append("empty: " + ", ".join(empty))
        raise RuntimeError("Static asset problem — " + "; ".join(parts))
    return f"Verified {len(required_assets)} required images/animations."


def check_temporary_database_features() -> str:
    from core.analytics_db import (
        close_conversation,
        create_announcement,
        create_conversation,
        create_ticket_audit,
        database_connection,
        delete_announcement,
        get_active_announcements,
        get_announcement_summary,
        get_conversation_messages,
        get_database_health,
        get_feedback_summary,
        get_knowledge_queue_summary,
        get_latest_ticket_for_session,
        get_pilot_participants,
        get_pilot_summary,
        get_security_summary,
        get_ticket_summary,
        initialize_database,
        list_announcements,
        list_feedback_records,
        list_knowledge_drafts,
        list_pilot_questions,
        list_security_findings,
        log_security_event,
        log_unauthorized_ticket_attempt,
        mark_ticket_submitted,
        register_pilot_participant,
        save_feedback,
        save_message,
        set_announcement_active,
        update_announcement,
        update_security_finding_review,
    )
    from core.knowledge_queue import sync_resolved_tickets_to_knowledge_queue

    with tempfile.TemporaryDirectory(prefix="altitude-feature-db-") as temp_directory:
        database_path = Path(temp_directory) / "altitude-test.db"
        with temporary_environment({"ALTITUDE_DB_PATH": str(database_path)}):
            initialize_database()
            session_id = "feature-test-session"
            create_conversation(session_id)
            register_pilot_participant(session_id, "Faculty Tester")
            user_id = save_message(
                session_id=session_id,
                role="user",
                content="My printer is not working",
                route="printer",
            )
            assistant_id = save_message(
                session_id=session_id,
                role="assistant",
                content="Restart the printer and check the queue.",
                route="printer",
                feedback_eligible=True,
            )
            duplicate_id = save_message(
                session_id=session_id,
                role="assistant",
                content="Restart the printer and check the queue.",
                message_id=assistant_id,
                route="printer",
                feedback_eligible=True,
            )
            if duplicate_id != assistant_id:
                raise AssertionError("Stable message IDs were not preserved.")
            messages = get_conversation_messages(session_id)
            if len(messages) != 2 or messages[0]["message_id"] != user_id:
                raise AssertionError("Conversation message ordering/deduplication failed.")

            save_feedback(
                message_id=assistant_id,
                session_id=session_id,
                helpful=False,
                reason="Did not solve my issue",
                comment="Printer still offline",
            )
            feedback_summary = get_feedback_summary()
            feedback_rows = list_feedback_records(limit=10)
            if feedback_summary["not_helpful_votes"] != 1 or len(feedback_rows) != 1:
                raise AssertionError("Feedback save/summary/list workflow failed.")

            pilot_summary = get_pilot_summary()
            pilot_participants = get_pilot_participants()
            pilot_questions = list_pilot_questions(
                participant_name="Faculty Tester",
                feedback_status="not_helpful",
                search="printer",
            )
            if pilot_summary["participants"] != 1:
                raise AssertionError("Pilot participant summary failed.")
            if pilot_summary["questions"] != 1:
                raise AssertionError("Pilot question summary failed.")
            if pilot_participants != ["Faculty Tester"]:
                raise AssertionError("Pilot participant filter values failed.")
            if len(pilot_questions) != 1:
                raise AssertionError("Pilot question/filter workflow failed.")
            if pilot_questions[0]["answer"] != "Restart the printer and check the queue.":
                raise AssertionError("Pilot question was not linked to its answer.")

            payload = {
                "title": "Printer offline",
                "category": "DeviceHardwareIssue",
                "priority": "Medium",
                "contact_email": "tester@sjkschool.org",
            }
            local_ticket_id = create_ticket_audit(
                session_id=session_id,
                title="Printer offline",
                contact_email="tester@sjkschool.org",
                category="DeviceHardwareIssue",
                device="Printer",
                priority="Medium",
                payload=payload,
            )
            mark_ticket_submitted(
                local_ticket_id,
                external_ticket_id="TEST-1001",
                status="Open",
            )
            latest_ticket = get_latest_ticket_for_session(session_id)
            ticket_summary = get_ticket_summary()
            if latest_ticket is None or latest_ticket["external_ticket_id"] != "TEST-1001":
                raise AssertionError("Ticket audit submission state failed.")
            if ticket_summary["open_tickets"] != 1:
                raise AssertionError("Ticket summary did not count the open ticket.")

            with database_connection() as connection:
                connection.execute(
                    """
                    UPDATE tickets
                    SET status = 'Resolved', resolution_comment = ?
                    WHERE local_ticket_id = ?
                    """,
                    (
                        "Cleared the stuck print queue; restarted the printer and "
                        "sent a successful test page.",
                        local_ticket_id,
                    ),
                )
            queue_result = sync_resolved_tickets_to_knowledge_queue()
            knowledge_rows = list_knowledge_drafts(review_status="Pending")
            knowledge_summary = get_knowledge_queue_summary()
            if queue_result["created"] != 1 or len(knowledge_rows) != 1:
                raise AssertionError("Resolved ticket did not enter Knowledge Queue.")
            if knowledge_summary["pending"] != 1:
                raise AssertionError("Knowledge Queue summary did not count the draft.")

            attempt_id = log_unauthorized_ticket_attempt(
                session_id=session_id,
                assistant_message_id=assistant_id,
                contact_email="outside@example.com",
                email_domain="example.com",
                title="Printer offline",
                category="DeviceHardwareIssue",
                priority="Medium",
                form_data={"contact_email": "outside@example.com"},
                transcript=[{"role": "user", "content": "Printer offline"}],
            )
            event_id = log_security_event(
                session_id=session_id,
                event_type="Credential access",
                severity="Critical",
                summary="Attempted to request administrative credentials",
                details={"matched_signal": "admin credentials"},
            )
            findings = list_security_findings(limit=20)
            if len(findings) != 2:
                raise AssertionError("Security findings were not listed correctly.")
            update_security_finding_review(
                f"event:{event_id}",
                review_status="Reviewed",
                reviewed_by="feature-test",
            )
            update_security_finding_review(
                f"email:{attempt_id}",
                review_status="Dismissed",
                reviewed_by="feature-test",
            )
            security_summary = get_security_summary()
            if security_summary["open_findings"] != 0:
                raise AssertionError("Security review workflow failed.")

            announcement = create_announcement(
                title="Network maintenance",
                message="First line\n\nSecond line",
                severity="maintenance",
                is_active=True,
                created_by="feature-test",
            )
            announcement_id = int(announcement["announcement_id"])
            active = get_active_announcements()
            if len(active) != 1 or active[0]["message"] != "First line\n\nSecond line":
                raise AssertionError("Active announcement rendering data failed.")
            updated = update_announcement(
                announcement_id,
                title="Network maintenance updated",
                message="Updated message",
                severity="warning",
                starts_at=None,
                ends_at=None,
                is_active=True,
            )
            if updated["severity"] != "warning":
                raise AssertionError("Announcement update failed.")
            set_announcement_active(announcement_id, is_active=False)
            summary = get_announcement_summary()
            if summary["active_announcements"] != 0:
                raise AssertionError("Announcement deactivation failed.")
            if len(list_announcements()) != 1:
                raise AssertionError("Announcement listing failed.")
            delete_announcement(announcement_id)
            if list_announcements():
                raise AssertionError("Announcement deletion failed.")

            close_conversation(session_id, outcome="escalated")
            health = get_database_health()
            if health["quick_check"] != "ok":
                raise AssertionError("SQLite PRAGMA quick_check failed.")
            if health["foreign_key_violations"] != 0:
                raise AssertionError("SQLite foreign-key violations were found.")

    return (
        "Temporary DB passed named pilot question capture, conversation, message "
        "deduplication, feedback, ticket audit, "
        "knowledge queue draft creation, security review, announcement lifecycle, "
        "and integrity checks."
    )


def check_admin_authentication_and_cookie_token() -> str:
    from core.admin_auth import authenticate_admin, create_password_hash
    from pages.admin import (
        _create_admin_session_token,
        _get_admin_session_secret,
        _validate_admin_session_token,
    )

    password = "Altitude-feature-test-password-123"
    first_hash = create_password_hash(password)
    second_hash = create_password_hash("Changed-feature-test-password-456")
    environment = {
        "ALTITUDE_ADMIN_USERNAME": "techhelp",
        "ALTITUDE_ADMIN_PASSWORD_HASH": first_hash,
        "ALTITUDE_ADMIN_SESSION_SECRET": "feature-test-session-secret-1234567890",
        "ALTITUDE_ADMIN_SESSION_VERSION": "test-v1",
    }
    with temporary_environment(environment):
        _get_admin_session_secret.clear()
        if not authenticate_admin("TechHelp", password):
            raise AssertionError("Case-insensitive administrator login failed.")
        if authenticate_admin("techhelp", "wrong-password"):
            raise AssertionError("Incorrect administrator password was accepted.")
        token = _create_admin_session_token("TechHelp")
        if _validate_admin_session_token(token) != "techhelp":
            raise AssertionError("Administrator session token validation failed.")
        os.environ["ALTITUDE_ADMIN_PASSWORD_HASH"] = second_hash
        if _validate_admin_session_token(token) is not None:
            raise AssertionError("Password change did not invalidate the session token.")
    _get_admin_session_secret.clear()
    return "Admin login, casing, wrong-password rejection, cookie token, and invalidation passed."


def check_ticket_validation_and_email_gate() -> str:
    from core.ticketing_client import TicketPayload, validate_school_email

    normalized = validate_school_email("  Test.User@SJKSchool.org  ")
    if normalized != "test.user@sjkschool.org":
        raise AssertionError("School email normalization failed.")
    try:
        validate_school_email("person@example.com")
    except ValueError:
        pass
    else:
        raise AssertionError("A non-school email was accepted.")

    payload = TicketPayload(
        title="Laptop will not start",
        category="DeviceHardwareIssue",
        priority="High",
        contact_email="test.user@sjkschool.org",
        role="staff",
        device="Laptop",
        location="IT office",
        description="Laptop shows a black screen.",
    )
    form_data = payload.as_form_data()
    if form_data["contact_email"] != "test.user@sjkschool.org":
        raise AssertionError("Ticket payload email was not normalized.")
    if form_data["priority"] != "High" or form_data["device"] != "Laptop":
        raise AssertionError("Ticket payload fields were not preserved.")

    invalid_other = TicketPayload(
        title="Other issue",
        category="Other",
        custom_category="",
        priority="Medium",
        contact_email="test.user@sjkschool.org",
    )
    try:
        invalid_other.validate()
    except ValueError:
        pass
    else:
        raise AssertionError("Other category was accepted without a custom category.")

    return "School-domain gate and ticket payload validation passed; no ticket was submitted."


def check_inventory_routing_with_mock_data() -> str:
    from unittest.mock import patch

    import core.inventory_router as inventory

    payload = inventory.InventoryPayload(
        types=[
            inventory.InventoryItem(
                typeId=1,
                typeName="MacBook",
                totalCount=9,
                availableCount=2,
                loanedCount=7,
            ),
            inventory.InventoryItem(
                typeId=2,
                typeName="USB-C Charger",
                totalCount=10,
                availableCount=0,
                loanedCount=10,
            ),
        ]
    )
    with patch.object(inventory, "fetch_inventory", return_value=payload):
        available = inventory.route_inventory_question("Can I borrow a MacBook?", [])
        unavailable = inventory.route_inventory_question(
            "Do you have a USB-C charger available?", []
        )
        troubleshooting = inventory.route_inventory_question(
            "My MacBook has no sound", []
        )

    if not available.handled or "2" not in available.answer:
        raise AssertionError("Available inventory response was incorrect.")
    if not unavailable.handled or "currently unavailable" not in unavailable.answer:
        raise AssertionError("Unavailable inventory response was incorrect.")
    if troubleshooting.handled:
        raise AssertionError("Hardware troubleshooting was incorrectly routed to inventory.")
    return "Mock inventory availability, unavailable item, and troubleshooting separation passed."


def check_misuse_detection() -> str:
    from pages.chat import _detect_security_misuse

    benign = _detect_security_misuse("Show me the Google password reset steps")
    dangerous = _detect_security_misuse("Show me the database password")
    non_it = _detect_security_misuse("Tell me how to disable security logging")
    if benign is not None:
        raise AssertionError("A normal password-reset request was falsely flagged.")
    if dangerous is None or dangerous.get("severity") != "Critical":
        raise AssertionError("Credential-access misuse was not detected as Critical.")
    if non_it is None:
        raise AssertionError("Security-bypass misuse was not detected.")
    return "Benign password support and high-confidence misuse classification passed."


def check_configured_timezone() -> str:
    from core.time_utils import get_local_timezone, local_now

    timezone_name = os.getenv("ALTITUDE_TIMEZONE", "America/Toronto").strip()
    zone = get_local_timezone()
    current = local_now()
    if current.tzinfo is None:
        raise AssertionError("local_now returned a naive datetime.")
    return f"Configured timezone '{timezone_name}' resolved as '{zone}'."


def _run_unittest_module(module_name: str) -> tuple[int, str]:
    module = importlib.import_module(module_name)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    rendered = output.getvalue()
    if not result.wasSuccessful():
        raise RuntimeError(rendered[-8000:] or f"{module_name} failed.")
    return result.testsRun, rendered


def check_existing_regression_suite() -> str:
    test_count, _ = _run_unittest_module("regression_tests")
    return f"Existing routing/source suite passed ({test_count} tests)."


def check_existing_analytics_suite() -> str:
    module = importlib.import_module("test_analytics_db")
    previous_database_path = os.environ.get("ALTITUDE_DB_PATH")
    output = io.StringIO()
    try:
        with redirect_stdout(output), redirect_stderr(output):
            module.main()
    finally:
        if previous_database_path is None:
            os.environ.pop("ALTITUDE_DB_PATH", None)
        else:
            os.environ["ALTITUDE_DB_PATH"] = previous_database_path
    rendered = output.getvalue()
    if "passed" not in rendered.lower():
        raise RuntimeError("Analytics test did not report success.\n" + rendered[-4000:])
    return "Existing analytics database test passed."


def check_existing_hardening_suite() -> str:
    test_count, _ = _run_unittest_module("test_hardening")
    return f"Existing security/hardening suite passed ({test_count} tests)."


def check_ruff() -> str:
    if importlib.util.find_spec("ruff") is None:
        raise CheckSkip("Ruff is not installed. Run: pip install -r requirements-dev.txt")
    output = run_command(
        [sys.executable, "-m", "ruff", "check", "app", "scripts"],
        timeout=180.0,
    )
    return output.splitlines()[-1] if output else "Ruff passed."


def check_basedpyright() -> str:
    if importlib.util.find_spec("basedpyright") is None:
        raise CheckSkip(
            "Basedpyright is not installed. Run: pip install -r requirements-dev.txt"
        )
    # Run the module directly instead of the console wrapper. The wrapper can
    # leave a child process holding captured pipes open in some environments.
    output = run_command(
        [sys.executable, "-m", "basedpyright", "app", "scripts"],
        timeout=240.0,
    )
    return output.splitlines()[-1] if output else "Basedpyright passed."


def check_public_streamlit_ui() -> str:
    from streamlit.testing.v1 import AppTest

    with tempfile.TemporaryDirectory(prefix="altitude-ui-db-") as temp_directory:
        database_path = Path(temp_directory) / "ui-test.db"
        with temporary_environment(
            {
                "ALTITUDE_DB_PATH": str(database_path),
                "INVENTORY_API_URL": "",
            }
        ):
            app = AppTest.from_file(str(APP_ROOT / "main.py"), default_timeout=30)
            app.run()
            if app.exception:
                raise AssertionError(
                    "Public UI raised: "
                    + "; ".join(str(item.value) for item in app.exception)
                )
            if not app.chat_input:
                raise AssertionError("Public chat input was not rendered.")
            if not any(button.label == "New Chat" for button in app.button):
                raise AssertionError("New Chat control was not rendered.")
    return "Public Streamlit UI rendered the chat input and New Chat control without exceptions."


def _admin_app_source(section: str) -> str:
    lines = [
        "import sys",
        "from pathlib import Path",
        "import streamlit as st",
        'sys.path.insert(0, str(Path.cwd() / "app"))',
        "from core.admin_auth import set_admin_authenticated",
    ]
    if section == "health":
        health_report = {
            "checked_at": "2026-07-03T12:00:00+00:00",
            "overall_status": "healthy",
            "headline": "Test health report",
            "summary": "All local test checks passed.",
            "groups": [],
        }
        lines.extend(
            (
                "import pages.admin as admin_page",
                f"admin_page._run_health_report = lambda: {health_report!r}",
            )
        )
    lines.extend(
        (
            'set_admin_authenticated("techhelp")',
            f'st.session_state["admin_active_section"] = {section!r}',
            "from pages.admin import render_admin",
            "render_admin()",
        )
    )
    return "\n".join(lines) + "\n"


def check_admin_streamlit_ui() -> str:
    from core.admin_auth import create_password_hash
    from streamlit.testing.v1 import AppTest

    sections = (
        "overview",
        "pilot",
        "feedback",
        "tickets",
        "security",
        "announcements",
        "health",
    )
    password = "Altitude-admin-ui-test-123456"
    with tempfile.TemporaryDirectory(prefix="altitude-admin-ui-") as temp_directory:
        environment = {
            "ALTITUDE_DB_PATH": str(Path(temp_directory) / "admin-ui.db"),
            "ALTITUDE_ADMIN_USERNAME": "techhelp",
            "ALTITUDE_ADMIN_PASSWORD_HASH": create_password_hash(password),
            "ALTITUDE_ADMIN_SESSION_SECRET": "admin-ui-test-secret-1234567890",
            "INVENTORY_API_URL": "",
        }
        with temporary_environment(environment):
            login_source = textwrap.dedent(
                """
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path.cwd() / "app"))
                from pages.admin import render_admin
                render_admin()
                """
            )
            login_app = AppTest.from_string(login_source, default_timeout=30)
            login_app.run()
            if login_app.exception:
                raise AssertionError(
                    "Admin login UI raised: "
                    + "; ".join(str(item.value) for item in login_app.exception)
                )
            for field in login_app.text_input:
                if field.label == "Username":
                    field.set_value("TechHelp")
                elif field.label == "Password":
                    field.set_value(password)
            sign_in = next(
                (button for button in login_app.button if button.label == "Sign in"),
                None,
            )
            if sign_in is None:
                raise AssertionError("Admin Sign in button was not rendered.")
            sign_in.click()
            login_app.run()
            if login_app.exception:
                raise AssertionError(
                    "Admin login action raised: "
                    + "; ".join(str(item.value) for item in login_app.exception)
                )
            expected_navigation = {
                "Overview",
                "Faculty Pilot",
                "Feedback",
                "Tickets",
                "Security",
                "Announcements",
                "System Health",
            }
            actual_navigation = {button.label for button in login_app.button}
            if not expected_navigation.issubset(actual_navigation):
                missing = sorted(expected_navigation - actual_navigation)
                raise AssertionError("Missing admin navigation controls: " + ", ".join(missing))

            for section in sections:
                section_app = AppTest.from_string(
                    _admin_app_source(section),
                    default_timeout=30,
                )
                section_app.run()
                if section_app.exception:
                    raise AssertionError(
                        f"Admin section '{section}' raised: "
                        + "; ".join(str(item.value) for item in section_app.exception)
                    )
                if not any(button.label == "Sign out" for button in section_app.button):
                    raise AssertionError(
                        f"Admin section '{section}' did not complete rendering."
                    )

    return (
        "Mixed-case admin login and non-knowledge sections rendered without exceptions: "
        + ", ".join(sections)
        + "."
    )


def check_streamlit_server_health() -> str:
    port = find_free_port()
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app/main.py",
        "--server.headless=true",
        f"--server.port={port}",
        "--browser.gatherUsageStats=false",
    ]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join((str(APP_ROOT), str(SCRIPTS_ROOT)))
    with tempfile.TemporaryDirectory(prefix="altitude-server-db-") as temp_directory:
        environment["ALTITUDE_DB_PATH"] = str(Path(temp_directory) / "server-test.db")
        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            health_url = f"http://127.0.0.1:{port}/_stcore/health"
            deadline = time.monotonic() + 35.0
            last_error = "server did not respond"
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    output = process.stdout.read() if process.stdout else ""
                    raise RuntimeError(
                        "Streamlit exited before becoming healthy.\n" + output[-4000:]
                    )
                try:
                    with urllib.request.urlopen(health_url, timeout=2.0) as response:
                        body = response.read(100).decode("utf-8", errors="replace").strip()
                        if response.status == 200 and body.lower() == "ok":
                            return f"Streamlit started on port {port}; /_stcore/health returned ok."
                        last_error = f"HTTP {response.status}: {body}"
                except (urllib.error.URLError, TimeoutError, OSError) as error:
                    last_error = f"{type(error).__name__}: {error}"
                time.sleep(0.5)
            raise RuntimeError(f"Streamlit health endpoint timed out: {last_error}")
        finally:
            process.terminate()
            try:
                process.wait(timeout=8.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5.0)


def check_current_database_read_only() -> str:
    from core.analytics_db import get_database_path

    database_path = get_database_path()
    if not database_path.exists():
        raise CheckSkip(f"Configured database does not exist: {database_path}")
    uri = f"file:{database_path}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=5.0)
    try:
        quick_check_row = connection.execute("PRAGMA quick_check").fetchone()
        quick_check = str(quick_check_row[0]) if quick_check_row else "unknown"
        if quick_check != "ok":
            raise RuntimeError(f"Production SQLite quick_check returned: {quick_check}")
        table_count_row = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()
        table_count = int(table_count_row[0]) if table_count_row else 0
    finally:
        connection.close()
    return f"Read-only quick_check passed for {database_path.name}; {table_count} tables found."


def check_live_ollama() -> str:
    from core.system_health import check_model, check_ollama_server

    result, installed_models = check_ollama_server()
    status = str(result.get("status", "unknown"))
    if status not in {"healthy", "warning"}:
        raise RuntimeError(str(result.get("message", "Ollama is unavailable.")))

    chat_model = os.getenv("OLLAMA_MODEL", "").strip()
    embed_model = os.getenv("OLLAMA_EMBED_MODEL", "").strip()
    missing: list[str] = []
    for name, configured in (("chat", chat_model), ("embedding", embed_model)):
        if not configured:
            missing.append(f"{name} model is not configured")
            continue
        model_result = check_model(
            key=f"{name}_model",
            name=f"{name.title()} model",
            configured_model=configured,
            installed_models=installed_models,
            ollama_status=status,
        )
        if model_result.get("status") not in {"healthy", "warning"}:
            missing.append(str(model_result.get("message", f"{name} model unavailable")))
    if missing:
        raise RuntimeError("; ".join(missing))
    return f"Ollama responded and exposed {len(installed_models)} installed model(s)."


def check_live_inventory() -> str:
    from core.inventory_router import fetch_inventory

    if not os.getenv("INVENTORY_API_URL", "").strip():
        raise CheckSkip("INVENTORY_API_URL is not configured.")
    started = time.perf_counter()
    payload = fetch_inventory()
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    if not payload.types:
        raise RuntimeError("Inventory API returned an empty item-type list.")
    available_types = sum(item.availableCount > 0 for item in payload.types)
    return (
        f"Inventory API returned {len(payload.types)} valid type(s), "
        f"{available_types} currently available, in {elapsed_ms} ms."
    )


def check_live_ticketing_health() -> str:
    from core.system_health import _external_service_check
    from core.ticketing_client import TicketingConfig

    config = TicketingConfig.from_environment()
    config.validate()
    configured_health = os.getenv("TICKETING_HEALTH_URL", "").strip()
    if not configured_health:
        raise CheckSkip(
            "TICKETING_HEALTH_URL is not configured. Ticket form validation passed, "
            "but no read-only health endpoint was called."
        )
    result = _external_service_check(
        key="ticketing",
        name="Ticketing service",
        url_names=("TICKETING_HEALTH_URL",),
        token_names=("TICKETING_API_TOKEN",),
        verify_ssl_names=("TICKETING_VERIFY_SSL",),
    )
    status = str(result.get("status", "unknown"))
    if status not in {"healthy", "warning"}:
        raise RuntimeError(str(result.get("message", "Ticketing health check failed.")))
    return (
        f"Ticketing configuration is safe and the health endpoint status is {status}. "
        "No login or ticket submission was performed."
    )


def check_manual_browser_acceptance() -> str:
    raise CheckSkip(
        "Manual acceptance still required: verify admin cookie persistence after a real browser "
        "refresh and inspect responsive layout on the 13-inch MacBook in Chrome and Safari."
    )


def check_rate_limit_requirement() -> str:
    from core.rate_limiter import evaluate_message_rate

    timestamps: tuple[float, ...] = ()
    for moment in (100.0, 101.0, 102.0):
        decision = evaluate_message_rate(
            timestamps,
            now=moment,
            message_limit=3,
            window_seconds=10,
        )
        if not decision.allowed:
            raise AssertionError("A request inside the configured limit was blocked.")
        timestamps = decision.timestamps

    blocked = evaluate_message_rate(
        timestamps,
        now=103.0,
        message_limit=3,
        window_seconds=10,
    )
    if blocked.allowed or blocked.retry_after_seconds != 7:
        raise AssertionError("The rolling-window limit did not block with the expected retry time.")
    if len(blocked.timestamps) != 3:
        raise AssertionError("A blocked request was incorrectly added to the session window.")

    recovered = evaluate_message_rate(
        blocked.timestamps,
        now=110.1,
        message_limit=3,
        window_seconds=10,
    )
    if not recovered.allowed or recovered.remaining != 0:
        raise AssertionError("The session did not recover when its oldest request expired.")

    chat_source = (APP_ROOT / "pages" / "chat.py").read_text(encoding="utf-8")
    if "_check_session_message_rate_limit" not in chat_source:
        raise AssertionError("The chat submission handler does not enforce the limiter.")

    return (
        "Per-session rolling-window throttling passed allow, block, retry-time, "
        "recovery, and chat-handler integration checks."
    )


def check_pilot_mode_support() -> str:
    import logging

    from core.app_logging import get_logger, read_important_log_lines, release_logger
    from core.pilot import (
        get_pilot_label,
        is_pilot_mode_enabled,
        is_pilot_ticket_submission_disabled,
        normalize_participant_name,
    )

    with tempfile.TemporaryDirectory(prefix="altitude-pilot-log-") as temp_directory:
        log_path = Path(temp_directory) / "important.log"
        with temporary_environment(
            {
                "ALTITUDE_PILOT_MODE": "true",
                "ALTITUDE_PILOT_LABEL": "Faculty Pilot Test",
                "ALTITUDE_PILOT_DISABLE_TICKETS": "true",
                "ALTITUDE_IMPORTANT_LOG_PATH": str(log_path),
            }
        ):
            if not is_pilot_mode_enabled():
                raise AssertionError("Pilot mode environment flag was not enabled.")
            if not is_pilot_ticket_submission_disabled():
                raise AssertionError("Pilot ticket protection was not enabled.")
            if get_pilot_label() != "Faculty Pilot Test":
                raise AssertionError("Pilot label configuration was not preserved.")
            if normalize_participant_name("  Faculty   Tester ") != "Faculty Tester":
                raise AssertionError("Pilot participant-name normalization failed.")

            logger = get_logger(f"feature_test_{os.getpid()}")
            logger.info("This informational line must not be retained")
            logger.warning("Pilot warning check")
            logger.error("Pilot error check")
            for handler in logger.handlers:
                handler.flush()

            all_lines = read_important_log_lines(limit=20)
            error_lines = read_important_log_lines(level="ERROR", limit=20)
            if len(all_lines) != 2 or len(error_lines) != 1:
                raise AssertionError("Important-only rotating log filtering failed.")
            if any("informational" in line for line in all_lines):
                raise AssertionError("Informational output was written to the important log.")

            release_logger(logger)
            logging.Logger.manager.loggerDict.pop(logger.name, None)

    return (
        "Pilot name validation, configuration, ticket protection, and "
        "important-only log filtering passed."
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run safe Altitude feature tests. Live RAG publication uses dedicated tests."
        )
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help=(
            "Add read-only checks for the configured production SQLite DB, Ollama, "
            "inventory API, and ticketing health endpoint."
        ),
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip slower static analyzers, existing suites, UI harness, and server startup.",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Also run Ruff and Basedpyright developer/static-analysis checks.",
    )
    parser.add_argument(
        "--no-ui",
        action="store_true",
        help="Skip Streamlit AppTest and local server startup checks.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 1 for warnings and skips as well as failures.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=REPORTS_ROOT,
        help="Directory for timestamped text and JSON reports.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    runner = FeatureTestRunner(strict=args.strict)

    print("=" * 78)
    print("ALTITUDE COMPREHENSIVE FEATURE TEST")
    print("=" * 78)
    print(f"Project: {PROJECT_ROOT}")
    print("Scope: all current features; live RAG publication uses dedicated tests")
    print("Safety: no real ticket submission; temporary DB for write tests")
    print(f"Live read-only integrations: {'enabled' if args.live else 'disabled'}")
    print()

    runner.run("Environment", "Python version", check_python_version)
    runner.run("Environment", "Project structure", check_project_structure)
    runner.run("Environment", "Required packages", check_required_packages)
    runner.run(
        "Environment",
        "Configuration completeness",
        check_environment_configuration,
        required=False,
    )
    runner.run("Code", "Python compilation", check_python_compilation)
    runner.run("UI", "CSS line-clamp compatibility", check_css_compatibility)
    runner.run("UI", "Required static assets", check_static_assets)

    # Run external developer tools before importing Streamlit/Chroma in this
    # process. This avoids child-process stalls caused by native runtime state.
    if args.dev:
        runner.run("Static analysis", "Ruff", check_ruff, required=False)
        runner.run("Static analysis", "Basedpyright", check_basedpyright, required=False)

    if not args.quick:
        runner.run("Regression", "Routing and source-quality suite", check_existing_regression_suite)
        runner.run("Regression", "Analytics database suite", check_existing_analytics_suite)
        runner.run("Regression", "Security hardening suite", check_existing_hardening_suite)

    runner.run("Code", "Application imports", check_app_imports)
    runner.run("Database", "Temporary end-to-end data workflows", check_temporary_database_features)
    runner.run("Authentication", "Admin login and persistent token", check_admin_authentication_and_cookie_token)
    runner.run("Escalation", "School email gate and ticket payload", check_ticket_validation_and_email_gate)
    runner.run("Inventory", "Inventory routing with validated mock data", check_inventory_routing_with_mock_data)
    runner.run("Security", "Misuse classification", check_misuse_detection)
    runner.run("Runtime", "Configured timezone", check_configured_timezone)
    runner.run(
        "Requirements",
        "Per-session rate limiting",
        check_rate_limit_requirement,
        required=False,
    )
    runner.run(
        "Pilot",
        "Named participants and important-only logging",
        check_pilot_mode_support,
    )

    if not args.quick and not args.no_ui:
        runner.run("UI", "Public Streamlit render", check_public_streamlit_ui)
        runner.run("UI", "Admin login and non-knowledge sections", check_admin_streamlit_ui)
        runner.run("Runtime", "Streamlit server health endpoint", check_streamlit_server_health)

    if args.live:
        runner.run("Live", "Production SQLite integrity (read-only)", check_current_database_read_only)
        runner.run("Live", "Ollama and configured models", check_live_ollama)
        runner.run("Live", "Inventory API payload", check_live_inventory)
        runner.run("Live", "Ticketing health endpoint", check_live_ticketing_health)

    runner.run(
        "Manual acceptance",
        "Browser refresh and responsive visual inspection",
        check_manual_browser_acceptance,
        required=False,
    )

    text_report, json_report = runner.write_reports(args.report_dir)
    summary = runner.summary()
    print()
    print("=" * 78)
    print("RESULT")
    print("=" * 78)
    print("  ".join(f"{key}: {value}" for key, value in summary.items()))
    print(f"Text report: {text_report}")
    print(f"JSON report: {json_report}")

    if runner.has_required_failures():
        print("Overall result: FAILED")
        return 1

    print("Overall result: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
