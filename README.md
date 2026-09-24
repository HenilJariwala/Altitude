# Altitude Routing + RAG Improvements

This patch is intended for the `routing-rag-improvements` branch.

Changed files:

- `app/core/retrieval_profile.py` (new)
- `app/core/rag.py`
- `app/core/assistant.py`
- `app/core/wifi_router.py`
- `app/core/support_router.py`
- `app/core/extended_support_router.py`
- `scripts/ingest_knowledge.py`
- `scripts/test_domain_aware_routing.py` (new)
- `.env.example`

## Main changes

1. Topic-aware RAG profile separates the actual failure from working context after words such as `but` and `even though`.
2. RAG candidates are filtered by product/device/problem compatibility before semantic ranking.
3. Learned ticket knowledge uses stricter topic + symptom compatibility.
4. Weak semantic matches use stronger confidence gates.
5. Wi-Fi access routing no longer hijacks certificate/privacy-warning questions when Wi-Fi is already working.
6. Administrator-password prompts during software installation are treated as an IT approval/install workflow rather than a password-reveal request.
7. Network-password account lockout is no longer misclassified as a request to reveal credentials.
8. Added high-confidence routes for several failures found by the 40-question benchmark: Chromebook charging, forced update restarts, projector image quality, browser pop-ups, microphone input, corrupted PDFs, stylus, calendar sync, scan-to-email, Smartboard calibration, account lockout, battery/display flicker, local database errors, Outlook sync, microphone-in-use, VPN network drives, ghost cursor, Adobe PDF garbled printing, audio/video sync, and managed Chromebook Wi-Fi selection.

## Test

```bash
cd "/Users/HenilJariwala/Documents/Altitude"
source .venv/bin/activate
PYTHONPATH=app python scripts/test_domain_aware_routing.py
python scripts/test_all_features.py --quick
```

Then rebuild Chroma because new retrieval metadata is added during ingestion:

```bash
PYTHONPATH=app python scripts/ingest_knowledge.py
```

Then rerun the same 40-question benchmark.
