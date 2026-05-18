# Integration Plan: Moss

## What It Does (from hackathon brief)
Moss is a RAG (Retrieval-Augmented Generation) service — sub-10ms semantic search over a knowledge base. In LeadSaver's architecture, Moss replaces the direct SQLite `profile_text` injection with a hosted RAG query at call time.

## ⚠️ Docs Status
Public API docs not found at `moss.ai` or `viamoss.ai` — likely a hackathon-exclusive product. **Need API key and docs from hackathon organizers before implementing.**

Likely URL candidates:
- `https://api.viamoss.ai`
- `https://api.moss.ai`

---

## Expected Integration Shape (to verify with actual docs)

### Ingest (onboarding — store scraped website)
```
POST /ingest  (or /documents or /knowledge)
Authorization: Bearer MOSS_API_KEY
{
  "content": "<scraped business profile text>",
  "namespace": "<business_id>",   // isolation per business
  "metadata": {"business": "Peak Flow Plumbing"}
}
```

### Query (at call time — before Gemini responds)
```
POST /query  (or /search or /rag)
Authorization: Bearer MOSS_API_KEY
{
  "query": "<caller's issue text>",
  "namespace": "<business_id>",
  "top_k": 3
}
→ returns relevant text chunks
```

---

## Implementation Plan

### Files to change

| File | Change |
|---|---|
| `leadsaver/moss.py` | New — `ingest(business_id, text)`, `query(business_id, caller_text) → str` |
| `leadsaver/main.py` | `complete_onboarding()` → call `moss.ingest()` after scraping |
| `leadsaver/agent.py` | `get_reply()` → call `moss.query()` and inject result into system prompt context |
| `leadsaver/config.py` | Add `MOSS_API_KEY`, `MOSS_BASE_URL` |

### New file: `moss.py`
```python
import httpx
from config import MOSS_API_KEY, MOSS_BASE_URL

def ingest(business_id: int, text: str) -> bool:
    ...

def query(business_id: int, caller_text: str, top_k: int = 3) -> str:
    ...
```

### How it fits into the call flow
```
Caller says: "my bathtub won't drain"
    ↓
moss.query(business_id=1, "bathtub won't drain")
    → "Drain Cleaning: Kitchen, bathroom, main-line clogs cleared; hydro-jetting available..."
    ↓
Injected into Gemini system prompt as context
    ↓
Gemini responds with business-specific knowledge
```

---

## .env Keys Needed
```
MOSS_API_KEY=
MOSS_BASE_URL=https://api.viamoss.ai  # confirm with hackathon organizers
```

## Priority
Medium — good demo story ("sub-10ms RAG over your business's knowledge"). Implement after E2E is stable and Moss docs are obtained.
