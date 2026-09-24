from __future__ import annotations

from types import SimpleNamespace

from core.retrieval_profile import (
    build_document_profile,
    build_retrieval_profile,
    profiles_are_compatible,
)
from core.web_support import (
    DEFAULT_TRUSTED_DOMAINS,
    is_microsoft_question,
    should_prefer_web_support,
)


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print(f"[PASS] {name}")


def main() -> int:
    web_first_questions = (
        "Chrome says ERR_SSL_PROTOCOL_ERROR when I open a website.",
        "Chrome keeps showing ERR_CERT_DATE_INVALID on my laptop.",
        "Chrome says DNS_PROBE_FINISHED_NXDOMAIN on one website.",
        "Chrome says ERR_HTTP2_PROTOCOL_ERROR.",
        "Chrome says STATUS_ACCESS_VIOLATION when a page crashes.",
        "Adobe Creative Cloud gives error 205.",
        "Zoom gives me error code 10004 when it starts.",
        "Google Drive gives error 403 when I open a file.",
        "Safari gives error 300 when I open the page.",
    )

    for question in web_first_questions:
        check(
            f"vendor error uses web first: {question}",
            should_prefer_web_support(question),
        )

    local_first_questions = (
        "My Mac says the application is damaged and can't be opened.",
        "My laptop battery is dying before lunch.",
        "The projector says No Signal after I selected Extend.",
    )

    for question in local_first_questions:
        check(
            f"normal school procedure stays local first: {question}",
            not should_prefer_web_support(question),
        )

    check(
        "Microsoft web support is disabled by default",
        "support.microsoft.com" not in DEFAULT_TRUSTED_DOMAINS,
    )
    check("OneDrive is recognized as unsupported", is_microsoft_question("OneDrive is not syncing"))
    check("Windows is recognized as unsupported", is_microsoft_question("My Windows laptop will not boot"))
    check("Word app request is recognized as unsupported", is_microsoft_question("Word won't open"))
    check(
        "ordinary use of the noun word is not treated as Microsoft Word",
        not is_microsoft_question("What does the word network mean?"),
    )

    chrome_question = "Chrome says ERR_SSL_PROTOCOL_ERROR when I open a website."
    query_profile = build_retrieval_profile(chrome_question)
    unrelated_doc = SimpleNamespace(
        metadata={
            "source": "day_to_day_troubleshooting.md",
            "section_title": "File access and permissions",
            "retrieval_domains": "collaboration",
        },
        page_content=(
            "The file may belong to another user or require permission from its owner."
        ),
    )
    document_profile = build_document_profile(unrelated_doc)
    check(
        "browser error cannot use unrelated file-permission KB article",
        not profiles_are_compatible(query_profile, document_profile),
    )

    print("\nAll web fallback routing checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
