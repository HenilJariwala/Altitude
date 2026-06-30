from __future__ import annotations

import base64
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from core.assistant import prepare_answer, stream_answer
from core.question_logger import log_user_question
from ui.layout import STATIC_DIRECTORY, image_data_uri

MAX_CHAT_MESSAGES = 80

LOADING_GIF_PATH = Path(__file__).resolve().parents[1] / "static" / "ai-loading.gif"


def get_greeting() -> str:
    """Return a greeting based on the current local time."""
    hour = datetime.now().hour

    if hour < 12:
        return "Good Morning"

    if hour < 17:
        return "Good Afternoon"

    return "Good Evening"


def initialize_chat() -> None:
    """Create the opening message once per browser session."""
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": (
                    "👋 Hi! I’m Altitude — your IT Support Assistant.\n\n"
                    "How can I help you?"
                ),
            }
        ]

    if "pending_question" not in st.session_state:
        st.session_state.pending_question = None


def trim_chat_history() -> None:
    """Bound in-memory history while preserving the opening greeting."""

    messages = list(st.session_state.chat_messages)

    if len(messages) <= MAX_CHAT_MESSAGES:
        return

    opening_message = messages[0]
    recent_messages = messages[-(MAX_CHAT_MESSAGES - 1) :]
    st.session_state.chat_messages = [opening_message, *recent_messages]


def display_greeting(animate: bool) -> None:
    """Display the time-based greeting."""
    greeting = get_greeting()
    eagle_uri = image_data_uri("eagle.png")

    if eagle_uri:
        eagle_html = f'<img src="{eagle_uri}" class="sjk-eagle" alt="SJK Eagle">'
    else:
        eagle_html = '<span class="sjk-eagle-fallback">🦅</span>'

    if animate:
        time_html = f"""
<span
    class="sjk-typewriter-shell"
    style="--sjk-character-count: {len(greeting)};"
>
    <span
        class="sjk-typewriter-reserve"
        aria-hidden="true"
    >
        {greeting}
    </span>

    <span class="sjk-greeting-time sjk-typewriter-text">
        {greeting}
    </span>
</span>
"""
    else:
        time_html = f'<span class="sjk-greeting-time">{greeting}</span>'

    st.html(
        f"""
<div class="sjk-greeting">
    {time_html}
    <span class="sjk-greeting-eagles">Eagles</span>
    {eagle_html}
</div>
"""
    )


def display_assistant_avatar() -> None:
    """Render the SJK crest beside assistant messages."""
    crest_uri = image_data_uri("sjk_crest.png")

    if crest_uri:
        st.html(
            f"""
<div class="sjk-message-avatar-wrapper">
    <img
        src="{crest_uri}"
        class="sjk-message-avatar-image"
        alt="SJK Altitude"
    >
</div>
"""
        )
    else:
        st.html(
            """
<div class="sjk-message-avatar-wrapper">
    <div class="sjk-fallback-avatar">🤖</div>
</div>
"""
        )


def display_student_avatar() -> None:
    """Render the student avatar beside user messages."""
    st.html(
        """
<div class="sjk-message-avatar-wrapper sjk-user-avatar-wrapper">
    <div class="sjk-student-avatar">👤</div>
</div>
"""
    )


def display_message(
    message: dict[str, Any],
    message_index: int,
) -> None:
    """Render an assistant or user message."""
    role = message.get("role", "assistant")
    content = str(message.get("content", ""))

    if role == "assistant":
        avatar_column, bubble_column = st.columns(
            [0.045, 0.955],
            gap="small",
            vertical_alignment="top",
        )

        with avatar_column:
            display_assistant_avatar()

        with bubble_column:
            with st.container(
                key=f"assistant_message_{message_index}",
                height="content",
                border=False,
            ):
                st.markdown(content)

                resource = message.get("resource")

                if resource:
                    resource_path = STATIC_DIRECTORY / str(resource)

                    if resource_path.exists():
                        st.image(
                            str(resource_path),
                            caption=message.get("caption"),
                            width=320,
                        )

    else:
        bubble_column, avatar_column = st.columns(
            [0.955, 0.045],
            gap="small",
            vertical_alignment="top",
        )

        with bubble_column:
            with st.container(
                key=f"user_message_{message_index}",
                height="content",
                border=False,
            ):
                st.markdown(content)

        with avatar_column:
            display_student_avatar()


def render_loading_animation(
    placeholder: Any,
) -> None:
    """Render the local loading GIF or fallback dots."""

    if not LOADING_GIF_PATH.exists():
        placeholder.markdown(
            """
<div class="sjk-thinking-loader">
    <span></span>
    <span></span>
    <span></span>
    <strong>ALTITUDE is thinking...</strong>
</div>
""",
            unsafe_allow_html=True,
        )
        return

    gif_bytes = LOADING_GIF_PATH.read_bytes()

    encoded_gif = base64.b64encode(gif_bytes).decode("utf-8")

    placeholder.markdown(
        f"""
<div class="sjk-thinking-loader">
    <img
        src="data:image/gif;base64,{encoded_gif}"
        alt=""
    />
    <strong></strong>
</div>
""",
        unsafe_allow_html=True,
    )


def display_streaming_assistant(
    question: str,
    history: list[dict[str, Any]],
    message_index: int,
) -> dict[str, Any]:
    """
    Display the loading animation before routing or generating
    the response.
    """

    avatar_column, bubble_column = st.columns(
        [0.045, 0.955],
        gap="small",
        vertical_alignment="top",
    )

    plan = None
    response_text = ""

    with avatar_column:
        display_assistant_avatar()

    with bubble_column:
        with st.container(
            key=f"assistant_message_{message_index}",
            height="content",
            border=False,
        ):
            loading_placeholder = st.empty()

            # Show the loader before prepare_answer(), because
            # routing may call Ollama or the live inventory API.
            render_loading_animation(loading_placeholder)

            # Give Streamlit a moment to render it.
            time.sleep(0.15)

            try:
                plan = prepare_answer(
                    question=question,
                    history=history,
                )

                if plan.direct_answer is not None:
                    # Keep the animation visible briefly so direct
                    # answers do not flash abruptly.
                    time.sleep(0.20)

                    loading_placeholder.empty()

                    response_text = plan.direct_answer

                    st.markdown(response_text)

                else:

                    def response_with_loading():
                        first_chunk_received = False

                        try:
                            for chunk in stream_answer(
                                question=question,
                                history=history,
                                plan=plan,
                            ):
                                if chunk and not first_chunk_received:
                                    loading_placeholder.empty()
                                    first_chunk_received = True

                                yield chunk

                        finally:
                            loading_placeholder.empty()

                    response_text = st.write_stream(
                        response_with_loading(),
                        cursor="▌",
                    )

            except Exception as error:
                loading_placeholder.empty()

                print(f"Chat response error: {type(error).__name__}: {error}")

                response_text = (
                    "I could not complete that request. Please contact the IT Helpdesk."
                )

                st.markdown(response_text)

            if plan is not None and plan.resource:
                resource_path = STATIC_DIRECTORY / plan.resource

                if resource_path.exists():
                    st.image(
                        str(resource_path),
                        caption=plan.caption,
                        width=320,
                    )
                else:
                    st.error("The requested support resource could not be found.")

                    print(
                        "Missing support resource:",
                        resource_path,
                    )

            scroll_chat_to_bottom()

    if not isinstance(response_text, str):
        response_text = str(response_text)

    return {
        "role": "assistant",
        "content": response_text,
        "resource": (plan.resource if plan is not None else None),
        "caption": (plan.caption if plan is not None else None),
    }


def scroll_chat_to_bottom() -> None:
    """Scroll the custom chat container to its newest content."""

    trigger_id = time.time_ns()

    st.html(
        f"""
<script data-scroll-trigger="{trigger_id}">
(() => {{
    const findScrollableContainer = () => {{
        const root = document.querySelector(
            ".st-key-chat_scroll_area"
        );

        if (!root) {{
            return null;
        }}

        const candidates = [
            root,
            ...root.querySelectorAll("div")
        ];

        return candidates.find((element) => {{
            const style = window.getComputedStyle(element);

            const canScroll =
                style.overflowY === "auto" ||
                style.overflowY === "scroll";

            return (
                canScroll &&
                element.scrollHeight >
                    element.clientHeight + 4
            );
        }}) || root;
    }};

    const scrollToBottom = () => {{
        const container = findScrollableContainer();

        if (!container) {{
            return;
        }}

        container.scrollTo({{
            top: container.scrollHeight,
            behavior: "smooth"
        }});
    }};

    requestAnimationFrame(scrollToBottom);
    setTimeout(scrollToBottom, 100);
    setTimeout(scrollToBottom, 350);
    setTimeout(scrollToBottom, 750);

    const chatRoot = document.querySelector(
        ".st-key-chat_scroll_area"
    );

    if (!chatRoot) {{
        return;
    }}

    /*
     * Continue following the response while text is streaming.
     */
    const observer = new MutationObserver(() => {{
        scrollToBottom();
    }});

    observer.observe(chatRoot, {{
        childList: true,
        subtree: true,
        characterData: true
    }});

    setTimeout(() => {{
        observer.disconnect();
        scrollToBottom();
    }}, 30000);
}})();
</script>
""",
        unsafe_allow_javascript=True,
    )


def render_chat() -> None:
    """Render chat and show user messages immediately."""
    initialize_chat()
    trim_chat_history()

    is_new_conversation = len(st.session_state.chat_messages) == 1

    with st.container(
        key="chat_page",
        height="stretch",
        gap="small",
    ):
        with st.container(
            key="chat_scroll_area",
            height="stretch",
            border=False,
            autoscroll=True,
        ):
            display_greeting(animate=is_new_conversation)

            for index, message in enumerate(st.session_state.chat_messages):
                display_message(
                    message=message,
                    message_index=index,
                )

            scroll_chat_to_bottom()

            pending_question = st.session_state.pending_question

            if pending_question:
                assistant_message = display_streaming_assistant(
                    question=pending_question,
                    history=st.session_state.chat_messages,
                    message_index=len(st.session_state.chat_messages),
                )

                st.session_state.chat_messages.append(assistant_message)

                st.session_state.pending_question = None
                st.rerun()

        user_question = st.chat_input(
            "Describe your IT issue...",
            key="sjk_support_chat",
            max_chars=1000,
        )

    if user_question:
        cleaned_question = user_question.strip()

        if not cleaned_question:
            return

        try:
            log_user_question(cleaned_question)
        except Exception as error:
            print(f"Question logging failed: {type(error).__name__}: {error}")

        st.session_state.chat_messages.append(
            {
                "role": "user",
                "content": cleaned_question,
            }
        )

        trim_chat_history()
        st.session_state.pending_question = cleaned_question

        st.rerun()
