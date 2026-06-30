import streamlit as st


def render_dashboard() -> None:
    st.subheader("IT Manager Dashboard")

    metric_1, metric_2, metric_3 = st.columns(3)

    metric_1.metric("Conversations", 0)
    metric_2.metric("Deflection Rate", "0%")
    metric_3.metric("Active Tickets", 0)

    st.info(
        "Analytics, knowledge gaps, ticket status, and "
        "system health will be added here."
    )