import streamlit as st


def render_knowledge() -> None:
    st.subheader("Knowledge Management")

    st.info(
        "Approved Markdown documents, knowledge gaps, "
        "and the document staging workflow will appear here."
    )