from __future__ import annotations

import base64
import mimetypes
from html import escape
from pathlib import Path

import streamlit as st

from core.analytics_db import get_active_announcements, initialize_database
from core.app_logging import get_logger
from core.inventory_router import fetch_inventory

APP_DIRECTORY = Path(__file__).resolve().parents[1]
STATIC_DIRECTORY = APP_DIRECTORY / "static"
STYLES_FILE = Path(__file__).with_name("styles.css")
LOGGER = get_logger("layout")



@st.cache_data(
    ttl=20,
    show_spinner=False,
)
def get_inventory_snapshot() -> tuple[
    tuple[str, int, int, int],
    ...,
]:
    """Return a cacheable snapshot of the live inventory."""

    payload = fetch_inventory()

    return tuple(
        (
            item.typeName,
            item.availableCount,
            item.totalCount,
            item.loanedCount,
        )
        for item in payload.types
    )

def configure_page() -> None:
    """Configure settings shared by every application page."""
    st.set_page_config(
        page_title="ALTITUDE",
        page_icon="🦅",
        layout="wide",
        initial_sidebar_state="collapsed",
    )


def load_styles() -> None:
    """Load the shared CSS file."""
    if not STYLES_FILE.exists():
        st.warning("Shared CSS file was not found.")
        return

    # Streamlit automatically wraps a CSS file in <style> tags.
    st.html(STYLES_FILE)


def image_data_uri(filename: str) -> str:
    """
    Convert a local image into a browser-compatible data URI.

    This lets us use local images inside custom HTML.
    """
    image_path = STATIC_DIRECTORY / filename

    if not image_path.exists():
        return ""

    mime_type, _ = mimetypes.guess_type(image_path.name)
    mime_type = mime_type or "image/png"

    encoded_image = base64.b64encode(
        image_path.read_bytes()
    ).decode("utf-8")

    return f"data:{mime_type};base64,{encoded_image}"


def render_header(*, admin_mode: bool = False) -> None:
    """Render the shared ALTITUDE header.

    The public chat intentionally has no link to the administrator portal.
    Administrators access /admin directly. The admin page keeps a plain-text
    link back to the support chat.
    """

    sjk_logo_uri = image_data_uri("sjk_wordmark.png")
    altitude_logo_uri = image_data_uri("altitude_center_logo.png")

    if sjk_logo_uri:
        sjk_logo_html = (
            f'<img src="{sjk_logo_uri}" '
            'class="sjk-wordmark" alt="SJK School">'
        )
    else:
        sjk_logo_html = '<div class="sjk-wordmark-fallback">SJK</div>'

    if altitude_logo_uri:
        altitude_logo_html = (
            f'<img src="{altitude_logo_uri}" '
            'class="altitude-center-logo" alt="ALTITUDE">'
        )
    else:
        altitude_logo_html = (
            '<div class="altitude-text-fallback">ALTITUDE</div>'
        )

    route_link_html = ""

    if admin_mode:
        route_link_html = (
            '<a class="sjk-header-route-link" href="./">'
            '<span>Support Chat</span>'
            '</a>'
        )

    header_class = (
        "sjk-header sjk-header-admin"
        if admin_mode
        else "sjk-header"
    )

    header_html = f"""
    <header class="{header_class}">
        <div class="sjk-header-left">
            {sjk_logo_html}
        </div>

        <div class="sjk-header-centre">
            <div class="altitude-center-wrap">
                {altitude_logo_html}
            </div>

            <div class="altitude-tagline">
                Taking IT Support to New Heights
            </div>
        </div>

        <div class="sjk-header-right">
            {route_link_html}
        </div>
    </header>
    """

    st.html(header_html)


ANNOUNCEMENT_TYPE_LABELS: dict[str, str] = {
    "info": "Information",
    "maintenance": "Maintenance",
    "warning": "Warning",
    "outage": "Service outage",
    "resolved": "Resolved",
}


def _active_announcement_rows() -> list[dict[str, object]]:
    """Load announcements currently visible to support-chat users."""
    initialize_database()
    return get_active_announcements(limit=30)


def _announcement_rows_html(
    announcements: list[dict[str, object]],
) -> str:
    """Return safe HTML for the scrollable left-panel announcement list."""
    if not announcements:
        return """
<div class="sjk-announcement-empty">
    There are no active announcements right now.
</div>
"""

    items: list[str] = []

    for announcement in announcements:
        severity = str(announcement.get("severity", "info")).lower()
        if severity not in ANNOUNCEMENT_TYPE_LABELS:
            severity = "info"

        title = escape(str(announcement.get("title", "Announcement")))
        message = escape(str(announcement.get("message", "")))
        type_label = escape(ANNOUNCEMENT_TYPE_LABELS[severity])

        items.append(
            f"""
<article class="sjk-announcement-item sjk-announcement-{severity}">
    <div class="sjk-announcement-item-heading">
        <strong>{title}</strong>
        <span>{type_label}</span>
    </div>
    <p>{message}</p>
</article>
"""
        )

    return "".join(items)


@st.fragment(run_every="15s")
def render_announcements_card() -> None:
    """Render live database-backed announcements and refresh every 15 seconds."""
    try:
        announcements = _active_announcement_rows()
        rows_html = _announcement_rows_html(announcements)
        count_label = (
            f"{len(announcements)} active"
            if announcements
            else "No active notices"
        )
    except Exception as error:
        LOGGER.exception(
            "Left-panel announcements error: %s: %s",
            type(error).__name__,
            error,
        )
        rows_html = """
<div class="sjk-announcement-empty">
    Announcements are temporarily unavailable.
</div>
"""
        count_label = "Unavailable"

    st.html(
        f"""
<section class="sjk-card sjk-announcements-card">
    <div class="sjk-announcements-header">
        <h2>Announcements</h2>
        <span>{escape(count_label)}</span>
    </div>
    <div class="sjk-announcements-scroll">
        {rows_html}
    </div>
</section>
"""
    )


@st.fragment(
    run_every="30s",
)
def render_live_inventory_card() -> None:
    """Render live inventory and refresh it every 30 seconds."""

    try:
        inventory_items = get_inventory_snapshot()

        sorted_items = sorted(
            inventory_items,
            key=lambda item: (
                item[1] == 0,
                item[0].lower(),
            ),
        )

        available_types = sum(
            1
            for item in sorted_items
            if item[1] > 0
        )

        available_units = sum(
            item[1]
            for item in sorted_items
        )

        rows: list[str] = []

        for (
            item_name,
            available_count,
            total_count,
            loaned_count,
        ) in sorted_items:
            unavailable_class = (
                " sjk-inventory-unavailable"
                if available_count == 0
                else ""
            )

            availability_text = (
                f"{available_count} available"
                if available_count > 0
                else "Unavailable"
            )

            rows.append(
                f"""
<div class="sjk-inventory-row{unavailable_class}">
    <div class="sjk-inventory-item-info">
        <span class="sjk-inventory-item-name">
            {escape(item_name)}
        </span>

        <span class="sjk-inventory-item-meta">
            {loaned_count} loaned · {total_count} total
        </span>
    </div>

    <span class="sjk-inventory-count">
        {escape(availability_text)}
    </span>
</div>
"""
            )

        rows_html = "".join(rows)

        if not rows_html:
            rows_html = """
<div class="sjk-inventory-message">
    No inventory items are currently listed.
</div>
"""

        st.html(
            f"""
<section class="sjk-card sjk-inventory-card">
    <div class="sjk-inventory-header">
        <h2>Live Inventory</h2>

        <span class="sjk-inventory-status sjk-inventory-live">
            <span class="sjk-inventory-dot"></span>
            Live
        </span>
    </div>

    <p class="sjk-inventory-summary">
        {available_units} units available across
        {available_types} item types
    </p>

    <div class="sjk-inventory-scroll">
        {rows_html}
    </div>

    <div class="sjk-inventory-refresh-text">
        Updates automatically every 30 seconds
    </div>
</section>
"""
        )

    except Exception as error:
        LOGGER.exception(
            "Left-panel inventory error: %s: %s",
            type(error).__name__,
            error,
        )

        st.html(
            """
<section class="sjk-card sjk-inventory-card">
    <div class="sjk-inventory-header">
        <h2>Live Inventory</h2>

        <span class="sjk-inventory-status sjk-inventory-offline">
            <span class="sjk-inventory-dot"></span>
            Offline
        </span>
    </div>

    <div class="sjk-inventory-message sjk-inventory-error">
        Live availability is temporarily unavailable.
        Please contact the IT Helpdesk for current inventory.
    </div>

    <div class="sjk-inventory-refresh-text">
        The panel will try again automatically
    </div>
</section>
"""
        )


def render_left_panel() -> None:
    """Render announcements, live inventory, and privacy."""

    shield_uri = image_data_uri(
        "privacy_shield.png"
    )

    if shield_uri:
        shield_html = (
            f'<img src="{shield_uri}" '
            'class="privacy-icon" '
            'alt="Privacy shield">'
        )
    else:
        shield_html = (
            '<span class="privacy-icon-fallback">'
            "🛡️"
            "</span>"
        )

    with st.container(
        key="left_panel_content",
        height="stretch",
        border=False,
        gap=None,
    ):
        render_announcements_card()

        render_live_inventory_card()

        st.html(
            f"""
<section class="sjk-card sjk-privacy-card">
    <div class="privacy-heading">
        {shield_html}
        <span>Privacy &amp; Safety</span>
    </div>

    <p>
        This assistant runs on SJK's local network.<br>
        Your data never leaves the school.
    </p>
</section>
"""
        )

def render_mobile_info_popover() -> None:
    """
    Show announcements, live inventory, and privacy
    information on mobile devices.
    """

    with st.container(
        key="mobile_info_bar"
    ):
        with st.popover(
            "Info",
            icon=":material/info:",
            key="mobile_info_popover",
            width="content",
        ):
            # Announcements
            st.markdown("### Announcements")

            try:
                mobile_announcements = _active_announcement_rows()

                if mobile_announcements:
                    with st.container(
                        key="mobile_announcements_list",
                        height=220,
                        border=True,
                    ):
                        st.html(
                            _announcement_rows_html(mobile_announcements)
                        )
                else:
                    st.caption("There are no active announcements right now.")
            except Exception as error:
                LOGGER.exception(
                    "Mobile announcements error: %s: %s",
                    type(error).__name__,
                    error,
                )
                st.warning("Announcements are temporarily unavailable.")

            st.divider()

            # Live inventory
            st.markdown(
                "### Live Inventory"
            )

            try:
                inventory_items = get_inventory_snapshot()

                available_items = sorted(
                    (
                        item
                        for item in inventory_items
                        if item[1] > 0
                    ),
                    key=lambda item: item[0].lower(),
                )

                total_available_units = sum(
                    item[1]
                    for item in available_items
                )

                st.caption(
                    f"{total_available_units} units available "
                    f"across {len(available_items)} item types"
                )

                if available_items:
                    with st.container(
                        key="mobile_inventory_list",
                        height=230,
                        border=True,
                    ):
                        for (
                            item_name,
                            available_count,
                            total_count,
                            loaned_count,
                        ) in available_items:
                            st.markdown(
                                f"**{escape(item_name)}**"
                            )

                            st.caption(
                                f"{available_count} available · "
                                f"{loaned_count} loaned · "
                                f"{total_count} total"
                            )

                else:
                    st.info(
                        "There are currently no loaner items available."
                    )

                st.caption(
                    "Availability may change before pickup."
                )

            except Exception as error:
                LOGGER.exception(
                    "Mobile inventory error: %s: %s",
                    type(error).__name__,
                    error,
                )

                st.warning(
                    "Live inventory is temporarily unavailable. "
                    "Please contact the IT Helpdesk for current "
                    "availability."
                )

            st.divider()

            # Privacy
            st.markdown(
                "### Privacy & Safety"
            )

            st.write(
                "This assistant runs on SJK's local network."
            )

            st.write(
                "Your data never leaves the school."
            )
