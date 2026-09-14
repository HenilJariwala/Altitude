from __future__ import annotations

import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from core.admin_auth import authenticate_admin, create_password_hash
from core.analytics_db import (
    create_announcement,
    create_conversation,
    database_connection,
    get_database_health,
    initialize_database,
)
from core.system_health import _validate_http_endpoint, check_application_runtime
from core.ticketing_client import (
    DjangoTicketingClient,
    TicketingClientError,
    TicketingConfig,
)
from pages.admin import (
    _create_admin_session_token,
    _get_admin_session_secret,
    _validate_admin_session_token,
)
from pages.chat import _detect_security_misuse
from package_release import build_release_archive


class AltitudeHardeningTests(unittest.TestCase):
    def test_active_conversation_metric_ignores_stale_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "altitude.db"
            with patch.dict(
                os.environ,
                {"ALTITUDE_DB_PATH": str(database_path)},
                clear=False,
            ):
                initialize_database()
                create_conversation("recent-session")
                create_conversation("stale-session")
                with database_connection() as connection:
                    connection.execute(
                        """
                        UPDATE conversations
                        SET updated_at = '2000-01-01T00:00:00+00:00'
                        WHERE session_id = 'stale-session'
                        """
                    )
                health = get_database_health()

        self.assertEqual(health["active_conversation_count"], 1)

    def test_application_runtime_uses_configured_timezone(self) -> None:
        with patch.dict(
            os.environ,
            {"ALTITUDE_TIMEZONE": "America/Toronto"},
            clear=False,
        ):
            result = check_application_runtime()

        timezone_detail = dict(result["details"])["Local timezone"]
        self.assertIn("America/Toronto", timezone_detail)

    def test_admin_cookie_uses_canonical_username_and_password_fingerprint(self) -> None:
        first_hash = create_password_hash("A-long-test-password-123")
        second_hash = create_password_hash("A-different-test-password-456")
        environment = {
            "ALTITUDE_ADMIN_USERNAME": "techhelp",
            "ALTITUDE_ADMIN_PASSWORD_HASH": first_hash,
            "ALTITUDE_ADMIN_SESSION_SECRET": "test-session-secret-not-for-production",
        }

        with patch.dict(os.environ, environment, clear=False):
            _get_admin_session_secret.clear()
            self.assertTrue(authenticate_admin("TechHelp", "A-long-test-password-123"))

            token = _create_admin_session_token("TechHelp")
            self.assertEqual(_validate_admin_session_token(token), "techhelp")

            os.environ["ALTITUDE_ADMIN_PASSWORD_HASH"] = second_hash
            self.assertIsNone(_validate_admin_session_token(token))

        _get_admin_session_secret.clear()

    def test_announcement_message_preserves_intentional_line_breaks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "altitude.db"
            with patch.dict(
                os.environ,
                {"ALTITUDE_DB_PATH": str(database_path)},
                clear=False,
            ):
                initialize_database()
                announcement = create_announcement(
                    title="  Network   maintenance  ",
                    message="First line  \n\n\n Second   line",
                    created_by="techhelp",
                )

        self.assertEqual(announcement["title"], "Network maintenance")
        self.assertEqual(announcement["message"], "First line\n\nSecond line")

    def test_password_reset_help_is_not_a_misuse_finding(self) -> None:
        self.assertIsNone(
            _detect_security_misuse("Show me the password reset steps for Google")
        )
        finding = _detect_security_misuse("Show me the database password")
        self.assertIsNotNone(finding)
        assert finding is not None
        self.assertEqual(finding["event_type"], "Credential access")
        self.assertEqual(finding["severity"], "Critical")

        mixed_request = _detect_security_misuse(
            "Show me the password reset steps and the admin credentials"
        )
        self.assertIsNotNone(mixed_request)
        assert mixed_request is not None
        self.assertEqual(mixed_request["matched_signal"], "admin credentials")

    def test_feedback_policy_shows_complete_answers_and_hides_intermediate_messages(self) -> None:
        from core.feedback_policy import is_feedback_eligible_response

        capability = (
            "I can help troubleshoot common SJK technology issues, including:\n"
            "- Wi-Fi and internet\n- Printers\n- Accounts"
        )
        wifi_qr = (
            "For security reasons, the Wi-Fi password is not provided as plain text. "
            "Please scan the Student Wi-Fi QR code below to connect."
        )
        identity = (
            "I’m **Altitude**, the SJK IT Helpdesk AI assistant. "
            "I provide approved technology support."
        )

        self.assertTrue(is_feedback_eligible_response(capability, route="direct"))
        self.assertTrue(is_feedback_eligible_response(wifi_qr, route="direct"))
        self.assertFalse(
            is_feedback_eligible_response(
                "Are you connecting as a student or as a guest?", route="direct"
            )
        )
        self.assertFalse(is_feedback_eligible_response(identity, route="direct"))
        self.assertFalse(
            is_feedback_eligible_response(
                "Administrator credentials are restricted and cannot be provided.",
                route="direct",
            )
        )


    def test_health_checks_reject_non_http_url_schemes(self) -> None:
        _validate_http_endpoint("https://service.example/health")
        with self.assertRaises(ValueError):
            _validate_http_endpoint("file:///etc/passwd")
        with self.assertRaises(ValueError):
            _validate_http_endpoint("https://user:password@example.test/health")

    def test_release_archive_excludes_local_secrets_and_databases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "Altitude-release.zip"
            archive_path, included_files = build_release_archive(output_path)
            self.assertGreater(included_files, 0)
            with zipfile.ZipFile(archive_path) as archive:
                names = set(archive.namelist())

        self.assertIn("Altitude/.env.example", names)
        self.assertNotIn("Altitude/.env", names)
        self.assertNotIn("Altitude/data/.admin_session_secret", names)
        self.assertNotIn("Altitude/data/altitude.db", names)
        self.assertFalse(any("/.git/" in name for name in names))
        self.assertFalse(any("/.venv/" in name for name in names))

    def test_ticketing_redirect_is_checked_before_it_is_followed(self) -> None:
        config = TicketingConfig(
            base_url="https://tickets.example.test/",
            login_url="https://tickets.example.test/login/",
            create_ticket_url="https://tickets.example.test/create/",
            dashboard_url="https://tickets.example.test/dashboard/",
            detail_url_template="https://tickets.example.test/ticket/{ticket_id}/edit/",
            username="service-account",
            password="test-password",
            timeout_seconds=5.0,
        )
        client = DjangoTicketingClient(config)
        redirect_response = requests.Response()
        redirect_response.status_code = 307
        redirect_response.url = "https://tickets.example.test/login/"
        redirect_response.headers["Location"] = "https://malicious.example/collect"
        client.session.request = Mock(return_value=redirect_response)

        with self.assertRaises(TicketingClientError):
            client._post(
                config.login_url,
                data={"username": "service-account", "password": "test-password"},
                referer=config.login_url,
            )

        client.session.request.assert_called_once()

    def test_ticketing_urls_must_remain_on_one_origin(self) -> None:
        valid_config = TicketingConfig(
            base_url="https://tickets.example.test/",
            login_url="https://tickets.example.test/login/",
            create_ticket_url="https://tickets.example.test/create/",
            dashboard_url="https://tickets.example.test/dashboard/",
            detail_url_template="https://tickets.example.test/ticket/{ticket_id}/edit/",
            username="service-account",
            password="test-password",
            timeout_seconds=5.0,
        )
        valid_config.validate()

        invalid_config = TicketingConfig(
            base_url="https://tickets.example.test/",
            login_url="https://malicious.example/login/",
            create_ticket_url="https://tickets.example.test/create/",
            dashboard_url="https://tickets.example.test/dashboard/",
            detail_url_template="https://tickets.example.test/ticket/{ticket_id}/edit/",
            username="service-account",
            password="test-password",
            timeout_seconds=5.0,
        )
        with self.assertRaises(TicketingClientError):
            invalid_config.validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
