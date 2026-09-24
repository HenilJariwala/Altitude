from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.text_matching import contains_phrase, normalize_text


CONTRAST_MARKERS = (
    " but ",
    " however ",
    " although ",
    " even though ",
    " except ",
    " yet ",
)


PRODUCT_PHRASES: dict[str, tuple[str, ...]] = {
    "zoom": ("zoom", "zoom workplace"),
    "google_chrome": ("google chrome", "chrome browser", "chrome"),
    "safari": ("safari", "safari browser"),
    "firefox": ("firefox", "mozilla firefox"),
    "google_drive": ("google drive",),
    "google_docs": ("google docs", "google doc", "docs"),
    "google_sheets": ("google sheets", "google sheet", "sheets"),
    "google_slides": ("google slides", "google slide", "slides"),
    "google_forms": ("google forms", "google form", "forms"),
    "google_chat": ("google chat",),
    "google_calendar": ("google calendar",),
    "google_classroom": ("google classroom",),
    "google_meet": ("google meet",),
    "gmail": ("gmail",),
    "microsoft_word": ("microsoft word", "ms word", "word app"),
    "microsoft_excel": ("microsoft excel", "ms excel", "excel"),
    "microsoft_onedrive": ("onedrive", "one drive"),
    "microsoft_outlook": ("outlook", "microsoft outlook"),
    "microsoft_365": ("microsoft 365", "office 365", "microsoft office"),
    "adobe_acrobat": ("adobe acrobat", "acrobat", "adobe reader"),
    "adobe_photoshop": ("adobe photoshop", "photoshop"),
    "adobe_creative_cloud": ("adobe creative cloud", "creative cloud", "adobe"),
    "adobe_sign": ("adobe sign", "acrobat sign"),
}


PLATFORM_PHRASES: dict[str, tuple[str, ...]] = {
    "chromebook": ("chromebook", "chromebooks", "chromeos", "chrome os"),
    "windows": ("windows", "task manager", "system interrupts"),
    "macos": ("mac", "macs", "macbook", "macbooks", "macos", "mac os", "system settings"),
}


DOMAIN_PHRASES: dict[str, tuple[str, ...]] = {
    "power_battery": (
        "charge",
        "charging",
        "charger",
        "power adapter",
        "battery",
        "plugged in",
        "unplug",
    ),
    "system_update": (
        "system update",
        "windows update",
        "software update",
        "updates",
        "update",
        "restart for updates",
    ),
    "external_display": (
        "external monitor",
        "external monitors",
        "second monitor",
        "two monitors",
        "dual monitors",
        "projector",
        "classroom display",
        "external display",
    ),
    "dock": ("docking station", "usb-c dock", "usb c dock", "dock"),
    "smartboard": ("smartboard", "smart board", "interactive display"),
    "keyboard": ("keyboard", "keys", "key stopped", "keys stopped"),
    "mouse_touchpad": ("mouse", "cursor", "pointer", "touchpad", "trackpad"),
    "stylus_touch": ("stylus", "pen", "touchscreen", "digital ink", "touch calibration"),
    "microphone": ("microphone", "mic", "voice", "recording apps"),
    "audio": ("audio", "sound", "speaker", "speakers", "headphones"),
    "printer": ("printer", "printing", "print job", "print queue", "spooling", "copier"),
    "scanner_copier": ("scanner", "scan to email", "copier"),
    "wifi": (
        "wifi",
        "wi-fi",
        "wireless network",
        "guest network",
        "staff network",
        "school network",
        "access point",
    ),
    "vpn_network": ("vpn", "network drive", "network drives", "internal drive", "internal drives"),
    "browser_security": (
        "ssl",
        "tls",
        "certificate",
        "security certificate",
        "certificate warning",
        "privacy warning",
        "connection is not private",
        "err ssl",
        "err cert",
        "dns probe",
        "err connection",
        "err network",
        "http2 protocol",
        "status access violation",
        "pop-up",
        "popup",
        "pop up",
    ),
    "browser_extension": (
        "extension",
        "extensions",
        "toolbar",
        "pin extension",
        "manage extensions",
        "content blocker",
    ),
    "browser_profile": (
        "bookmarks",
        "chrome profile",
        "browser profile",
        "wrong google account",
        "wrong account",
        "sync bookmarks",
    ),
    "classroom_assignment": (
        "assignment",
        "assignments",
        "scheduled assignment",
        "scheduled post",
        "turn in",
        "turned in",
        "submitted",
        "submission",
        "missing assignment",
    ),
    "classroom_grading": (
        "gradebook",
        "grades",
        "grading",
        "graded",
    ),
    "classroom_roster": (
        "roster",
        "co-teacher",
        "co teacher",
        "people page",
    ),
    "drive_sharing": (
        "anyone with the link",
        "sharing permission",
        "sharing permissions",
        "shared folder",
        "request access",
        "general access",
    ),
    "drive_versioning": (
        "version history",
        "restore version",
        "earlier version",
        "previous version",
    ),
    "drive_sync": (
        "drive for desktop",
        "drive folder",
        "syncing",
        "not syncing",
        "sync failure",
    ),
    "email_filtering": (
        "filter",
        "filters",
        "auto-archive",
        "auto archive",
        "all mail",
    ),
    "email_delegation": (
        "gmail delegation",
        "delegate access",
        "delegated access",
        "send emails as me",
        "send mail as me",
    ),
    "calendar_sync": (
        "calendar sync",
        "calendar app",
        "phone calendar",
        "not showing on my phone",
    ),
    "meeting_attendance": (
        "attendance",
        "attendance report",
        "take attendance",
    ),
    "meeting_waiting_room": (
        "waiting room",
        "admit",
    ),
    "meeting_breakout": (
        "breakout room",
        "breakout rooms",
        "main room",
    ),
    "licensing": (
        "license",
        "licenses",
        "licence",
        "licences",
        "licensed",
        "unlicensed",
        "downgraded to basic",
        "basic account",
        "40 minutes",
    ),
    "ownership_transfer": (
        "transfer ownership",
        "ownership transfer",
        "departed owner",
        "teacher who left",
        "left the school owns",
    ),
    "time_sync": (
        "wrong time",
        "time zone",
        "timestamp",
        "clock is",
        "minutes off",
    ),
    "autosave_recovery": (
        "autosave",
        "without saving",
        "draft gone",
        "gone forever",
    ),
    "device_management": (
        "kiosk app",
        "managed app",
        "managed chromebook",
        "developer mode",
        "managed extension",
        "re-enroll",
        "re-enrolled",
        "enrollment",
    ),
    "peripheral_bluetooth": (
        "bluetooth keyboard",
        "bluetooth mouse",
        "wireless mouse",
        "wireless keyboard",
    ),
    "storage": ("disk space", "storage full", "disk full", "storage"),
    "pdf_file": ("pdf", "file format", "corrupted", "unsupported file"),
    "email": ("email", "emails", "inbox", "mail"),
    "calendar": ("calendar", "calendar app", "event", "invitation"),
    "collaboration": ("shared link", "shared folder", "shared drive", "co-author", "editing by another user"),
    "authentication": (
        "password",
        "sign in",
        "login",
        "log in",
        "account locked",
        "failed login",
    ),
    "mfa": (
        "two-factor",
        "two factor",
        "2fa",
        "multi-factor",
        "multifactor",
        "authenticator",
        "approval notification",
        "verification code",
    ),
    "software_install": (
        "install a program",
        "install program",
        "install software",
        "administrator password",
        "admin password",
    ),
    "software_runtime": (
        "application",
        "program",
        "software",
        "local database",
        "database server",
    ),
    "boot_startup": (
        "boot loop",
        "reboot loop",
        "login screen",
        "will not start",
        "won't start",
        "cannot start",
    ),
    "performance": ("100%", "cpu", "fan", "fans", "running slowly", "running slow", "slow computer", "mac is slow", "macbook is slow"),
    "device_freeze": ("computer freezes", "device freezes", "locking up", "locks up", "system freeze", "whole computer freezes"),
    "camera": ("camera", "webcam", "camera permission", "camera access"),
    "managed_permission": ("admin rights", "local admin", "administrator access", "admin access", "whitelist", "allowlist", "managed permission", "permissions are locked", "grayed out", "greyed out"),
    "screen_capture": ("screenshot", "screen shot", "screen capture"),
    "browser_data": ("clear cache", "clear cookies", "delete browsing data", "website data"),
    "assessment": ("standardized test", "testing browser", "lockdown browser", "mid-test", "mid test"),
    "inventory_loaner": ("loaner", "borrow", "available", "availability", "reserve", "hold"),
}


SYMPTOM_PHRASES: dict[str, tuple[str, ...]] = {
    "not_charging": ("won't charge", "wont charge", "not charging", "does not charge"),
    "battery_drain": ("drains", "draining", "zero in less than", "battery dies"),
    "forced_restart": ("force a system restart", "forced restart", "restart for updates"),
    "not_detected": ("not detected", "not being detected", "doesn't detect", "does not detect"),
    "image_quality": ("purple tint", "fuzzy", "blurry", "wrong resolution", "cutting off the edges"),
    "no_signal": ("no signal",),
    "popups": ("pop-up", "popup", "pop up", "random tabs"),
    "browser_error": (
        "err ssl protocol error",
        "err cert date invalid",
        "net err cert authority invalid",
        "dns probe finished nxdomain",
        "err connection reset",
        "err network changed",
        "err http2 protocol error",
        "status access violation",
    ),
    "certificate_warning": (
        "invalid security certificate",
        "certificate warning",
        "privacy warning",
        "err cert date invalid",
        "err cert authority invalid",
    ),
    "no_input": ("not picking up", "not responding", "stopped responding", "isn't picking up"),
    "missing": ("cannot find", "can't find", "missing", "disappeared", "not showing"),
    "sync_failure": ("not syncing", "sync", "not downloading", "not arriving"),
    "scan_to_email": ("sending documents to my email", "scan to email", "scanner"),
    "locked_editing": ("locked for editing", "cannot edit", "can't edit", "read only", "view only"),
    "refresh_loop": ("constantly refreshes", "keeps refreshing", "page refreshes"),
    "app_freeze": ("freezes", "freezing", "force quit", "not responding", "crashing", "keeps crashing"),
    "loading_failure": ("not loading", "isn't loading", "won't load", "wont load", "stuck loading"),
    "permission_blocked": ("grayed out", "greyed out", "disabled by administrator", "need admin rights", "local admin", "request access"),
    "session_expired": ("session has expired", "session expired"),
    "send_failure": ("not sending", "isn't sending", "won't send", "wont send", "cannot send", "can't send"),
    "not_opening": ("won't open", "wont open", "cannot open", "can't open", "not opening"),
    "garbled_print": ("weird symbols", "gibberish", "garbled", "random characters"),
    "wrong_network": ("guest network instead", "staff network", "won't let me click forget", "cannot forget"),
    "av_sync": ("out of sync", "seconds out of sync", "audio delay", "audio is delayed"),
    "account_error": ("account error", "problems with your account", "unlicensed product", "activation"),
    "high_cpu": ("system interrupts", "100% of my cpu", "100% cpu"),
    "calibration": ("three inches away", "offset", "calibration", "touches register"),
    "account_lockout": ("locking my account", "too many failed login attempts", "account lockout"),
    "display_flicker": ("screen flickers", "flickers violently", "goes completely dim", "screen goes dim"),
    "local_database": ("local database server", "cannot connect to local database", "database server"),
    "stale_mail": ("old emails", "three years ago", "new emails", "none of my new emails"),
    "spooling": ("spooling", "stuck in the queue", "stuck like that", "won't cancel", "cannot cancel"),
    "device_in_use": ("device is currently in use", "in use by another application", "used by another application"),
    "network_drive_access": ("can't access any of the internal network drives", "cannot access network drives", "network drives"),
    "ghost_pointer": ("cursor keeps jumping", "pointer keeps jumping", "moves on its own", "completely on its own"),
}


APP_PRODUCTS = frozenset(PRODUCT_PHRASES)

BROWSER_PRODUCTS = frozenset({"google_chrome", "safari", "firefox"})

# If the user's actual problem is one of these device/system domains, a
# product-specific article (Zoom/Google/Microsoft) should not win unless that
# product was actually named or the document matches the same problem domain.
SPECIFIC_TASK_DOMAINS = frozenset(
    {
        "browser_extension",
        "browser_profile",
        "classroom_assignment",
        "classroom_grading",
        "classroom_roster",
        "drive_sharing",
        "drive_versioning",
        "drive_sync",
        "email_filtering",
        "email_delegation",
        "calendar_sync",
        "meeting_attendance",
        "meeting_waiting_room",
        "meeting_breakout",
        "licensing",
        "ownership_transfer",
        "time_sync",
        "autosave_recovery",
        "device_management",
        "peripheral_bluetooth",
    }
)


SYSTEM_DOMAINS = frozenset(
    {
        "power_battery",
        "system_update",
        "external_display",
        "dock",
        "smartboard",
        "keyboard",
        "mouse_touchpad",
        "stylus_touch",
        "microphone",
        "audio",
        "printer",
        "scanner_copier",
        "wifi",
        "vpn_network",
        "browser_security",
        "browser_extension",
        "browser_profile",
        "classroom_assignment",
        "classroom_grading",
        "classroom_roster",
        "drive_sharing",
        "drive_versioning",
        "drive_sync",
        "email_filtering",
        "email_delegation",
        "calendar_sync",
        "meeting_attendance",
        "meeting_waiting_room",
        "meeting_breakout",
        "licensing",
        "ownership_transfer",
        "time_sync",
        "autosave_recovery",
        "device_management",
        "peripheral_bluetooth",
        "storage",
        "pdf_file",
        "software_install",
        "software_runtime",
        "boot_startup",
        "performance",
        "device_freeze",
        "camera",
        "managed_permission",
        "screen_capture",
        "browser_data",
        "assessment",
        "inventory_loaner",
    }
)


@dataclass(frozen=True)
class RetrievalProfile:
    full_text: str
    focus_text: str
    products: frozenset[str]
    platforms: frozenset[str]
    domains: frozenset[str]
    focus_domains: frozenset[str]
    symptoms: frozenset[str]
    focus_symptoms: frozenset[str]


@dataclass(frozen=True)
class DocumentProfile:
    products: frozenset[str]
    platforms: frozenset[str]
    domains: frozenset[str]
    symptoms: frozenset[str]
    source: str


def _contains(text: str, phrase: str) -> bool:
    return contains_phrase(text, phrase)


def _detect(text: str, vocabulary: dict[str, tuple[str, ...]]) -> frozenset[str]:
    normalized = normalize_text(text)
    found = {
        label
        for label, phrases in vocabulary.items()
        if any(_contains(normalized, phrase) for phrase in phrases)
    }
    return frozenset(found)


def issue_focus(text: str) -> str:
    """Prefer the clause after contrast words such as 'but'.

    Users often state a working condition first and the actual failure second:
    'Wi-Fi works, but every website shows a certificate warning'. Retrieval
    should focus on the failure, not the working context.
    """

    normalized = normalize_text(text)
    best_index = -1
    best_marker = ""

    for marker in CONTRAST_MARKERS:
        index = normalized.rfind(marker)
        if index > best_index:
            best_index = index
            best_marker = marker

    if best_index < 0:
        return normalized

    focused = normalized[best_index + len(best_marker) :].strip()

    if len(focused.split()) < 3:
        return normalized

    return focused


def _contextual_products(text: str, detected: frozenset[str]) -> frozenset[str]:
    """Infer product names only when surrounding words make them unambiguous.

    Staff often say "Classroom", "Meet", or "Drive" without the Google
    prefix. Treating those single words as product aliases globally creates new
    collisions (for example "classroom projector"). This helper therefore
    requires product-specific task words before enriching the profile.
    """

    products = set(detected)

    if contains_phrase(text, "classroom") and any(
        contains_phrase(text, phrase)
        for phrase in (
            "assignment", "assignments", "gradebook", "grades",
            "co-teacher", "co teacher", "class code", "classwork",
            "roster", "stream", "announcement", "turn in",
            "turned in", "submitted", "submission",
        )
    ):
        products.add("google_classroom")

    if contains_phrase(text, "meet") and any(
        contains_phrase(text, phrase)
        for phrase in (
            "meeting", "call", "join", "link", "host", "co-host",
            "camera", "microphone", "recording", "attendance",
            "breakout room", "breakout rooms", "present", "share screen",
        )
    ):
        products.add("google_meet")

    if contains_phrase(text, "drive") and any(
        contains_phrase(text, phrase)
        for phrase in (
            "file", "files", "folder", "folders", "shared drive",
            "shared folder", "version history", "sync", "storage",
            "drive for desktop", "anyone with the link",
        )
    ):
        products.add("google_drive")

    if contains_phrase(text, "calendar") and any(
        contains_phrase(text, phrase)
        for phrase in (
            "event", "events", "shared", "sharing", "sync", "phone",
            "invite", "invitation", "school calendar",
        )
    ):
        products.add("google_calendar")

    return frozenset(products)


def build_retrieval_profile(text: str) -> RetrievalProfile:
    normalized = normalize_text(text)
    focused = issue_focus(normalized)
    products = _contextual_products(
        normalized,
        _detect(normalized, PRODUCT_PHRASES),
    )

    return RetrievalProfile(
        full_text=normalized,
        focus_text=focused,
        products=products,
        platforms=_detect(normalized, PLATFORM_PHRASES),
        domains=_detect(normalized, DOMAIN_PHRASES),
        focus_domains=_detect(focused, DOMAIN_PHRASES),
        symptoms=_detect(normalized, SYMPTOM_PHRASES),
        focus_symptoms=_detect(focused, SYMPTOM_PHRASES),
    )


def _metadata_text(document: Any) -> str:
    """Return topic identity text without pulling incidental words from the body.

    Full procedure text often mentions another device or product only as an
    escalation/example. Using that body text for routing caused collisions such
    as projector questions matching Google Slides speaker notes and Chromebook
    questions matching Zoom articles. Titles and intent keywords are the
    authoritative retrieval identity.
    """

    metadata = getattr(document, "metadata", {}) or {}
    values = [
        metadata.get("source", ""),
        metadata.get("document_title", ""),
        metadata.get("title", ""),
        metadata.get("section_title", ""),
        metadata.get("intent_keywords", ""),
    ]
    return " ".join(str(value) for value in values if value)


def build_document_profile(document: Any) -> DocumentProfile:
    metadata = getattr(document, "metadata", {}) or {}
    source = str(metadata.get("source", "")).lower()
    text = _metadata_text(document)

    products = set(
        _contextual_products(
            normalize_text(text),
            _detect(text, PRODUCT_PHRASES),
        )
    )
    platforms = set(_detect(text, PLATFORM_PHRASES))
    domains = set(_detect(text, DOMAIN_PHRASES))
    symptoms = set(_detect(text, SYMPTOM_PHRASES))

    if "zoom_workplace" in source:
        products.add("zoom")
    if "google_password" in source:
        domains.add("authentication")
    if "microsoft_365" in source:
        domains.add("authentication")
    if "windows_basic" in source:
        platforms.add("windows")
    if "mac_basic" in source:
        platforms.add("macos")
    if "printer_support" in source:
        domains.add("printer")
    if "wifi_support" in source:
        domains.add("wifi")

    return DocumentProfile(
        products=frozenset(products),
        platforms=frozenset(platforms),
        domains=frozenset(domains),
        symptoms=frozenset(symptoms),
        source=source,
    )


def profiles_are_compatible(
    question: RetrievalProfile,
    document: DocumentProfile,
) -> bool:
    """Hard-reject obviously unrelated knowledge before semantic reranking."""

    query_products = question.products
    document_products = document.products

    if query_products and document_products and query_products.isdisjoint(document_products):
        return False

    # An operating-system or physical-device question must not be answered by
    # an app-specific article merely because both mention a microphone, camera,
    # keyboard, or other shared noun. For example, a USB microphone missing
    # from macOS Sound settings cannot use a Zoom audio procedure.
    if (
        not query_products
        and document_products
        and (question.focus_domains or question.domains).intersection(SYSTEM_DOMAINS)
    ):
        return False

    # Opposite-device matches are never useful. A Chromebook question must not
    # use a Mac procedure merely because both mention Wi-Fi, and vice versa.
    if (
        question.platforms
        and document.platforms
        and question.platforms.isdisjoint(document.platforms)
    ):
        return False

    focus_domains = question.focus_domains or question.domains
    focus_symptoms = question.focus_symptoms or question.symptoms

    domain_overlap = focus_domains.intersection(document.domains)
    symptom_overlap = focus_symptoms.intersection(document.symptoms)

    # If both the question and the topic identify a concrete task/problem
    # family, they must agree. This is deliberately broader than the old
    # SYSTEM_DOMAINS-only check because most remaining v9 failures were within
    # the same product suite: Classroom grades -> Chat history, Chrome extension
    # -> accessibility, Gmail filter -> spam, Meet attendance -> join-meeting.
    if focus_domains and document.domains and not domain_overlap:
        return False

    # Generic parent domains such as "calendar" or "email" are not enough
    # when the query names a more specific task. A Calendar sync question must
    # match Calendar sync, not merely any Calendar article.
    query_specific = focus_domains.intersection(SPECIFIC_TASK_DOMAINS)
    document_specific = document.domains.intersection(SPECIFIC_TASK_DOMAINS)
    if query_specific and not query_specific.intersection(document_specific):
        return False

    # A named browser problem must stay in the browser/security family. This
    # prevents Chrome/Safari error codes from drifting into file permissions,
    # external drives, calendars, or other semantically nearby KB articles.
    if (
        query_products.intersection(BROWSER_PRODUCTS)
        and "browser_security" in focus_domains
        and "browser_security" not in document.domains
    ):
        return False

    # A generic hardware/system question must not be answered by a Zoom,
    # Google, Microsoft, or Adobe article merely because a generic word is
    # semantically similar.
    if (
        not query_products
        and document_products
        and focus_domains.intersection(SYSTEM_DOMAINS)
        and not domain_overlap
    ):
        return False

    # When both sides have strong system domains and none match, reject.
    if (
        focus_domains.intersection(SYSTEM_DOMAINS)
        and document.domains.intersection(SYSTEM_DOMAINS)
        and not domain_overlap
    ):
        return False

    # A named app with a clear failure symptom should not use a same-suite
    # article about a different symptom merely because the product name matches.
    if (
        query_products
        and focus_symptoms
        and document.symptoms
        and not symptom_overlap
        and focus_domains
        and document.domains
        and not domain_overlap
    ):
        return False

    # Generic device/system failures must not drift into a product article just
    # because the document happens to mention the same platform (for example,
    # Chromebook -> Zoom Web App). Require a matching problem family.
    if (
        not query_products
        and document_products
        and (focus_domains or focus_symptoms)
        and not domain_overlap
        and not symptom_overlap
    ):
        return False

    # Learned ticket knowledge is intentionally strict. A learned fix should
    # match the same device/problem family, not just share one generic word.
    if document.source == "learned_support.md":
        if not domain_overlap:
            return False
        if focus_symptoms and document.symptoms and not symptom_overlap:
            return False

    return True


def profile_score(
    question: RetrievalProfile,
    document: DocumentProfile,
) -> int:
    focus_domains = question.focus_domains or question.domains
    focus_symptoms = question.focus_symptoms or question.symptoms

    score = 0
    score += len(focus_domains.intersection(document.domains)) * 90
    score += len(question.domains.intersection(document.domains)) * 25
    score += len(focus_symptoms.intersection(document.symptoms)) * 80
    score += len(question.symptoms.intersection(document.symptoms)) * 25
    score += len(question.products.intersection(document.products)) * 120
    score += len(question.platforms.intersection(document.platforms)) * 35

    if question.products and not document.products:
        score -= 15

    if (
        question.platforms
        and document.platforms
        and question.platforms.isdisjoint(document.platforms)
    ):
        score -= 100

    return score


def serialize_tags(values: frozenset[str]) -> str:
    return ",".join(sorted(values))
