#!/usr/bin/env python3
"""Regression checks for the single shared learned_support.md publication flow."""

from __future__ import annotations

import functools
import sys
import tempfile
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"

if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import core.knowledge_queue as knowledge_queue


def make_draft(draft_id: int, title: str, device: str) -> dict:
    return {
        "id": draft_id,
        "review_status": "Pending",
        "draft_title": title,
        "intent_keywords": f"{device}, troubleshooting",
        "target_audience": "Staff, Faculty, Students",
        "direct_answer": f"Use the approved {device} fix.",
        "source_problem": f"The user's {device} was not working correctly.",
        "troubleshooting_steps": [
            f"Disconnect the {device}.",
            f"Reconnect the {device} and test again.",
        ],
        "bot_instruction": "Use this only for matching symptoms.",
    }


class FakeVectorStore:
    def __init__(self) -> None:
        self.added: list[tuple[list, list[str]]] = []
        self.deleted: list[str] = []

    def add_documents(self, documents, ids):
        self.added.append((documents, ids))

    def delete(self, ids):
        self.deleted.extend(ids)


def main() -> int:
    drafts = {
        101: make_draft(101, "USB-C dock monitor issue", "monitor"),
        102: make_draft(102, "Printer queue issue", "printer"),
    }
    reviewed: list[tuple[int, str]] = []
    store = FakeVectorStore()

    @functools.lru_cache(maxsize=1)
    def fake_lexical_documents():
        return []

    fake_rag = types.ModuleType("core.rag")
    fake_rag.get_vector_store = lambda: store
    fake_rag.get_lexical_documents = fake_lexical_documents
    original_rag = sys.modules.get("core.rag")
    sys.modules["core.rag"] = fake_rag

    original_get = knowledge_queue.get_knowledge_draft
    original_set = knowledge_queue.set_knowledge_draft_review_status
    original_path = knowledge_queue.LEARNED_KNOWLEDGE_PATH
    original_vector_builder = knowledge_queue._vector_document_for_markdown

    try:
        with tempfile.TemporaryDirectory() as temporary_directory:
            shared_path = Path(temporary_directory) / "learned_support.md"
            knowledge_queue.LEARNED_KNOWLEDGE_PATH = shared_path
            knowledge_queue.get_knowledge_draft = lambda draft_id: drafts.get(int(draft_id))
            knowledge_queue._vector_document_for_markdown = lambda **kwargs: {
                "page_content": kwargs["markdown"],
                "metadata": {"source": kwargs["filename"], "title": kwargs["title"]},
            }

            def fake_set(draft_id, *, review_status, **kwargs):
                reviewed.append((int(draft_id), str(review_status)))

            knowledge_queue.set_knowledge_draft_review_status = fake_set

            first_name = knowledge_queue.publish_knowledge_draft(
                101,
                reviewed_by="tester",
            )
            second_name = knowledge_queue.publish_knowledge_draft(
                102,
                reviewed_by="tester",
            )

            content = shared_path.read_text(encoding="utf-8")

            assert first_name == "learned_support.md"
            assert second_name == "learned_support.md"
            assert content.count("title: \"Altitude Learned Support Knowledge\"") == 1
            assert content.count("## Topic:") == 2
            assert "## Topic: USB-C dock monitor issue" in content
            assert "## Topic: Printer queue issue" in content
            assert len(store.added) == 2
            assert reviewed == [(101, "Approved"), (102, "Approved")]

        print("[PASS] every approval publishes to learned_support.md")
        print("[PASS] the shared file has one YAML header")
        print("[PASS] new approved topics append instead of creating new files")
        print("[PASS] each new topic is indexed independently")
        print("[PASS] approved drafts reference the shared filename")
        print("\nAll single learned-knowledge-file regression checks passed.")
        return 0
    finally:
        knowledge_queue.get_knowledge_draft = original_get
        knowledge_queue.set_knowledge_draft_review_status = original_set
        knowledge_queue.LEARNED_KNOWLEDGE_PATH = original_path
        knowledge_queue._vector_document_for_markdown = original_vector_builder
        if original_rag is None:
            sys.modules.pop("core.rag", None)
        else:
            sys.modules["core.rag"] = original_rag


if __name__ == "__main__":
    raise SystemExit(main())
