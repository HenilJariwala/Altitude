from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import shutil
import socket
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from core.analytics_db import (
    PROJECT_ROOT,
    get_database_health,
    get_database_path,
    initialize_database,
)
from core.time_utils import get_local_timezone, local_now


PROCESS_STARTED_AT = datetime.now(timezone.utc)
PROCESS_STARTED_MONOTONIC = time.monotonic()

HEALTHY = "healthy"
WARNING = "warning"
UNAVAILABLE = "unavailable"
NOT_CONFIGURED = "not_configured"

STATUS_LABELS = {
    HEALTHY: "Healthy",
    WARNING: "Warning",
    UNAVAILABLE: "Unavailable",
    NOT_CONFIGURED: "Not configured",
}


def _elapsed_ms(started_at: float) -> int:
    """Return elapsed milliseconds for one health check."""
    return max(0, round((time.perf_counter() - started_at) * 1000))


def _format_bytes(value: int | float | None) -> str:
    """Return a compact human-readable byte value."""
    if value is None:
        return "Not available"

    size = float(value)
    units = ("B", "KB", "MB", "GB", "TB")

    for unit in units:
        if abs(size) < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size):,} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024

    return f"{size:.1f} TB"


def _format_duration(seconds: float) -> str:
    """Return a compact uptime string."""
    total_seconds = max(0, int(seconds))
    days, remainder = divmod(total_seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, seconds = divmod(remainder, 60)

    parts: list[str] = []

    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")

    return " ".join(parts)


def _safe_relative_path(path: Path) -> str:
    """Return a project-relative path without exposing the full host path."""
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except (OSError, ValueError):
        return path.name


def _safe_url(value: str) -> str:
    """Return only the URL scheme and host for administrator display."""
    try:
        parsed = urlparse(value)
    except ValueError:
        return "Configured endpoint"

    if not parsed.scheme or not parsed.netloc:
        return "Configured endpoint"

    return f"{parsed.scheme}://{parsed.netloc}"


def _validate_http_endpoint(url: str) -> None:
    """Reject unsafe URL schemes and embedded credentials."""
    try:
        parsed = urlparse(url)
        _ = parsed.port
    except ValueError as error:
        raise ValueError("The configured endpoint is not a valid URL") from error

    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
        raise ValueError(
            "The configured endpoint must be a complete http:// or https:// URL"
        )

    if parsed.username is not None or parsed.password is not None:
        raise ValueError("The configured endpoint must not include URL credentials")


def _first_environment_value(*names: str) -> str:
    """Return the first non-empty environment value from a list of names."""
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _environment_boolean(
    *names: str,
    default: bool,
) -> bool:
    """Return a boolean environment setting with a safe default."""
    raw_value = _first_environment_value(*names)

    if not raw_value:
        return default

    normalized = raw_value.strip().lower()

    if normalized in {"1", "true", "yes", "on", "enabled"}:
        return True

    if normalized in {"0", "false", "no", "off", "disabled"}:
        return False

    return default


def _tls_verification_enabled(
    *,
    verify_names: tuple[str, ...],
    allow_self_signed_names: tuple[str, ...],
) -> bool:
    """Resolve whether TLS certificate verification should be enabled."""
    explicit_verify = _first_environment_value(*verify_names)
    if explicit_verify:
        return _environment_boolean(*verify_names, default=True)

    allow_self_signed = _environment_boolean(
        *allow_self_signed_names,
        default=False,
    )
    return not allow_self_signed


def _is_certificate_verification_error(error: BaseException) -> bool:
    """Return whether an exception represents TLS certificate rejection."""
    if isinstance(error, ssl.SSLCertVerificationError):
        return True

    reason = getattr(error, "reason", None)
    if isinstance(reason, ssl.SSLCertVerificationError):
        return True

    text = str(error).upper()
    return (
        "CERTIFICATE_VERIFY_FAILED" in text
        or "SELF-SIGNED CERTIFICATE" in text
    )


def _urlopen_context(
    url: str,
    *,
    verify_ssl: bool,
) -> ssl.SSLContext | None:
    """Return an SSL context only when HTTPS needs custom handling."""
    if not url.lower().startswith("https://"):
        return None

    if verify_ssl:
        return ssl.create_default_context()

    # This context is intentionally scoped to one optional internal-service
    # health probe. It never changes global TLS behavior for the application.
    return ssl._create_unverified_context()  # noqa: SLF001


def _check_result(
    *,
    key: str,
    name: str,
    status: str,
    message: str,
    metric: str = "—",
    details: list[tuple[str, str]] | None = None,
    recommendation: str | None = None,
    required: bool = False,
) -> dict[str, Any]:
    """Build one normalized health-check result."""
    return {
        "key": key,
        "name": name,
        "status": status,
        "status_label": STATUS_LABELS.get(status, status.title()),
        "message": message,
        "metric": metric,
        "details": details or [],
        "recommendation": recommendation,
        "required": required,
    }


def check_sqlite() -> dict[str, Any]:
    """Check SQLite connectivity, integrity, row counts, and file size."""
    started_at = time.perf_counter()

    try:
        initialize_database()
        health = get_database_health()
        database_path = get_database_path()
        response_ms = _elapsed_ms(started_at)
        quick_check = str(health.get("quick_check", "unknown"))
        foreign_key_violations = int(
            health.get("foreign_key_violations", 0)
        )

        if quick_check != "ok" or foreign_key_violations:
            status = WARNING
            message = "Database checks completed with items that need attention."
            recommendation = (
                "Back up the database, run SQLite integrity checks, and review "
                "foreign-key violations before making schema changes."
            )
        else:
            status = HEALTHY
            message = "Database integrity and foreign-key checks passed."
            recommendation = None

        details = [
            ("Response time", f"{response_ms} ms"),
            ("Database", _safe_relative_path(database_path)),
            ("Schema version", str(health.get("schema_version", "Unknown"))),
            ("Journal mode", str(health.get("journal_mode", "Unknown"))),
            ("Conversations", f"{int(health.get('conversation_count', 0)):,}"),
            ("Messages", f"{int(health.get('message_count', 0)):,}"),
            ("Feedback", f"{int(health.get('feedback_count', 0)):,}"),
            ("Announcements", f"{int(health.get('announcement_count', 0)):,}"),
            ("Tickets", f"{int(health.get('ticket_count', 0)):,}"),
            (
                "Database size",
                _format_bytes(health.get("database_size_bytes")),
            ),
            (
                "WAL size",
                _format_bytes(health.get("wal_size_bytes")),
            ),
        ]

        return _check_result(
            key="sqlite",
            name="SQLite Analytics",
            status=status,
            message=message,
            metric=f"{response_ms} ms",
            details=details,
            recommendation=recommendation,
            required=True,
        )
    except Exception as error:
        return _check_result(
            key="sqlite",
            name="SQLite Analytics",
            status=UNAVAILABLE,
            message="The analytics database could not be opened or checked.",
            metric=f"{_elapsed_ms(started_at)} ms",
            details=[
                ("Database", _safe_relative_path(get_database_path())),
                ("Safe error", f"{type(error).__name__}: {error}"),
            ],
            recommendation=(
                "Confirm that the data directory is writable and restore the "
                "latest database backup if the file is damaged."
            ),
            required=True,
        )


def check_application_runtime() -> dict[str, Any]:
    """Check Python, Streamlit, host, timezone, and process uptime."""
    try:
        streamlit_version = importlib.metadata.version("streamlit")
    except importlib.metadata.PackageNotFoundError:
        streamlit_version = "Not installed"

    current_local_time = local_now()
    uptime_seconds = time.monotonic() - PROCESS_STARTED_MONOTONIC
    hostname = socket.gethostname() or "Unknown host"

    details = [
        ("Python", platform.python_version()),
        ("Streamlit", streamlit_version),
        ("Operating system", f"{platform.system()} {platform.release()}"),
        ("Architecture", platform.machine() or "Unknown"),
        ("Host", hostname),
        ("Local timezone", str(current_local_time.tzinfo)),
        ("Server time", current_local_time.strftime("%b %d, %Y %I:%M:%S %p")),
        ("Process started", PROCESS_STARTED_AT.isoformat(timespec="seconds")),
        ("Application uptime", _format_duration(uptime_seconds)),
    ]

    return _check_result(
        key="runtime",
        name="Altitude Application",
        status=HEALTHY,
        message="The administrator application process is running.",
        metric=_format_duration(uptime_seconds),
        details=details,
        required=True,
    )


def check_disk_storage() -> dict[str, Any]:
    """Check free space on the filesystem that stores the project."""
    try:
        usage = shutil.disk_usage(PROJECT_ROOT)
        used_percent = (
            round(((usage.total - usage.free) / usage.total) * 100, 1)
            if usage.total
            else 0.0
        )

        if used_percent >= 95:
            status = UNAVAILABLE
            message = "Storage is critically full."
            recommendation = (
                "Free disk space immediately before database or index writes fail."
            )
        elif used_percent >= 85:
            status = WARNING
            message = "Storage usage is high."
            recommendation = (
                "Archive old backups, logs, and unused model files."
            )
        else:
            status = HEALTHY
            message = "Storage capacity is within the safe operating range."
            recommendation = None

        return _check_result(
            key="disk",
            name="Disk and Storage",
            status=status,
            message=message,
            metric=f"{used_percent:.1f}% used",
            details=[
                ("Project location", _safe_relative_path(PROJECT_ROOT)),
                ("Total", _format_bytes(usage.total)),
                ("Used", _format_bytes(usage.total - usage.free)),
                ("Available", _format_bytes(usage.free)),
                ("Usage", f"{used_percent:.1f}%"),
            ],
            recommendation=recommendation,
            required=True,
        )
    except OSError as error:
        return _check_result(
            key="disk",
            name="Disk and Storage",
            status=UNAVAILABLE,
            message="Storage usage could not be read.",
            details=[("Safe error", f"{type(error).__name__}: {error}")],
            recommendation="Confirm that the project filesystem is mounted.",
            required=True,
        )


def _read_json_url(
    url: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    verify_ssl: bool = True,
) -> tuple[Any, int]:
    """Read one JSON endpoint and return parsed data plus response time."""
    _validate_http_endpoint(url)
    started_at = time.perf_counter()
    request = urllib.request.Request(
        url,
        headers=headers or {"Accept": "application/json"},
        method="GET",
    )
    context = _urlopen_context(url, verify_ssl=verify_ssl)

    with urllib.request.urlopen(
        request,
        timeout=timeout,
        context=context,
    ) as response:
        raw_body = response.read()
        elapsed_ms = _elapsed_ms(started_at)

    return json.loads(raw_body.decode("utf-8")), elapsed_ms


def _probe_url(
    url: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    verify_ssl: bool = True,
) -> tuple[int, int]:
    """Probe one HTTP endpoint without requiring a JSON response body."""
    _validate_http_endpoint(url)
    started_at = time.perf_counter()
    request = urllib.request.Request(
        url,
        headers=headers or {"Accept": "*/*"},
        method="GET",
    )
    context = _urlopen_context(url, verify_ssl=verify_ssl)

    with urllib.request.urlopen(
        request,
        timeout=timeout,
        context=context,
    ) as response:
        response.read(1)
        return int(response.status), _elapsed_ms(started_at)


def check_ollama_server() -> tuple[dict[str, Any], list[str]]:
    """Check the Ollama API and return the installed model names."""
    base_url = _first_environment_value(
        "OLLAMA_BASE_URL",
        "OLLAMA_HOST",
    ) or "http://127.0.0.1:11434"
    endpoint = base_url.rstrip("/") + "/api/tags"

    try:
        payload, response_ms = _read_json_url(endpoint, timeout=3.0)
        model_rows = payload.get("models", []) if isinstance(payload, dict) else []
        model_names = sorted(
            {
                str(row.get("name", "")).strip()
                for row in model_rows
                if isinstance(row, dict) and str(row.get("name", "")).strip()
            }
        )

        result = _check_result(
            key="ollama",
            name="Ollama Server",
            status=HEALTHY,
            message="The local Ollama API responded successfully.",
            metric=f"{response_ms} ms",
            details=[
                ("Endpoint", _safe_url(base_url)),
                ("Response time", f"{response_ms} ms"),
                ("Installed models", f"{len(model_names):,}"),
                (
                    "Model list",
                    ", ".join(model_names[:8]) if model_names else "No models found",
                ),
            ],
            required=True,
        )
        return result, model_names
    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as error:
        result = _check_result(
            key="ollama",
            name="Ollama Server",
            status=UNAVAILABLE,
            message="The local Ollama API did not respond.",
            metric="Offline",
            details=[
                ("Endpoint", _safe_url(base_url)),
                ("Safe error", f"{type(error).__name__}: {error}"),
            ],
            recommendation=(
                "Start Ollama, confirm the configured host and port, then run "
                "the health checks again."
            ),
            required=True,
        )
        return result, []


def _configured_model(*names: str) -> str:
    """Return one configured model name without inventing a default."""
    return _first_environment_value(*names)


def _model_matches(configured_model: str, installed_models: list[str]) -> bool:
    """Return whether an installed Ollama model matches the configured value."""
    target = configured_model.strip()

    if not target:
        return False

    if target in installed_models:
        return True

    target_without_tag = target.split(":", 1)[0]
    return any(
        installed.split(":", 1)[0] == target_without_tag
        for installed in installed_models
    )


def check_model(
    *,
    key: str,
    name: str,
    configured_model: str,
    installed_models: list[str],
    ollama_status: str,
) -> dict[str, Any]:
    """Check whether one configured Ollama model is installed."""
    if not configured_model:
        return _check_result(
            key=key,
            name=name,
            status=NOT_CONFIGURED,
            message="No model name is configured for this role.",
            details=[
                (
                    "Configuration",
                    "Add the model name to the project environment settings.",
                )
            ],
            recommendation=(
                "Configure the model environment variable before production use."
            ),
        )

    if ollama_status != HEALTHY:
        return _check_result(
            key=key,
            name=name,
            status=UNAVAILABLE,
            message="The model could not be verified because Ollama is offline.",
            metric=configured_model,
            details=[("Configured model", configured_model)],
            recommendation="Restore Ollama, then run the health checks again.",
            required=True,
        )

    installed = _model_matches(configured_model, installed_models)

    return _check_result(
        key=key,
        name=name,
        status=HEALTHY if installed else WARNING,
        message=(
            "The configured model is installed."
            if installed
            else "The configured model was not found in Ollama."
        ),
        metric=configured_model,
        details=[
            ("Configured model", configured_model),
            ("Installed", "Yes" if installed else "No"),
        ],
        recommendation=(
            None
            if installed
            else f"Run `ollama pull {configured_model}` on the Altitude host."
        ),
        required=True,
    )


def _candidate_path(
    *,
    environment_names: tuple[str, ...],
    fallbacks: tuple[Path, ...],
) -> tuple[Path | None, bool]:
    """Resolve a configured or existing fallback path."""
    configured = _first_environment_value(*environment_names)
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path.resolve(), True

    for fallback in fallbacks:
        if fallback.exists():
            return fallback.resolve(), False

    return None, False


def check_chromadb() -> dict[str, Any]:
    """Check the persistent ChromaDB directory and indexed collections."""
    chroma_path, explicitly_configured = _candidate_path(
        environment_names=(
            "CHROMA_PATH",
            "CHROMA_DB_PATH",
            "CHROMA_PERSIST_DIRECTORY",
            "CHROMA_PERSIST_DIR",
        ),
        fallbacks=(
            PROJECT_ROOT / "data" / "chroma_active",
            PROJECT_ROOT / "data" / "chroma",
            PROJECT_ROOT / "data" / "chromadb",
            PROJECT_ROOT / "chroma_db",
        ),
    )

    configured_collection = _first_environment_value(
        "CHROMA_COLLECTION_NAME",
        "CHROMA_COLLECTION",
        "COLLECTION_NAME",
    )

    if chroma_path is None:
        return _check_result(
            key="chromadb",
            name="ChromaDB Knowledge Index",
            status=NOT_CONFIGURED,
            message="No persistent ChromaDB directory was found.",
            details=[
                (
                    "Expected location",
                    "data/chroma, data/chroma_active, or configured path",
                )
            ],
            recommendation=(
                "Configure the Chroma directory or run the knowledge-ingestion "
                "process to create the index."
            ),
        )

    if not chroma_path.exists():
        return _check_result(
            key="chromadb",
            name="ChromaDB Knowledge Index",
            status=UNAVAILABLE if explicitly_configured else NOT_CONFIGURED,
            message="The configured ChromaDB directory does not exist.",
            details=[("Directory", _safe_relative_path(chroma_path))],
            recommendation="Create or restore the knowledge index.",
            required=explicitly_configured,
        )

    started_at = time.perf_counter()

    try:
        import chromadb  # Imported lazily so the health page still loads.

        client = chromadb.PersistentClient(path=str(chroma_path))
        listed_collections = client.list_collections()
        collection_names: list[str] = []

        for item in listed_collections:
            if isinstance(item, str):
                collection_names.append(item)
            else:
                name = str(getattr(item, "name", "")).strip()
                if name:
                    collection_names.append(name)

        total_chunks = 0
        target_count: int | None = None

        for collection_name in collection_names:
            collection = client.get_collection(name=collection_name)
            collection_count = int(collection.count())
            total_chunks += collection_count

            if configured_collection and collection_name == configured_collection:
                target_count = collection_count

        response_ms = _elapsed_ms(started_at)

        if configured_collection and configured_collection not in collection_names:
            status = WARNING
            message = "ChromaDB loaded, but the configured collection is missing."
            recommendation = (
                "Run the knowledge-ingestion script for the configured collection."
            )
        elif total_chunks == 0:
            status = WARNING
            message = "ChromaDB loaded, but no indexed knowledge chunks were found."
            recommendation = "Run the approved-knowledge ingestion process."
        else:
            status = HEALTHY
            message = "The persistent knowledge index loaded successfully."
            recommendation = None

        latest_modified = datetime.fromtimestamp(
            chroma_path.stat().st_mtime,
            tz=timezone.utc,
        ).astimezone(get_local_timezone())

        details = [
            ("Directory", _safe_relative_path(chroma_path)),
            ("Response time", f"{response_ms} ms"),
            ("Collections", f"{len(collection_names):,}"),
            ("Indexed chunks", f"{total_chunks:,}"),
            (
                "Configured collection",
                configured_collection or "Not specified",
            ),
            (
                "Configured collection chunks",
                str(target_count) if target_count is not None else "Not available",
            ),
            (
                "Last directory update",
                latest_modified.strftime("%b %d, %Y %I:%M %p"),
            ),
        ]

        return _check_result(
            key="chromadb",
            name="ChromaDB Knowledge Index",
            status=status,
            message=message,
            metric=f"{total_chunks:,} chunks",
            details=details,
            recommendation=recommendation,
            required=True,
        )
    except ImportError:
        return _check_result(
            key="chromadb",
            name="ChromaDB Knowledge Index",
            status=UNAVAILABLE,
            message="The ChromaDB Python package is not installed.",
            details=[("Directory", _safe_relative_path(chroma_path))],
            recommendation="Install the project's ChromaDB dependency.",
            required=True,
        )
    except Exception as error:
        return _check_result(
            key="chromadb",
            name="ChromaDB Knowledge Index",
            status=UNAVAILABLE,
            message="The persistent knowledge index could not be opened.",
            metric=f"{_elapsed_ms(started_at)} ms",
            details=[
                ("Directory", _safe_relative_path(chroma_path)),
                ("Safe error", f"{type(error).__name__}: {error}"),
            ],
            recommendation=(
                "Back up the current index, rebuild it from approved Markdown "
                "files, and test retrieval before replacing the active index."
            ),
            required=True,
        )


def check_knowledge_files() -> dict[str, Any]:
    """Check approved Markdown knowledge files and their latest update."""
    knowledge_path, explicitly_configured = _candidate_path(
        environment_names=(
            "KNOWLEDGE_BASE_PATH",
            "KNOWLEDGE_DIR",
            "KNOWLEDGE_BASE_DIR",
        ),
        fallbacks=(
            PROJECT_ROOT / "knowledge_base" / "approved",
            PROJECT_ROOT / "knowledge_base",
            PROJECT_ROOT / "knowledge",
        ),
    )

    if knowledge_path is None:
        return _check_result(
            key="knowledge_files",
            name="Knowledge Files",
            status=NOT_CONFIGURED,
            message="No knowledge directory was found.",
            recommendation="Create the approved knowledge directory.",
        )

    if not knowledge_path.exists():
        return _check_result(
            key="knowledge_files",
            name="Knowledge Files",
            status=UNAVAILABLE if explicitly_configured else NOT_CONFIGURED,
            message="The configured knowledge directory does not exist.",
            details=[("Directory", _safe_relative_path(knowledge_path))],
            recommendation="Create or restore the knowledge directory.",
            required=explicitly_configured,
        )

    try:
        markdown_files = sorted(
            (
                path
                for path in knowledge_path.rglob("*.md")
                if path.is_file()
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        empty_files = [
            path
            for path in markdown_files
            if path.stat().st_size == 0
        ]
        total_size = sum(path.stat().st_size for path in markdown_files)

        if not markdown_files:
            status = WARNING
            message = "The knowledge directory contains no Markdown files."
            recommendation = "Add reviewed and approved support documentation."
            latest_label = "No files"
        elif empty_files:
            status = WARNING
            message = "Knowledge files were found, but some are empty."
            recommendation = "Review or remove empty Markdown files."
            latest_label = markdown_files[0].name
        else:
            status = HEALTHY
            message = "Reviewed Markdown knowledge files are available."
            recommendation = None
            latest_label = markdown_files[0].name

        latest_modified = (
            datetime.fromtimestamp(
                markdown_files[0].stat().st_mtime,
                tz=timezone.utc,
            ).astimezone(get_local_timezone()).strftime("%b %d, %Y %I:%M %p")
            if markdown_files
            else "Not available"
        )

        return _check_result(
            key="knowledge_files",
            name="Knowledge Files",
            status=status,
            message=message,
            metric=f"{len(markdown_files):,} files",
            details=[
                ("Directory", _safe_relative_path(knowledge_path)),
                ("Markdown files", f"{len(markdown_files):,}"),
                ("Empty files", f"{len(empty_files):,}"),
                ("Total size", _format_bytes(total_size)),
                ("Latest file", latest_label),
                ("Latest update", latest_modified),
            ],
            recommendation=recommendation,
            required=True,
        )
    except OSError as error:
        return _check_result(
            key="knowledge_files",
            name="Knowledge Files",
            status=UNAVAILABLE,
            message="Knowledge files could not be inspected.",
            details=[
                ("Directory", _safe_relative_path(knowledge_path)),
                ("Safe error", f"{type(error).__name__}: {error}"),
            ],
            recommendation="Confirm file permissions on the knowledge directory.",
            required=True,
        )


def _external_service_check(
    *,
    key: str,
    name: str,
    url_names: tuple[str, ...],
    token_names: tuple[str, ...] = (),
    verify_ssl_names: tuple[str, ...] = (),
    allow_self_signed_names: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Check one optional HTTP API without exposing credentials."""
    configured_url = _first_environment_value(*url_names)

    if not configured_url:
        return _check_result(
            key=key,
            name=name,
            status=NOT_CONFIGURED,
            message="This integration has not been configured.",
            details=[("Authentication", "Not configured")],
        )

    token = _first_environment_value(*token_names)
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    verify_ssl = _tls_verification_enabled(
        verify_names=verify_ssl_names,
        allow_self_signed_names=allow_self_signed_names,
    )
    is_https = configured_url.lower().startswith("https://")

    try:
        status_code, response_ms = _probe_url(
            configured_url,
            timeout=4.0,
            headers=headers,
            verify_ssl=verify_ssl,
        )
        tls_verification_disabled = is_https and not verify_ssl
        return _check_result(
            key=key,
            name=name,
            status=WARNING if tls_verification_disabled else HEALTHY,
            message=(
                "The endpoint responded, but TLS certificate verification is disabled."
                if tls_verification_disabled
                else "The configured service endpoint responded successfully."
            ),
            metric=f"{response_ms} ms",
            details=[
                ("Endpoint", _safe_url(configured_url)),
                ("Response time", f"{response_ms} ms"),
                ("HTTP status", str(status_code)),
                (
                    "Authentication",
                    "Configured" if token else "Not configured",
                ),
                (
                    "TLS verification",
                    "Disabled" if tls_verification_disabled else "Enabled",
                ),
            ],
            recommendation=(
                "Install a trusted certificate or the internal certificate authority on the Altitude host."
                if tls_verification_disabled
                else None
            ),
        )
    except urllib.error.HTTPError as error:
        status = WARNING if error.code in {401, 403} else UNAVAILABLE
        message = (
            "The endpoint is reachable, but authentication was rejected."
            if error.code in {401, 403}
            else "The configured endpoint returned an HTTP error."
        )
        return _check_result(
            key=key,
            name=name,
            status=status,
            message=message,
            metric=f"HTTP {error.code}",
            details=[
                ("Endpoint", _safe_url(configured_url)),
                ("HTTP status", str(error.code)),
                (
                    "Authentication",
                    "Configured" if token else "Not configured",
                ),
            ],
            recommendation=(
                "Verify the configured service credential."
                if error.code in {401, 403}
                else "Confirm the service health endpoint and server status."
            ),
        )
    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as error:
        if verify_ssl and is_https and _is_certificate_verification_error(error):
            setting_name = (
                verify_ssl_names[0]
                if verify_ssl_names
                else "SERVICE_VERIFY_SSL"
            )

            if token:
                return _check_result(
                    key=key,
                    name=name,
                    status=WARNING,
                    message=(
                        "The HTTPS certificate was rejected. Altitude did not "
                        "retry without verification because a service credential "
                        "is configured."
                    ),
                    metric="TLS rejected",
                    details=[
                        ("Endpoint", _safe_url(configured_url)),
                        ("TLS verification", "Certificate rejected"),
                        ("Authentication", "Configured and protected"),
                    ],
                    recommendation=(
                        "Install the service certificate or internal certificate "
                        "authority on the Altitude host. Only for an approved "
                        "internal self-signed service, set "
                        f"{setting_name}=false in .env and restart Altitude."
                    ),
                )

            try:
                status_code, response_ms = _probe_url(
                    configured_url,
                    timeout=4.0,
                    headers={"Accept": "*/*"},
                    verify_ssl=False,
                )
            except (
                urllib.error.HTTPError,
                urllib.error.URLError,
                TimeoutError,
                OSError,
                ValueError,
            ):
                pass
            else:
                return _check_result(
                    key=key,
                    name=name,
                    status=WARNING,
                    message=(
                        "The endpoint is reachable, but its HTTPS certificate "
                        "is self-signed or not trusted by this host."
                    ),
                    metric=f"{response_ms} ms",
                    details=[
                        ("Endpoint", _safe_url(configured_url)),
                        ("Response time", f"{response_ms} ms"),
                        ("HTTP status", str(status_code)),
                        ("TLS verification", "Certificate rejected"),
                        ("Authentication", "Not configured"),
                    ],
                    recommendation=(
                        "Preferred: install the service certificate or internal "
                        "certificate authority on the Altitude host. For an "
                        "approved internal self-signed service only, set "
                        f"{setting_name}=false in .env and restart Altitude."
                    ),
                )

        return _check_result(
            key=key,
            name=name,
            status=UNAVAILABLE,
            message="The configured service endpoint did not respond.",
            details=[
                ("Endpoint", _safe_url(configured_url)),
                ("Safe error", f"{type(error).__name__}: {error}"),
            ],
            recommendation="Confirm the endpoint, network route, and service status.",
        )


def _overall_status(groups: list[dict[str, Any]]) -> tuple[str, str, str]:
    """Return status key, headline, and summary for the complete report."""
    checks = [
        check
        for group in groups
        for check in group.get("checks", [])
    ]

    required_unavailable = any(
        check.get("required")
        and check.get("status") == UNAVAILABLE
        for check in checks
    )
    has_attention = any(
        check.get("status") in {WARNING, UNAVAILABLE}
        for check in checks
    )

    if required_unavailable:
        return (
            "critical",
            "Critical service unavailable",
            "One or more required Altitude services are unavailable.",
        )

    if has_attention:
        return (
            WARNING,
            "Some services need attention",
            "Altitude is running, but one or more checks require review.",
        )

    return (
        HEALTHY,
        "All systems operational",
        "All configured Altitude services passed their latest checks.",
    )


def run_system_health_checks() -> dict[str, Any]:
    """Run all administrator health checks and return a safe report."""
    checked_at = datetime.now(timezone.utc)
    sqlite_check = check_sqlite()
    runtime_check = check_application_runtime()
    disk_check = check_disk_storage()
    ollama_check, installed_models = check_ollama_server()

    chat_model = _configured_model(
        "OLLAMA_CHAT_MODEL",
        "CHAT_MODEL",
        "LLM_MODEL",
        "OLLAMA_MODEL",
    )
    embedding_model = _configured_model(
        "OLLAMA_EMBEDDING_MODEL",
        "EMBEDDING_MODEL",
        "EMBED_MODEL",
    )

    groups = [
        {
            "key": "core",
            "label": "Core application",
            "description": "Application runtime, analytics storage, and disk capacity.",
            "checks": [
                runtime_check,
                sqlite_check,
                disk_check,
            ],
        },
        {
            "key": "ai",
            "label": "AI services",
            "description": "Local inference server and configured model availability.",
            "checks": [
                ollama_check,
                check_model(
                    key="chat_model",
                    name="Chat Model",
                    configured_model=chat_model,
                    installed_models=installed_models,
                    ollama_status=str(ollama_check["status"]),
                ),
                check_model(
                    key="embedding_model",
                    name="Embedding Model",
                    configured_model=embedding_model,
                    installed_models=installed_models,
                    ollama_status=str(ollama_check["status"]),
                ),
            ],
        },
        {
            "key": "knowledge",
            "label": "Knowledge system",
            "description": "Approved documentation and the active retrieval index.",
            "checks": [
                check_chromadb(),
                check_knowledge_files(),
            ],
        },
        {
            "key": "external",
            "label": "Connected services",
            "description": "Optional school systems connected to Altitude.",
            "checks": [
                _external_service_check(
                    key="inventory_api",
                    name="Inventory API",
                    url_names=(
                        "INVENTORY_HEALTH_URL",
                        "INVENTORY_API_URL",
                        "INVENTORY_BASE_URL",
                    ),
                    token_names=(
                        "INVENTORY_API_TOKEN",
                        "INVENTORY_TOKEN",
                    ),
                    verify_ssl_names=(
                        "INVENTORY_VERIFY_SSL",
                        "INVENTORY_TLS_VERIFY",
                    ),
                    allow_self_signed_names=(
                        "INVENTORY_ALLOW_SELF_SIGNED",
                    ),
                ),
                _external_service_check(
                    key="ticketing_api",
                    name="Ticketing API",
                    url_names=(
                        "TICKETING_HEALTH_URL",
                        "TICKETING_API_URL",
                        "TICKET_API_URL",
                        "TECHHELP_API_URL",
                    ),
                    token_names=(
                        "TICKETING_API_TOKEN",
                        "TICKET_API_TOKEN",
                        "TECHHELP_API_TOKEN",
                    ),
                    verify_ssl_names=(
                        "TICKETING_VERIFY_SSL",
                        "TICKETING_TLS_VERIFY",
                    ),
                    allow_self_signed_names=(
                        "TICKETING_ALLOW_SELF_SIGNED",
                    ),
                ),
            ],
        },
    ]

    overall_status, overall_label, overall_message = _overall_status(groups)
    counts = {
        status: sum(
            1
            for group in groups
            for check in group["checks"]
            if check["status"] == status
        )
        for status in (HEALTHY, WARNING, UNAVAILABLE, NOT_CONFIGURED)
    }

    return {
        "checked_at": checked_at.isoformat(timespec="seconds"),
        "checked_at_display": checked_at.astimezone(get_local_timezone()).strftime(
            "%b %d, %Y at %I:%M:%S %p"
        ),
        "overall_status": overall_status,
        "overall_label": overall_label,
        "overall_message": overall_message,
        "counts": counts,
        "groups": groups,
    }
