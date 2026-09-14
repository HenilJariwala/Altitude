#!/usr/bin/env python3
"""Consolidate legacy learned_*.md files into knowledge_base/learned_support.md.

By default this script performs a dry run. Use --apply to write the shared file,
move the old per-ticket learned files into data/learned_knowledge_archive, and
update approved Knowledge Queue records to reference learned_support.md.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"

if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from core.analytics_db import database_connection, initialize_database
from core.knowledge_queue import (
    LEARNED_KNOWLEDGE_FILENAME,
    LEARNED_KNOWLEDGE_HEADER,
    LEARNED_KNOWLEDGE_PATH,
)

KNOWLEDGE_DIRECTORY = PROJECT_ROOT / "knowledge_base"
ARCHIVE_ROOT = PROJECT_ROOT / "data" / "learned_knowledge_archive"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Combine legacy per-ticket learned Markdown files into one shared file."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the consolidation. Without this flag, only show what would change.",
    )
    return parser.parse_args()


def strip_frontmatter(text: str) -> str:
    cleaned = text.lstrip()
    if not cleaned.startswith("---"):
        return cleaned.strip()

    match = re.match(r"\A---\s*\n.*?\n---\s*\n?", cleaned, flags=re.DOTALL)
    if match:
        return cleaned[match.end() :].strip()
    return cleaned.strip()


def topic_sections(text: str) -> list[str]:
    body = strip_frontmatter(text)
    matches = list(re.finditer(r"(?m)^## Topic:\s*.+?\s*$", body))
    if not matches:
        return []

    sections: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        section = body[match.start() : end].strip()
        if section:
            sections.append(section)
    return sections


def section_key(section: str) -> str:
    normalized = re.sub(r"\s+", " ", section).strip().casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_shared_content(sections: list[str]) -> str:
    return f"{LEARNED_KNOWLEDGE_HEADER}\n\n" + "\n\n".join(sections) + "\n"


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    temporary_path.write_text(content, encoding="utf-8")
    temporary_path.replace(path)


def main() -> int:
    args = parse_args()
    legacy_files = [
        path
        for path in sorted(KNOWLEDGE_DIRECTORY.glob("learned_*.md"))
        if path.name != LEARNED_KNOWLEDGE_FILENAME
    ]

    existing_sections: list[str] = []
    if LEARNED_KNOWLEDGE_PATH.exists():
        existing_sections = topic_sections(
            LEARNED_KNOWLEDGE_PATH.read_text(encoding="utf-8")
        )

    combined_sections = list(existing_sections)
    seen = {section_key(section) for section in combined_sections}
    imported_files = 0
    imported_sections = 0

    for path in legacy_files:
        sections = topic_sections(path.read_text(encoding="utf-8"))
        if not sections:
            print(f"Skipping {path.name}: no ## Topic section found")
            continue

        imported_files += 1
        for section in sections:
            key = section_key(section)
            if key in seen:
                continue
            seen.add(key)
            combined_sections.append(section)
            imported_sections += 1

    print(f"Shared file: {LEARNED_KNOWLEDGE_PATH}")
    print(f"Existing shared topics: {len(existing_sections)}")
    print(f"Legacy learned files found: {len(legacy_files)}")
    print(f"Legacy files with usable topics: {imported_files}")
    print(f"New unique topics to append: {imported_sections}")
    print(f"Final shared topic count: {len(combined_sections)}")

    if not args.apply:
        print("\nDry run only. Re-run with --apply to make these changes.")
        return 0

    if not combined_sections:
        print("No learned topics were found. Nothing changed.")
        return 0

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_directory = ARCHIVE_ROOT / timestamp
    archive_directory.mkdir(parents=True, exist_ok=True)

    if LEARNED_KNOWLEDGE_PATH.exists():
        shutil.copy2(
            LEARNED_KNOWLEDGE_PATH,
            archive_directory / f"before_{LEARNED_KNOWLEDGE_FILENAME}",
        )

    write_atomic(
        LEARNED_KNOWLEDGE_PATH,
        build_shared_content(combined_sections),
    )

    moved = 0
    for path in legacy_files:
        if not path.exists():
            continue
        shutil.move(str(path), str(archive_directory / path.name))
        moved += 1

    initialize_database()
    with database_connection() as connection:
        connection.execute(
            """
            UPDATE knowledge_drafts
            SET published_filename = ?
            WHERE review_status = 'Approved'
              AND published_filename LIKE 'learned_%'
              AND published_filename <> ?
            """,
            (LEARNED_KNOWLEDGE_FILENAME, LEARNED_KNOWLEDGE_FILENAME),
        )

    print("\nConsolidation complete.")
    print(f"Live learned file: {LEARNED_KNOWLEDGE_PATH}")
    print(f"Legacy files moved: {moved}")
    print(f"Backup/archive: {archive_directory}")
    print("\nRebuild the knowledge index next:")
    print("PYTHONPATH=app python scripts/ingest_knowledge.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
