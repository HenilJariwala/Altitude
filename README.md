# SJK AID — Altitude IT Support Assistant

SJK AID is a local-first Streamlit helpdesk assistant. It routes common school IT workflows, retrieves approved procedures from a local Chroma knowledge base, and uses Ollama to generate grounded answers.

## Highlights

- Conversation-aware follow-ups: a reply such as **“I am using a Mac”** keeps the original issue instead of becoming a new query.
- Operating-system safety: macOS requests cannot use Windows-only documents, and vice versa.
- Deterministic routes for Wi-Fi, printers, AirPlay, inventory, account recovery, phishing, and common conversations.
- Local Ollama inference and local Chroma storage.
- Inventory API validation, bounded timeouts, no redirects, optional bearer authentication, and local suppression of self-signed-certificate warnings.
- Redacted, size-limited local question logs.

## Requirements

- Python 3.11 or newer
- Ollama running locally or at a configured `OLLAMA_BASE_URL`
- Recommended RAM: at least 8 GB for the default small model

## Quick start on macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Install the default Ollama models:

```bash
ollama pull qwen2.5:1.5b
ollama pull all-minilm
```

Build the local knowledge database after installing dependencies and starting Ollama:

```bash
PYTHONPATH=app python scripts/ingest_knowledge.py
```

Run the application:

```bash
streamlit run app/main.py
```

Then open the local URL printed by Streamlit.

## Configuration

Copy `.env.example` to `.env`. Never commit `.env`; it may contain the inventory API token.

| Variable | Purpose |
|---|---|
| `OLLAMA_MODEL` | Chat model used to produce grounded answers |
| `OLLAMA_EMBED_MODEL` | Embedding model used by ingestion and retrieval |
| `OLLAMA_BASE_URL` | Ollama server URL |
| `RAG_MAX_DISTANCE` | Maximum semantic distance unless topic matching is strong |
| `RAG_DEBUG` | Shows retrieval diagnostics in answers when `true` |
| `USE_LLM_FOR_RAG` | Enables model-generated RAG answers when `true` |
| `INVENTORY_API_URL` | Optional inventory endpoint |
| `INVENTORY_API_TOKEN` | Optional bearer token |
| `INVENTORY_API_VERIFY_SSL` | Keep `true` for trusted HTTPS certificates |
| `INVENTORY_API_TIMEOUT_SECONDS` | Inventory read timeout |

Setting `INVENTORY_API_VERIFY_SSL=false` should only be used for a known internal server with a self-signed certificate. A trusted internal CA certificate is preferable.

## Knowledge-base workflow

1. Edit or add approved Markdown files in `knowledge_base/`.
2. Include YAML frontmatter with at least `title`, `topic`, and `audience: public`. OS-specific files should also use `platform: macos` or `platform: windows`.
3. Rebuild Chroma:

```bash
PYTHONPATH=app python scripts/ingest_knowledge.py
```

Topic sections are embedded in smaller chunks for retrieval, while the complete approved topic is retained as answer context.

## Verification

Run the automated regression suite and static checks:

```bash
PYTHONPATH=app python scripts/regression_tests.py
python -m compileall -q app scripts
ruff check app scripts
basedpyright --pythonpath "$(command -v python)"
```

`ruff` and `basedpyright` are development tools and are not required to run the application.

An interactive retrieval test is also available after the knowledge database is built:

```bash
PYTHONPATH=app python scripts/test_retrieval.py
```

## Security notes

- Do not place passwords, Wi-Fi credentials, recovery codes, or API tokens in the knowledge base.
- Do not expose Ollama, Chroma, or the inventory API directly to the public internet.
- Run the Streamlit app behind school authentication and HTTPS before production use.
- Question logging is local and redacts common secrets, email addresses, phone numbers, and long account-like numbers, but logs should still be access-controlled and retained only as long as required.
- The assistant is designed for approved Tier-1 instructions and should escalate unresolved or sensitive cases to the IT Helpdesk.
