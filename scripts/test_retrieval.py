from __future__ import annotations

import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings


load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHROMA_DIRECTORY = (
    PROJECT_ROOT / "data" / "chroma"
)

COLLECTION_NAME = "sjk_public_knowledge"

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
)

EMBEDDING_MODEL = os.getenv(
    "OLLAMA_EMBED_MODEL",
    "all-minilm",
)


def create_vector_store() -> Chroma:
    """Open the existing local ChromaDB collection."""

    embeddings = OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url=OLLAMA_BASE_URL,
    )

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIRECTORY)
    )

    return Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
    )


def print_results(
    query: str,
    vector_store: Chroma,
) -> None:
    """Search Chroma and display the best matching chunks."""

    print()
    print("=" * 70)
    print(f"QUERY: {query}")
    print("=" * 70)

    results = vector_store.similarity_search_with_score(
        query=query,
        k=3,
        filter={
            "audience": "public",
        },
    )

    if not results:
        print("No matching documents were found.")
        return

    for position, result in enumerate(
        results,
        start=1,
    ):
        document, score = result

        print()
        print(f"RESULT {position}")
        print(f"Distance score: {score:.4f}")
        print(
            "Source:",
            document.metadata.get(
                "source",
                "unknown",
            ),
        )
        print(
            "Title:",
            document.metadata.get(
                "title",
                "unknown",
            ),
        )
        print(
            "Topic:",
            document.metadata.get(
                "topic",
                "unknown",
            ),
        )
        print(
            "Audience:",
            document.metadata.get(
                "audience",
                "unknown",
            ),
        )
        print(
            "Chunk:",
            document.metadata.get(
                "chunk_index",
                "unknown",
            ),
        )
        print("-" * 70)
        print(document.page_content)
        print("-" * 70)


def verify_collection() -> None:
    """Confirm that the collection exists and contains chunks."""

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIRECTORY)
    )

    try:
        collection = client.get_collection(
            name=COLLECTION_NAME
        )
    except Exception as error:
        raise RuntimeError(
            "The Chroma collection was not found. "
            "Run scripts/ingest_knowledge.py first."
        ) from error

    count = collection.count()

    print(f"Collection: {COLLECTION_NAME}")
    print(f"Stored chunks: {count}")
    print(f"Database: {CHROMA_DIRECTORY}")
    print(f"Embedding model: {EMBEDDING_MODEL}")

    if count == 0:
        raise RuntimeError(
            "The collection exists but contains no chunks."
        )


def main() -> None:
    """Run automatic and interactive retrieval tests."""

    verify_collection()

    vector_store = create_vector_store()

    test_queries = [
        "What is the school Wi-Fi password?",
        "I am a student and need to connect to Wi-Fi.",
        "I am a guest. How do I connect to Wi-Fi?",
        "The Wi-Fi QR code is not working.",
        "My device cannot connect to the school network.",
    ]

    for query in test_queries:
        print_results(
            query=query,
            vector_store=vector_store,
        )

    print()
    print("=" * 70)
    print("INTERACTIVE TEST")
    print("Enter your own question.")
    print("Type exit to stop.")
    print("=" * 70)

    while True:
        user_query = input("\nQuestion: ").strip()

        if user_query.lower() in {
            "exit",
            "quit",
            "q",
        }:
            print("Retrieval test finished.")
            break

        if not user_query:
            continue

        print_results(
            query=user_query,
            vector_store=vector_store,
        )


if __name__ == "__main__":
    main()