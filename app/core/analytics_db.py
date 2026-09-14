from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = 1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "altitude.db"


def utc_now() -> str:
    """Return the current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_database_path() -> Path:
    """Return the configured SQLite database path."""
    configured_path = os.getenv("ALTITUDE_DB_PATH", "").strip()

    if not configured_path:
        return DEFAULT_DB_PATH

    path = Path(configured_path).expanduser()

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path.resolve()


@contextmanager
def database_connection() -> Iterator[sqlite3.Connection]:
    """Open a short-lived SQLite connection suitable for Streamlit sessions."""
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        database_path,
        timeout=5.0,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    """Create the Altitude analytics database when it does not exist."""
    with database_connection() as connection:
        connection.execute("PRAGMA journal_mode = WAL")

        current_version = int(
            connection.execute("PRAGMA user_version").fetchone()[0]
        )

        if current_version > SCHEMA_VERSION:
            raise RuntimeError(
                "The analytics database was created by a newer version "
                "of Altitude."
            )

        if current_version < 1:
            _create_schema_v1(connection)
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        else:
            # Keep startup idempotent for databases that already use v1.
            _create_schema_v1(connection)

        _ensure_schema_extensions(connection)


def _create_schema_v1(connection: sqlite3.Connection) -> None:
    """Create the initial analytics, feedback, ticket, and announcement schema."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            session_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            ended_at TEXT,
            outcome TEXT NOT NULL DEFAULT 'active',
            escalated INTEGER NOT NULL DEFAULT 0
                CHECK (escalated IN (0, 1)),
            ticket_created INTEGER NOT NULL DEFAULT 0
                CHECK (ticket_created IN (0, 1))
        );

        CREATE TABLE IF NOT EXISTS messages (
            message_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL
                CHECK (role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            route TEXT,
            intent TEXT,
            platform TEXT,
            source_document TEXT,
            feedback_eligible INTEGER NOT NULL DEFAULT 0
                CHECK (feedback_eligible IN (0, 1)),
            created_at TEXT NOT NULL,

            FOREIGN KEY (session_id)
                REFERENCES conversations(session_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL UNIQUE,
            session_id TEXT NOT NULL,
            helpful INTEGER NOT NULL
                CHECK (helpful IN (0, 1)),
            reason TEXT,
            comment TEXT,
            created_at TEXT NOT NULL,

            FOREIGN KEY (message_id)
                REFERENCES messages(message_id)
                ON DELETE CASCADE,

            FOREIGN KEY (session_id)
                REFERENCES conversations(session_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS admin_reviews (
            review_id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL UNIQUE,
            is_correct INTEGER NOT NULL
                CHECK (is_correct IN (0, 1)),
            notes TEXT,
            reviewed_by TEXT,
            reviewed_at TEXT NOT NULL,

            FOREIGN KEY (message_id)
                REFERENCES messages(message_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tickets (
            local_ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            altitude_reference TEXT UNIQUE,
            session_id TEXT NOT NULL,
            external_ticket_id TEXT UNIQUE,
            title TEXT NOT NULL,
            contact_email TEXT NOT NULL,
            category TEXT NOT NULL,
            device TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            resolution_comment TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}',
            submission_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            FOREIGN KEY (session_id)
                REFERENCES conversations(session_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS unauthorized_ticket_attempts (
            attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            assistant_message_id TEXT NOT NULL,
            contact_email TEXT NOT NULL,
            email_domain TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            form_data_json TEXT NOT NULL DEFAULT '{}',
            transcript_json TEXT NOT NULL DEFAULT '[]',
            capture_reason TEXT NOT NULL DEFAULT 'non_school_email',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            UNIQUE (session_id, assistant_message_id, contact_email),

            FOREIGN KEY (session_id)
                REFERENCES conversations(session_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS announcements (
            announcement_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'info',
            starts_at TEXT,
            ends_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
                CHECK (is_active IN (0, 1)),
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_messages_session_created
            ON messages(session_id, created_at);

        CREATE INDEX IF NOT EXISTS idx_messages_feedback_eligible
            ON messages(feedback_eligible);

        CREATE INDEX IF NOT EXISTS idx_feedback_session
            ON feedback(session_id);

        CREATE INDEX IF NOT EXISTS idx_feedback_helpful
            ON feedback(helpful);

        CREATE INDEX IF NOT EXISTS idx_tickets_status
            ON tickets(status);

        CREATE INDEX IF NOT EXISTS idx_tickets_created
            ON tickets(created_at);

        CREATE INDEX IF NOT EXISTS idx_unauthorized_ticket_attempts_created
            ON unauthorized_ticket_attempts(created_at);

        CREATE INDEX IF NOT EXISTS idx_unauthorized_ticket_attempts_email
            ON unauthorized_ticket_attempts(contact_email);

        CREATE INDEX IF NOT EXISTS idx_announcements_active
            ON announcements(is_active, starts_at, ends_at);
        """
    )



def _table_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> set[str]:
    """Return column names for an existing SQLite table."""
    return {
        str(row["name"])
        for row in connection.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    }


def _ensure_column(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    column_name: str,
    definition: str,
) -> None:
    """Add one SQLite column when an older database does not have it."""
    if column_name in _table_columns(connection, table_name):
        return
    connection.execute(
        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
    )


def _ensure_schema_extensions(connection: sqlite3.Connection) -> None:
    """Apply idempotent ticket-sync, security, and knowledge schema extensions."""
    _ensure_column(
        connection,
        table_name="tickets",
        column_name="last_synced_at",
        definition="TEXT",
    )
    _ensure_column(
        connection,
        table_name="tickets",
        column_name="altitude_reference",
        definition="TEXT",
    )
    _ensure_column(
        connection,
        table_name="tickets",
        column_name="remote_ticket_url",
        definition="TEXT",
    )
    _ensure_column(
        connection,
        table_name="tickets",
        column_name="status_sync_error",
        definition="TEXT",
    )
    _ensure_column(
        connection,
        table_name="tickets",
        column_name="resolution_comment",
        definition="TEXT",
    )
    _ensure_column(
        connection,
        table_name="tickets",
        column_name="resolution_email_pending",
        definition="INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table_name="tickets",
        column_name="resolution_email_sent_at",
        definition="TEXT",
    )
    _ensure_column(
        connection,
        table_name="tickets",
        column_name="resolution_email_error",
        definition="TEXT",
    )

    _ensure_column(
        connection,
        table_name="unauthorized_ticket_attempts",
        column_name="review_status",
        definition="TEXT NOT NULL DEFAULT 'Open'",
    )
    _ensure_column(
        connection,
        table_name="unauthorized_ticket_attempts",
        column_name="reviewed_by",
        definition="TEXT",
    )
    _ensure_column(
        connection,
        table_name="unauthorized_ticket_attempts",
        column_name="reviewed_at",
        definition="TEXT",
    )

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS security_events (
            security_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_fingerprint TEXT NOT NULL UNIQUE,
            session_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'Medium',
            summary TEXT NOT NULL,
            details_json TEXT NOT NULL DEFAULT '{}',
            occurrence_count INTEGER NOT NULL DEFAULT 1,
            review_status TEXT NOT NULL DEFAULT 'Open',
            reviewed_by TEXT,
            reviewed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            FOREIGN KEY (session_id)
                REFERENCES conversations(session_id)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_security_events_updated
            ON security_events(updated_at);

        CREATE INDEX IF NOT EXISTS idx_security_events_review
            ON security_events(review_status, severity);

        CREATE TABLE IF NOT EXISTS knowledge_drafts (
            draft_id INTEGER PRIMARY KEY AUTOINCREMENT,
            local_ticket_id INTEGER NOT NULL UNIQUE,
            external_ticket_id TEXT,
            altitude_reference TEXT,
            source_status TEXT NOT NULL,
            source_title TEXT NOT NULL,
            source_category TEXT,
            source_device TEXT,
            source_problem TEXT,
            source_resolution TEXT NOT NULL,
            draft_title TEXT NOT NULL,
            intent_keywords TEXT NOT NULL DEFAULT '',
            target_audience TEXT NOT NULL DEFAULT 'Staff, Faculty, Students',
            direct_answer TEXT NOT NULL,
            troubleshooting_steps TEXT NOT NULL DEFAULT '[]',
            bot_instruction TEXT,
            review_status TEXT NOT NULL DEFAULT 'Pending',
            review_notes TEXT,
            reviewed_by TEXT,
            reviewed_at TEXT,
            published_filename TEXT,
            published_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            FOREIGN KEY (local_ticket_id)
                REFERENCES tickets(local_ticket_id)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_knowledge_drafts_review_status
            ON knowledge_drafts(review_status, updated_at);

        CREATE INDEX IF NOT EXISTS idx_knowledge_drafts_ticket
            ON knowledge_drafts(local_ticket_id);
        """
    )

    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_tickets_altitude_reference
            ON tickets(altitude_reference)
            WHERE altitude_reference IS NOT NULL
        """
    )

    # Failed rows represent attempts that never became real tickets. The
    # administrator Tickets page now contains only tickets accepted remotely.
    connection.execute(
        "DELETE FROM tickets WHERE LOWER(TRIM(status)) = 'failed'"
    )


def create_conversation(session_id: str) -> None:
    """Create a conversation if it does not already exist."""
    session_id = session_id.strip()

    if not session_id:
        raise ValueError("session_id cannot be empty")

    now = utc_now()

    with database_connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO conversations (
                session_id,
                started_at,
                updated_at
            )
            VALUES (?, ?, ?)
            """,
            (session_id, now, now),
        )

        connection.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE session_id = ?
            """,
            (now, session_id),
        )


def save_message(
    *,
    session_id: str,
    role: str,
    content: str,
    message_id: str | None = None,
    route: str | None = None,
    intent: str | None = None,
    platform: str | None = None,
    source_document: str | None = None,
    feedback_eligible: bool = False,
) -> str:
    """Save one message and return its stable message ID."""
    session_id = session_id.strip()
    role = role.strip().lower()
    content = content.strip()

    if not session_id:
        raise ValueError("session_id cannot be empty")

    if role not in {"user", "assistant", "system"}:
        raise ValueError(f"Unsupported message role: {role}")

    if not content:
        raise ValueError("Message content cannot be empty")

    content = content[:50_000]
    final_message_id = message_id or str(uuid.uuid4())
    now = utc_now()

    with database_connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO conversations (
                session_id,
                started_at,
                updated_at
            )
            VALUES (?, ?, ?)
            """,
            (session_id, now, now),
        )

        connection.execute(
            """
            INSERT OR IGNORE INTO messages (
                message_id,
                session_id,
                role,
                content,
                route,
                intent,
                platform,
                source_document,
                feedback_eligible,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                final_message_id,
                session_id,
                role,
                content,
                route,
                intent,
                platform,
                source_document,
                int(feedback_eligible),
                now,
            ),
        )

        connection.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE session_id = ?
            """,
            (now, session_id),
        )

    return final_message_id


def close_conversation(
    session_id: str,
    *,
    outcome: str = "closed",
) -> None:
    """Mark a conversation as ended."""
    now = utc_now()

    with database_connection() as connection:
        connection.execute(
            """
            UPDATE conversations
            SET
                outcome = ?,
                ended_at = ?,
                updated_at = ?
            WHERE session_id = ?
            """,
            (
                outcome.strip() or "closed",
                now,
                now,
                session_id,
            ),
        )


def get_conversation_messages(
    session_id: str,
) -> list[dict[str, Any]]:
    """Return all messages for a conversation in chronological order."""
    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                message_id,
                session_id,
                role,
                content,
                route,
                intent,
                platform,
                source_document,
                feedback_eligible,
                created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at ASC, rowid ASC
            """,
            (session_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def save_feedback(
    *,
    message_id: str,
    session_id: str,
    helpful: bool,
    reason: str | None = None,
    comment: str | None = None,
) -> dict[str, Any]:
    """
    Create or update one feedback vote for an assistant response.

    One message can have only one feedback row. Submitting again safely
    changes the existing vote instead of creating a duplicate.
    """
    message_id = message_id.strip()
    session_id = session_id.strip()

    if not message_id:
        raise ValueError("message_id cannot be empty")

    if not session_id:
        raise ValueError("session_id cannot be empty")

    clean_reason = _clean_optional_text(reason, maximum_length=120)
    clean_comment = _clean_optional_text(comment, maximum_length=2_000)
    now = utc_now()

    with database_connection() as connection:
        message = connection.execute(
            """
            SELECT session_id, role, feedback_eligible
            FROM messages
            WHERE message_id = ?
            """,
            (message_id,),
        ).fetchone()

        if message is None:
            raise ValueError("The selected message does not exist")

        if str(message["session_id"]) != session_id:
            raise ValueError("The message does not belong to this conversation")

        if str(message["role"]) != "assistant":
            raise ValueError("Feedback can only be attached to assistant messages")

        if int(message["feedback_eligible"]) != 1:
            raise ValueError("This assistant message is not feedback eligible")

        connection.execute(
            """
            INSERT INTO feedback (
                message_id,
                session_id,
                helpful,
                reason,
                comment,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(message_id) DO UPDATE SET
                session_id = excluded.session_id,
                helpful = excluded.helpful,
                reason = excluded.reason,
                comment = excluded.comment,
                created_at = excluded.created_at
            """,
            (
                message_id,
                session_id,
                int(helpful),
                clean_reason,
                clean_comment,
                now,
            ),
        )

        row = connection.execute(
            """
            SELECT
                feedback_id,
                message_id,
                session_id,
                helpful,
                reason,
                comment,
                created_at
            FROM feedback
            WHERE message_id = ?
            """,
            (message_id,),
        ).fetchone()

    if row is None:
        raise RuntimeError("Feedback was not saved")

    return dict(row)


def get_feedback_for_message(
    message_id: str,
) -> dict[str, Any] | None:
    """Return feedback for one assistant message, if it exists."""
    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT
                feedback_id,
                message_id,
                session_id,
                helpful,
                reason,
                comment,
                created_at
            FROM feedback
            WHERE message_id = ?
            """,
            (message_id,),
        ).fetchone()

    return dict(row) if row is not None else None


def get_feedback_for_session(
    session_id: str,
) -> dict[str, dict[str, Any]]:
    """Return feedback rows keyed by assistant message ID."""
    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                feedback_id,
                message_id,
                session_id,
                helpful,
                reason,
                comment,
                created_at
            FROM feedback
            WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,),
        ).fetchall()

    return {
        str(row["message_id"]): dict(row)
        for row in rows
    }


def get_feedback_summary() -> dict[str, Any]:
    """Return system-wide vote totals and feedback coverage metrics."""
    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total_votes,
                COALESCE(SUM(helpful), 0) AS helpful_votes,
                COALESCE(SUM(CASE WHEN helpful = 0 THEN 1 ELSE 0 END), 0)
                    AS not_helpful_votes
            FROM feedback
            """
        ).fetchone()

        eligible_row = connection.execute(
            """
            SELECT COUNT(*) AS eligible_responses
            FROM messages
            WHERE role = 'assistant'
              AND feedback_eligible = 1
            """
        ).fetchone()

    total_votes = int(row["total_votes"] if row is not None else 0)
    helpful_votes = int(row["helpful_votes"] if row is not None else 0)
    not_helpful_votes = int(
        row["not_helpful_votes"] if row is not None else 0
    )
    eligible_responses = int(
        eligible_row["eligible_responses"]
        if eligible_row is not None
        else 0
    )
    helpful_rate = (
        round((helpful_votes / total_votes) * 100, 1)
        if total_votes
        else 0.0
    )
    feedback_coverage = (
        round((total_votes / eligible_responses) * 100, 1)
        if eligible_responses
        else 0.0
    )

    return {
        "total_votes": total_votes,
        "helpful_votes": helpful_votes,
        "not_helpful_votes": not_helpful_votes,
        "helpful_rate": helpful_rate,
        "eligible_responses": eligible_responses,
        "feedback_coverage": feedback_coverage,
    }


def list_feedback_records(
    *,
    helpful: bool | None = None,
    search: str | None = None,
    reason: str | None = None,
    platform: str | None = None,
    source_document: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Return feedback joined to its assistant answer and preceding question.

    The preceding meaningful user message is selected by SQLite ``rowid``.
    This remains reliable when a user and assistant message share the same
    second-level timestamp.
    """
    safe_limit = max(1, min(int(limit), 2_000))
    safe_offset = max(0, int(offset))
    clauses: list[str] = []
    parameters: list[Any] = []

    if helpful is not None:
        clauses.append("feedback_row.helpful = ?")
        parameters.append(int(helpful))

    clean_reason = (reason or "").strip()
    if clean_reason:
        clauses.append("COALESCE(feedback_row.reason, '') = ?")
        parameters.append(clean_reason)

    clean_platform = (platform or "").strip()
    if clean_platform:
        clauses.append("COALESCE(feedback_row.platform, '') = ?")
        parameters.append(clean_platform)

    clean_source = (source_document or "").strip()
    if clean_source:
        clauses.append("COALESCE(feedback_row.source_document, '') = ?")
        parameters.append(clean_source)

    clean_search = (search or "").strip().lower()
    if clean_search:
        clauses.append(
            """
            (
                LOWER(COALESCE(feedback_row.user_question, '')) LIKE ?
                OR LOWER(COALESCE(feedback_row.bot_answer, '')) LIKE ?
                OR LOWER(COALESCE(feedback_row.reason, '')) LIKE ?
                OR LOWER(COALESCE(feedback_row.comment, '')) LIKE ?
                OR LOWER(COALESCE(feedback_row.platform, '')) LIKE ?
                OR LOWER(COALESCE(feedback_row.source_document, '')) LIKE ?
            )
            """
        )
        pattern = f"%{clean_search}%"
        parameters.extend([pattern] * 6)

    where_sql = ""
    if clauses:
        where_sql = "WHERE " + " AND ".join(clauses)

    parameters.extend((safe_limit, safe_offset))

    with database_connection() as connection:
        rows = connection.execute(
            f"""
            WITH feedback_row AS (
                SELECT
                    f.feedback_id,
                    f.message_id AS assistant_message_id,
                    f.session_id,
                    f.helpful,
                    f.reason,
                    f.comment,
                    f.created_at AS feedback_created_at,
                    assistant.content AS bot_answer,
                    assistant.route,
                    assistant.intent,
                    assistant.platform,
                    assistant.source_document,
                    assistant.created_at AS answer_created_at,
                    (
                        SELECT user_message.content
                        FROM messages AS user_message
                        WHERE user_message.session_id = assistant.session_id
                          AND user_message.role = 'user'
                          AND user_message.rowid < assistant.rowid
                        ORDER BY user_message.rowid DESC
                        LIMIT 1
                    ) AS user_question
                FROM feedback AS f
                INNER JOIN messages AS assistant
                    ON assistant.message_id = f.message_id
                WHERE assistant.role = 'assistant'
            )
            SELECT *
            FROM feedback_row
            {where_sql}
            ORDER BY feedback_created_at DESC, feedback_id DESC
            LIMIT ? OFFSET ?
            """,
            tuple(parameters),
        ).fetchall()

    return [dict(row) for row in rows]


def get_feedback_filter_options() -> dict[str, list[str]]:
    """Return distinct values used by feedback dashboard filters."""
    with database_connection() as connection:
        reason_rows = connection.execute(
            """
            SELECT DISTINCT TRIM(reason) AS value
            FROM feedback
            WHERE reason IS NOT NULL AND TRIM(reason) <> ''
            ORDER BY value COLLATE NOCASE
            """
        ).fetchall()
        platform_rows = connection.execute(
            """
            SELECT DISTINCT TRIM(messages.platform) AS value
            FROM feedback
            INNER JOIN messages ON messages.message_id = feedback.message_id
            WHERE messages.platform IS NOT NULL
              AND TRIM(messages.platform) <> ''
            ORDER BY value COLLATE NOCASE
            """
        ).fetchall()
        source_rows = connection.execute(
            """
            SELECT DISTINCT TRIM(messages.source_document) AS value
            FROM feedback
            INNER JOIN messages ON messages.message_id = feedback.message_id
            WHERE messages.source_document IS NOT NULL
              AND TRIM(messages.source_document) <> ''
            ORDER BY value COLLATE NOCASE
            """
        ).fetchall()

    return {
        "reasons": [str(row["value"]) for row in reason_rows],
        "platforms": [str(row["value"]) for row in platform_rows],
        "sources": [str(row["value"]) for row in source_rows],
    }


def get_recent_knowledge_gaps(limit: int = 5) -> list[dict[str, Any]]:
    """Return the newest Not Helpful responses for the Overview page."""
    return list_feedback_records(helpful=False, limit=limit)



def cleanup_non_analytical_messages() -> dict[str, int]:
    """
    Remove historical UI-only and canned messages from the analytics DB.

    This is intended as a one-time cleanup after enabling filtered logging.
    It is safe to run more than once. Deleting assistant messages also removes
    feedback attached to those messages through the existing foreign key.
    """
    trivial_user_messages = (
        "bye",
        "cool",
        "goodbye",
        "got it",
        "great",
        "hello",
        "hey",
        "hi",
        "nice",
        "no",
        "nope",
        "ok",
        "okay",
        "thanks",
        "thank you",
        "thnaks",
        "thx",
        "tnx",
        "yes",
        "yep",
        "android",
        "chrome os",
        "chromebook",
        "chromeos",
        "iphone",
        "ipad",
        "mac",
        "macbook",
        "macos",
        "pc",
        "windows",
        "windows 10",
        "windows 11",
    )
    assistant_prefixes = (
        "i can only help with it-related questions%",
        "i can help with it-related issues, but i do not have an approved procedure%",
        "i could not complete that request%",
        "i'm unable to help with that request%",
        "i am unable to help with that request%",
        "this assistant can only help with%",
        "that request is outside%",
        "i cannot help with%",
    )

    with database_connection() as connection:
        before_messages = int(
            connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        )
        before_conversations = int(
            connection.execute(
                "SELECT COUNT(*) FROM conversations"
            ).fetchone()[0]
        )

        # Any assistant message that was not a final feedback-eligible answer is
        # UI/conversation scaffolding rather than an analytics answer.
        connection.execute(
            """
            DELETE FROM messages
            WHERE role = 'assistant'
              AND feedback_eligible = 0
            """
        )

        for prefix in assistant_prefixes:
            connection.execute(
                """
                DELETE FROM messages
                WHERE role = 'assistant'
                  AND LOWER(TRIM(content)) LIKE ?
                """,
                (prefix,),
            )

        placeholders = ", ".join("?" for _ in trivial_user_messages)
        connection.execute(
            f"""
            DELETE FROM messages
            WHERE role = 'user'
              AND LOWER(TRIM(RTRIM(content, '.!?'))) IN ({placeholders})
            """,
            trivial_user_messages,
        )

        # Remove empty analytics sessions, but never remove a conversation that
        # already has a ticket associated with it.
        connection.execute(
            """
            DELETE FROM conversations
            WHERE NOT EXISTS (
                SELECT 1
                FROM messages
                WHERE messages.session_id = conversations.session_id
            )
              AND NOT EXISTS (
                SELECT 1
                FROM tickets
                WHERE tickets.session_id = conversations.session_id
            )
            """
        )

        after_messages = int(
            connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        )
        after_conversations = int(
            connection.execute(
                "SELECT COUNT(*) FROM conversations"
            ).fetchone()[0]
        )

    return {
        "messages_removed": before_messages - after_messages,
        "conversations_removed": (
            before_conversations - after_conversations
        ),
        "messages_remaining": after_messages,
        "conversations_remaining": after_conversations,
    }

def _clean_optional_text(
    value: str | None,
    *,
    maximum_length: int,
) -> str | None:
    """Normalize optional feedback text and enforce a storage limit."""
    if value is None:
        return None

    cleaned = " ".join(str(value).split()).strip()

    if not cleaned:
        return None

    return cleaned[:maximum_length]


def get_database_health() -> dict[str, Any]:
    """Return database integrity, storage, and row-count diagnostics."""
    database_path = get_database_path()

    with database_connection() as connection:
        quick_check_row = connection.execute(
            "PRAGMA quick_check"
        ).fetchone()
        quick_check = (
            str(quick_check_row[0])
            if quick_check_row is not None
            else "unknown"
        )

        schema_version_row = connection.execute(
            "PRAGMA user_version"
        ).fetchone()
        schema_version = int(
            schema_version_row[0]
            if schema_version_row is not None
            else 0
        )

        journal_mode_row = connection.execute(
            "PRAGMA journal_mode"
        ).fetchone()
        journal_mode = (
            str(journal_mode_row[0])
            if journal_mode_row is not None
            else "unknown"
        )

        foreign_key_violations = len(
            connection.execute("PRAGMA foreign_key_check").fetchall()
        )

        tables = [
            str(row["name"])
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        ]

        def _table_count(table_name: str) -> int:
            if table_name not in tables:
                return 0

            row = connection.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()
            return int(row[0] if row is not None else 0)

        conversation_count = _table_count("conversations")
        message_count = _table_count("messages")
        feedback_count = _table_count("feedback")
        announcement_count = _table_count("announcements")
        ticket_count = _table_count("tickets")
        admin_review_count = _table_count("admin_reviews")
        unauthorized_attempt_count = _table_count(
            "unauthorized_ticket_attempts"
        )

        active_conversation_count = 0
        if "conversations" in tables:
            row = connection.execute(
                """
                SELECT COUNT(*)
                FROM conversations
                WHERE outcome = 'active'
                  AND datetime(updated_at) >= datetime('now', '-30 minutes')
                """
            ).fetchone()
            active_conversation_count = int(
                row[0] if row is not None else 0
            )

    database_size_bytes = (
        database_path.stat().st_size
        if database_path.exists()
        else 0
    )
    wal_path = Path(f"{database_path}-wal")
    wal_size_bytes = (
        wal_path.stat().st_size
        if wal_path.exists()
        else 0
    )

    return {
        "database_path": str(database_path),
        "database_size_bytes": database_size_bytes,
        "wal_size_bytes": wal_size_bytes,
        "quick_check": quick_check,
        "foreign_key_violations": foreign_key_violations,
        "journal_mode": journal_mode,
        "schema_version": schema_version,
        "tables": tables,
        "conversation_count": conversation_count,
        "active_conversation_count": active_conversation_count,
        "message_count": message_count,
        "feedback_count": feedback_count,
        "announcement_count": announcement_count,
        "ticket_count": ticket_count,
        "admin_review_count": admin_review_count,
        "unauthorized_attempt_count": unauthorized_attempt_count,
    }

def log_unauthorized_ticket_attempt(
    *,
    session_id: str,
    assistant_message_id: str,
    contact_email: str,
    email_domain: str,
    title: str,
    category: str,
    priority: str,
    form_data: dict[str, Any],
    transcript: list[dict[str, Any]],
    capture_reason: str = "non_school_email",
) -> int:
    """Store or refresh a transparently disclosed non-school email attempt.

    One row is kept per conversation, escalation message, and normalized email
    address. Repeated Streamlit reruns update the same row instead of creating
    duplicates.
    """
    clean_session_id = str(session_id).strip()
    clean_message_id = str(assistant_message_id).strip()
    clean_email = str(contact_email).strip().lower()[:254]
    clean_domain = str(email_domain).strip().lower()[:253]
    clean_title = str(title).strip()[:255] or "IT support request"
    clean_category = str(category).strip()[:120] or "Other"
    clean_priority = str(priority).strip()[:40] or "Medium"
    clean_reason = str(capture_reason).strip()[:120] or "non_school_email"

    if not clean_session_id:
        raise ValueError("session_id cannot be empty")
    if not clean_message_id:
        raise ValueError("assistant_message_id cannot be empty")
    if not clean_email or not clean_domain:
        raise ValueError("A valid non-school email is required for audit logging")

    now = utc_now()
    form_data_json = json.dumps(
        form_data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    transcript_json = json.dumps(
        transcript,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    with database_connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO conversations (
                session_id,
                started_at,
                updated_at
            )
            VALUES (?, ?, ?)
            """,
            (clean_session_id, now, now),
        )

        connection.execute(
            """
            INSERT INTO unauthorized_ticket_attempts (
                session_id,
                assistant_message_id,
                contact_email,
                email_domain,
                title,
                category,
                priority,
                form_data_json,
                transcript_json,
                capture_reason,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id, assistant_message_id, contact_email)
            DO UPDATE SET
                email_domain = excluded.email_domain,
                title = excluded.title,
                category = excluded.category,
                priority = excluded.priority,
                form_data_json = excluded.form_data_json,
                transcript_json = excluded.transcript_json,
                capture_reason = excluded.capture_reason,
                review_status = 'Open',
                reviewed_by = NULL,
                reviewed_at = NULL,
                updated_at = excluded.updated_at
            """,
            (
                clean_session_id,
                clean_message_id,
                clean_email,
                clean_domain,
                clean_title,
                clean_category,
                clean_priority,
                form_data_json,
                transcript_json,
                clean_reason,
                now,
                now,
            ),
        )

        row = connection.execute(
            """
            SELECT attempt_id
            FROM unauthorized_ticket_attempts
            WHERE session_id = ?
              AND assistant_message_id = ?
              AND contact_email = ?
            """,
            (clean_session_id, clean_message_id, clean_email),
        ).fetchone()

    if row is None:
        raise RuntimeError("The non-school email attempt was not recorded")

    return int(row["attempt_id"])


def list_unauthorized_ticket_attempts(
    *,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return recent non-school email attempts for future admin review."""
    safe_limit = max(1, min(int(limit), 1_000))

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                attempt_id,
                session_id,
                assistant_message_id,
                contact_email,
                email_domain,
                title,
                category,
                priority,
                form_data_json,
                transcript_json,
                capture_reason,
                review_status,
                reviewed_by,
                reviewed_at,
                created_at,
                updated_at
            FROM unauthorized_ticket_attempts
            ORDER BY updated_at DESC, attempt_id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def create_ticket_audit(
    *,
    session_id: str,
    title: str,
    contact_email: str,
    category: str,
    device: str,
    priority: str,
    payload: dict[str, Any],
) -> int:
    """Create a local audit row before submitting a remote ticket."""
    clean_session_id = session_id.strip()
    clean_title = title.strip()[:255]
    clean_contact_email = contact_email.strip().lower()[:254]
    clean_category = category.strip()[:120]
    clean_device = (device.strip() or "Not provided")[:120]
    clean_priority = priority.strip()[:40]

    if not clean_session_id:
        raise ValueError("session_id cannot be empty")
    if not clean_title:
        raise ValueError("Ticket title cannot be empty")
    if not clean_contact_email:
        raise ValueError("Ticket contact email cannot be empty")
    if not clean_category:
        raise ValueError("Ticket category cannot be empty")
    if not clean_priority:
        raise ValueError("Ticket priority cannot be empty")

    now = utc_now()
    payload_json = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    with database_connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO conversations (
                session_id,
                started_at,
                updated_at
            )
            VALUES (?, ?, ?)
            """,
            (clean_session_id, now, now),
        )

        cursor = connection.execute(
            """
            INSERT INTO tickets (
                session_id,
                external_ticket_id,
                title,
                contact_email,
                category,
                device,
                priority,
                status,
                payload_json,
                submission_error,
                created_at,
                updated_at
            )
            VALUES (?, NULL, ?, ?, ?, ?, ?, 'Submitting', ?, NULL, ?, ?)
            """,
            (
                clean_session_id,
                clean_title,
                clean_contact_email,
                clean_category,
                clean_device,
                clean_priority,
                payload_json,
                now,
                now,
            ),
        )
        inserted_id = cursor.lastrowid

    if inserted_id is None:
        raise RuntimeError("SQLite did not return a local ticket ID")

    return int(inserted_id)



def _format_altitude_reference(local_ticket_id: int) -> str:
    """Return a stable public-facing Altitude ticket reference."""
    if local_ticket_id <= 0:
        raise ValueError("local_ticket_id must be positive")
    year = datetime.now(timezone.utc).year
    return f"ALT-{year}-{local_ticket_id:06d}"


def normalize_altitude_reference(value: str) -> str | None:
    """Normalize a user-entered Altitude reference such as ALT-2026-000009."""
    text = " ".join(str(value).upper().replace("_", "-").split())
    match = __import__("re").search(r"\bALT\s*-?\s*(20\d{2})\s*-?\s*(\d{1,8})\b", text)
    if match is None:
        return None
    year = match.group(1)
    number = int(match.group(2))
    return f"ALT-{year}-{number:06d}"


def ensure_ticket_altitude_reference(local_ticket_id: int) -> str:
    """Create or return the local Altitude reference for a ticket row."""
    if local_ticket_id <= 0:
        raise ValueError("local_ticket_id must be positive")

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT altitude_reference
            FROM tickets
            WHERE local_ticket_id = ?
            """,
            (local_ticket_id,),
        ).fetchone()
        if row is None:
            raise ValueError("The local ticket audit row does not exist")

        existing = str(row["altitude_reference"] or "").strip()
        if existing:
            return existing

        reference = _format_altitude_reference(local_ticket_id)
        now = utc_now()
        connection.execute(
            """
            UPDATE tickets
            SET altitude_reference = ?, updated_at = ?
            WHERE local_ticket_id = ?
            """,
            (reference, now, local_ticket_id),
        )
        return reference


def get_ticket_by_altitude_reference(
    altitude_reference: str,
    *,
    session_id: str | None = None,
    contact_email: str | None = None,
) -> dict[str, Any] | None:
    """Return one ticket row by Altitude reference plus optional verifier."""
    reference = normalize_altitude_reference(altitude_reference)
    if reference is None:
        return None

    clauses = ["altitude_reference = ?"]
    values: list[Any] = [reference]

    if session_id is not None and str(session_id).strip():
        clauses.append("session_id = ?")
        values.append(str(session_id).strip())

    if contact_email is not None and str(contact_email).strip():
        clauses.append("LOWER(TRIM(contact_email)) = LOWER(TRIM(?))")
        values.append(str(contact_email).strip())

    with database_connection() as connection:
        row = connection.execute(
            f"""
            SELECT
                local_ticket_id,
                altitude_reference,
                session_id,
                external_ticket_id,
                title,
                contact_email,
                category,
                device,
                priority,
                status,
                resolution_comment,
                payload_json,
                submission_error,
                last_synced_at,
                remote_ticket_url,
                status_sync_error,
                created_at,
                updated_at
            FROM tickets
            WHERE {' AND '.join(clauses)}
            LIMIT 1
            """,
            tuple(values),
        ).fetchone()

    return dict(row) if row is not None else None

def mark_ticket_submitted(
    local_ticket_id: int,
    *,
    external_ticket_id: str | None,
    status: str = "Open",
    remote_ticket_url: str | None = None,
) -> None:
    """Mark a local audit row as accepted by the remote ticketing system."""
    if local_ticket_id <= 0:
        raise ValueError("local_ticket_id must be positive")

    clean_external_id = (
        str(external_ticket_id).strip()[:120]
        if external_ticket_id is not None
        else None
    )
    clean_status = status.strip()[:80] or "Open"
    clean_remote_url = (
        str(remote_ticket_url).strip()[:1000]
        if remote_ticket_url is not None
        else None
    )
    now = utc_now()

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT session_id
            FROM tickets
            WHERE local_ticket_id = ?
            """,
            (local_ticket_id,),
        ).fetchone()

        if row is None:
            raise ValueError("The local ticket audit row does not exist")

        connection.execute(
            """
            UPDATE tickets
            SET
                external_ticket_id = ?,
                status = ?,
                remote_ticket_url = COALESCE(?, remote_ticket_url),
                submission_error = NULL,
                status_sync_error = NULL,
                last_synced_at = ?,
                updated_at = ?
            WHERE local_ticket_id = ?
            """,
            (
                clean_external_id,
                clean_status,
                clean_remote_url,
                now,
                now,
                local_ticket_id,
            ),
        )
        connection.execute(
            """
            UPDATE conversations
            SET
                escalated = 1,
                ticket_created = 1,
                updated_at = ?
            WHERE session_id = ?
            """,
            (now, str(row["session_id"])),
        )


def mark_ticket_submission_failed(
    local_ticket_id: int,
    *,
    error_message: str,
) -> None:
    """Remove a local audit row when no remote ticket was created.

    Failed submission attempts are not real tickets and are therefore kept out
    of the administrator ticket list. The user still receives the safe error
    message in the chat interface.
    """
    if local_ticket_id <= 0:
        raise ValueError("local_ticket_id must be positive")

    with database_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM tickets WHERE local_ticket_id = ?",
            (local_ticket_id,),
        )
        if cursor.rowcount == 0:
            raise ValueError("The local ticket audit row does not exist")


def get_latest_ticket_for_session(
    session_id: str,
) -> dict[str, Any] | None:
    """Return the newest ticket audit row for one chat session."""
    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT
                local_ticket_id,
                altitude_reference,
                session_id,
                external_ticket_id,
                title,
                contact_email,
                category,
                device,
                priority,
                status,
                resolution_comment,
                payload_json,
                submission_error,
                last_synced_at,
                remote_ticket_url,
                status_sync_error,
                created_at,
                updated_at
            FROM tickets
            WHERE session_id = ?
            ORDER BY local_ticket_id DESC
            LIMIT 1
            """,
            (session_id.strip(),),
        ).fetchone()

    return dict(row) if row is not None else None


def list_ticket_audits(
    *,
    limit: int = 250,
) -> list[dict[str, Any]]:
    """Return accepted/current ticket records for the administrator page."""
    safe_limit = max(1, min(int(limit), 1000))

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                local_ticket_id,
                altitude_reference,
                session_id,
                external_ticket_id,
                title,
                contact_email,
                category,
                device,
                priority,
                status,
                resolution_comment,
                last_synced_at,
                remote_ticket_url,
                status_sync_error,
                created_at,
                updated_at
            FROM tickets
            WHERE LOWER(TRIM(status)) <> 'failed'
            ORDER BY created_at DESC, local_ticket_id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_tickets_for_status_sync(
    *,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Return local ticket identifiers used to match dashboard records."""
    safe_limit = max(1, min(int(limit), 1000))
    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                local_ticket_id,
                altitude_reference,
                external_ticket_id,
                remote_ticket_url,
                title,
                contact_email,
                status,
                resolution_comment
            FROM tickets
            WHERE LOWER(TRIM(status)) <> 'failed'
            ORDER BY created_at DESC, local_ticket_id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def apply_ticket_status_updates(
    updates: list[dict[str, Any]],
) -> int:
    """Apply current remote statuses and references to local ticket rows."""
    if not updates:
        return 0

    now = utc_now()
    updated_count = 0
    with database_connection() as connection:
        for update in updates:
            try:
                local_ticket_id = int(update.get("local_ticket_id", 0))
            except (TypeError, ValueError):
                continue
            status = " ".join(str(update.get("status") or "").split())[:80]
            if local_ticket_id <= 0 or not status:
                continue

            external_ticket_id = str(
                update.get("external_ticket_id") or ""
            ).strip()[:120] or None
            remote_ticket_url = str(
                update.get("remote_ticket_url") or ""
            ).strip()[:1000] or None
            resolution_comment = " ".join(
                str(update.get("resolution_comment") or "").split()
            ).strip()[:5000] or None

            existing = connection.execute(
                """
                SELECT
                    status,
                    resolution_comment,
                    resolution_email_pending,
                    resolution_email_sent_at
                FROM tickets
                WHERE local_ticket_id = ?
                """,
                (local_ticket_id,),
            ).fetchone()
            if existing is None:
                continue

            resolved_states = {"closed", "resolved", "completed", "complete"}
            new_is_resolved = status.casefold() in resolved_states
            old_is_resolved = str(existing["status"] or "").strip().casefold() in resolved_states
            old_resolution = str(existing["resolution_comment"] or "").strip()
            already_sent = bool(str(existing["resolution_email_sent_at"] or "").strip())
            current_pending = int(existing["resolution_email_pending"] or 0)

            resolution_became_actionable = (
                new_is_resolved
                and bool(resolution_comment)
                and not already_sent
                and (not old_is_resolved or not old_resolution)
            )
            if not new_is_resolved:
                resolution_email_pending = 0
            elif resolution_became_actionable:
                resolution_email_pending = 1
            else:
                resolution_email_pending = current_pending

            cursor = connection.execute(
                """
                UPDATE tickets
                SET
                    status = ?,
                    external_ticket_id = COALESCE(?, external_ticket_id),
                    remote_ticket_url = COALESCE(?, remote_ticket_url),
                    resolution_comment = COALESCE(?, resolution_comment),
                    resolution_email_pending = ?,
                    last_synced_at = ?,
                    status_sync_error = NULL,
                    updated_at = ?
                WHERE local_ticket_id = ?
                """,
                (
                    status,
                    external_ticket_id,
                    remote_ticket_url,
                    resolution_comment,
                    resolution_email_pending,
                    now,
                    now,
                    local_ticket_id,
                ),
            )
            updated_count += int(cursor.rowcount > 0)
    return updated_count


def get_tickets_pending_resolution_email(
    *,
    limit: int = 250,
) -> list[dict[str, Any]]:
    """Return newly resolved tickets waiting for an Altitude follow-up email.

    A ticket becomes eligible only when a status synchronization observes a
    transition into a resolved state with a meaningful resolution note. This
    prevents enabling the feature from emailing every historical resolved
    ticket already stored in Altitude.
    """
    safe_limit = max(1, min(int(limit), 1000))
    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                local_ticket_id,
                altitude_reference,
                external_ticket_id,
                title,
                contact_email,
                category,
                device,
                priority,
                status,
                resolution_comment,
                remote_ticket_url,
                resolution_email_sent_at,
                resolution_email_error,
                created_at,
                updated_at
            FROM tickets
            WHERE resolution_email_pending = 1
              AND resolution_email_sent_at IS NULL
              AND LOWER(TRIM(status)) IN (
                    'closed', 'resolved', 'completed', 'complete'
              )
              AND TRIM(COALESCE(resolution_comment, '')) <> ''
              AND TRIM(COALESCE(contact_email, '')) <> ''
            ORDER BY updated_at ASC, local_ticket_id ASC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def mark_resolution_email_sent(local_ticket_id: int) -> None:
    """Mark a resolution-details email as delivered exactly once."""
    if int(local_ticket_id) <= 0:
        raise ValueError("local_ticket_id must be positive")
    now = utc_now()
    with database_connection() as connection:
        connection.execute(
            """
            UPDATE tickets
            SET
                resolution_email_pending = 0,
                resolution_email_sent_at = ?,
                resolution_email_error = NULL,
                updated_at = ?
            WHERE local_ticket_id = ?
            """,
            (now, now, int(local_ticket_id)),
        )


def mark_resolution_email_error(
    local_ticket_id: int,
    error_message: str,
) -> None:
    """Store a safe email error while leaving the ticket eligible for retry."""
    if int(local_ticket_id) <= 0:
        raise ValueError("local_ticket_id must be positive")
    safe_error = " ".join(str(error_message).split()).strip()[:500]
    if not safe_error:
        safe_error = "Resolution email could not be sent"
    now = utc_now()
    with database_connection() as connection:
        connection.execute(
            """
            UPDATE tickets
            SET
                resolution_email_pending = 1,
                resolution_email_error = ?,
                updated_at = ?
            WHERE local_ticket_id = ?
              AND resolution_email_sent_at IS NULL
            """,
            (safe_error, now, int(local_ticket_id)),
        )


def record_ticket_status_sync_error(error_message: str) -> None:
    """Store a safe sync error without changing any remote ticket status."""
    safe_error = " ".join(str(error_message).split()).strip()[:500]
    if not safe_error:
        return
    with database_connection() as connection:
        connection.execute(
            """
            UPDATE tickets
            SET status_sync_error = ?
            WHERE LOWER(TRIM(status)) <> 'failed'
            """,
            (safe_error,),
        )


def get_ticket_summary() -> dict[str, int]:
    """Return live-status totals for the administrator portal."""
    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total_tickets,
                COALESCE(SUM(
                    CASE WHEN LOWER(TRIM(status)) IN ('open', 'new', 'pending')
                    THEN 1 ELSE 0 END
                ), 0) AS open_tickets,
                COALESCE(SUM(
                    CASE WHEN LOWER(TRIM(status)) IN (
                        'in progress', 'in-progress', 'working', 'assigned',
                        'processing', 'reopened'
                    ) THEN 1 ELSE 0 END
                ), 0) AS in_progress_tickets,
                COALESCE(SUM(
                    CASE WHEN LOWER(TRIM(status)) IN (
                        'closed', 'resolved', 'completed', 'complete'
                    ) THEN 1 ELSE 0 END
                ), 0) AS closed_tickets,
                COALESCE(SUM(
                    CASE WHEN LOWER(TRIM(status)) = 'submitting'
                    THEN 1 ELSE 0 END
                ), 0) AS pending_sync_tickets
            FROM tickets
            WHERE LOWER(TRIM(status)) <> 'failed'
            """
        ).fetchone()

    if row is None:
        return {
            "total_tickets": 0,
            "open_tickets": 0,
            "in_progress_tickets": 0,
            "closed_tickets": 0,
            "pending_sync_tickets": 0,
        }

    return {
        "total_tickets": int(row["total_tickets"]),
        "open_tickets": int(row["open_tickets"]),
        "in_progress_tickets": int(row["in_progress_tickets"]),
        "closed_tickets": int(row["closed_tickets"]),
        "pending_sync_tickets": int(row["pending_sync_tickets"]),
    }


KNOWLEDGE_REVIEW_STATES = frozenset({"Pending", "Approved", "Rejected"})


def get_resolved_tickets_without_knowledge_drafts(
    *,
    limit: int = 250,
) -> list[dict[str, Any]]:
    """Return resolved tickets that have not yet entered the review queue."""
    safe_limit = max(1, min(int(limit), 1000))

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                t.local_ticket_id,
                t.altitude_reference,
                t.external_ticket_id,
                t.title,
                t.category,
                t.device,
                t.status,
                t.resolution_comment,
                t.payload_json,
                t.created_at,
                t.updated_at
            FROM tickets AS t
            LEFT JOIN knowledge_drafts AS k
                ON k.local_ticket_id = t.local_ticket_id
            WHERE k.draft_id IS NULL
              AND LOWER(TRIM(t.status)) IN (
                    'closed', 'resolved', 'completed', 'complete'
              )
              AND TRIM(COALESCE(t.resolution_comment, '')) <> ''
            ORDER BY t.updated_at DESC, t.local_ticket_id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def create_knowledge_draft(
    *,
    local_ticket_id: int,
    external_ticket_id: str | None,
    altitude_reference: str | None,
    source_status: str,
    source_title: str,
    source_category: str,
    source_device: str,
    source_problem: str,
    source_resolution: str,
    draft_title: str,
    intent_keywords: str,
    target_audience: str,
    direct_answer: str,
    troubleshooting_steps: list[str],
    bot_instruction: str | None,
) -> int:
    """Insert one human-reviewable knowledge draft for a resolved ticket."""
    if int(local_ticket_id) <= 0:
        raise ValueError("local_ticket_id must be positive")

    clean_resolution = str(source_resolution).strip()[:6000]
    clean_draft_title = " ".join(str(draft_title).split()).strip()[:220]
    clean_direct_answer = str(direct_answer).strip()[:5000]
    clean_steps = [
        " ".join(str(step).split()).strip()[:1200]
        for step in troubleshooting_steps
        if " ".join(str(step).split()).strip()
    ][:20]

    if not clean_resolution:
        raise ValueError("A resolution note is required for a knowledge draft")
    if not clean_draft_title:
        raise ValueError("Knowledge draft title cannot be empty")
    if not clean_direct_answer:
        raise ValueError("Knowledge draft direct answer cannot be empty")
    if not clean_steps:
        clean_steps = [clean_direct_answer]

    now = utc_now()
    with database_connection() as connection:
        existing = connection.execute(
            """
            SELECT draft_id
            FROM knowledge_drafts
            WHERE local_ticket_id = ?
            """,
            (int(local_ticket_id),),
        ).fetchone()
        if existing is not None:
            return int(existing["draft_id"])

        cursor = connection.execute(
            """
            INSERT INTO knowledge_drafts (
                local_ticket_id,
                external_ticket_id,
                altitude_reference,
                source_status,
                source_title,
                source_category,
                source_device,
                source_problem,
                source_resolution,
                draft_title,
                intent_keywords,
                target_audience,
                direct_answer,
                troubleshooting_steps,
                bot_instruction,
                review_status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?, ?)
            """,
            (
                int(local_ticket_id),
                str(external_ticket_id or "").strip()[:120] or None,
                str(altitude_reference or "").strip()[:120] or None,
                " ".join(str(source_status).split()).strip()[:80] or "Resolved",
                " ".join(str(source_title).split()).strip()[:255],
                " ".join(str(source_category).split()).strip()[:120],
                " ".join(str(source_device).split()).strip()[:120],
                str(source_problem).strip()[:6000],
                clean_resolution,
                clean_draft_title,
                ", ".join(
                    part.strip()
                    for part in str(intent_keywords).split(",")
                    if part.strip()
                )[:1500],
                " ".join(str(target_audience).split()).strip()[:250]
                or "Staff, Faculty, Students",
                clean_direct_answer,
                json.dumps(clean_steps, ensure_ascii=False),
                str(bot_instruction or "").strip()[:2500] or None,
                now,
                now,
            ),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return a knowledge draft ID")
        return int(cursor.lastrowid)


def list_knowledge_drafts(
    *,
    review_status: str | None = None,
    limit: int = 250,
) -> list[dict[str, Any]]:
    """Return knowledge queue rows for the administrator portal."""
    safe_limit = max(1, min(int(limit), 1000))
    clauses: list[str] = []
    values: list[Any] = []

    if review_status is not None:
        clean_status = str(review_status).strip().title()
        if clean_status not in KNOWLEDGE_REVIEW_STATES:
            raise ValueError("Unsupported knowledge review status")
        clauses.append("review_status = ?")
        values.append(clean_status)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    values.append(safe_limit)

    with database_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT
                draft_id,
                local_ticket_id,
                external_ticket_id,
                altitude_reference,
                source_status,
                source_title,
                source_category,
                source_device,
                source_problem,
                source_resolution,
                draft_title,
                intent_keywords,
                target_audience,
                direct_answer,
                troubleshooting_steps,
                bot_instruction,
                review_status,
                review_notes,
                reviewed_by,
                reviewed_at,
                published_filename,
                published_at,
                created_at,
                updated_at
            FROM knowledge_drafts
            {where_sql}
            ORDER BY
                CASE review_status
                    WHEN 'Pending' THEN 0
                    WHEN 'Rejected' THEN 1
                    ELSE 2
                END,
                updated_at DESC,
                draft_id DESC
            LIMIT ?
            """,
            tuple(values),
        ).fetchall()

    results: list[dict[str, Any]] = []
    for row in rows:
        record = dict(row)
        try:
            parsed_steps = json.loads(str(record.get("troubleshooting_steps") or "[]"))
        except json.JSONDecodeError:
            parsed_steps = []
        record["troubleshooting_steps"] = (
            [str(step) for step in parsed_steps if str(step).strip()]
            if isinstance(parsed_steps, list)
            else []
        )
        results.append(record)
    return results


def get_knowledge_draft(draft_id: int) -> dict[str, Any] | None:
    """Return one knowledge draft with parsed troubleshooting steps."""
    numeric_id = int(draft_id)
    if numeric_id <= 0:
        return None

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT
                draft_id,
                local_ticket_id,
                external_ticket_id,
                altitude_reference,
                source_status,
                source_title,
                source_category,
                source_device,
                source_problem,
                source_resolution,
                draft_title,
                intent_keywords,
                target_audience,
                direct_answer,
                troubleshooting_steps,
                bot_instruction,
                review_status,
                review_notes,
                reviewed_by,
                reviewed_at,
                published_filename,
                published_at,
                created_at,
                updated_at
            FROM knowledge_drafts
            WHERE draft_id = ?
            LIMIT 1
            """,
            (numeric_id,),
        ).fetchone()

    if row is None:
        return None
    record = dict(row)
    try:
        parsed_steps = json.loads(str(record.get("troubleshooting_steps") or "[]"))
    except json.JSONDecodeError:
        parsed_steps = []
    record["troubleshooting_steps"] = (
        [str(step) for step in parsed_steps if str(step).strip()]
        if isinstance(parsed_steps, list)
        else []
    )
    return record


def update_knowledge_draft(
    draft_id: int,
    *,
    draft_title: str,
    intent_keywords: str,
    target_audience: str,
    direct_answer: str,
    troubleshooting_steps: list[str],
    bot_instruction: str | None,
    review_notes: str | None = None,
) -> None:
    """Save administrator edits while the draft is pending review."""
    numeric_id = int(draft_id)
    if numeric_id <= 0:
        raise ValueError("draft_id must be positive")

    clean_title = " ".join(str(draft_title).split()).strip()[:220]
    clean_answer = str(direct_answer).strip()[:5000]
    clean_steps = [
        " ".join(str(step).split()).strip()[:1200]
        for step in troubleshooting_steps
        if " ".join(str(step).split()).strip()
    ][:20]
    if not clean_title or not clean_answer or not clean_steps:
        raise ValueError("Title, direct answer, and at least one step are required")

    with database_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE knowledge_drafts
            SET
                draft_title = ?,
                intent_keywords = ?,
                target_audience = ?,
                direct_answer = ?,
                troubleshooting_steps = ?,
                bot_instruction = ?,
                review_notes = ?,
                updated_at = ?
            WHERE draft_id = ? AND review_status = 'Pending'
            """,
            (
                clean_title,
                ", ".join(
                    part.strip()
                    for part in str(intent_keywords).split(",")
                    if part.strip()
                )[:1500],
                " ".join(str(target_audience).split()).strip()[:250]
                or "Staff, Faculty, Students",
                clean_answer,
                json.dumps(clean_steps, ensure_ascii=False),
                str(bot_instruction or "").strip()[:2500] or None,
                str(review_notes or "").strip()[:3000] or None,
                utc_now(),
                numeric_id,
            ),
        )
        if cursor.rowcount == 0:
            raise ValueError("Only pending knowledge drafts can be edited")


def set_knowledge_draft_review_status(
    draft_id: int,
    *,
    review_status: str,
    reviewed_by: str,
    review_notes: str | None = None,
    published_filename: str | None = None,
) -> None:
    """Mark one pending knowledge draft approved or rejected."""
    numeric_id = int(draft_id)
    clean_status = str(review_status).strip().title()
    if numeric_id <= 0:
        raise ValueError("draft_id must be positive")
    if clean_status not in {"Approved", "Rejected"}:
        raise ValueError("Knowledge draft must be Approved or Rejected")

    now = utc_now()
    with database_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE knowledge_drafts
            SET
                review_status = ?,
                review_notes = COALESCE(?, review_notes),
                reviewed_by = ?,
                reviewed_at = ?,
                published_filename = COALESCE(?, published_filename),
                published_at = CASE WHEN ? = 'Approved' THEN ? ELSE published_at END,
                updated_at = ?
            WHERE draft_id = ? AND review_status = 'Pending'
            """,
            (
                clean_status,
                str(review_notes or "").strip()[:3000] or None,
                " ".join(str(reviewed_by).split()).strip()[:120] or "administrator",
                now,
                str(published_filename or "").strip()[:500] or None,
                clean_status,
                now,
                now,
                numeric_id,
            ),
        )
        if cursor.rowcount == 0:
            raise ValueError("Only pending knowledge drafts can be reviewed")


def get_knowledge_queue_summary() -> dict[str, int]:
    """Return pending/approved/rejected knowledge queue totals."""
    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(CASE WHEN review_status = 'Pending' THEN 1 ELSE 0 END), 0)
                    AS pending,
                COALESCE(SUM(CASE WHEN review_status = 'Approved' THEN 1 ELSE 0 END), 0)
                    AS approved,
                COALESCE(SUM(CASE WHEN review_status = 'Rejected' THEN 1 ELSE 0 END), 0)
                    AS rejected
            FROM knowledge_drafts
            """
        ).fetchone()

    if row is None:
        return {"total": 0, "pending": 0, "approved": 0, "rejected": 0}
    return {
        "total": int(row["total"]),
        "pending": int(row["pending"]),
        "approved": int(row["approved"]),
        "rejected": int(row["rejected"]),
    }


SECURITY_SEVERITIES = frozenset({"Low", "Medium", "High", "Critical"})
SECURITY_REVIEW_STATES = frozenset({"Open", "Reviewed", "Dismissed"})


def log_security_event(
    *,
    session_id: str,
    event_type: str,
    severity: str,
    summary: str,
    details: dict[str, Any] | None = None,
) -> int:
    """Create or increment one deduplicated chatbot misuse/security event."""
    clean_session_id = str(session_id).strip()
    clean_type = " ".join(str(event_type).split()).strip()[:120]
    clean_severity = str(severity).strip().title()
    clean_summary = " ".join(str(summary).split()).strip()[:500]

    if not clean_session_id:
        raise ValueError("session_id cannot be empty")
    if not clean_type or not clean_summary:
        raise ValueError("Security event type and summary are required")
    if clean_severity not in SECURITY_SEVERITIES:
        clean_severity = "Medium"

    normalized_key = "|".join(
        (
            clean_session_id,
            clean_type.casefold(),
            clean_summary.casefold(),
        )
    )
    fingerprint = hashlib.sha256(normalized_key.encode("utf-8")).hexdigest()
    details_json = json.dumps(
        details or {},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    now = utc_now()

    with database_connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO conversations (
                session_id,
                started_at,
                updated_at
            )
            VALUES (?, ?, ?)
            """,
            (clean_session_id, now, now),
        )
        connection.execute(
            """
            INSERT INTO security_events (
                event_fingerprint,
                session_id,
                event_type,
                severity,
                summary,
                details_json,
                occurrence_count,
                review_status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, 'Open', ?, ?)
            ON CONFLICT(event_fingerprint) DO UPDATE SET
                severity = excluded.severity,
                details_json = excluded.details_json,
                occurrence_count = security_events.occurrence_count + 1,
                review_status = 'Open',
                reviewed_by = NULL,
                reviewed_at = NULL,
                updated_at = excluded.updated_at
            """,
            (
                fingerprint,
                clean_session_id,
                clean_type,
                clean_severity,
                clean_summary,
                details_json,
                now,
                now,
            ),
        )
        row = connection.execute(
            """
            SELECT security_event_id
            FROM security_events
            WHERE event_fingerprint = ?
            """,
            (fingerprint,),
        ).fetchone()

    if row is None:
        raise RuntimeError("The security event was not recorded")
    return int(row["security_event_id"])


def list_security_findings(
    *,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Return unauthorized-email and misuse findings in one admin feed."""
    safe_limit = max(1, min(int(limit), 2_000))
    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM (
                SELECT
                    'email:' || attempt_id AS finding_id,
                    'Unauthorized email' AS event_type,
                    'Medium' AS severity,
                    'Non-school email used for ticket escalation' AS summary,
                    contact_email AS actor,
                    email_domain AS context,
                    1 AS occurrence_count,
                    review_status,
                    created_at,
                    updated_at
                FROM unauthorized_ticket_attempts

                UNION ALL

                SELECT
                    'event:' || security_event_id AS finding_id,
                    event_type,
                    severity,
                    summary,
                    session_id AS actor,
                    details_json AS context,
                    occurrence_count,
                    review_status,
                    created_at,
                    updated_at
                FROM security_events
            )
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_security_summary() -> dict[str, int]:
    """Return counts for the Security administrator page."""
    with database_connection() as connection:
        unauthorized = int(
            connection.execute(
                "SELECT COUNT(*) FROM unauthorized_ticket_attempts"
            ).fetchone()[0]
        )
        misuse = int(
            connection.execute(
                "SELECT COUNT(*) FROM security_events"
            ).fetchone()[0]
        )
        open_findings = int(
            connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM unauthorized_ticket_attempts
                     WHERE review_status = 'Open')
                  + (SELECT COUNT(*) FROM security_events
                     WHERE review_status = 'Open')
                """
            ).fetchone()[0]
        )
        high_severity = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM security_events
                WHERE severity IN ('High', 'Critical')
                  AND review_status = 'Open'
                """
            ).fetchone()[0]
        )
    return {
        "total_findings": unauthorized + misuse,
        "open_findings": open_findings,
        "unauthorized_email_findings": unauthorized,
        "misuse_findings": misuse,
        "high_severity_findings": high_severity,
    }


def update_security_finding_review(
    finding_id: str,
    *,
    review_status: str,
    reviewed_by: str | None = None,
) -> None:
    """Mark a security finding as Open, Reviewed, or Dismissed."""
    clean_id = str(finding_id).strip()
    clean_status = str(review_status).strip().title()
    if clean_status not in SECURITY_REVIEW_STATES:
        raise ValueError("Unsupported security review status")

    reviewer = " ".join(str(reviewed_by or "").split()).strip()[:120] or None
    reviewed_at = utc_now() if clean_status != "Open" else None

    if clean_id.startswith("email:"):
        table = "unauthorized_ticket_attempts"
        id_column = "attempt_id"
        raw_id = clean_id.split(":", 1)[1]
    elif clean_id.startswith("event:"):
        table = "security_events"
        id_column = "security_event_id"
        raw_id = clean_id.split(":", 1)[1]
    else:
        raise ValueError("Unsupported security finding identifier")

    try:
        numeric_id = int(raw_id)
    except ValueError as error:
        raise ValueError("Invalid security finding identifier") from error

    with database_connection() as connection:
        cursor = connection.execute(
            f"""
            UPDATE {table}
            SET review_status = ?, reviewed_by = ?, reviewed_at = ?
            WHERE {id_column} = ?
            """,
            (clean_status, reviewer, reviewed_at, numeric_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("The selected security finding does not exist")


ANNOUNCEMENT_SEVERITIES = frozenset(
    {"info", "maintenance", "warning", "outage", "resolved"}
)


def _clean_announcement_text(
    value: str,
    *,
    field_name: str,
    maximum_length: int,
    preserve_line_breaks: bool = False,
) -> str:
    """Normalize required announcement text and enforce a safe size limit."""
    raw_value = str(value).replace("\r\n", "\n").replace("\r", "\n")

    if preserve_line_breaks:
        normalized_lines = [
            " ".join(line.split()).strip()
            for line in raw_value.split("\n")
        ]
        compact_lines: list[str] = []
        previous_was_blank = False
        for line in normalized_lines:
            is_blank = not line
            if is_blank and previous_was_blank:
                continue
            compact_lines.append(line)
            previous_was_blank = is_blank
        cleaned = "\n".join(compact_lines).strip()
    else:
        cleaned = " ".join(raw_value.split()).strip()

    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty")

    return cleaned[:maximum_length].rstrip()


def _normalize_announcement_timestamp(value: str | None) -> str | None:
    """Validate an optional ISO timestamp and return canonical UTC text."""
    if value is None:
        return None

    cleaned = str(value).strip()

    if not cleaned:
        return None

    try:
        parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Announcement timestamps must use ISO-8601 format") from error

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")


def create_announcement(
    *,
    title: str,
    message: str,
    severity: str = "info",
    starts_at: str | None = None,
    ends_at: str | None = None,
    is_active: bool = True,
    created_by: str | None = None,
) -> dict[str, Any]:
    """Create an announcement and return the stored row."""
    clean_title = _clean_announcement_text(
        title,
        field_name="Announcement title",
        maximum_length=120,
    )
    clean_message = _clean_announcement_text(
        message,
        field_name="Announcement message",
        maximum_length=1500,
        preserve_line_breaks=True,
    )
    clean_severity = str(severity).strip().lower()

    if clean_severity not in ANNOUNCEMENT_SEVERITIES:
        raise ValueError(f"Unsupported announcement severity: {severity}")

    clean_starts_at = _normalize_announcement_timestamp(starts_at)
    clean_ends_at = _normalize_announcement_timestamp(ends_at)

    if (
        clean_starts_at is not None
        and clean_ends_at is not None
        and clean_ends_at <= clean_starts_at
    ):
        raise ValueError("The announcement end time must be after the start time")

    clean_created_by = (
        _clean_optional_text(created_by, maximum_length=120)
        if created_by is not None
        else None
    )
    now = utc_now()

    with database_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO announcements (
                title,
                message,
                severity,
                starts_at,
                ends_at,
                is_active,
                created_by,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                clean_title,
                clean_message,
                clean_severity,
                clean_starts_at,
                clean_ends_at,
                int(is_active),
                clean_created_by,
                now,
                now,
            ),
        )
        inserted_id = cursor.lastrowid

        if inserted_id is None:
            raise RuntimeError(
                "SQLite did not return an announcement ID after insert"
            )

        announcement_id = inserted_id

        row = connection.execute(
            """
            SELECT *
            FROM announcements
            WHERE announcement_id = ?
            """,
            (announcement_id,),
        ).fetchone()

    if row is None:
        raise RuntimeError("The announcement was not created")

    return dict(row)


def update_announcement(
    announcement_id: int,
    *,
    title: str,
    message: str,
    severity: str,
    starts_at: str | None,
    ends_at: str | None,
    is_active: bool,
) -> dict[str, Any]:
    """Update an existing announcement and return the stored row."""
    if announcement_id <= 0:
        raise ValueError("announcement_id must be positive")

    clean_title = _clean_announcement_text(
        title,
        field_name="Announcement title",
        maximum_length=120,
    )
    clean_message = _clean_announcement_text(
        message,
        field_name="Announcement message",
        maximum_length=1500,
        preserve_line_breaks=True,
    )
    clean_severity = str(severity).strip().lower()

    if clean_severity not in ANNOUNCEMENT_SEVERITIES:
        raise ValueError(f"Unsupported announcement severity: {severity}")

    clean_starts_at = _normalize_announcement_timestamp(starts_at)
    clean_ends_at = _normalize_announcement_timestamp(ends_at)

    if (
        clean_starts_at is not None
        and clean_ends_at is not None
        and clean_ends_at <= clean_starts_at
    ):
        raise ValueError("The announcement end time must be after the start time")

    now = utc_now()

    with database_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE announcements
            SET
                title = ?,
                message = ?,
                severity = ?,
                starts_at = ?,
                ends_at = ?,
                is_active = ?,
                updated_at = ?
            WHERE announcement_id = ?
            """,
            (
                clean_title,
                clean_message,
                clean_severity,
                clean_starts_at,
                clean_ends_at,
                int(is_active),
                now,
                announcement_id,
            ),
        )

        if cursor.rowcount == 0:
            raise ValueError("The selected announcement does not exist")

        row = connection.execute(
            """
            SELECT *
            FROM announcements
            WHERE announcement_id = ?
            """,
            (announcement_id,),
        ).fetchone()

    if row is None:
        raise RuntimeError("The announcement update could not be loaded")

    return dict(row)


def set_announcement_active(
    announcement_id: int,
    *,
    is_active: bool,
) -> None:
    """Activate or deactivate an announcement without deleting it."""
    if announcement_id <= 0:
        raise ValueError("announcement_id must be positive")

    with database_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE announcements
            SET is_active = ?, updated_at = ?
            WHERE announcement_id = ?
            """,
            (int(is_active), utc_now(), announcement_id),
        )

        if cursor.rowcount == 0:
            raise ValueError("The selected announcement does not exist")


def delete_announcement(announcement_id: int) -> None:
    """Permanently delete an announcement."""
    if announcement_id <= 0:
        raise ValueError("announcement_id must be positive")

    with database_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM announcements
            WHERE announcement_id = ?
            """,
            (announcement_id,),
        )

        if cursor.rowcount == 0:
            raise ValueError("The selected announcement does not exist")


def list_announcements(
    *,
    include_inactive: bool = True,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return announcements newest first for administrator management."""
    safe_limit = max(1, min(int(limit), 500))
    where_clause = "" if include_inactive else "WHERE is_active = 1"

    with database_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT
                announcement_id,
                title,
                message,
                severity,
                starts_at,
                ends_at,
                is_active,
                created_by,
                created_at,
                updated_at
            FROM announcements
            {where_clause}
            ORDER BY created_at DESC, announcement_id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_active_announcements(
    *,
    at_time: str | None = None,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """Return announcements that are active and within their schedule window."""
    reference_time = _normalize_announcement_timestamp(at_time) or utc_now()
    safe_limit = max(1, min(int(limit), 100))

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                announcement_id,
                title,
                message,
                severity,
                starts_at,
                ends_at,
                created_by,
                created_at,
                updated_at
            FROM announcements
            WHERE is_active = 1
              AND (starts_at IS NULL OR starts_at <= ?)
              AND (ends_at IS NULL OR ends_at >= ?)
            ORDER BY
                CASE severity
                    WHEN 'outage' THEN 1
                    WHEN 'warning' THEN 2
                    WHEN 'maintenance' THEN 3
                    WHEN 'info' THEN 4
                    WHEN 'resolved' THEN 5
                    ELSE 6
                END,
                created_at DESC,
                announcement_id DESC
            LIMIT ?
            """,
            (reference_time, reference_time, safe_limit),
        ).fetchall()

    return [dict(row) for row in rows]


def get_announcement_summary() -> dict[str, int]:
    """Return counts used by the administrator overview."""
    now = utc_now()

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total_announcements,
                COALESCE(SUM(
                    CASE
                        WHEN is_active = 1
                         AND (starts_at IS NULL OR starts_at <= ?)
                         AND (ends_at IS NULL OR ends_at >= ?)
                        THEN 1 ELSE 0
                    END
                ), 0) AS active_announcements,
                COALESCE(SUM(
                    CASE
                        WHEN is_active = 1
                         AND starts_at IS NOT NULL
                         AND starts_at > ?
                        THEN 1 ELSE 0
                    END
                ), 0) AS scheduled_announcements
            FROM announcements
            """,
            (now, now, now),
        ).fetchone()

    if row is None:
        return {
            "total_announcements": 0,
            "active_announcements": 0,
            "scheduled_announcements": 0,
        }

    return {
        "total_announcements": int(row["total_announcements"]),
        "active_announcements": int(row["active_announcements"]),
        "scheduled_announcements": int(row["scheduled_announcements"]),
    }
