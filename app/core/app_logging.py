"""Important-only rotating application logs for Altitude operations."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_PATH = PROJECT_ROOT / "logs" / "altitude-important.log"
LOG_FORMAT = "%(asctime)sZ %(levelname)s %(name)s: %(message)s"
_HANDLERS_BY_PATH: dict[str, RotatingFileHandler] = {}


def get_important_log_path() -> Path:
    """Return the configured important-event log path."""
    configured = os.getenv("ALTITUDE_IMPORTANT_LOG_PATH", "").strip()
    if not configured:
        return DEFAULT_LOG_PATH
    path = Path(configured).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def get_logger(name: str) -> logging.Logger:
    """Return a logger that persists warnings and errors with rotation."""
    logger = logging.getLogger(f"altitude.{name}")
    logger.setLevel(logging.WARNING)
    logger.propagate = False

    if logger.handlers:
        return logger

    try:
        log_path = get_important_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        path_key = str(log_path)
        handler = _HANDLERS_BY_PATH.get(path_key)
        if handler is None:
            handler = RotatingFileHandler(
                log_path,
                maxBytes=2_000_000,
                backupCount=5,
                encoding="utf-8",
            )
            handler.setLevel(logging.WARNING)
            formatter = logging.Formatter(LOG_FORMAT)
            formatter.converter = __import__("time").gmtime
            handler.setFormatter(formatter)
            _HANDLERS_BY_PATH[path_key] = handler
        logger.addHandler(handler)
    except OSError:
        # Logging must never prevent the support application from starting.
        logger.addHandler(logging.NullHandler())

    return logger


def release_logger(logger: logging.Logger) -> None:
    """Close a task-scoped logger; intended for isolated test cleanup."""
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        for path_key, registered in list(_HANDLERS_BY_PATH.items()):
            if registered is handler:
                _HANDLERS_BY_PATH.pop(path_key, None)
        handler.close()


def read_important_log_lines(
    *,
    level: str | None = None,
    search: str | None = None,
    limit: int = 500,
) -> list[str]:
    """Return the newest matching warning/error log lines in display order."""
    log_path = get_important_log_path()
    if not log_path.is_file():
        return []

    safe_limit = max(1, min(int(limit), 5_000))
    clean_level = str(level or "").strip().upper()
    clean_search = str(search or "").strip().casefold()

    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    selected: list[str] = []
    for line in reversed(lines):
        if clean_level and f" {clean_level} " not in line:
            continue
        if clean_search and clean_search not in line.casefold():
            continue
        selected.append(line)
        if len(selected) >= safe_limit:
            break

    selected.reverse()
    return selected
