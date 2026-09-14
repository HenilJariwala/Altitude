from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADMIN_FILE = PROJECT_ROOT / "app" / "pages" / "admin.py"


def function_source(tree: ast.Module, name: str, source: str) -> str:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(source, node) or ""
    raise AssertionError(f"Function {name!r} was not found in {ADMIN_FILE}")


def main() -> None:
    source = ADMIN_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source)

    render_knowledge = function_source(tree, "_render_knowledge_section", source)
    finish_action = function_source(tree, "_finish_knowledge_review_action", source)
    scroll_helper = function_source(tree, "_scroll_admin_content_to_top", source)

    checks = [
        (
            "Knowledge Queue does not live-sync just by opening",
            "_auto_sync_ticket_statuses()" not in render_knowledge,
        ),
        (
            "Manual Sync resolved tickets control remains available",
            "_synchronize_ticket_statuses()" in render_knowledge,
        ),
        (
            "Approve uses clean post-action flow",
            "_finish_knowledge_review_action" in render_knowledge
            and "approved and published" in render_knowledge,
        ),
        (
            "Reject uses clean post-action flow",
            "rejected and kept out of live knowledge" in render_knowledge,
        ),
        (
            "Selected draft is cleared after review",
            'pop("admin_knowledge_selected_draft", None)' in finish_action,
        ),
        (
            "Post-action scroll-to-top flag is set",
            'admin_knowledge_scroll_top' in finish_action,
        ),
        (
            "Admin content container is explicitly scrolled to top",
            ".st-key-admin_content_scroll" in scroll_helper
            and "scrollTo" in scroll_helper,
        ),
    ]

    failures = 0
    for label, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {label}")
        failures += 0 if passed else 1

    if failures:
        raise SystemExit(f"\n{failures} Knowledge Queue admin-flow check(s) failed.")

    print("\nAll Knowledge Queue admin-flow regression checks passed.")


if __name__ == "__main__":
    main()
