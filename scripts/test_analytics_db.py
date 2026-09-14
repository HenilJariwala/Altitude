from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        test_database = (
            Path(temporary_directory) / "test_altitude.db"
        )

        # Set before importing analytics_db.
        os.environ["ALTITUDE_DB_PATH"] = str(test_database)

        from core.analytics_db import (
            create_conversation,
            get_conversation_messages,
            get_database_health,
            initialize_database,
            save_message,
        )

        initialize_database()

        session_id = str(uuid.uuid4())
        create_conversation(session_id)

        user_message_id = str(uuid.uuid4())

        save_message(
            message_id=user_message_id,
            session_id=session_id,
            role="user",
            content="How do I force quit an application?",
        )

        # Save the same message again to simulate a Streamlit rerun.
        save_message(
            message_id=user_message_id,
            session_id=session_id,
            role="user",
            content="How do I force quit an application?",
        )

        save_message(
            session_id=session_id,
            role="assistant",
            content="Are you using a Mac or Windows device?",
            route="clarification",
            feedback_eligible=False,
        )

        messages = get_conversation_messages(session_id)

        assert len(messages) == 2, (
            f"Expected 2 messages, found {len(messages)}"
        )

        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

        health = get_database_health()

        assert health["quick_check"] == "ok"
        assert health["schema_version"] == 1
        assert health["conversation_count"] == 1
        assert health["message_count"] == 2

        print("Analytics database test passed.")
        print(f"Database path: {health['database_path']}")
        print(f"Tables: {', '.join(health['tables'])}")
        print(
            f"Conversations: {health['conversation_count']}"
        )
        print(f"Messages: {health['message_count']}")


if __name__ == "__main__":
    main()
    