import streamlit as st

from pages.chat import render_chat
from pages.dashboard import render_dashboard
from pages.knowledge import render_knowledge
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
    icon="💬",
    url_path="support",
    default=True,
)

dashboard_page = st.Page(
    render_dashboard,
    title="IT Dashboard",
    icon="📊",
    url_path="dashboard",
)

knowledge_page = st.Page(
    render_knowledge,
    title="Knowledge Management",
    icon="📚",
    url_path="knowledge",
)

selected_page = st.navigation(
    [chat_page, dashboard_page, knowledge_page],
    position="hidden",
)

render_header()
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