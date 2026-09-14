from __future__ import annotations

import os
import re
from dataclasses import dataclass, replace
from html import unescape
from html.parser import HTMLParser
from typing import Any, Iterable, Mapping
from urllib.parse import urljoin, urlparse

import requests
from dotenv import load_dotenv


load_dotenv()

DEFAULT_BASE_URL = "http://192.168.0.201:8080/sjk-ticketingsystem/"
DEFAULT_LOGIN_PATH = ""
DEFAULT_CREATE_PATH = "create_ticket/"
DEFAULT_DASHBOARD_PATH = "faculty/dashboard/"
DEFAULT_DETAIL_URL_TEMPLATE = "faculty/ticket/{ticket_id}/edit/"
DEFAULT_TIMEOUT_SECONDS = 12.0
DEFAULT_DETAIL_SCAN_START_ID = 1
DEFAULT_DETAIL_SCAN_END_ID = 300

ALLOWED_EMAIL_DOMAINS = frozenset({"sjkeagles.com", "sjkschool.org"})
EMAIL_PATTERN = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@([A-Z0-9.-]+)$",
    re.IGNORECASE,
)

CATEGORY_VALUES = frozenset(
    {
        "Wifi-Network",
        "AudioVideo",
        "GoogleApps",
        "OnSJK",
        "Reset_Password",
        "DeviceHardwareIssue",
        "AirplayScreenMirror",
        "Other",
    }
)
DEVICE_VALUES = frozenset(
    {"", "Smartboard", "TV", "Laptop", "Tablet", "Printer", "Other"}
)
ROLE_VALUES = frozenset({"", "faculty", "staff", "supply_teacher"})
PRIORITY_VALUES = frozenset({"Low", "Medium", "High"})


class TicketingClientError(RuntimeError):
    """Raised when the ticketing website cannot be used safely."""


def _http_origin(url: str, *, field_name: str) -> tuple[str, str, int]:
    """Validate an HTTP(S) URL and return its normalized origin."""
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError as error:
        raise TicketingClientError(f"{field_name} is not a valid URL") from error

    scheme = parsed.scheme.casefold()
    hostname = (parsed.hostname or "").casefold()
    if scheme not in {"http", "https"} or not hostname:
        raise TicketingClientError(
            f"{field_name} must be a complete http:// or https:// URL"
        )

    if parsed.username is not None or parsed.password is not None:
        raise TicketingClientError(
            f"{field_name} must not contain credentials in the URL"
        )

    effective_port = port or (443 if scheme == "https" else 80)
    return scheme, hostname, effective_port


def _require_same_ticketing_origin(
    candidate_url: str,
    trusted_base_url: str,
    *,
    field_name: str,
) -> None:
    """Prevent forms or redirects from sending data to another website."""
    trusted_origin = _http_origin(
        trusted_base_url,
        field_name="TICKETING_BASE_URL",
    )
    candidate_origin = _http_origin(candidate_url, field_name=field_name)
    if candidate_origin != trusted_origin:
        raise TicketingClientError(
            f"{field_name} must use the same origin as TICKETING_BASE_URL"
        )


@dataclass(frozen=True)
class TicketingConfig:
    """Runtime configuration for the Django ticketing website."""

    base_url: str
    login_url: str
    create_ticket_url: str
    dashboard_url: str
    detail_url_template: str
    username: str
    password: str
    timeout_seconds: float

    @classmethod
    def from_environment(cls) -> "TicketingConfig":
        base_url = os.getenv("TICKETING_BASE_URL", DEFAULT_BASE_URL).strip()
        if not base_url.endswith("/"):
            base_url += "/"

        login_value = os.getenv("TICKETING_LOGIN_URL", "").strip()
        create_value = os.getenv("TICKETING_CREATE_URL", "").strip()
        dashboard_value = os.getenv("TICKETING_DASHBOARD_URL", "").strip()
        detail_template_value = os.getenv("TICKETING_DETAIL_URL_TEMPLATE", "").strip()

        login_url = login_value or urljoin(base_url, DEFAULT_LOGIN_PATH)
        create_ticket_url = create_value or urljoin(
            base_url,
            DEFAULT_CREATE_PATH,
        )
        dashboard_url = dashboard_value or urljoin(
            base_url,
            DEFAULT_DASHBOARD_PATH,
        )

        detail_url_template = detail_template_value or DEFAULT_DETAIL_URL_TEMPLATE
        username = os.getenv("TICKETING_USERNAME", "").strip()
        password = os.getenv("TICKETING_PASSWORD", "")

        try:
            timeout_seconds = float(
                os.getenv(
                    "TICKETING_TIMEOUT_SECONDS",
                    str(DEFAULT_TIMEOUT_SECONDS),
                )
            )
        except ValueError:
            timeout_seconds = DEFAULT_TIMEOUT_SECONDS

        return cls(
            base_url=base_url,
            login_url=login_url,
            create_ticket_url=create_ticket_url,
            dashboard_url=dashboard_url,
            detail_url_template=detail_url_template,
            username=username,
            password=password,
            timeout_seconds=max(3.0, min(timeout_seconds, 60.0)),
        )

    def validate(self) -> None:
        _http_origin(self.base_url, field_name="TICKETING_BASE_URL")
        for field_name, url in (
            ("TICKETING_LOGIN_URL", self.login_url),
            ("TICKETING_CREATE_URL", self.create_ticket_url),
            ("TICKETING_DASHBOARD_URL", self.dashboard_url),
        ):
            _require_same_ticketing_origin(
                url,
                self.base_url,
                field_name=field_name,
            )

        if "{ticket_id}" not in self.detail_url_template:
            raise TicketingClientError(
                "TICKETING_DETAIL_URL_TEMPLATE must include {ticket_id}"
            )
        if re.match(r"^https?://", self.detail_url_template, flags=re.IGNORECASE):
            preview_detail_url = self.detail_url_template.replace("{ticket_id}", "1")
        else:
            preview_detail_url = urljoin(self.base_url, self.detail_url_template.replace("{ticket_id}", "1"))
        _require_same_ticketing_origin(
            preview_detail_url,
            self.base_url,
            field_name="TICKETING_DETAIL_URL_TEMPLATE",
        )

        if not self.username or not self.password:
            raise TicketingClientError(
                "Ticketing credentials are not configured. Add "
                "TICKETING_USERNAME and TICKETING_PASSWORD to .env."
            )


@dataclass(frozen=True)
class TicketPayload:
    """Validated data submitted to the Django create-ticket form.

    Altitude generates only ``title``, ``category``, and ``priority``.
    ``contact_email`` is supplied by the requester. Every other field is
    optional and is included only when the user chooses to provide it.
    """

    title: str
    category: str
    priority: str
    contact_email: str
    location: str = ""
    description: str = ""
    role: str = ""
    device: str = ""
    custom_device: str = ""
    custom_category: str = ""
    bestwaytocontact: str = "email"
    besttimetocontact: str = ""
    image_url: str = ""
    status: str = ""
    assignedto: str = ""

    def validate(self) -> None:
        if not self.title.strip():
            raise ValueError("Ticket title cannot be empty")

        if len(self.title.strip()) > 255:
            raise ValueError("Ticket title must be 255 characters or fewer")

        if self.category not in CATEGORY_VALUES:
            raise ValueError("Unsupported ticket category")

        if self.category == "Other":
            custom_words = [
                word
                for word in self.custom_category.strip().split()
                if word
            ]
            if not custom_words:
                raise ValueError(
                    "Enter a short custom category when Category is Other"
                )
            if len(custom_words) > 3:
                raise ValueError(
                    "Custom category must be between 1 and 3 words"
                )

        if self.priority not in PRIORITY_VALUES:
            raise ValueError("Unsupported ticket priority")

        if self.device not in DEVICE_VALUES:
            raise ValueError("Unsupported ticket device")

        if self.role not in ROLE_VALUES:
            raise ValueError("Unsupported requester role")

        if self.bestwaytocontact not in {"", "email", "inperson"}:
            raise ValueError("Unsupported contact preference")

        validate_school_email(self.contact_email)

    def as_form_data(self) -> dict[str, str]:
        """Return all supported form values.

        The client later filters this mapping against the fields that actually
        exist in the live Django form. This keeps the integration compatible if
        fields such as ``status`` or ``assignedto`` are not exposed publicly.
        """
        self.validate()
        form_data = {
            "contact_email": self.contact_email.strip().lower(),
            "title": self.title.strip(),
            "category": self.category,
            "priority": self.priority,
            "bestwaytocontact": self.bestwaytocontact,
        }
        optional_values = {
            "location": self.location.strip(),
            "description": self.description.strip(),
            "role": self.role,
            "device": self.device,
            "custom_device": self.custom_device.strip(),
            "custom_category": self.custom_category.strip(),
            "besttimetocontact": self.besttimetocontact.strip(),
            "image_url": self.image_url.strip(),
            "status": self.status.strip(),
            "assignedto": self.assignedto.strip(),
        }
        form_data.update(
            {
                name: value
                for name, value in optional_values.items()
                if value
            }
        )
        return form_data


def payload_with_altitude_reference(
    payload: TicketPayload,
    altitude_reference: str,
) -> TicketPayload:
    """Return a TicketPayload that embeds the Altitude reference as text.

    This does not require any ticketing-system schema change. The reference is
    stored in normal title/description fields so the IT team can search for it.
    """
    reference = " ".join(str(altitude_reference).upper().split()).strip()
    if not reference:
        return payload

    original_title = payload.title.strip()
    prefix = f"[{reference}] "
    title = original_title
    if not original_title.upper().startswith(prefix.upper()):
        max_original = max(20, 255 - len(prefix))
        title = prefix + original_title[:max_original].rstrip()

    description = payload.description.strip()
    reference_block = (
        f"Altitude Reference: {reference}\n"
        f"Requester Email: {payload.contact_email.strip().lower()}"
    )
    if description:
        description = reference_block + "\n\n" + description
    else:
        description = reference_block

    return replace(
        payload,
        title=title,
        description=description[:4000],
    )


@dataclass(frozen=True)
class TicketSubmissionResult:
    """Result returned after the remote form accepted a ticket."""

    success: bool
    external_ticket_id: str | None
    final_url: str
    message: str
    remote_ticket_url: str | None = None


@dataclass
class _ParsedForm:
    action: str
    method: str
    fields: list[dict[str, str]]

    def hidden_values(self) -> dict[str, str]:
        return {
            field["name"]: field.get("value", "")
            for field in self.fields
            if field.get("name") and field.get("type") == "hidden"
        }

    def field_names(self) -> set[str]:
        return {
            field["name"]
            for field in self.fields
            if field.get("name")
        }


class _FormParser(HTMLParser):
    """Minimal HTML form parser with no third-party dependency."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: list[_ParsedForm] = []
        self._current: _ParsedForm | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attribute_map = {
            key.lower(): (value or "")
            for key, value in attrs
        }

        if tag.lower() == "form":
            self._current = _ParsedForm(
                action=attribute_map.get("action", ""),
                method=attribute_map.get("method", "get").lower(),
                fields=[],
            )
            return

        if self._current is None:
            return

        if tag.lower() == "input":
            self._current.fields.append(
                {
                    "name": attribute_map.get("name", ""),
                    "type": attribute_map.get("type", "text").lower(),
                    "value": attribute_map.get("value", ""),
                }
            )
        elif tag.lower() in {"select", "textarea"}:
            self._current.fields.append(
                {
                    "name": attribute_map.get("name", ""),
                    "type": tag.lower(),
                    "value": "",
                }
            )

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "form" and self._current is not None:
            self.forms.append(self._current)
            self._current = None


def _parse_forms(html: str) -> list[_ParsedForm]:
    parser = _FormParser()
    parser.feed(html)
    parser.close()
    return parser.forms


def parse_email_address(email: str) -> tuple[str, str]:
    """Return a normalized email address and domain.

    Common copy/paste whitespace and zero-width characters are removed before
    validation so a valid school address is not rejected because of hidden
    browser or clipboard characters.
    """
    normalized = str(email)
    normalized = normalized.replace("\u200b", "").replace("\ufeff", "")
    normalized = re.sub(r"\s+", "", normalized).strip().lower()
    match = EMAIL_PATTERN.fullmatch(normalized)

    if match is None:
        raise ValueError("Enter a valid email address")

    domain = match.group(1).lower().rstrip(".")
    return normalized, domain


def is_authorized_school_email(email: str) -> bool:
    """Return True only for a syntactically valid authorized SJK address."""
    try:
        _, domain = parse_email_address(email)
    except ValueError:
        return False

    return domain in ALLOWED_EMAIL_DOMAINS


def validate_school_email(email: str) -> str:
    """Validate and normalize an authorized SJK email address."""
    normalized, domain = parse_email_address(email)

    if domain not in ALLOWED_EMAIL_DOMAINS:
        allowed = " or ".join(
            f"@{item}" for item in sorted(ALLOWED_EMAIL_DOMAINS)
        )
        raise ValueError(f"Email must use {allowed}")

    return normalized


def _find_login_form(forms: list[_ParsedForm]) -> _ParsedForm:
    for form in forms:
        if any(field.get("type") == "password" for field in form.fields):
            return form

    raise TicketingClientError("The ticketing login form could not be found")


def _find_ticket_form(forms: list[_ParsedForm]) -> _ParsedForm:
    for form in forms:
        names = form.field_names()
        if {"title", "category", "priority"}.issubset(names):
            return form

    raise TicketingClientError("The create-ticket form could not be found")


def _find_field_name(
    form: _ParsedForm,
    *,
    field_type: str,
    preferred_names: tuple[str, ...],
) -> str:
    names = form.field_names()

    for name in preferred_names:
        if name in names:
            return name

    for field in form.fields:
        if field.get("type") == field_type and field.get("name"):
            return field["name"]

    raise TicketingClientError(
        f"The login {field_type} field could not be identified"
    )


def _extract_external_ticket_id(response: requests.Response) -> str | None:
    candidates = (
        re.search(r"/tickets?/(?:detail/)?(\d+)", response.url, re.IGNORECASE),
        re.search(r"ticket\s*#?\s*(\d+)", response.text, re.IGNORECASE),
        re.search(r"ticket[_-]?id[\"'=:\s]+(\d+)", response.text, re.IGNORECASE),
    )

    for candidate in candidates:
        if candidate is not None:
            return candidate.group(1)

    return None


def _safe_form_errors(html: str) -> str | None:
    if "errorlist" not in html.lower():
        return None

    clean = re.sub(r"<[^>]+>", " ", html)
    clean = re.sub(r"\s+", " ", clean).strip()
    match = re.search(r"errorlist(.{0,500})", clean, re.IGNORECASE)
    return match.group(1).strip() if match else "The form returned validation errors"


def _page_text(html: str) -> str:
    """Return normalized visible text for safe success verification."""
    without_scripts = re.sub(
        r"<(script|style)\b[^>]*>.*?</\1>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    clean = re.sub(r"<[^>]+>", " ", without_scripts)
    clean = unescape(clean)
    return " ".join(clean.split()).strip().lower()


def _ticket_title_count(html: str, title: str) -> int:
    """Count exact normalized title occurrences on a dashboard page."""
    normalized_title = " ".join(title.split()).strip().lower()
    if not normalized_title:
        return 0
    return _page_text(html).count(normalized_title)


def _dashboard_confirms_new_ticket(
    *,
    before_html: str,
    after_html: str,
    payload: TicketPayload,
) -> bool:
    """Confirm a newly-visible ticket when the Django view stays on the form."""
    before_count = _ticket_title_count(before_html, payload.title)
    after_count = _ticket_title_count(after_html, payload.title)

    if after_count > before_count:
        return True

    # Some dashboards collapse or truncate duplicate titles. In that case,
    # require both the title and requester email to be visible after submit.
    after_text = _page_text(after_html)
    title_text = " ".join(payload.title.split()).strip().lower()
    email_text = payload.contact_email.strip().lower()
    return bool(
        title_text
        and title_text in after_text
        and email_text
        and email_text in after_text
        and title_text not in _page_text(before_html)
    )


class DjangoTicketingClient:
    """Authenticate to the internal Django site and submit ticket forms."""

    def __init__(self, config: TicketingConfig | None = None) -> None:
        self.config = config or TicketingConfig.from_environment()
        self.config.validate()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Altitude-IT-Assistant/1.0",
                "Accept": "text/html,application/xhtml+xml",
            }
        )

    def _request(
        self,
        method: str,
        url: str,
        *,
        data: dict[str, str] | None = None,
        referer: str | None = None,
    ) -> requests.Response:
        """Send one request while following only same-origin redirects."""
        current_method = method.upper()
        current_url = url
        current_data = data
        current_referer = referer

        for _ in range(6):
            _require_same_ticketing_origin(
                current_url,
                self.config.base_url,
                field_name="Ticketing request URL",
            )
            if current_referer:
                _require_same_ticketing_origin(
                    current_referer,
                    self.config.base_url,
                    field_name="Ticketing referer",
                )

            headers = (
                {"Referer": current_referer}
                if current_referer
                else None
            )
            try:
                response = self.session.request(
                    current_method,
                    current_url,
                    data=current_data,
                    headers=headers,
                    timeout=self.config.timeout_seconds,
                    allow_redirects=False,
                )
            except requests.RequestException as error:
                raise TicketingClientError(
                    "The ticketing website could not be reached"
                ) from error

            if response.status_code not in {301, 302, 303, 307, 308}:
                try:
                    response.raise_for_status()
                except requests.RequestException as error:
                    raise TicketingClientError(
                        "The ticketing website did not accept the request"
                    ) from error
                return response

            location = response.headers.get("Location", "").strip()
            if not location:
                raise TicketingClientError(
                    "The ticketing website returned an invalid redirect"
                )

            next_url = urljoin(response.url, location)
            _require_same_ticketing_origin(
                next_url,
                self.config.base_url,
                field_name="Ticketing redirect URL",
            )

            current_referer = response.url
            if response.status_code == 303 or (
                response.status_code in {301, 302}
                and current_method == "POST"
            ):
                current_method = "GET"
                current_data = None
            current_url = next_url

        raise TicketingClientError(
            "The ticketing website redirected too many times"
        )

    def _get(self, url: str) -> requests.Response:
        return self._request("GET", url)

    def _post(
        self,
        url: str,
        *,
        data: dict[str, str],
        referer: str,
    ) -> requests.Response:
        return self._request(
            "POST",
            url,
            data=data,
            referer=referer,
        )

    def login(self) -> None:
        login_page = self._get(self.config.login_url)
        login_form = _find_login_form(_parse_forms(login_page.text))

        username_field = _find_field_name(
            login_form,
            field_type="text",
            preferred_names=("username", "email", "user", "login"),
        )
        password_field = _find_field_name(
            login_form,
            field_type="password",
            preferred_names=("password", "passwd"),
        )

        form_data = login_form.hidden_values()
        form_data[username_field] = self.config.username
        form_data[password_field] = self.config.password

        action_url = urljoin(login_page.url, login_form.action or login_page.url)
        login_response = self._post(
            action_url,
            data=form_data,
            referer=login_page.url,
        )

        # A successful login must make the protected create form available.
        create_page = self._get(self.config.create_ticket_url)
        try:
            _find_ticket_form(_parse_forms(create_page.text))
        except TicketingClientError as error:
            if any(
                field.get("type") == "password"
                for form in _parse_forms(login_response.text)
                for field in form.fields
            ):
                raise TicketingClientError(
                    "The ticketing username or password was rejected"
                ) from error

            raise TicketingClientError(
                "Login completed, but the create-ticket page is not available "
                "to this account"
            ) from error

    def submit_ticket(self, payload: TicketPayload) -> TicketSubmissionResult:
        payload.validate()
        self.login()

        try:
            dashboard_before = self._get(self.config.dashboard_url)
            dashboard_before_html = dashboard_before.text
        except TicketingClientError:
            dashboard_before_html = ""

        create_page = self._get(self.config.create_ticket_url)
        ticket_form = _find_ticket_form(_parse_forms(create_page.text))
        form_data = ticket_form.hidden_values()
        available_fields = ticket_form.field_names()
        form_data.update(
            {
                name: value
                for name, value in payload.as_form_data().items()
                if name in available_fields
            }
        )

        action_url = urljoin(
            create_page.url,
            ticket_form.action or create_page.url,
        )
        response = self._post(
            action_url,
            data=form_data,
            referer=create_page.url,
        )

        forms_after_submit = _parse_forms(response.text)
        if any(
            any(field.get("type") == "password" for field in form.fields)
            for form in forms_after_submit
        ):
            raise TicketingClientError(
                "The ticketing session expired before the ticket was created"
            )

        form_error = _safe_form_errors(response.text)
        if form_error:
            raise TicketingClientError(
                f"The ticketing form rejected the ticket: {form_error}"
            )

        still_on_create_form = False
        try:
            _find_ticket_form(forms_after_submit)
            still_on_create_form = True
        except TicketingClientError:
            pass

        success_text = response.text.lower()
        confirmed_by_text = any(
            phrase in success_text
            for phrase in (
                "ticket created",
                "created successfully",
                "successfully created",
                "ticket submitted",
                "submitted successfully",
                "successfully submitted",
                "your ticket has been created",
            )
        )
        redirected_away = response.url.rstrip("/") != action_url.rstrip("/")
        confirmed_by_dashboard = False
        dashboard_after: requests.Response | None = None

        if still_on_create_form and not confirmed_by_text and not redirected_away:
            try:
                dashboard_after = self._get(self.config.dashboard_url)
                confirmed_by_dashboard = _dashboard_confirms_new_ticket(
                    before_html=dashboard_before_html,
                    after_html=dashboard_after.text,
                    payload=payload,
                )
            except TicketingClientError:
                confirmed_by_dashboard = False

        if (
            still_on_create_form
            and not confirmed_by_text
            and not redirected_away
            and not confirmed_by_dashboard
        ):
            raise TicketingClientError(
                "The ticketing website returned the create form again and the "
                "new ticket was not found on the dashboard. Check required "
                "fields and the Django form validation rules."
            )

        dashboard_ticket_id: str | None = None
        dashboard_ticket_url: str | None = None
        try:
            if dashboard_after is None:
                dashboard_after = self._get(self.config.dashboard_url)

            altitude_match = re.search(
                r"\bALT\s*-?\s*(20\d{2})\s*-?\s*(\d{1,8})\b",
                f"{payload.title}\n{payload.description}",
                flags=re.IGNORECASE,
            )
            altitude_reference = None
            if altitude_match is not None:
                altitude_reference = (
                    f"ALT-{altitude_match.group(1)}-"
                    f"{int(altitude_match.group(2)):06d}"
                )

            blocks = _dashboard_blocks(
                dashboard_after.text,
                page_url=dashboard_after.url,
            )
            matched_block, _ = _best_ticket_block(
                {
                    "altitude_reference": altitude_reference or "",
                    "external_ticket_id": "",
                    "title": payload.title,
                    "contact_email": payload.contact_email,
                },
                blocks,
            )
            if matched_block is not None:
                links = [
                    str(item)
                    for item in matched_block.get("links", [])
                    if str(item).strip()
                ]
                dashboard_ticket_id = str(
                    matched_block.get("external_ticket_id") or ""
                ).strip() or None
                if dashboard_ticket_id is None:
                    dashboard_ticket_id = _external_id_from_text_or_links(
                        str(matched_block.get("text") or ""),
                        links,
                    )
                dashboard_ticket_url = next(
                    (
                        link
                        for link in links
                        if re.search(
                            r"ticket|detail|view|update|edit",
                            link,
                            flags=re.IGNORECASE,
                        )
                    ),
                    links[0] if links else None,
                )
                if dashboard_ticket_url is None and dashboard_ticket_id:
                    configured_url = self.config.detail_url_template.replace(
                        "{ticket_id}",
                        dashboard_ticket_id,
                    )
                    dashboard_ticket_url = (
                        configured_url
                        if re.match(
                            r"^https?://",
                            configured_url,
                            flags=re.IGNORECASE,
                        )
                        else urljoin(self.config.base_url, configured_url)
                    )
        except Exception:
            # Ticket creation has already been accepted. If the dashboard lookup
            # cannot determine the real Django ticket ID, still return success
            # and allow later status sync to retry.
            dashboard_ticket_id = None
            dashboard_ticket_url = None

        external_id = dashboard_ticket_id or _extract_external_ticket_id(response)
        if external_id is None and dashboard_after is not None:
            external_id = _extract_external_ticket_id(dashboard_after)

        return TicketSubmissionResult(
            success=True,
            external_ticket_id=external_id,
            final_url=dashboard_ticket_url or response.url,
            message=(
                f"Ticket {external_id} was created"
                if external_id
                else "The ticket was created successfully"
            ),
            remote_ticket_url=dashboard_ticket_url,
        )



REMOTE_STATUS_PATTERNS: tuple[tuple[str, str], ...] = (
    ("Resolved", r"\b(?:resolved|completed|complete)\b"),
    ("Closed", r"\bclosed\b"),
    ("In Progress", r"\b(?:in[ -]?progress|working|assigned|processing)\b"),
    ("Open", r"\b(?:open|pending|awaiting|new)\b"),
)


@dataclass(frozen=True)
class RemoteTicketStatus:
    """One ticket status matched from the authenticated Django dashboard."""

    local_ticket_id: int
    status: str
    external_ticket_id: str | None
    remote_ticket_url: str | None
    matched_by: str
    resolution_comment: str | None = None


def _canonical_remote_status(text: str) -> str | None:
    """Return a stable status label from dashboard or detail-page text."""
    normalized = " ".join(str(text).split()).strip().lower()
    if not normalized:
        return None

    for label, pattern in REMOTE_STATUS_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            return label

    return None


def _canonical_status_value(value: str) -> str | None:
    """Normalize one raw status value/label from Django HTML."""
    cleaned = " ".join(unescape(str(value or "")).split()).strip()
    if not cleaned:
        return None

    normalized = cleaned.replace("_", " ").replace("-", " ").casefold()
    mapping = {
        "open": "Open",
        "new": "Open",
        "pending": "Open",
        "in progress": "In Progress",
        "assigned": "In Progress",
        "working": "In Progress",
        "resolved": "Resolved",
        "complete": "Resolved",
        "completed": "Resolved",
        "closed": "Closed",
    }
    return mapping.get(normalized)


def _extract_detail_page_status(html: str) -> str | None:
    """Extract the selected status from the Django ticket edit page.

    The faculty edit page renders all statuses inside a select box, so scanning
    the full page text can incorrectly return Open just because Open is the
    first option. Prefer the selected option from ``name="status"`` and only
    then fall back to plain text matching.
    """
    select_match = re.search(
        r"<select\b(?=[^>]*\bname\s*=\s*(['\"])status\1)[^>]*>(?P<body>.*?)</select>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if select_match is not None:
        select_body = select_match.group("body")
        for option_match in re.finditer(
            r"<option\b(?P<attrs>[^>]*)>(?P<label>.*?)</option>",
            select_body,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            attrs = option_match.group("attrs")
            if not re.search(r"\bselected\b", attrs, flags=re.IGNORECASE):
                continue

            value_match = re.search(
                r"\bvalue\s*=\s*(['\"])(?P<value>.*?)\1",
                attrs,
                flags=re.IGNORECASE | re.DOTALL,
            )
            raw_value = (
                value_match.group("value")
                if value_match is not None
                else _html_fragment_text(option_match.group("label"))
            )
            return _canonical_status_value(raw_value) or _canonical_status_value(
                _html_fragment_text(option_match.group("label"))
            )

    # Some templates render status as a checked radio input.
    for input_match in re.finditer(
        r"<input\b(?=[^>]*\bname\s*=\s*(['\"])status\1)(?=[^>]*\bchecked\b)(?P<attrs>[^>]*)>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        attrs = input_match.group("attrs")
        value_match = re.search(
            r"\bvalue\s*=\s*(['\"])(?P<value>.*?)\1",
            attrs,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if value_match is not None:
            status = _canonical_status_value(value_match.group("value"))
            if status:
                return status

    return _canonical_remote_status(_page_text(html))



def _clean_remote_comment(value: str) -> str | None:
    """Return a safe, short ticket-resolution comment for end users."""
    text = unescape(str(value or ""))
    text = re.sub(r"\s+", " ", text).strip(" :-\t\r\n")
    if not text:
        return None

    lowered = text.casefold()
    blocked_fragments = (
        "csrf",
        "altitude reference",
        "requester email",
        "password",
        "token",
        "api key",
        "secret",
        "submit",
        "save note",
        "add note",
        "new note",
    )
    if any(fragment in lowered for fragment in blocked_fragments):
        return None

    # Avoid returning full pages or ticket descriptions by mistake.
    if len(text) > 700:
        text = text[:700].rsplit(" ", 1)[0].rstrip() + "…"
    return text


def _html_fragment_text(html: str) -> str:
    """Convert a small HTML fragment to readable text."""
    without_scripts = re.sub(
        r"<(script|style)\b[^>]*>.*?</\1>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    separated = re.sub(
        r"</(?:tr|div|p|li|section|article|label|dt|dd|td|th|h1|h2|h3|h4|h5|span)>\s*",
        "\n",
        without_scripts,
        flags=re.IGNORECASE,
    )
    separated = re.sub(r"<br\s*/?>", "\n", separated, flags=re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", separated)
    clean = unescape(clean)
    lines = [" ".join(line.split()).strip() for line in clean.splitlines()]
    return "\n".join(line for line in lines if line)


def _html_to_labeled_text(html: str) -> str:
    """Convert common ticket-detail HTML into readable labeled lines."""
    return _html_fragment_text(html)


def _extract_named_form_values(html: str) -> list[str]:
    """Extract stored comment-like textarea/input values from a ticket page."""
    values: list[str] = []
    name_pattern = r"(?:comment|comments|resolution|resolved|close|closed|closure|note|notes|remark|remarks|content)"

    for match in re.finditer(
        rf"<textarea\b(?=[^>]*\bname\s*=\s*(['\"])[^'\"]*{name_pattern}[^'\"]*\1)[^>]*>(.*?)</textarea>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        value = _clean_remote_comment(match.group(2))
        if value:
            values.append(value)

    for match in re.finditer(
        rf"<input\b(?=[^>]*\bname\s*=\s*(['\"])[^'\"]*{name_pattern}[^'\"]*\1)[^>]*\bvalue\s*=\s*(['\"])(.*?)\2",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        value = _clean_remote_comment(match.group(3))
        if value:
            values.append(value)

    return values


def _note_content_from_text(text: str) -> str | None:
    """Strip Django Note metadata from one rendered note block."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None

    # Drop common headings and metadata generated by Note.__str__ or templates.
    filtered: list[str] = []
    metadata_patterns = (
        r"^notes?$",
        r"^comments?$",
        r"^ticket notes?$",
        r"^resolution comments?$",
        r"^add note$",
        r"^new note$",
        r"^save$",
        r"^submit$",
        r"^created at$",
        r"^author$",
        r"^content$",
        r"^note by .+ on \d{4}-\d{2}-\d{2}(?: \d{1,2}:\d{2})?$",
        r"^by .+ on \d{4}-\d{2}-\d{2}(?: \d{1,2}:\d{2})?$",
        r"^\d{4}-\d{2}-\d{2}(?: \d{1,2}:\d{2})?$",
        r"^.+\s+\d{4}-\d{2}-\d{2}(?: \d{1,2}:\d{2})?$",
    )
    for line in lines:
        normalized = line.casefold().rstrip(":")
        if any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in metadata_patterns):
            continue
        filtered.append(line)

    # If a template renders everything on one line, remove leading
    # "Note by <author> on <date>" metadata from that line.
    candidate = " ".join(filtered or lines)
    candidate = re.sub(
        r"^\s*note by\s+.+?\s+on\s+\d{4}-\d{2}-\d{2}(?:\s+\d{1,2}:\d{2})?\s*[:\-]?\s*",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(
        r"^\s*by\s+.+?\s+on\s+\d{4}-\d{2}-\d{2}(?:\s+\d{1,2}:\d{2})?\s*[:\-]?\s*",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    return _clean_remote_comment(candidate)



def _extract_note_card_values(html: str) -> list[str]:
    """Extract latest Django Note.content from the ticket detail template.

    The current ticketing template renders notes as:
    <div class="note-card"><p class="note-content"><strong>user:</strong> content</p>
    <p class="note-timestamp">...</p></div>.
    This parser intentionally returns only the note-content text and ignores the
    note timestamp/author metadata.
    """
    values: list[str] = []

    # Prefer the exact rendered note-card structure. Each note card contains a
    # note-content paragraph and an optional note-timestamp paragraph.
    for card_match in re.finditer(
        r"<div\b(?=[^>]*\bclass\s*=\s*(['\"])[^'\"]*\bnote-card\b[^'\"]*\1)[^>]*>(?P<body>.*?)</div>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        body = card_match.group("body")
        content_match = re.search(
            r"<(?:p|div|span)\b(?=[^>]*\bclass\s*=\s*(['\"])[^'\"]*\bnote-content\b[^'\"]*\1)[^>]*>(?P<content>.*?)</(?:p|div|span)>",
            body,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if content_match is None:
            continue

        content_html = content_match.group("content")
        # Remove the rendered author label, for example
        # <strong>heniljariwala:</strong>.
        content_html = re.sub(
            r"<strong\b[^>]*>\s*[^<]{1,120}:\s*</strong>",
            " ",
            content_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        value = _clean_remote_comment(_html_fragment_text(content_html))
        if value:
            values.append(value)

    if values:
        return values

    # Fallback: some templates may render note-content blocks without a wrapping
    # note-card. Return them in display order.
    for content_match in re.finditer(
        r"<(?:p|div|span)\b(?=[^>]*\bclass\s*=\s*(['\"])[^'\"]*\bnote-content\b[^'\"]*\1)[^>]*>(?P<content>.*?)</(?:p|div|span)>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        content_html = re.sub(
            r"<strong\b[^>]*>\s*[^<]{1,120}:\s*</strong>",
            " ",
            content_match.group("content"),
            flags=re.IGNORECASE | re.DOTALL,
        )
        value = _clean_remote_comment(_html_fragment_text(content_html))
        if value:
            values.append(value)

    return values

def _extract_django_note_blocks(html: str) -> list[str]:
    """Return rendered Django Note.content values, ordered as displayed.

    The ticketing model stores comments in ``Note.content`` and relates them as
    ``ticket.notes``. Common Django templates render each note as an element
    with class/id containing ``note`` or ``comment``. We extract those blocks and
    take the last valid one, while ignoring the add-note form.
    """
    note_values: list[str] = []
    block_pattern = (
        r"<(div|li|tr|article|section)\b"
        r"(?=[^>]*(?:class|id)\s*=\s*(['\"])[^'\"]*(?:note|comment)[^'\"]*\2)"
        r"[^>]*>.*?</\1>"
    )
    for match in re.finditer(block_pattern, html, flags=re.IGNORECASE | re.DOTALL):
        fragment = match.group(0)
        if re.search(r"<form\b|<textarea\b|name\s*=\s*(['\"])(?:content|note|notes|comment)", fragment, flags=re.IGNORECASE):
            continue
        fragment_text = _html_fragment_text(fragment)
        if len(re.findall(r"\bnote by\b", fragment_text, flags=re.IGNORECASE)) >= 2:
            note_values.extend(_extract_notes_section_values(fragment_text))
            continue
        value = _note_content_from_text(fragment_text)
        if value:
            note_values.append(value)

    return note_values


def _extract_notes_section_values(text: str) -> list[str]:
    """Extract notes from a plain-text version of a ticket-detail page."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    # First, handle the exact Django model string style:
    # "Note by <username> on YYYY-MM-DD HH:MM" followed by content.
    combined = "\n".join(lines)
    note_pattern = (
        r"(?is)(?:^|\n)\s*note by\s+[^\n]{1,120}?\s+on\s+"
        r"\d{4}-\d{2}-\d{2}(?:\s+\d{1,2}:\d{2})?\s*"
        r"(?P<content>.*?)"
        r"(?=(?:\n\s*note by\s+[^\n]{1,120}?\s+on\s+\d{4}-\d{2}-\d{2})|\Z)"
    )
    values: list[str] = []
    for match in re.finditer(note_pattern, combined, flags=re.IGNORECASE | re.DOTALL):
        value = _note_content_from_text(match.group("content"))
        if value:
            values.append(value)
    if values:
        return values

    # Otherwise, locate a Notes/Comments section and stop at the next ticket
    # field heading. This catches simple templates that render:
    # Notes\n<old note>\n<new note>.
    stop_labels = {
        "status",
        "priority",
        "category",
        "device",
        "assigned",
        "assigned to",
        "created",
        "updated",
        "requester",
        "email",
        "title",
        "description",
        "location",
        "best way",
        "best time",
        "image",
        "attachment",
        "submit",
        "save",
    }
    section: list[str] = []
    in_notes = False
    for line in lines:
        normalized = line.casefold().rstrip(":")
        if normalized in {"notes", "note", "comments", "comment", "ticket notes", "resolution comments"}:
            in_notes = True
            section = []
            continue
        if in_notes and normalized in stop_labels:
            break
        if in_notes:
            section.append(line)

    if not section:
        return []

    # Split multiple displayed notes if author/date markers are present, else
    # treat the section as one rendered note and return the last meaningful line.
    section_text = "\n".join(section)
    values = []
    for part in re.split(r"(?=\b(?:note by|by)\s+.+?\s+on\s+\d{4}-\d{2}-\d{2})", section_text, flags=re.IGNORECASE):
        value = _note_content_from_text(part)
        if value:
            values.append(value)
    if values:
        return values

    final_value = _note_content_from_text("\n".join(section))
    return [final_value] if final_value else []


def _extract_json_note_values(raw_text: str) -> list[str]:
    """Extract note content if a ticket detail endpoint returns JSON."""
    import json

    try:
        payload = json.loads(raw_text)
    except Exception:
        return []

    def walk(value: Any) -> list[str]:
        found: list[str] = []
        if isinstance(value, dict):
            # Django REST shapes usually use notes: [{content, created_at, ...}].
            for key, nested in value.items():
                key_text = str(key).casefold()
                if key_text in {"content", "comment", "note", "resolution_comment"}:
                    cleaned = _clean_remote_comment(str(nested))
                    if cleaned:
                        found.append(cleaned)
                elif key_text in {"notes", "comments", "ticket_notes"}:
                    found.extend(walk(nested))
                elif isinstance(nested, (dict, list)):
                    found.extend(walk(nested))
        elif isinstance(value, list):
            for item in value:
                found.extend(walk(item))
        return found

    return walk(payload)


def _extract_ticket_resolution_comment(html: str) -> str | None:
    """Extract the latest real ticket note/comment from a detail page.

    The SJK ticketing system renders saved Django Note records as:

        <div class="note-card">
            <p class="note-content"><strong>user:</strong> content</p>
            <p class="note-timestamp">...</p>
        </div>

    Only saved/rendered notes should be returned. Empty ``Comments`` sections,
    the new-note textarea, Submit buttons, and Cancel buttons must not become
    fake comments such as "s".
    """
    json_values = _extract_json_note_values(html)
    if json_values:
        return json_values[-1]

    note_card_values = _extract_note_card_values(html)
    if note_card_values:
        return note_card_values[-1]

    note_blocks = _extract_django_note_blocks(html)
    if note_blocks:
        return note_blocks[-1]

    text = _html_to_labeled_text(html)
    if text:
        section_values = _extract_notes_section_values(text)
        if section_values:
            return section_values[-1]

    # Do not fall back to generic "Comments:" labels or form fields here.
    # The ticket edit page always contains an empty "Comments" heading and a
    # new-note form. Generic label parsing can accidentally capture button text
    # like "Submit"/"Cancel" and display fake comments.
    return None

def _extract_links(fragment: str, *, page_url: str) -> list[str]:
    """Return absolute links found inside an HTML ticket row/card."""
    links: list[str] = []
    for match in re.finditer(
        r"<a\b[^>]*\bhref\s*=\s*(['\"])(.*?)\1",
        fragment,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        href = unescape(match.group(2)).strip()
        if href:
            absolute = urljoin(page_url, href)
            if absolute not in links:
                links.append(absolute)
    return links


def _external_id_from_text_or_links(text: str, links: Iterable[str]) -> str | None:
    """Extract a likely numeric ticket identifier from a row or its links."""
    patterns = (
        r"(?:^|/)(?:it/|faculty/|staff/)?(?:tickets?|ticket-detail|view-ticket|update-ticket)/(?:detail/|view/|edit/|update/)?(\d+)(?:/(?:edit|view|update|detail))?(?:/|$|[?#])",
        r"(?:ticket|tickets|ticket_detail|view_ticket|update_ticket)/(?:detail/)?(\d+)(?:/(?:edit|view|update|detail))?",
        r"[?&](?:ticket_id|id|pk)=(\d+)",
    )
    for link in links:
        for pattern in patterns:
            match = re.search(pattern, link, flags=re.IGNORECASE)
            if match:
                return match.group(1)

    text_match = re.search(
        r"\bticket\s*(?:#|id\s*[:#]?)?\s*(\d+)\b",
        text,
        flags=re.IGNORECASE,
    )
    return text_match.group(1) if text_match else None


def _extract_all_ticket_detail_links(
    html: str,
    *,
    page_url: str,
    config: TicketingConfig,
) -> list[str]:
    """Return same-origin ticket-detail links from a dashboard page.

    Some dashboard layouts do not place the detail link inside the same
    table/card fragment that contains the Altitude reference. When that
    happens, the row matcher can still determine the status from visible
    text, but it cannot reach the detail page where Django Note comments are
    rendered. This helper safely scans every same-origin ticket detail link
    on the authenticated dashboard so the caller can fetch candidates and
    match them by Altitude reference.
    """
    links: list[str] = []
    ticket_link_pattern = re.compile(
        r"(?:^|/)(?:it/|faculty/|staff/)?(?:tickets?|ticket-detail|view-ticket|update-ticket)/(?:detail/|view/|edit/|update/)?\d+(?:/(?:edit|view|update|detail))?/?(?:$|[?#])|"
        r"(?:ticket_id|id|pk)=\d+",
        flags=re.IGNORECASE,
    )

    for match in re.finditer(
        r"<a\b[^>]*\bhref\s*=\s*(['\"])(.*?)\1",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        href = unescape(match.group(2)).strip()
        if not href:
            continue
        absolute = urljoin(page_url, href)
        if not ticket_link_pattern.search(absolute):
            continue
        try:
            _require_same_ticketing_origin(
                absolute,
                config.base_url,
                field_name="Dashboard ticket detail URL",
            )
        except TicketingClientError:
            continue
        if absolute not in links:
            links.append(absolute)

    return links


def _detail_page_match_score(
    html: str,
    local_ticket: Mapping[str, Any],
) -> int:
    """Score whether a fetched detail page belongs to a local ticket."""
    text = _page_text(html)
    if not text:
        return 0

    altitude_reference = str(
        local_ticket.get("altitude_reference") or ""
    ).strip().lower()
    external_ticket_id = str(
        local_ticket.get("external_ticket_id") or ""
    ).strip().lower()
    title = " ".join(str(local_ticket.get("title") or "").split()).lower()
    email = str(local_ticket.get("contact_email") or "").strip().lower()

    score = 0
    if altitude_reference and altitude_reference in text:
        score += 200
    if external_ticket_id and re.search(
        rf"(?:ticket\s*(?:#|id)?\s*)?{re.escape(external_ticket_id)}\b",
        text,
        flags=re.IGNORECASE,
    ):
        score += 100
    if title and title in text:
        score += 60
    if email and email in text:
        score += 40

    return score


def _fetch_matching_ticket_detail_page(
    client: "DjangoTicketingClient",
    *,
    local_ticket: Mapping[str, Any],
    dashboard_html: str,
    dashboard_url: str,
) -> tuple[requests.Response, str | None] | None:
    """Fetch the detail page matching a local Altitude ticket, if possible.

    Returns the authenticated detail response and the numeric ticketing ID
    parsed from its URL/link. This is intentionally read-only.
    """
    candidates = _extract_all_ticket_detail_links(
        dashboard_html,
        page_url=dashboard_url,
        config=client.config,
    )

    # Keep the status lookup quick and avoid crawling large dashboards.
    for candidate_url in candidates[:500]:
        try:
            detail_page = client._get(candidate_url)
        except TicketingClientError:
            continue

        score = _detail_page_match_score(detail_page.text, local_ticket)
        # Prefer an Altitude reference or ticket ID, but allow an exact title
        # match for older tickets created before the reference was embedded in
        # the ticketing-system title/description. This is still read-only and
        # only scans authenticated same-origin ticket detail pages.
        if score >= 60:
            links = [candidate_url]
            ticket_id = _external_id_from_text_or_links(
                _page_text(detail_page.text),
                links,
            )
            return detail_page, ticket_id

    return None


def _ticket_detail_scan_bounds() -> tuple[int, int]:
    """Return the safe faculty-edit ticket ID range used as a fallback scan."""
    def parse_int(name: str, default: int) -> int:
        try:
            return int(os.getenv(name, str(default)).strip())
        except ValueError:
            return default

    start_id = parse_int("TICKETING_DETAIL_SCAN_START_ID", DEFAULT_DETAIL_SCAN_START_ID)
    end_id = parse_int("TICKETING_DETAIL_SCAN_END_ID", DEFAULT_DETAIL_SCAN_END_ID)
    start_id = max(1, start_id)
    end_id = max(start_id, min(end_id, 2000))
    return start_id, end_id


def _ticket_id_from_detail_url(url: str) -> str | None:
    """Extract the numeric Django ticket id from a ticket-detail URL."""
    patterns = (
        r"/(?:faculty|it|staff)/ticket/(?P<id>\d+)(?:/edit)?/?(?:$|[?#])",
        r"/ticket/(?P<id>\d+)(?:/edit)?/?(?:$|[?#])",
        r"/tickets?/(?:detail/)?(?P<id>\d+)/?(?:$|[?#])",
    )
    for pattern in patterns:
        match = re.search(pattern, str(url), flags=re.IGNORECASE)
        if match is not None:
            return match.group("id")
    return None


def _detail_page_is_safe_match(html: str, local_ticket: Mapping[str, Any]) -> bool:
    """Return True only when a detail page confidently belongs to the ticket."""
    score = _detail_page_match_score(html, local_ticket)
    altitude_reference = str(local_ticket.get("altitude_reference") or "").strip()

    # The Altitude reference is the strongest identifier and is embedded in new
    # remote ticket titles/descriptions. For older tickets, require at least an
    # exact title + email match (60 + 40 = 100). Never accept email-only pages,
    # because the same requester can have many tickets.
    if altitude_reference and score >= 200:
        return True
    return score >= 100


def _scan_matching_ticket_detail_page(
    client: "DjangoTicketingClient",
    *,
    local_ticket: Mapping[str, Any],
) -> tuple[requests.Response, str] | None:
    """Scan faculty ticket edit pages when the dashboard has no detail links.

    The current ticketing dashboard can show status rows without links, while
    notes are available only on /faculty/ticket/<id>/edit/. This read-only scan
    finds the page containing the Altitude reference, saves that real Django ID,
    and lets future checks use the saved URL directly.
    """
    start_id, end_id = _ticket_detail_scan_bounds()
    best: tuple[int, requests.Response, str] | None = None

    for ticket_id in range(start_id, end_id + 1):
        ticket_url = urljoin(
            client.config.base_url,
            f"faculty/ticket/{ticket_id}/edit/",
        )
        try:
            detail_page = client._get(ticket_url)
        except TicketingClientError:
            continue

        if detail_page.status_code != 200:
            continue

        score = _detail_page_match_score(detail_page.text, local_ticket)
        if score <= 0:
            continue

        if best is None or score > best[0]:
            best = (score, detail_page, str(ticket_id))

        # An Altitude reference match is exact enough to stop scanning.
        if score >= 200:
            return detail_page, str(ticket_id)

    if best is None:
        return None

    score, detail_page, ticket_id = best
    if score >= 100:
        return detail_page, ticket_id
    return None


def _dashboard_blocks(html: str, *, page_url: str) -> list[dict[str, Any]]:
    """Extract likely ticket rows/cards from a dashboard without extra deps."""
    patterns = (
        r"<tr\b[^>]*>.*?</tr>",
        r"<article\b[^>]*(?:class|id)\s*=\s*(['\"])[^'\"]*ticket[^'\"]*\1[^>]*>.*?</article>",
        r"<li\b[^>]*(?:class|id)\s*=\s*(['\"])[^'\"]*ticket[^'\"]*\1[^>]*>.*?</li>",
        r"<div\b[^>]*(?:class|id)\s*=\s*(['\"])[^'\"]*(?:ticket-card|ticket-row|ticket-item|ticket-list-item)[^'\"]*\1[^>]*>.*?</div>",
    )

    blocks: list[dict[str, Any]] = []
    seen_text: set[str] = set()
    for pattern in patterns:
        for match in re.finditer(
            pattern,
            html,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            fragment = match.group(0)
            text = _page_text(fragment)
            if not text or text in seen_text:
                continue
            seen_text.add(text)
            links = _extract_links(fragment, page_url=page_url)
            blocks.append(
                {
                    "text": text,
                    "links": links,
                    "status": _canonical_remote_status(text),
                    "external_ticket_id": _external_id_from_text_or_links(
                        text,
                        links,
                    ),
                    "fragment": fragment,
                }
            )
    return blocks


def _best_ticket_block(
    local_ticket: Mapping[str, Any],
    blocks: Iterable[Mapping[str, Any]],
) -> tuple[Mapping[str, Any] | None, str]:
    """Match a local audit row to the most likely dashboard row/card."""
    local_reference = str(
        local_ticket.get("external_ticket_id") or ""
    ).strip()
    altitude_reference = str(
        local_ticket.get("altitude_reference") or ""
    ).strip().upper()
    title = " ".join(str(local_ticket.get("title") or "").split()).lower()
    email = str(local_ticket.get("contact_email") or "").strip().lower()

    best: Mapping[str, Any] | None = None
    best_score = 0
    matched_by = ""

    for block in blocks:
        block_text = str(block.get("text") or "").lower()
        block_reference = str(
            block.get("external_ticket_id") or ""
        ).strip()
        score = 0
        reasons: list[str] = []

        if altitude_reference and altitude_reference.lower() in block_text:
            score += 240
            reasons.append("altitude reference")

        # A previous Altitude bug could save the local audit ID as the remote
        # Django ticket ID. Treat a ticketing-reference match as useful, but
        # let an exact title/email or Altitude-reference match win over it.
        if local_reference and block_reference == local_reference:
            score += 80
            reasons.append("ticketing reference")
        elif local_reference and re.search(
            rf"(?:#|\b){re.escape(local_reference)}\b",
            block_text,
        ):
            score += 60
            reasons.append("ticketing reference text")

        if title and title in block_text:
            score += 100
            reasons.append("title")

        if email and email in block_text:
            score += 50
            reasons.append("email")

        # Require a strong identifier to avoid assigning another user's status.
        if score > best_score and (
            score >= 70 or (score >= 25 and (local_reference or altitude_reference))
        ):
            best = block
            best_score = score
            matched_by = ", ".join(reasons)

    return best, matched_by



def _candidate_ticket_detail_urls(
    config: TicketingConfig,
    *,
    remote_ticket_url: str | None,
    dashboard_detail_url: str | None,
    external_ticket_id: str | None,
) -> list[str]:
    """Return same-origin ticket detail URLs to try for status/comment lookup."""
    candidates: list[str] = []

    def add(url: str | None) -> None:
        if not url:
            return
        absolute = urljoin(config.base_url, str(url).strip())
        try:
            _require_same_ticketing_origin(
                absolute,
                config.base_url,
                field_name="Ticket detail URL",
            )
        except TicketingClientError:
            return
        if absolute not in candidates:
            candidates.append(absolute)

    add(remote_ticket_url)
    add(dashboard_detail_url)

    ticket_id = str(external_ticket_id or "").strip()
    if ticket_id.isdigit():
        configured_template = str(config.detail_url_template or "").strip()
        if configured_template:
            configured_url = configured_template.replace("{ticket_id}", ticket_id)
            add(configured_url if re.match(r"^https?://", configured_url, flags=re.IGNORECASE) else urljoin(config.base_url, configured_url))

        # The current Django ticketing app exposes detail pages as
        # /sjk-ticketingsystem/faculty/ticket/<id>/edit/. Keep other common
        # read-only/status/detail routes as safe fallbacks for older deployments.
        for path in (
            f"faculty/ticket/{ticket_id}/edit/",
            f"it/ticket/{ticket_id}/",
            f"faculty/ticket/{ticket_id}/",
            f"staff/ticket/{ticket_id}/edit/",
            f"ticket/{ticket_id}/edit/",
            f"ticket/{ticket_id}/",
            f"tickets/{ticket_id}/",
            f"tickets/detail/{ticket_id}/",
            f"ticket/detail/{ticket_id}/",
        ):
            add(urljoin(config.base_url, path))

    return candidates

def fetch_ticket_statuses(
    local_tickets: Iterable[Mapping[str, Any]],
) -> list[RemoteTicketStatus]:
    """Fetch and match current ticket statuses from the Django ticketing app.

    The dashboard is used for status when it is available, but this function no
    longer depends on dashboard detail links. If a local row does not yet have
    the real Django ticket URL, Altitude scans the same-origin faculty edit
    pages and selects the page that contains the Altitude reference.
    """
    client = DjangoTicketingClient()
    client.login()
    dashboard = client._get(client.config.dashboard_url)
    blocks = _dashboard_blocks(dashboard.text, page_url=dashboard.url)

    results: list[RemoteTicketStatus] = []
    for local_ticket in local_tickets:
        try:
            local_ticket_id = int(local_ticket.get("local_ticket_id", 0))
        except (TypeError, ValueError):
            continue
        if local_ticket_id <= 0:
            continue

        matched_block, matched_by = _best_ticket_block(local_ticket, blocks)

        status = ""
        links: list[str] = []
        dashboard_detail_url: str | None = None
        resolution_comment: str | None = None
        detail_url: str | None = None
        remote_reference = str(
            local_ticket.get("external_ticket_id") or ""
        ).strip() or None

        if matched_block is not None:
            status = str(matched_block.get("status") or "").strip()
            links = [str(item) for item in matched_block.get("links", [])]
            dashboard_detail_url = next(
                (
                    link
                    for link in links
                    if re.search(
                        r"ticket|detail|view|update|edit",
                        link,
                        re.IGNORECASE,
                    )
                ),
                links[0] if links else None,
            )
            remote_reference = str(
                matched_block.get("external_ticket_id")
                or remote_reference
                or ""
            ).strip() or None

        detail_candidates = _candidate_ticket_detail_urls(
            client.config,
            remote_ticket_url=str(local_ticket.get("remote_ticket_url") or "").strip() or None,
            dashboard_detail_url=dashboard_detail_url,
            external_ticket_id=remote_reference,
        )

        # Try saved/configured/detail-link candidates first, but only accept a
        # note from pages that actually match this Altitude ticket. This avoids
        # using another ticket from the same requester when an older local row
        # has the wrong Django ID.
        for candidate_url in detail_candidates:
            try:
                detail_page = client._get(candidate_url)
            except TicketingClientError:
                continue

            if not _detail_page_is_safe_match(detail_page.text, local_ticket):
                continue

            detail_url = detail_page.url
            found_ticket_id = _ticket_id_from_detail_url(detail_page.url)
            if found_ticket_id:
                remote_reference = found_ticket_id

            detail_status = _extract_detail_page_status(detail_page.text)
            if detail_status:
                status = detail_status

            resolution_comment = _extract_ticket_resolution_comment(
                detail_page.text
            )
            break

        # If there was no known detail URL, scan faculty/ticket/<id>/edit/ pages
        # and pick the page containing the Altitude reference.
        if not detail_url:
            scanned_detail = _scan_matching_ticket_detail_page(
                client,
                local_ticket=local_ticket,
            )
            if scanned_detail is not None:
                detail_page, found_ticket_id = scanned_detail
                detail_url = detail_page.url
                remote_reference = found_ticket_id

                detail_status = _extract_detail_page_status(detail_page.text)
                if detail_status:
                    status = detail_status

                resolution_comment = _extract_ticket_resolution_comment(
                    detail_page.text
                )

        # Older dashboards may contain links even when row/card extraction did
        # not capture them. Keep this as a final fallback.
        if not detail_url:
            matched_detail = _fetch_matching_ticket_detail_page(
                client,
                local_ticket=local_ticket,
                dashboard_html=dashboard.text,
                dashboard_url=dashboard.url,
            )
            if matched_detail is not None:
                detail_page, found_ticket_id = matched_detail
                detail_url = detail_page.url
                if found_ticket_id:
                    remote_reference = found_ticket_id

                detail_status = _extract_detail_page_status(detail_page.text)
                if detail_status:
                    status = detail_status

                resolution_comment = _extract_ticket_resolution_comment(
                    detail_page.text
                )

        if not status and matched_block is not None:
            status = str(matched_block.get("status") or "").strip()

        if not status:
            continue

        if not resolution_comment and matched_block is not None:
            dashboard_fragment = str(matched_block.get("fragment") or "")
            if dashboard_fragment:
                resolution_comment = _extract_ticket_resolution_comment(
                    dashboard_fragment
                )

        results.append(
            RemoteTicketStatus(
                local_ticket_id=local_ticket_id,
                status=status,
                external_ticket_id=remote_reference,
                remote_ticket_url=detail_url,
                matched_by=matched_by or (
                    "faculty ticket detail scan" if detail_url else "dashboard row"
                ),
                resolution_comment=resolution_comment,
            )
        )

    return results

def submit_ticket(payload: TicketPayload) -> TicketSubmissionResult:
    """Convenience wrapper used by the Streamlit chat workflow."""
    return DjangoTicketingClient().submit_ticket(payload)
