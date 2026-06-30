from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any

import chromadb
import frontmatter
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import (
    Document,
)
from langchain_ollama import (
    OllamaEmbeddings,
)


load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parents[1]

KNOWLEDGE_DIRECTORY = PROJECT_ROOT / "knowledge_base"

CHROMA_DIRECTORY = PROJECT_ROOT / "data" / "chroma"

COLLECTION_NAME = "sjk_public_knowledge"

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
)

EMBEDDING_MODEL = os.getenv(
    "OLLAMA_EMBED_MODEL",
    "all-minilm",
)

CHUNK_SIZE = 700
CHUNK_OVERLAP = 80


def normalize_metadata_value(
    value: Any,
) -> str | int | float | bool:
    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    return str(value)


def split_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    cleaned = text.strip()

    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(cleaned):
        maximum_end = min(
            start + chunk_size,
            len(cleaned),
        )

        end = maximum_end

        if maximum_end < len(cleaned):
            segment = cleaned[start:maximum_end]

            boundary = max(
                segment.rfind("\n\n"),
                segment.rfind("\n"),
                segment.rfind(". "),
                segment.rfind(" "),
            )

            if boundary >= int(chunk_size * 0.6):
                end = start + boundary + 1

        chunk = cleaned[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(cleaned):
            break

        start = max(
            start + 1,
            end - overlap,
        )

    return chunks


def split_topic_sections(
    text: str,
) -> list[
    tuple[
        str | None,
        str,
    ]
]:
    """Keep each `## Topic:` procedure together."""

    matches = list(
        re.finditer(
            r"(?m)^## Topic:\s*(.+?)\s*$",
            text,
        )
    )

    if not matches:
        return [
            (
                None,
                text.strip(),
            )
        ]

    sections: list[
        tuple[
            str | None,
            str,
        ]
    ] = []

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)

        title = match.group(1).strip()

        section = text[match.start() : end].strip()

        sections.append(
            (
                title,
                section,
            )
        )

    return sections


def extract_intent_keywords(
    section: str,
) -> str:
    match = re.search(
        r"\*\*Intent Keywords:\*\*\s*(.+)",
        section,
        flags=re.IGNORECASE,
    )

    return match.group(1).strip() if match else ""


def load_markdown_chunks() -> list[Document]:
    documents: list[Document] = []

    for file_path in sorted(KNOWLEDGE_DIRECTORY.glob("*.md")):
        post = frontmatter.load(file_path)

        content = post.content.strip()

        if not content:
            print(f"Skipping empty file: {file_path.name}")

            continue

        base_metadata = {
            str(key): (normalize_metadata_value(value))
            for (
                key,
                value,
            ) in post.metadata.items()
        }

        base_metadata.update(
            {
                "source": file_path.name,
                "audience": str(
                    base_metadata.get(
                        "audience",
                        "public",
                    )
                ).lower(),
            }
        )

        sections = split_topic_sections(content)

        file_chunk_count = 0

        for (
            section_index,
            (
                section_title,
                section_text,
            ),
        ) in enumerate(sections):
            section_chunks = split_text(section_text)

            for (
                section_chunk_index,
                chunk_text,
            ) in enumerate(section_chunks):
                metadata = base_metadata.copy()

                metadata.update(
                    {
                        "chunk_index": (file_chunk_count),
                        "section_index": (section_index),
                        "section_chunk_index": (section_chunk_index),
                    }
                )

                if section_title:
                    metadata["document_title"] = str(
                        base_metadata.get(
                            "title",
                            file_path.stem,
                        )
                    )

                    metadata["title"] = section_title

                    metadata["section_title"] = section_title

                    metadata["intent_keywords"] = extract_intent_keywords(section_text)
                    # Retrieve using smaller embedding chunks, but pass the
                    # complete approved procedure to the answer generator.
                    metadata["full_section"] = section_text

                documents.append(
                    Document(
                        page_content=chunk_text,
                        metadata=metadata,
                    )
                )

                file_chunk_count += 1

        print(f"Loaded {file_path.name}: {file_chunk_count} chunks")

    return documents


def create_chunk_id(
    document: Document,
) -> str:
    source = str(
        document.metadata.get(
            "source",
            "unknown",
        )
    )

    section = str(
        document.metadata.get(
            "section_title",
            "",
        )
    )

    index = str(
        document.metadata.get(
            "chunk_index",
            0,
        )
    )

    raw = f"{source}:{section}:{index}:{document.page_content}"

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def rebuild_vector_database(
    documents: list[Document],
) -> None:
    CHROMA_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(f"Loading embedding model: {EMBEDDING_MODEL}")

    embeddings = OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url=OLLAMA_BASE_URL,
    )

    client = chromadb.PersistentClient(path=str(CHROMA_DIRECTORY))

    collection_names = [
        (
            collection
            if isinstance(
                collection,
                str,
            )
            else collection.name
        )
        for collection in client.list_collections()
    ]

    if COLLECTION_NAME in collection_names:
        print(f"Deleting existing collection: {COLLECTION_NAME}")

        client.delete_collection(name=COLLECTION_NAME)

    vector_store = Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        collection_metadata={
            "hnsw:space": "cosine",
        },
    )

    ids = [create_chunk_id(document) for document in documents]

    print(f"Embedding {len(documents)} chunks...")

    vector_store.add_documents(
        documents=documents,
        ids=ids,
    )


def main() -> None:
    print(f"Knowledge directory: {KNOWLEDGE_DIRECTORY}")

    if not KNOWLEDGE_DIRECTORY.exists():
        raise RuntimeError("knowledge_base directory does not exist.")

    documents = load_markdown_chunks()

    if not documents:
        raise RuntimeError("No valid Markdown content was found.")

    print(f"Total chunks: {len(documents)}")

    rebuild_vector_database(documents)

    print("\nKnowledge ingestion completed.")

    print(f"Chroma location: {CHROMA_DIRECTORY}")

    print(f"Collection: {COLLECTION_NAME}")


if __name__ == "__main__":
    main()
