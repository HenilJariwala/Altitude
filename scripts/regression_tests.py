from __future__ import annotations

import ast
from types import SimpleNamespace
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]

APP_ROOT = PROJECT_ROOT / "app"

app_path = str(APP_ROOT)

if app_path not in sys.path:
    sys.path.insert(
        0,
        app_path,
    )


from core.conversation_context import (  # noqa: E402
    build_contextual_query,
)
from core.conversation_router import (  # noqa: E402
    route_conversation_message,
)
from core.extended_support_router import (  # noqa: E402
    route_extended_support_question,
)
import core.assistant as assistant  # noqa: E402
import core.inventory_router as inventory  # noqa: E402
import core.rag as rag  # noqa: E402
from core.platform_context import (  # noqa: E402
    detect_platform,
    is_platform_only_reply,
)
from core.printer_router import (  # noqa: E402
    route_printer_question,
)
from core.question_logger import (  # noqa: E402
    redact_sensitive_information,
)
from ingest_knowledge import (  # noqa: E402
    load_markdown_chunks,
    split_text,
)
from core.support_router import (  # noqa: E402
    prepare_support_question,
    route_security_or_account_question,
)
from core.wifi_router import (  # noqa: E402
    route_wifi_question,
)

REAL_FETCH_INVENTORY = inventory.fetch_inventory


def fake_fetch_inventory() -> inventory.InventoryPayload:
    """Return predictable inventory data for automated tests."""

    return inventory.InventoryPayload(
        types=[
            inventory.InventoryItem(
                typeId=1,
                typeName="MacBook",
                totalCount=9,
                availableCount=2,
                loanedCount=7,
            ),
            inventory.InventoryItem(
                typeId=8,
                typeName="USB-C Cable",
                totalCount=31,
                availableCount=15,
                loanedCount=16,
            ),
            inventory.InventoryItem(
                typeId=11,
                typeName="USB-C Charger",
                totalCount=11,
                availableCount=8,
                loanedCount=3,
            ),
        ]
    )


class RoutingRegressionTests(unittest.TestCase):
    def setUp(
        self,
    ) -> None:
        """
        Replace the real inventory API call during each test and
        restore it automatically afterward.
        """

        patcher = patch.object(
            inventory,
            "fetch_inventory",
            new=fake_fetch_inventory,
        )

        patcher.start()

        self.addCleanup(patcher.stop)

    def test_inventory_does_not_capture_troubleshooting(
        self,
    ) -> None:
        self.assertFalse(
            inventory.route_inventory_question(
                "My MacBook has no sound.",
                [],
            ).handled
        )

        self.assertFalse(
            inventory.route_inventory_question(
                "My USB drive is not showing.",
                [],
            ).handled
        )

    def test_inventory_requests(
        self,
    ) -> None:
        self.assertTrue(
            inventory.route_inventory_question(
                "Can I borrow a MacBook?",
                [],
            ).handled
        )

        result = inventory.route_inventory_question(
            "I want a USB-C cable.",
            [],
        )

        self.assertTrue(result.handled)

        self.assertIn(
            "15",
            result.answer,
        )

        self.assertIn(
            "USB-C Cable",
            result.answer,
        )

    def test_named_inventory_item_beats_list_language(
        self,
    ) -> None:
        result = inventory.route_inventory_question(
            "Check the live inventory to see if any MacBooks are available.",
            [],
        )

        self.assertTrue(result.handled)
        self.assertIn("MacBook", result.answer)
        self.assertIn("2", result.answer)
        self.assertNotIn("USB-C Cable", result.answer)

    def test_extended_support_prevents_cross_topic_rag(
        self,
    ) -> None:
        cases = {
            "How do I troubleshoot a DNS server not responding error?": "DNS",
            "Why is the staff copier asking for a PIN?": "PIN",
            "How do I reopen a closed helpdesk ticket?": "reopen",
            "Why is my Python script not running?": "Python",
            "How do I safely clean my device screen?": "microfiber",
        }

        for question, expected in cases.items():
            with self.subTest(question=question):
                decision = route_extended_support_question(question, [])
                self.assertTrue(decision.handled)
                self.assertIn(expected.lower(), decision.answer.lower())

    def test_feedback_worthy_wifi_and_capability_answers(
        self,
    ) -> None:
        from core.feedback_policy import is_feedback_eligible_response

        capability = assistant.prepare_answer(
            "What can you help me with?",
            [],
        )
        self.assertIsNotNone(capability.direct_answer)
        self.assertTrue(
            is_feedback_eligible_response(
                str(capability.direct_answer),
                route="direct",
            )
        )

        wifi = assistant.prepare_answer(
            "How do I connect to Student Wi-Fi?",
            [],
        )
        self.assertIsNotNone(wifi.direct_answer)
        self.assertTrue(
            is_feedback_eligible_response(
                str(wifi.direct_answer),
                route="direct",
            )
        )

    def test_inventory_list(
        self,
    ) -> None:
        result = inventory.route_inventory_question(
            "What items are currently available?",
            [],
        )

        self.assertTrue(result.handled)

        self.assertIn(
            "MacBook",
            result.answer,
        )

        self.assertIn(
            "USB-C Cable",
            result.answer,
        )

    def test_printer_direct_setup(
        self,
    ) -> None:
        first = route_printer_question(
            "How do I add the Learning Commons printer?",
            [],
        )

        self.assertTrue(first.handled)

        self.assertIn(
            "Mac",
            first.answer,
        )

        self.assertIn(
            "Windows",
            first.answer,
        )

        history = [
            {
                "role": "user",
                "content": ("How do I add the Learning Commons printer?"),
            },
            {
                "role": "assistant",
                "content": first.answer,
            },
            {
                "role": "user",
                "content": "Mac",
            },
        ]

        second = route_printer_question(
            "Mac",
            history,
        )

        self.assertTrue(second.handled)

        self.assertIn(
            "192.168.1.205",
            second.answer,
        )

    def test_wifi_follow_up_keeps_troubleshooting_mode(
        self,
    ) -> None:
        first = route_wifi_question(
            "I cannot connect to Wi-Fi",
            [],
        )

        self.assertTrue(first.handled)

        history = [
            {
                "role": "user",
                "content": ("I cannot connect to Wi-Fi"),
            },
            {
                "role": "assistant",
                "content": first.answer,
            },
            {
                "role": "user",
                "content": "Student",
            },
        ]

        second = route_wifi_question(
            "Student",
            history,
        )

        self.assertTrue(second.handled)

        self.assertIn(
            "Forget This Network",
            second.answer,
        )

        self.assertEqual(
            second.resource,
            "student_wifi_qr.png",
        )

    def test_os_clarification(
        self,
    ) -> None:
        first = prepare_support_question(
            "My USB drive is not showing.",
            [],
        )

        self.assertTrue(first.handled)

        self.assertIn(
            "Mac",
            first.answer,
        )

        self.assertIn(
            "Windows",
            first.answer,
        )

        history = [
            {
                "role": "user",
                "content": ("My USB drive is not showing."),
            },
            {
                "role": "assistant",
                "content": first.answer,
            },
            {
                "role": "user",
                "content": "Mac",
            },
        ]

        second = prepare_support_question(
            "Mac",
            history,
        )

        self.assertFalse(second.handled)

        self.assertIn(
            "USB drive",
            second.retrieval_question,
        )

        self.assertIn(
            "Mac",
            second.retrieval_question,
        )

    def test_vague_laptop_problem(
        self,
    ) -> None:
        result = prepare_support_question(
            "My laptop is not working.",
            [],
        )

        self.assertTrue(result.handled)

        self.assertIn(
            "What exactly is happening",
            result.answer,
        )

    def test_force_quit_requests_operating_system(
        self,
    ) -> None:
        result = prepare_support_question(
            "Help me force quit my computer",
            [],
        )

        self.assertTrue(result.handled)
        self.assertIn("Mac", result.answer)
        self.assertIn("Windows", result.answer)

    def test_natural_mac_follow_up_preserves_issue(
        self,
    ) -> None:
        first = prepare_support_question(
            "Help me force quit my computer",
            [],
        )

        history = [
            {
                "role": "user",
                "content": "Help me force quit my computer",
            },
            {
                "role": "assistant",
                "content": first.answer,
            },
            {
                "role": "user",
                "content": "I am using a Mac",
            },
        ]

        result = prepare_support_question(
            "I am using a Mac",
            history,
        )

        self.assertFalse(result.handled)
        self.assertIn(
            "force quit",
            result.retrieval_question.lower(),
        )
        self.assertIn(
            "Operating system: Mac",
            result.retrieval_question,
        )

    def test_platform_correction_recovers_after_wrong_answer(
        self,
    ) -> None:
        history = [
            {
                "role": "user",
                "content": "Help me force quit my computer",
            },
            {
                "role": "assistant",
                "content": ("Open Task Manager and select End task."),
            },
            {
                "role": "user",
                "content": "I am using Mac",
            },
        ]

        result = prepare_support_question(
            "I am using Mac",
            history,
        )

        self.assertFalse(result.handled)
        self.assertIn(
            "Help me force quit my computer",
            result.retrieval_question,
        )
        self.assertIn(
            "Operating system: Mac",
            result.retrieval_question,
        )

    def test_context_query_rewrites_natural_os_reply(
        self,
    ) -> None:
        history = [
            {
                "role": "user",
                "content": "My USB drive is not showing",
            },
            {
                "role": "assistant",
                "content": "Are you using Mac or Windows?",
            },
            {
                "role": "user",
                "content": "I am on macOS",
            },
        ]

        query = build_contextual_query(
            "I am on macOS",
            history,
        )

        self.assertIn("USB drive", query)
        self.assertIn("Operating system: Mac", query)

    def test_platform_matching_uses_whole_phrases(
        self,
    ) -> None:
        self.assertIsNone(detect_platform("The machine learning model is slow"))
        self.assertTrue(is_platform_only_reply("Actually, I am using Windows 11"))

    def test_printer_accepts_natural_device_reply(
        self,
    ) -> None:
        first = route_printer_question(
            "How do I add the Learning Commons printer?",
            [],
        )

        history = [
            {
                "role": "user",
                "content": ("How do I add the Learning Commons printer?"),
            },
            {
                "role": "assistant",
                "content": first.answer,
            },
            {
                "role": "user",
                "content": "I am using a Mac",
            },
        ]

        second = route_printer_question(
            "I am using a Mac",
            history,
        )

        self.assertTrue(second.handled)
        self.assertIn("192.168.1.205", second.answer)

    def test_inventory_request_configuration(
        self,
    ) -> None:
        response = Mock()
        response.status_code = 200
        response.content = b"{}"
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "types": [
                {
                    "typeId": 1,
                    "typeName": "MacBook",
                    "totalCount": 2,
                    "availableCount": 1,
                    "loanedCount": 1,
                }
            ]
        }

        with (
            patch.object(
                inventory,
                "INVENTORY_API_URL",
                "https://inventory.example/api",
            ),
            patch.object(
                inventory,
                "INVENTORY_API_TIMEOUT_SECONDS",
                8.0,
            ),
            patch.object(
                inventory.requests,
                "get",
                return_value=response,
            ) as request_get,
        ):
            payload = REAL_FETCH_INVENTORY()

        self.assertEqual(payload.types[0].typeName, "MacBook")
        request_get.assert_called_once()
        call_kwargs = request_get.call_args.kwargs
        self.assertEqual(call_kwargs["timeout"], (5.0, 8.0))
        self.assertFalse(call_kwargs["allow_redirects"])

    def test_force_quit_follow_up_uses_lexical_fallback(
        self,
    ) -> None:
        history = [
            {
                "role": "user",
                "content": "Help me force quit my computer",
            },
            {
                "role": "assistant",
                "content": "Are you using a Mac or Windows device?",
            },
            {
                "role": "user",
                "content": "Mac",
            },
        ]

        with patch.object(
            rag,
            "get_vector_store",
            side_effect=ConnectionError("Ollama unavailable"),
        ):
            plan = assistant.prepare_answer(
                "Mac",
                history,
            )

        self.assertIsNone(plan.direct_answer)
        self.assertIn("Force Quit", plan.context)
        self.assertEqual(
            plan.sources,
            ("mac_basic_troubleshooting.md",),
        )
        self.assertNotIn("Task Manager", plan.context)

    def test_microsoft_word_learning_request_is_it_help(
        self,
    ) -> None:
        history = [
            {
                "role": "user",
                "content": "Help me with Google Docs",
            },
            {
                "role": "assistant",
                "content": (
                    "What would you like help with in Google Docs?"
                ),
            },
            {
                "role": "user",
                "content": (
                    "I want to learn about Microsoft Word"
                ),
            },
        ]

        plan = assistant.prepare_answer(
            "I want to learn about Microsoft Word",
            history,
        )

        self.assertIsNotNone(plan.direct_answer)
        self.assertIn("Microsoft Word", plan.direct_answer or "")
        self.assertNotEqual(
            plan.direct_answer,
            assistant.OUT_OF_SCOPE_MESSAGE,
        )

    def test_new_product_does_not_inherit_old_product_context(
        self,
    ) -> None:
        history = [
            {
                "role": "user",
                "content": "Help me with Google Docs",
            },
            {
                "role": "assistant",
                "content": (
                    "What would you like help with in Google Docs?"
                ),
            },
        ]

        query = rag.build_retrieval_query(
            "How do I save a Microsoft Word file as PDF?",
            history,
        )

        self.assertEqual(
            query,
            "How do I save a Microsoft Word file as PDF?",
        )
        self.assertNotIn("Google Docs", query)

    def test_platform_alone_requests_the_actual_issue(
        self,
    ) -> None:
        result = prepare_support_question(
            "Mac",
            [
                {
                    "role": "assistant",
                    "content": "How can I help you?",
                },
                {
                    "role": "user",
                    "content": "Mac",
                },
            ],
        )

        self.assertTrue(result.handled)
        self.assertIn("What IT issue", result.answer)

    def test_prepare_answer_preserves_issue_end_to_end(
        self,
    ) -> None:
        history = [
            {
                "role": "user",
                "content": "Help me force quit my computer",
            },
            {
                "role": "assistant",
                "content": "Are you using a Mac or Windows device?",
            },
            {
                "role": "user",
                "content": "I am using a Mac",
            },
        ]
        captured_question = ""

        def fake_retrieval(
            question: str,
            history: list[dict[str, object]] | None = None,
            result_count: int = 16,
        ) -> rag.RagResult:
            del history, result_count
            nonlocal captured_question
            captured_question = question
            return rag.RagResult(
                context="Press Option Command Escape and choose Force Quit.",
                sources=("mac_basic_troubleshooting.md",),
                best_distance=0.1,
                matched_chunks=1,
            )

        with patch.object(
            assistant,
            "retrieve_public_knowledge",
            side_effect=fake_retrieval,
        ):
            plan = assistant.prepare_answer(
                "I am using a Mac",
                history,
            )

        self.assertIsNone(plan.direct_answer)
        self.assertIn("force quit", captured_question.lower())
        self.assertIn("Operating system: Mac", captured_question)
        self.assertNotIn("Task Manager", plan.context)

    def test_rag_rejects_opposite_platform_document(
        self,
    ) -> None:
        windows_document = SimpleNamespace(
            page_content=(
                "Use Task Manager and select End task for a frozen application."
            ),
            metadata={
                "audience": "public",
                "platform": "windows",
                "section_title": "Windows Application Is Frozen",
                "intent_keywords": ("application frozen, force quit, end task"),
                "source": "windows_basic_troubleshooting.md",
            },
        )
        mac_document = SimpleNamespace(
            page_content=(
                "Press Option Command Escape, select the frozen "
                "application, and choose Force Quit."
            ),
            metadata={
                "audience": "public",
                "platform": "macos",
                "section_title": ("Mac Is Frozen or Shows a Spinning Beachball"),
                "intent_keywords": (
                    "application frozen, force quit, Mac not responding"
                ),
                "source": "mac_basic_troubleshooting.md",
            },
        )

        vector_store = Mock()
        vector_store.similarity_search_with_score.return_value = [
            (windows_document, 0.05),
            (mac_document, 0.80),
        ]

        with patch.object(
            rag,
            "get_vector_store",
            return_value=vector_store,
        ):
            result = rag.retrieve_public_knowledge(
                question=(
                    "Help me force quit a frozen application\nOperating system: Mac"
                ),
                history=[],
            )

        self.assertEqual(
            result.sources,
            ("mac_basic_troubleshooting.md",),
        )
        self.assertIn("Force Quit", result.context)

    def test_rag_returns_complete_topic_context(
        self,
    ) -> None:
        full_section = (
            "## Topic: Mac App Is Frozen\n"
            "**Intent Keywords:** force quit, frozen app\n"
            "1. Save work.\n2. Press Option Command Escape.\n"
            "3. Select the application and choose Force Quit."
        )
        document = SimpleNamespace(
            page_content="Press Option Command Escape.",
            metadata={
                "audience": "public",
                "platform": "macos",
                "section_title": "Mac App Is Frozen",
                "intent_keywords": "force quit, frozen app",
                "source": "mac_basic_troubleshooting.md",
                "full_section": full_section,
            },
        )
        vector_store = Mock()
        vector_store.similarity_search_with_score.return_value = [
            (document, 0.10),
        ]

        with patch.object(
            rag,
            "get_vector_store",
            return_value=vector_store,
        ):
            result = rag.retrieve_public_knowledge("Force quit a frozen app on Mac")

        self.assertEqual(result.context, full_section)

    def test_knowledge_topics_are_chunked_safely(
        self,
    ) -> None:
        documents = load_markdown_chunks()

        self.assertTrue(documents)
        self.assertTrue(
            any(
                document.metadata.get("section_chunk_index", 0) > 0
                for document in documents
            )
        )
        self.assertTrue(
            all(len(document.page_content) <= 700 for document in documents)
        )
        self.assertTrue(
            all(
                "full_section" in document.metadata
                for document in documents
                if document.metadata.get("section_title")
            )
        )

        with self.assertRaises(ValueError):
            split_text("test", chunk_size=100, overlap=100)

    def test_question_log_redacts_sensitive_values(
        self,
    ) -> None:
        cleaned = redact_sensitive_information(
            "Email me at student@example.com; password is Hunter2; "
            "OTP: 123456; call 519-555-1234; token=abc123"
        )

        self.assertNotIn("student@example.com", cleaned)
        self.assertNotIn("Hunter2", cleaned)
        self.assertNotIn("123456", cleaned)
        self.assertNotIn("519-555-1234", cleaned)
        self.assertNotIn("abc123", cleaned)
        self.assertIn("[EMAIL REDACTED]", cleaned)

    def test_invalid_numeric_settings_fall_back(
        self,
    ) -> None:
        with patch.dict(
            "os.environ",
            {
                "RAG_TEST_FLOAT": "nan",
                "INVENTORY_TEST_FLOAT": "inf",
            },
        ):
            self.assertEqual(
                rag.get_float_setting("RAG_TEST_FLOAT", 0.95),
                0.95,
            )
            self.assertEqual(
                inventory.get_positive_float_setting(
                    "INVENTORY_TEST_FLOAT",
                    5.0,
                ),
                5.0,
            )

    def test_security_and_password(
        self,
    ) -> None:
        phishing = route_security_or_account_question(
            "I clicked a link in a suspicious email."
        )

        self.assertTrue(phishing.handled)

        self.assertIn(
            "immediately",
            phishing.answer,
        )

        password = route_security_or_account_question(
            "I forgot my school Google password."
        )

        self.assertTrue(password.handled)

        self.assertIn(
            "IT Helpdesk",
            password.answer,
        )

    def test_conversation_and_scope(
        self,
    ) -> None:
        self.assertTrue(
            route_conversation_message(
                "thank you",
                [],
            ).handled
        )

        out = route_conversation_message(
            "How do I request paid time off?",
            [],
        )

        self.assertTrue(out.handled)

        self.assertIn(
            "non-IT",
            out.answer,
        )

        self.assertIn(
            "Wi-Fi",
            out.answer,
        )

        self.assertFalse(
            route_conversation_message(
                "yes",
                [],
            ).handled
        )


class SourceQualityTests(unittest.TestCase):
    def test_no_duplicate_top_level_definitions(
        self,
    ) -> None:
        for path in (PROJECT_ROOT / "app" / "core").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))

            names: set[str] = set()
            duplicates: set[str] = set()

            for node in tree.body:
                if isinstance(
                    node,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                        ast.ClassDef,
                    ),
                ):
                    if node.name in names:
                        duplicates.add(node.name)

                    names.add(node.name)

            self.assertFalse(
                duplicates,
                (f"{path.name}: duplicate definitions {duplicates}"),
            )

    def test_knowledge_frontmatter(
        self,
    ) -> None:
        for path in (PROJECT_ROOT / "knowledge_base").glob("*.md"):
            lines = path.read_text(encoding="utf-8").splitlines()

            self.assertGreaterEqual(
                len(lines),
                3,
                path.name,
            )

            self.assertEqual(
                lines[0],
                "---",
                path.name,
            )

            self.assertIn(
                "---",
                lines[1:12],
                path.name,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
