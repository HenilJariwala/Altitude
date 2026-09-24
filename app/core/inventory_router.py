from __future__ import annotations

import math
import os
import re
import warnings
from dataclasses import dataclass
from typing import Any

import requests
from dotenv import load_dotenv
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
)
from rapidfuzz import fuzz

from core.text_matching import contains_phrase, normalize_text

from urllib3.exceptions import (
    InsecureRequestWarning,
)

load_dotenv()


INVENTORY_API_URL = os.getenv(
    "INVENTORY_API_URL",
    "",
).strip()


INVENTORY_API_VERIFY_SSL = os.getenv(
    "INVENTORY_API_VERIFY_SSL",
    "true",
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


INVENTORY_API_TOKEN = os.getenv(
    "INVENTORY_API_TOKEN",
    "",
).strip()


def get_positive_float_setting(
    name: str,
    default: float,
) -> float:
    raw_value = os.getenv(
        name,
        str(default),
    ).strip()

    try:
        value = float(raw_value)
    except ValueError:
        return default

    if not math.isfinite(value) or value <= 0:
        return default

    return value


INVENTORY_API_TIMEOUT_SECONDS = get_positive_float_setting(
    "INVENTORY_API_TIMEOUT_SECONDS",
    5.0,
)


class InventoryItem(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
    )

    typeId: int
    typeName: str = Field(
        min_length=1,
    )
    totalCount: int = Field(
        ge=0,
    )
    availableCount: int = Field(
        ge=0,
    )
    loanedCount: int = Field(
        ge=0,
    )


class InventoryPayload(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
    )

    types: list[InventoryItem]


@dataclass(frozen=True)
class InventoryDecision:
    handled: bool
    answer: str = ""


@dataclass(frozen=True)
class InventoryMatch:
    item: InventoryItem | None
    alternatives: tuple[str, ...] = ()


class InventoryServiceError(RuntimeError):
    pass


ITEM_ALIASES: dict[
    str,
    tuple[str, ...],
] = {
    "macbook": (
        "macbook",
        "mac book",
        "mac laptop",
        "apple laptop",
    ),
    "dell laptop": (
        "dell laptop",
        "windows laptop",
        "dell computer",
    ),
    "usb-c hub": (
        "usb c hub",
        "type c hub",
        "usb hub",
    ),
    "usb-a block": (
        "usb a block",
        "usb block",
        "wall block",
        "power block",
    ),
    "micro-usb cable": (
        "micro usb cable",
        "micro usb cord",
        "micro usb",
    ),
    "usb-c block": (
        "usb c block",
        "type c block",
        "usb c power block",
        "usb c charging block",
        "usb-c charging block",
        "type c charging block",
    ),
    "usb-c adapter": (
        "usb c adapter",
        "type c adapter",
    ),
    "usb-c cable": (
        "usb c cable",
        "type c cable",
        "usb c cord",
        "type c cord",
    ),
    "hp chromebook": (
        "hp chromebook",
        "chromebook",
        "chrome book",
    ),
    "mini-usb cable": (
        "mini usb cable",
        "mini usb cord",
    ),
    "usb-c charger": (
        "usb c charger",
        "type c charger",
    ),
    "usb-c lightning cable": (
        "usb c lightning cable",
        "usb c to lightning cable",
        "iphone usb c cable",
    ),
    "magsafe 2 charger": (
        "magsafe 2 charger",
        "magsafe two charger",
    ),
    "cx12 charger": ("cx12 charger",),
    "speaks": (
        "speaker",
        "speakers",
    ),
    "extension": (
        "extension cord",
        "extension cable",
    ),
    "usb-a lightning cable": (
        "usb a lightning cable",
        "usb a to lightning cable",
        "iphone usb a cable",
    ),
    "hp chromebook charger": (
        "hp chromebook charger",
        "chromebook charger",
    ),
    "usb-c to audio jack": (
        "usb c to audio jack",
        "usb c audio adapter",
        "usb c headphone adapter",
    ),
    "ipad": (
        "ipad",
        "apple ipad",
    ),
    "mouse": (
        "mouse",
        "computer mouse",
    ),
    "remote": (
        "remote",
        "remote control",
    ),
    "document scanner": (
        "document scanner",
        "document scanners",
        "scanner",
        "scanners",
    ),
    "apple stylus": (
        "apple stylus",
        "apple pencil",
        "stylus",
    ),
    "key card": (
        "key card",
        "access card",
    ),
    "usb-c mulit-port adapter": (
        "usb c multi port adapter",
        "usb c multiport adapter",
        "usb c multipurpose adapter",
    ),
    "magsafe-3 cable": (
        "magsafe 3 cable",
        "magsafe three cable",
    ),
    "usb-a to micro cable": (
        "usb a to micro cable",
        "usb a micro cable",
    ),
    "usb-c to micro cable": (
        "usb c to micro cable",
        "usb c micro cable",
    ),
    "usb-a to c cable": (
        "usb a to c cable",
        "usb a to usb c cable",
    ),
    "usb-a mouse": (
        "usb a mouse",
        "usb mouse",
        "wired usb mouse",
    ),
}


CANONICAL_REQUEST_ALIASES: dict[str, tuple[str, ...]] = {
    "MacBook": ("macbook", "mackbook", "mac book", "apple laptop", "loaner mac"),
    "USB-C Charger": (
        "usb c charger",
        "usb-c charger",
        "type c charger",
        "usb c power adapter",
    ),
    "Micro-USB Cable": (
        "micro usb cable",
        "micro-usb cable",
        "micro usb cord",
    ),
    "USB-C Cable": ("usb c cable", "usb-c cable", "type c cable"),
    "Chromebook": ("chromebook", "chrome book"),
    "USB-C Block": ("usb c block", "usb-c block", "usb c charging block", "usb-c charging block"),
    "HDMI Adapter": ("hdmi adapter", "hdmi dongle", "hdmi adaptor"),
    "iPad": ("ipad", "tablet"),
    "Apple Stylus": ("apple pencil", "apple stylus", "stylus"),
    "Document Camera": ("document camera", "document cameras"),
    "Document Scanner": ("document scanner", "document scanners", "scanner"),
}


def requested_canonical_names(question: str) -> tuple[str, ...]:
    """Identify named hardware even when it is missing from the API payload."""

    normalized = normalize_text(question)
    matches: list[str] = []

    for display_name, aliases in CANONICAL_REQUEST_ALIASES.items():
        if any(
            alias in normalized or alias.replace("-", " ") in normalized
            for alias in aliases
        ):
            matches.append(display_name)

    # A generic charger request is intentionally kept broad. Prefer an exact
    # charger in the API later, but do not confuse it with a cable.
    if "charger" in normalized and not any("Charger" in name for name in matches):
        matches.append("Charger")

    # Common misspelling observed during acceptance testing.
    if "mackbook" in normalized and "MacBook" not in matches:
        matches.append("MacBook")

    return tuple(dict.fromkeys(matches))


def recent_inventory_subject(
    history: list[dict[str, Any]],
    current_question: str,
) -> str:
    current = normalize_text(current_question)

    for message in reversed(history[-12:]):
        if message.get("role") != "user":
            continue
        content = str(message.get("content", "")).strip()
        if not content or normalize_text(content) == current:
            continue
        names = requested_canonical_names(content)
        if names:
            return names[-1]

    return ""


def find_item_for_canonical(
    canonical_name: str,
    items: list[InventoryItem],
) -> InventoryItem | None:
    normalized_canonical = normalize_text(canonical_name)

    # First prefer an exact type name or configured alias.
    for item in items:
        terms = get_item_search_terms(item)
        if any(normalize_text(term) == normalized_canonical for term in terms):
            return item

    # Then allow a contained product class, while keeping chargers separate
    # from cables and adapters.
    for item in items:
        item_name = normalize_text(item.typeName)
        if canonical_name == "Charger":
            if "charger" in item_name:
                return item
        elif normalized_canonical in item_name or item_name in normalized_canonical:
            return item

    return None


def format_missing_inventory_item(canonical_name: str) -> str:
    return (
        f"**{canonical_name}** is not listed in the current live inventory "
        "response, so no available count can be confirmed right now. "
        "Please contact the IT Helpdesk to check stock or an alternative."
    )


UNCONDITIONAL_INVENTORY_PHRASES = (
    "can i borrow",
    "could i borrow",
    "may i borrow",
    "in stock",
    "out of stock",
    "loaner",
    "reserve",
    "reservation",
    "hold for me",
    "hold one",
    "check inventory",
    "inventory check",
    "what can i borrow",
    "what items can i borrow",
    "what items are available",
    "show available items",
    "list available items",
    "show inventory",
)


HARDWARE_REQUIRED_INVENTORY_PHRASES = (
    "do you have",
    "is there a",
    "is there an",
    "are there any",
    "how many",
    "available",
    "availability",
    "can i get",
)


POSSIBLE_ITEM_REQUEST_PHRASES = (
    "i want",
    "i need",
    "we need",
    "looking for",
    "i am looking for",
    "get me",
    "give me",
    "request a",
    "request an",
    "would like",
    "pick up",
    "what about",
)


HARDWARE_TERMS = (
    "macbook",
    "mackbook",
    "laptop",
    "computer",
    "chromebook",
    "ipad",
    "tablet",
    "usb",
    "cable",
    "cord",
    "charger",
    "block",
    "adapter",
    "dongle",
    "hub",
    "mouse",
    "keyboard",
    "headphone",
    "headset",
    "projector",
    "remote",
    "stylus",
    "pencil",
    "key card",
    "extension cord",
    "extension cable",
    "speaker",
    "magsafe",
    "lightning",
    "audio jack",
    "equipment",
    "hardware",
    "device",
    "scanner",
    "scanners",
    "document scanner",
    "document scanners",
    "document camera",
    "document cameras",
)


TROUBLESHOOTING_PHRASES = (
    "not working",
    "re-enroll",
    "re-enrolled",
    "needs to be enrolled",
    "lost the charger",
    "lost charger",
    "returning",
    "return it",
    "wipe before returning",
    "someone else's name",
    "someone elses name",
    "old apps installed",
    "does not work",
    "doesn't work",
    "not showing",
    "not detected",
    "cannot detect",
    "can't detect",
    "cant detect",
    "no sound",
    "no audio",
    "no internet",
    "microphone not working",
    "mic not working",
    "broken",
    "freezing",
    "frozen",
    "crashing",
    "running slow",
    "very slow",
    "not responding",
    "not charging",
    "will not start",
    "won't start",
    "wont start",
    "keeps disconnecting",
    "disconnecting",
    "stuck",
    "snapped",
    "broken off",
    "stuck inside",
    "mirroring",
    "mirror to",
    "screen is mirroring",
    "error",
    "issue",
    "problem",
    "repair",
    "fix",
    "troubleshoot",
)


ITEM_QUERY_NOISE = (
    "can i borrow",
    "could i borrow",
    "may i borrow",
    "do you have any",
    "do you have",
    "is there an",
    "is there a",
    "are there any",
    "how many",
    "can i get an",
    "can i get a",
    "can i use an",
    "can i use a",
    "could i get an",
    "could i get a",
    "i am looking for",
    "i would like an",
    "i would like a",
    "would like an",
    "would like a",
    "i want an",
    "i want a",
    "i want",
    "i need an",
    "i need a",
    "i need",
    "we need an",
    "we need a",
    "we need",
    "looking for",
    "get me an",
    "get me a",
    "give me an",
    "give me a",
    "request an",
    "request a",
    "pick up an",
    "pick up a",
    "what about",
    "please check",
    "check inventory",
    "inventory check",
    "inventory",
    "currently",
    "right now",
    "available",
    "availability",
    "in stock",
    "out of stock",
    "to borrow",
    "for loan",
    "loaner",
    "left",
)


ITEM_STOP_WORDS = {
    "a",
    "also",
    "an",
    "and",
    "any",
    "are",
    "do",
    "for",
    "get",
    "give",
    "have",
    "i",
    "is",
    "like",
    "looking",
    "me",
    "need",
    "of",
    "one",
    "please",
    "request",
    "some",
    "the",
    "there",
    "want",
    "we",
    "would",
    "you",
}


def contains_known_inventory_item(question: str) -> bool:
    """Return whether the text names one of the supported inventory items."""

    normalized = normalize_text(question)

    for canonical_name, aliases in ITEM_ALIASES.items():
        terms = (canonical_name, *aliases)
        if any(normalize_text(term) in normalized for term in terms):
            return True

    return bool(requested_canonical_names(question))


def recent_inventory_context(
    history: list[dict[str, Any]],
) -> bool:
    """Detect whether the immediately recent conversation is about inventory."""

    assistant_markers = (
        "current live availability",
        "currently available",
        "inventory item",
        "inventory items",
        "which item would you like me to check",
        "which one would you like me to check",
        "which hardware item would you like me to check",
        "cannot check live hardware availability",
        "cannot check live",
        "visit the it helpdesk to request one",
    )

    for message in reversed(history[-6:]):
        content = normalize_text(str(message.get("content", "")))
        if not content:
            continue

        if message.get("role") == "assistant" and any(
            marker in content for marker in assistant_markers
        ):
            return True

        if message.get("role") == "user":
            if any(phrase in content for phrase in UNCONDITIONAL_INVENTORY_PHRASES):
                return True
            if has_hardware_term(content) and any(
                phrase in content for phrase in HARDWARE_REQUIRED_INVENTORY_PHRASES
            ):
                return True

    return False


def is_short_inventory_addition(
    question: str,
    history: list[dict[str, Any]],
) -> bool:
    """Handle additions such as "and usb-c block" after an inventory check."""

    normalized = normalize_text(question)

    if not recent_inventory_context(history):
        return False

    if len(normalized.split()) > 8:
        return False

    starts_like_addition = normalized.startswith(("and ", "also ", "what about "))

    return starts_like_addition and contains_known_inventory_item(question)


def get_last_assistant_message(
    history: list[dict[str, Any]],
) -> str:
    for message in reversed(history):
        if message.get("role") == "assistant":
            return normalize_text(
                str(
                    message.get(
                        "content",
                        "",
                    )
                )
            )

    return ""


def waiting_for_inventory_item(
    history: list[dict[str, Any]],
) -> bool:
    last_assistant = get_last_assistant_message(history)

    markers = (
        "which hardware item would you like me to check",
        "which item would you like me to check",
        "which one would you like me to check",
        "please name the item you want to borrow",
    )

    return any(marker in last_assistant for marker in markers)


def has_hardware_term(
    question: str,
) -> bool:
    normalized = normalize_text(question)

    # Use phrase boundaries rather than substring checks. In particular, the
    # inventory alias "block" must not match words such as "blocked" in a web
    # filtering/security question.
    return any(contains_phrase(normalized, term) for term in HARDWARE_TERMS)


def is_hardware_troubleshooting_request(
    question: str,
) -> bool:
    normalized = normalize_text(question)

    return any(phrase in normalized for phrase in TROUBLESHOOTING_PHRASES)


def is_inventory_list_request(
    question: str,
) -> bool:
    normalized = normalize_text(question)

    words = set(normalized.split())

    item_words = {
        "item",
        "items",
        "equipment",
        "hardware",
        "inventory",
        "loaner",
        "loaners",
    }

    availability_words = {
        "available",
        "availability",
        "borrow",
        "stock",
    }

    if words.intersection(item_words) and words.intersection(availability_words):
        return True

    phrases = (
        "what can i borrow",
        "what do you have available",
        "show available items",
        "list available items",
        "show inventory",
        "available equipment",
    )

    return any(phrase in normalized for phrase in phrases)


def is_possible_item_request(
    question: str,
    history: list[dict[str, Any]],
) -> bool:
    normalized = normalize_text(question)

    if not normalized:
        return False

    if is_hardware_troubleshooting_request(question):
        return False

    if waiting_for_inventory_item(history):
        return len(normalized.split()) <= 10

    if is_short_inventory_addition(question, history):
        return True

    has_request_language = any(
        phrase in normalized for phrase in POSSIBLE_ITEM_REQUEST_PHRASES
    )
    if not has_request_language or not has_hardware_term(question):
        return False

    # Generic phrases such as "I want" or "I need" are not enough to prove an
    # inventory lookup. Require the request to be compact and item-oriented so
    # "I want to see my notes on my MacBook" or "give me the bypass code" do
    # not hijack the live inventory router.
    if len(normalized.split()) > 9:
        return False

    task_markers = (
        "connect", "mirror", "mirroring", "install", "fix", "repair",
        "blocked", "bypass", "snapped", "stuck inside", "screen",
        "not working", "won't", "wont", "cannot", "can't", "cant",
    )
    if any(marker in normalized for marker in task_markers):
        return False

    return True


def is_inventory_request(
    question: str,
    history: list[dict[str, Any]],
) -> bool:
    normalized = normalize_text(question)

    if not normalized:
        return False

    explicit_loan_request = any(
        phrase in normalized
        for phrase in (
            "loaner",
            "can i borrow",
            "could i borrow",
            "may i borrow",
            "need a loaner",
            "need loaner",
        )
    )
    if is_hardware_troubleshooting_request(question) and not explicit_loan_request:
        return False

    if is_inventory_list_request(question):
        return True

    if waiting_for_inventory_item(history):
        return True

    if is_short_inventory_addition(question, history):
        return True

    if any(phrase in normalized for phrase in UNCONDITIONAL_INVENTORY_PHRASES):
        return True

    return has_hardware_term(question) and any(
        phrase in normalized for phrase in (HARDWARE_REQUIRED_INVENTORY_PHRASES)
    )


def fetch_inventory() -> InventoryPayload:
    """Fetch and validate live inventory without following redirects."""

    if not INVENTORY_API_URL:
        raise InventoryServiceError("INVENTORY_API_URL is not configured.")

    headers = {
        "Accept": "application/json",
    }

    if INVENTORY_API_TOKEN:
        headers["Authorization"] = f"Bearer {INVENTORY_API_TOKEN}"

    connect_timeout = min(
        5.0,
        INVENTORY_API_TIMEOUT_SECONDS,
    )

    try:
        with warnings.catch_warnings():
            if not INVENTORY_API_VERIFY_SSL:
                warnings.simplefilter(
                    "ignore",
                    InsecureRequestWarning,
                )

            response = requests.get(
                INVENTORY_API_URL,
                headers=headers,
                timeout=(
                    connect_timeout,
                    INVENTORY_API_TIMEOUT_SECONDS,
                ),
                verify=INVENTORY_API_VERIFY_SSL,
                allow_redirects=False,
            )

    except requests.Timeout as error:
        raise InventoryServiceError("The inventory API request timed out.") from error

    except requests.RequestException as error:
        raise InventoryServiceError(
            "The inventory API could not be reached."
        ) from error

    if 300 <= response.status_code < 400:
        raise InventoryServiceError(
            "The inventory API returned an unexpected redirect."
        )

    if response.status_code in {401, 403}:
        raise InventoryServiceError(
            "The inventory API rejected the configured credentials."
        )

    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        raise InventoryServiceError(
            "The inventory API returned an error response."
        ) from error

    if len(response.content) > 1_000_000:
        raise InventoryServiceError(
            "The inventory API response was unexpectedly large."
        )

    try:
        payload = InventoryPayload.model_validate(response.json())
    except (
        ValueError,
        ValidationError,
    ) as error:
        raise InventoryServiceError(
            "The inventory API returned invalid JSON data."
        ) from error

    seen_type_ids: set[int] = set()

    for item in payload.types:
        if item.typeId in seen_type_ids:
            raise InventoryServiceError(f"Duplicate inventory type ID: {item.typeId}.")

        seen_type_ids.add(item.typeId)

        if (
            item.availableCount > item.totalCount
            or item.loanedCount > item.totalCount
            or item.availableCount + item.loanedCount > item.totalCount
        ):
            raise InventoryServiceError(
                f"Invalid inventory counts for {item.typeName}."
            )

    return payload


def extract_requested_item(
    question: str,
) -> str:
    requested_item = normalize_text(question)

    for phrase in sorted(
        ITEM_QUERY_NOISE,
        key=len,
        reverse=True,
    ):
        requested_item = requested_item.replace(
            phrase,
            " ",
        )

    requested_item = re.sub(
        r"\s+",
        " ",
        requested_item,
    ).strip()

    words = [word for word in requested_item.split() if word not in ITEM_STOP_WORDS]

    return " ".join(words).strip()


def get_item_search_terms(
    item: InventoryItem,
) -> tuple[str, ...]:
    normalized_name = normalize_text(item.typeName)

    return (
        normalized_name,
        *ITEM_ALIASES.get(
            normalized_name,
            (),
        ),
    )


def score_item(
    requested_item: str,
    item: InventoryItem,
) -> float:
    scores: list[float] = []

    for search_term in get_item_search_terms(item):
        normalized_term = normalize_text(search_term)

        if not normalized_term:
            continue

        if requested_item == normalized_term:
            scores.append(120.0)
            continue

        if normalized_term in requested_item:
            coverage = len(normalized_term) / max(
                len(requested_item),
                1,
            )

            scores.append(100.0 + coverage * 10.0)

            continue

        if requested_item in normalized_term and len(requested_item) >= 4:
            coverage = len(requested_item) / max(
                len(normalized_term),
                1,
            )

            scores.append(92.0 + coverage * 8.0)

            continue

        scores.append(
            float(
                fuzz.WRatio(
                    requested_item,
                    normalized_term,
                )
            )
        )

    return max(
        scores,
        default=0.0,
    )


def match_inventory_item(
    question: str,
    items: list[InventoryItem],
) -> InventoryMatch:
    requested_item = extract_requested_item(question)

    if not requested_item:
        return InventoryMatch(item=None)

    scored_items = sorted(
        (
            (
                score_item(
                    requested_item,
                    item,
                ),
                item,
            )
            for item in items
        ),
        key=lambda pair: pair[0],
        reverse=True,
    )

    if not scored_items:
        return InventoryMatch(item=None)

    best_score, best_item = scored_items[0]

    if best_score < 82:
        return InventoryMatch(item=None)

    close_alternatives = [
        item.typeName
        for score, item in scored_items[1:5]
        if (score >= 82 and best_score - score <= 5)
    ]

    if close_alternatives:
        return InventoryMatch(
            item=None,
            alternatives=(
                best_item.typeName,
                *close_alternatives,
            ),
        )

    return InventoryMatch(item=best_item)


def format_inventory_answer(
    item: InventoryItem,
) -> str:
    if item.availableCount > 0:
        return (
            f"Current live availability for "
            f"**{item.typeName}**:\n\n"
            f"- **Available:** "
            f"{item.availableCount}\n\n"
            "You can visit the IT Helpdesk to "
            "request one. Availability may change "
            "before pickup."
        )

    if item.totalCount == 0:
        return (
            f"**{item.typeName}** is not currently "
            "stocked. Please contact the IT Helpdesk "
            "if you need an alternative item."
        )

    return (
        f"**{item.typeName}** is currently "
        "unavailable.\n\n"
        f"- **Available:** 0\n"
        f"- **Total:** "
        f"{item.totalCount}\n"
        f"- **Currently loaned:** "
        f"{item.loanedCount}\n\n"
        "Please check again later or contact the "
        "IT Helpdesk about alternatives."
    )


def format_available_inventory(
    items: list[InventoryItem],
) -> str:
    available_items = sorted(
        (item for item in items if item.availableCount > 0),
        key=lambda item: item.typeName.lower(),
    )

    if not available_items:
        return (
            "There are currently no loaner items "
            "available. Please contact the "
            "IT Helpdesk."
        )

    lines = [
        (f"- **{item.typeName}:** {item.availableCount} available")
        for item in available_items
    ]

    return (
        "These items are currently available:\n\n"
        + "\n".join(lines)
        + "\n\nAvailability may change before pickup."
    )


def route_inventory_question(
    question: str,
    history: list[dict[str, Any]],
) -> InventoryDecision:
    normalized = normalize_text(question)

    cart_reservation = (
        "cart" in normalized
        and any(term in normalized for term in ("laptop", "chromebook", "computer"))
        and any(
            phrase in normalized
            for phrase in (
                "reserve", "hold", "borrow", "need a cart", "need the cart",
                "take the cart", "field trip", "for tomorrow", "for my class",
            )
        )
    )
    if cart_reservation:
        return InventoryDecision(
            handled=True,
            answer=(
                "Live inventory tracks individual loaner items, but Altitude cannot confirm or "
                "reserve an entire cart for a class or field trip. Contact the IT Helpdesk with "
                "the date, number of devices, and event/class purpose so availability can be confirmed."
            ),
        )

    reservation_request = any(
        phrase in normalized
        for phrase in (
            "reserve ",
            "hold ",
            "save a macbook for me",
            "save a chromebook for me",
            "put aside",
        )
    ) and any(term in normalized for term in ("macbook", "chromebook", "laptop", "loaner", "ipad"))

    if reservation_request:
        return InventoryDecision(
            handled=True,
            answer=(
                "I can check live inventory, but I cannot reserve or hold devices for a future "
                "date. Please contact the IT Helpdesk with the quantity, date, and class/event "
                "purpose so the request can be confirmed. Availability may change before pickup."
            ),
        )

    # Resolve short availability follow-ups from the most recently named item.
    effective_question = question
    if normalized in {
        "how many are available",
        "how many are left",
        "are any available",
        "what about availability",
    }:
        recent_subject = recent_inventory_subject(history, question)
        if recent_subject:
            effective_question = f"How many {recent_subject} are available?"
            normalized = normalize_text(effective_question)

    explicit_loan_request = any(
        phrase in normalized
        for phrase in ("loaner", "can i borrow", "could i borrow", "may i borrow")
    )
    if is_hardware_troubleshooting_request(effective_question) and not explicit_loan_request:
        return InventoryDecision(handled=False)

    explicit_request = is_inventory_request(
        effective_question,
        history,
    )

    possible_request = is_possible_item_request(
        effective_question,
        history,
    )

    if not explicit_request and not possible_request:
        return InventoryDecision(handled=False)

    try:
        payload = fetch_inventory()

    except InventoryServiceError as error:
        print(f"Inventory lookup failed: {type(error).__name__}: {error}")

        requested_items = requested_canonical_names(effective_question)
        if requested_items:
            item_text = ", ".join(requested_items)
            return InventoryDecision(
                handled=True,
                answer=(
                    f"I cannot check live **{item_text}** availability right now. "
                    "Please contact the IT Helpdesk for the current inventory status "
                    "before borrowing or picking up a loaner item."
                ),
            )

        if any(term in normalized for term in ("laptop", "computer", "loaner", "loner")):
            return InventoryDecision(
                handled=True,
                answer=(
                    "I cannot check live **loaner laptop** availability right now. "
                    "Please contact the IT Helpdesk for the current inventory status, "
                    "especially if you need a loaner urgently for a class or test."
                ),
            )

        return InventoryDecision(
            handled=True,
            answer=(
                "I cannot check live hardware availability right now. Please contact "
                "the IT Helpdesk for the current inventory status."
            ),
        )

    if not payload.types:
        return InventoryDecision(
            handled=True,
            answer=(
                "No hardware types are currently "
                "listed in the inventory system. "
                "Please contact the IT Helpdesk."
            ),
        )

    canonical_names = requested_canonical_names(effective_question)

    # A named item must take precedence over broad phrases such as
    # "check the live inventory". Otherwise a Chromebook question can
    # incorrectly return every available item in the API payload.
    if not canonical_names and is_inventory_list_request(effective_question):
        return InventoryDecision(
            handled=True,
            answer=format_available_inventory(payload.types),
        )

    if len(canonical_names) > 1:
        answers: list[str] = []
        for canonical_name in canonical_names:
            item = find_item_for_canonical(canonical_name, payload.types)
            answers.append(
                format_inventory_answer(item)
                if item is not None
                else format_missing_inventory_item(canonical_name)
            )
        return InventoryDecision(handled=True, answer="\n\n".join(answers))

    match = match_inventory_item(
        effective_question,
        payload.types,
    )

    if match.alternatives:
        options = "\n".join(f"- **{name}**" for name in match.alternatives)

        return InventoryDecision(
            handled=True,
            answer=(
                "I found more than one possible "
                "inventory item. Which one would "
                "you like me to check?\n\n"
                f"{options}"
            ),
        )

    if match.item is None:
        if canonical_names:
            return InventoryDecision(
                handled=True,
                answer=format_missing_inventory_item(canonical_names[0]),
            )

        generic_hardware = any(
            term in normalized
            for term in ("laptop", "computer", "charger", "tablet")
        )
        if generic_hardware:
            matching_types = [
                item.typeName
                for item in payload.types
                if any(
                    term in normalize_text(item.typeName)
                    for term in ("laptop", "macbook", "chromebook", "charger", "ipad")
                )
            ]
            if matching_types:
                options = "\n".join(f"- **{name}**" for name in matching_types[:8])
                return InventoryDecision(
                    handled=True,
                    answer=(
                        "Which inventory item would you like me to check?\n\n"
                        f"{options}"
                    ),
                )

            return InventoryDecision(
                handled=True,
                answer=(
                    "No matching laptop, computer, charger, or tablet is listed in "
                    "the current live inventory response. Please contact the IT "
                    "Helpdesk to confirm availability."
                ),
            )

        examples = "\n".join(f"- **{item.typeName}**" for item in payload.types[:8])

        return InventoryDecision(
            handled=True,
            answer=(
                "I could not identify the requested inventory item. Which hardware "
                "item would you like me to check?"
                + (f"\n\nExamples:\n{examples}" if examples else "")
            ),
        )

    return InventoryDecision(
        handled=True,
        answer=format_inventory_answer(match.item),
    )
