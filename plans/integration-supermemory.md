# Integration Plan: Supermemory

## What It Does
Vector store / memory layer for business profiles. Replaces the SQLite `profile_text` flat string with semantic search — at call time, query the most relevant chunks of a business's knowledge base instead of dumping the whole profile into the system prompt.

## Current State (without Supermemory)
- `businesses.profile_text` in SQLite holds a plain-text dump from the website scraper
- Entire profile injected into Gemini system prompt on every call turn
- Works for demo, degrades for large profiles or many businesses

## What Changes With Supermemory
- On onboarding: scraped website content chunked and stored in Supermemory (one space per business, keyed by `containerTag = business_id`)
- At call time: query Supermemory with the caller's issue → get top-k relevant chunks → inject into Gemini context instead of full profile
- On owner email reply: update the relevant memory entries

---

## API Reference

**Base URL:** `https://api.supermemory.ai/v3`
**Auth:** Bearer token (`SUPERMEMORY_API_KEY`)

### Add content (onboarding)
```
POST /ingest/add-document
{
  "content": "<scraped text chunk>",
  "containerTag": "<business_id>",
  "metadata": {"business_id": 1, "source": "website"}
}
```

### Search at call time
```
POST /recall-search/search-memory-entries
{
  "query": "<caller's issue, e.g. 'sink won't drain'>",
  "containerTag": "<business_id>",
  "limit": 3
}
→ returns relevant chunks to inject into system prompt
```

### Update on email reply
```
POST /content-management/update-a-memory-creates-new-version
{
  "id": "<memory_id>",
  "content": "<updated content>"
}
```

---

## Implementation Plan

### Files to change

| File | Change |
|---|---|
| `leadsaver/supermemory.py` | New — `store_profile(business_id, text)`, `query_profile(business_id, query) → str` |
| `leadsaver/browser_submit.py` | `scrape_business_website()` → call `store_profile()` after scraping |
| `leadsaver/agent.py` | `_build_system_prompt()` → call `query_profile()` instead of using `profile_text` directly |
| `leadsaver/config.py` | Add `SUPERMEMORY_API_KEY` |

### New file: `supermemory.py`
```python
import httpx
from config import SUPERMEMORY_API_KEY

BASE = "https://api.supermemory.ai/v3"

def store_profile(business_id: int, text: str):
    # Chunk text into ~500 char pieces, store each with containerTag=business_id
    ...

def query_profile(business_id: int, query: str, limit: int = 3) -> str:
    # Search and return joined relevant chunks
    ...
```

### Key decision: chunk size
Split scraped text by paragraph (~500 chars). Don't send one giant blob — that defeats the point of RAG.

---

## .env Keys Needed
```
SUPERMEMORY_API_KEY=
```

## Priority
Low for demo — SQLite profile works fine. Add after full E2E is stable.

Sources:
- [Supermemory Docs](https://supermemory.ai/docs/)
