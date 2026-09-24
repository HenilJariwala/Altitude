from __future__ import annotations

import math
import os
import re
from functools import lru_cache
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv

from core.text_matching import contains_any_phrase, normalize_text


load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_positive_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError:
        return default
    if not math.isfinite(value) or value <= 0:
        return default
    return value


def _env_positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


WEB_FALLBACK_ENABLED = _env_bool("WEB_FALLBACK_ENABLED", True)
MICROSOFT_SUPPORT_ENABLED = _env_bool("MICROSOFT_SUPPORT_ENABLED", False)
WEB_SEARCH_REGION = os.getenv("WEB_SEARCH_REGION", "ca-en").strip() or "ca-en"
WEB_SEARCH_TIMEOUT_SECONDS = _env_positive_float(
    "WEB_SEARCH_TIMEOUT_SECONDS",
    4.0,
)
WEB_SEARCH_MAX_RESULTS = _env_positive_int(
    "WEB_SEARCH_MAX_RESULTS",
    2,
)


DEFAULT_TRUSTED_DOMAINS = (
    "support.apple.com",
    "support.google.com",
    "support.zoom.com",
    "helpx.adobe.com",
    "support.mozilla.org",
    "support.hp.com",
    "kyoceradocumentsolutions.com",
)


MICROSOFT_TERMS = (
    "microsoft",
    "microsoft 365",
    "office 365",
    "microsoft office",
    "microsoft word",
    "word app",
    "microsoft excel",
    "microsoft powerpoint",
    "microsoft teams",
    "outlook",
    "onedrive",
    "one drive",
    "sharepoint",
    "windows 10",
    "windows 11",
    "windows pc",
    "windows computer",
    "windows desktop",
    "windows laptop",
    "windows os",
    "microsoft edge",
    "edge browser",
)


SUPPORTED_WEB_PRODUCT_TERMS = (
    "chrome",
    "google chrome",
    "chromebook",
    "chromeos",
    "google",
    "gmail",
    "google drive",
    "google docs",
    "google sheets",
    "google slides",
    "google classroom",
    "google meet",
    "safari",
    "mac",
    "macbook",
    "macos",
    "ipad",
    "iphone",
    "airplay",
    "adobe",
    "acrobat",
    "creative cloud",
    "photoshop",
    "zoom",
    "firefox",
    "mozilla",
    "hp",
    "kyocera",
    "printer",
)


EXPLICIT_VENDOR_ERROR_PATTERNS = (
    re.compile(r"\b(?:NET::)?ERR_[A-Z0-9_]+\b", re.IGNORECASE),
    re.compile(r"\bDNS_PROBE_[A-Z0-9_]+\b", re.IGNORECASE),
    re.compile(r"\bSTATUS_[A-Z0-9_]+\b", re.IGNORECASE),
    re.compile(r"\b0x[0-9a-f]{6,}\b", re.IGNORECASE),
    re.compile(
        r"\berror(?:\s+code)?\s*[:#-]?\s*(?:[a-z]+-?)?\d{2,}\b",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True)
class WebSource:
    title: str
    url: str
    snippet: str
    domain: str


@dataclass(frozen=True)
class WebSearchBundle:
    context: str = ""
    sources: tuple[WebSource, ...] = ()




def is_microsoft_question(question: str) -> bool:
    """Return whether the request is about an unsupported Microsoft product."""

    if contains_any_phrase(question, MICROSOFT_TERMS):
        return True

    normalized = normalize_text(question)
    if normalized in {"word", "excel", "powerpoint", "teams"}:
        return True

    desktop_app_terms = ("word", "excel", "powerpoint", "teams")
    app_context_terms = (
        "app", "application", "document", "workbook", "presentation",
        "open", "install", "launch", "sign in", "login", "error", "crash",
        "create", "edit", "save", "print", "format", "table", "page",
        "file", "formula", "chart", "slide", "sync",
    )
    return (
        contains_any_phrase(question, desktop_app_terms)
        and contains_any_phrase(question, app_context_terms)
    )


def should_prefer_web_support(question: str) -> bool:
    """Prefer official vendor search for exact vendor/browser error codes.

    Deterministic school procedures still run first. This catches errors such
    as ERR_SSL_PROTOCOL_ERROR, ERR_CERT_DATE_INVALID, DNS_PROBE_* and vendor
    numeric error codes before a weak semantic KB match can answer the wrong
    topic.
    """

    if not WEB_FALLBACK_ENABLED:
        return False

    if is_microsoft_question(question) and not MICROSOFT_SUPPORT_ENABLED:
        return False

    has_explicit_error = any(
        pattern.search(question)
        for pattern in EXPLICIT_VENDOR_ERROR_PATTERNS
    )

    if not has_explicit_error:
        return False

    return contains_any_phrase(
        question,
        SUPPORTED_WEB_PRODUCT_TERMS,
    ) or bool(
        re.search(
            r"\b(?:NET::)?ERR_[A-Z0-9_]+\b|\bDNS_PROBE_[A-Z0-9_]+\b",
            question,
            re.IGNORECASE,
        )
    )


SENSITIVE_SEARCH_PATTERNS = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    re.compile(r"https?://\S+", re.IGNORECASE),
    re.compile(r"\bALT\s*-?\s*20\d{2}\s*-?\s*\d{1,8}\b", re.IGNORECASE),
    re.compile(r"\b(?:asset|serial|service tag)\s*[:#-]?\s*[A-Z0-9-]{5,}\b", re.IGNORECASE),
)


def sanitize_search_question(question: str) -> str:
    """Remove common identifiers before sending a technical query to web search."""

    cleaned = question.strip()
    for pattern in SENSITIVE_SEARCH_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned) > 280:
        cleaned = cleaned[:280].rsplit(" ", 1)[0]

    return cleaned


def _configured_trusted_domains() -> tuple[str, ...]:
    configured = os.getenv("WEB_TRUSTED_DOMAINS", "").strip()
    if not configured:
        return DEFAULT_TRUSTED_DOMAINS

    values = []
    for raw in configured.split(","):
        domain = raw.strip().lower().removeprefix("https://").removeprefix("http://")
        domain = domain.strip(" /")
        if domain and re.fullmatch(r"[a-z0-9.-]+", domain):
            values.append(domain)

    return tuple(dict.fromkeys(values)) or DEFAULT_TRUSTED_DOMAINS


def _domain_allowed(hostname: str, allowed_domains: tuple[str, ...]) -> bool:
    host = hostname.lower().strip(".")
    return any(host == domain or host.endswith(f".{domain}") for domain in allowed_domains)


def _candidate_domains(question: str, allowed_domains: tuple[str, ...]) -> tuple[str, ...]:
    """Return only domains that match the named product/device family.

    Explicit application/vendor names take priority over the host platform. A
    Photoshop problem on a Mac should search Adobe, not Apple + Google + Zoom.
    """

    preferred: list[str] = []

    def add(domain: str) -> None:
        if domain in allowed_domains and domain not in preferred:
            preferred.append(domain)

    # Explicit products first.
    if contains_any_phrase(question, ("adobe", "acrobat", "creative cloud", "photoshop")):
        add("helpx.adobe.com")
        return tuple(preferred)

    if contains_any_phrase(question, ("zoom",)):
        add("support.zoom.com")
        return tuple(preferred)

    if contains_any_phrase(question, ("firefox", "mozilla")):
        add("support.mozilla.org")
        return tuple(preferred)

    if contains_any_phrase(
        question,
        (
            "google", "gmail", "chromebook", "chromeos", "chrome os", "chrome",
            "classroom", "google drive", "google docs", "google sheets",
            "google slides", "google meet", "google calendar",
        ),
    ):
        add("support.google.com")
        return tuple(preferred)

    if contains_any_phrase(
        question,
        (
            "safari", "airplay", "apple tv", "airdrop", "iphone", "ipad",
            "mac", "macbook", "macos", "bluetooth",
        ),
    ):
        add("support.apple.com")
        return tuple(preferred)

    if contains_any_phrase(question, ("kyocera", "taskalfa")):
        add("kyoceradocumentsolutions.com")
        return tuple(preferred)

    if contains_any_phrase(question, ("hp",)):
        add("support.hp.com")
        return tuple(preferred)

    if MICROSOFT_SUPPORT_ENABLED and is_microsoft_question(question):
        add("support.microsoft.com")

    return tuple(preferred)


def _is_vague_web_question(question: str) -> bool:
    normalized = normalize_text(question).strip(" .")
    vague = {
        "it's not working",
        "its not working",
        "it is not working",
        "the thing with the screen is broken again",
        "my computer is being weird",
        "same issue as last time",
    }
    return normalized in vague or len(normalized.split()) <= 2


def _official_article_url(url: str) -> bool:
    """Reject community/forum result pages even when hosted on a trusted domain."""

    parsed = urlparse(url)
    path = parsed.path.lower()
    blocked_markers = (
        "/thread/",
        "/community/",
        "/communities/",
        "/discussions/",
        "/forum/",
    )
    return not any(marker in path for marker in blocked_markers)


def _source_dedupe_key(url: str) -> str:
    """Collapse locale/country copies of the same vendor article."""

    parsed = urlparse(url)
    path = re.sub(
        r"^/(?:[a-z]{2}(?:[-_][a-z]{2})?)/",
        "/",
        parsed.path,
        flags=re.IGNORECASE,
    )
    return f"{(parsed.hostname or '').lower()}{path.rstrip('/')}"


def _source_matches_platform(question: str, title: str, snippet: str) -> bool:
    """Reject search results that clearly target the wrong device family."""

    q = normalize_text(question)
    source_text = normalize_text(f"{title} {snippet}")

    wants_mac = any(term in q for term in ("mac", "macbook", "macos", "safari"))
    wants_mobile = any(term in q for term in ("iphone", "ipad", "ios"))

    if wants_mac and not wants_mobile:
        mobile_only = any(term in source_text for term in ("iphone", "ipad", "ios"))
        desktop_signal = any(term in source_text for term in ("mac", "macos", "desktop"))
        if mobile_only and not desktop_signal:
            return False

    wants_chromebook = any(term in q for term in ("chromebook", "chromeos", "chrome os"))
    if wants_chromebook:
        unrelated_mobile = any(term in source_text for term in ("iphone", "ipad", "android phone"))
        chrome_signal = any(term in source_text for term in ("chromebook", "chromeos", "chrome browser", "chrome"))
        if unrelated_mobile and not chrome_signal:
            return False

    return True


def _safe_snippet(value: object) -> str:
    snippet = re.sub(r"\s+", " ", str(value or "")).strip()
    return snippet[:450]


def _safe_title(value: object) -> str:
    title = re.sub(r"\s+", " ", str(value or "")).strip()
    return title[:180] or "Official support result"


@lru_cache(maxsize=64)
def search_trusted_web(question: str) -> WebSearchBundle:
    """Search only approved official vendor support domains.

    Results are cached for the current app process so repeated vendor errors do
    not pay the full search latency again.
    """

    if not WEB_FALLBACK_ENABLED:
        return WebSearchBundle()

    search_question = sanitize_search_question(question)
    if not search_question or _is_vague_web_question(search_question):
        return WebSearchBundle()

    normalized_search = normalize_text(search_question)
    if "safari" in normalized_search and not any(
        term in normalized_search for term in ("iphone", "ipad", "ios", "mac", "macbook", "macos")
    ):
        search_question = f"{search_question} Mac"

    try:
        from ddgs import DDGS
    except ImportError as error:
        print(
            "Web fallback is enabled but the ddgs package is not installed: "
            f"{type(error).__name__}: {error}"
        )
        return WebSearchBundle()

    allowed_domains = _configured_trusted_domains()
    domains = _candidate_domains(search_question, allowed_domains)
    if not domains:
        return WebSearchBundle()

    results: list[WebSource] = []
    seen_urls: set[str] = set()
    seen_keys: set[str] = set()

    try:
        search_client = DDGS(timeout=max(1, int(round(WEB_SEARCH_TIMEOUT_SECONDS))))

        for domain in domains:
            if len(results) >= WEB_SEARCH_MAX_RESULTS:
                break

            query = f"{search_question} troubleshooting site:{domain}"
            per_domain_limit = min(2, WEB_SEARCH_MAX_RESULTS)

            try:
                domain_results = search_client.text(
                    query,
                    region=WEB_SEARCH_REGION,
                    safesearch="moderate",
                    max_results=per_domain_limit,
                    backend="auto",
                )
            except Exception as error:
                print(
                    "Trusted web search failed for "
                    f"{domain}: {type(error).__name__}: {error}"
                )
                continue

            for raw_result in domain_results or []:
                url = str(raw_result.get("href", "")).strip()
                if not url or url in seen_urls or not _official_article_url(url):
                    continue

                parsed = urlparse(url)
                hostname = parsed.hostname or ""
                if parsed.scheme not in {"http", "https"}:
                    continue
                if not _domain_allowed(hostname, allowed_domains):
                    continue

                dedupe_key = _source_dedupe_key(url)
                if dedupe_key in seen_keys:
                    continue

                title = _safe_title(raw_result.get("title"))
                snippet = _safe_snippet(raw_result.get("body"))
                if not _source_matches_platform(search_question, title, snippet):
                    continue

                source = WebSource(
                    title=title,
                    url=url,
                    snippet=snippet,
                    domain=hostname.lower(),
                )
                results.append(source)
                seen_urls.add(url)
                seen_keys.add(dedupe_key)

                if len(results) >= WEB_SEARCH_MAX_RESULTS:
                    break

    except Exception as error:
        print(f"Trusted web fallback failed: {type(error).__name__}: {error}")
        return WebSearchBundle()

    if not results:
        return WebSearchBundle()

    context_parts: list[str] = []
    for index, source in enumerate(results, start=1):
        context_parts.append(
            "\n".join(
                (
                    f"SOURCE {index}",
                    f"Title: {source.title}",
                    f"URL: {source.url}",
                    f"Excerpt: {source.snippet or 'No search excerpt was returned.'}",
                )
            )
        )

    return WebSearchBundle(
        context="\n\n".join(context_parts),
        sources=tuple(results),
    )
