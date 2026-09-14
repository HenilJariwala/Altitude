import streamlit as st

from pages.admin import render_admin
from pages.chat import render_chat
from ui.layout import (
    configure_page,
    load_styles,
    render_header,
    render_left_panel,
    render_mobile_info_popover,
)


configure_page()
load_styles()

chat_page = st.Page(
    render_chat,
    title="IT Support",
    url_path="support",
    default=True,
)

admin_page = st.Page(
    render_admin,
    title="IT Admin",
    url_path="admin",
    visibility="hidden",
)

selected_page = st.navigation(
    [chat_page, admin_page],
    position="hidden",
)

is_admin_page = selected_page.url_path == "admin"

render_header(admin_mode=is_admin_page)

if is_admin_page:
    with st.container(
        key="admin_body",
        height="stretch",
        border=False,
        gap=None,
    ):
        selected_page.run()
else:
    render_mobile_info_popover()

    with st.container(
        key="app_body",
        height="stretch",
    ):
        left_column, main_column = st.columns(
            [1.05, 4.35],
            gap="small",
            vertical_alignment="top",
        )

        with left_column:
            with st.container(
                key="left_panel_shell",
                height="stretch",
                border=False,
            ):
                render_left_panel()

        with main_column:
            with st.container(
                key="main_panel_shell",
                height="stretch",
                border=False,
                gap=None,
            ):
                selected_page.run()
