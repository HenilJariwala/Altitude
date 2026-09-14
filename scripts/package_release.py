from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "dist" / "Altitude-release.zip"
EXCLUDED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".venv",
        ".vscode",
        ".ruff_cache",
        ".pytest_cache",
        ".mypy_cache",
        "__pycache__",
        "__MACOSX",
        "dist",
        "logs",
        "test_reports",
    }
)
EXCLUDED_FILE_NAMES = frozenset(
    {
        ".env",
        ".DS_Store",
        ".admin_session_secret",
    }
)


def _should_exclude(path: Path) -> bool:
    relative_path = path.relative_to(PROJECT_ROOT)
    if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative_path.parts):
        return True

    if path.name in EXCLUDED_FILE_NAMES or path.name.startswith(".env"):
        if path.name != ".env.example":
            return True

    if (
        path.name == "secrets.toml"
        and ".streamlit" in relative_path.parts
    ):
        return True

    if path.suffix.lower() in {
        ".pyc",
        ".pyo",
        ".log",
        ".key",
        ".pem",
        ".p12",
        ".pfx",
    }:
        return True

    if relative_path.parts and relative_path.parts[0] == "data":
        name = path.name.lower()
        if name.endswith(
            (
                ".db",
                ".db-wal",
                ".db-shm",
                ".db-journal",
                ".sqlite",
                ".sqlite-wal",
                ".sqlite-shm",
                ".sqlite-journal",
                ".sqlite3",
                ".sqlite3-wal",
                ".sqlite3-shm",
                ".sqlite3-journal",
            )
        ):
            return True

    return False


def build_release_archive(output_path: Path) -> tuple[Path, int]:
    """Create a deployment ZIP without credentials, sessions, or local data."""
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    included_files = 0
    with zipfile.ZipFile(
        output_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(PROJECT_ROOT.rglob("*")):
            if not path.is_file() or _should_exclude(path):
                continue
            if path.resolve() == output_path:
                continue

            archive_name = Path("Altitude") / path.relative_to(PROJECT_ROOT)
            archive.write(path, archive_name.as_posix())
            included_files += 1

    return output_path, included_files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a clean Altitude deployment ZIP.",
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output ZIP path (default: dist/Altitude-release.zip)",
    )
    arguments = parser.parse_args()

    output_path, included_files = build_release_archive(arguments.output)
    print(f"Created {output_path} with {included_files} files.")


if __name__ == "__main__":
    main()
