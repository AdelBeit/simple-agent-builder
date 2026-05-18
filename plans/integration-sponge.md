# Integration Plan: Sponge

## What It Does
Sponge (YC W26, founded by ex-Stripe engineers) provides wallets for AI agents — enabling agents to autonomously hold and spend money without human intervention. Products: **Sponge Wallet** (agent holds funds) and **Sponge Gateway** (business receives funds).

In LeadSaver: each Browser Use session costs money (compute). Sponge handles per-session micropayments autonomously — the LeadSaver agent pays for its own Browser Use costs from its Sponge wallet, rather than charging the business owner a flat fee that may not reflect actual usage.

## ⚠️ Docs Status
No public API documentation found. Sponge is a hackathon sponsor — **need API key and docs from hackathon organizers.**

Likely endpoints (to verify):
- `https://api.sponge.so` or `https://api.sponge.ai`

---

## Expected Integration Shape (to verify with actual docs)

### Initialize wallet / session
```
POST /sessions
Authorization: Bearer SPONGE_API_KEY
{
  "agent_id": "leadsaver",
  "budget_usd": 0.10,   // max spend per Browser Use session
  "purpose": "browser_automation"
}
→ { "session_id": "...", "wallet_address": "..." }
```

### Authorize payment (before Browser Use runs)
```
POST /sessions/{session_id}/authorize
{
  "amount_usd": 0.05,
  "description": "Browser Use form submission"
}
```

### Settle (after Browser Use completes)
```
POST /sessions/{session_id}/settle
{
  "actual_amount_usd": 0.03
}
```

---

## Implementation Plan

### Files to change

| File | Change |
|---|---|
| `leadsaver/sponge.py` | New — `start_session()`, `authorize(session_id, amount)`, `settle(session_id, amount)` |
| `leadsaver/browser_submit.py` | Wrap `submit_lead_to_form()` and `scrape_business_website()` with Sponge session |
| `leadsaver/config.py` | Add `SPONGE_API_KEY`, `SPONGE_BASE_URL` |

### New file: `sponge.py`
```python
import httpx
from config import SPONGE_API_KEY, SPONGE_BASE_URL

def start_session(budget_usd: float = 0.10) -> str:
    """Returns session_id."""
    ...

def authorize(session_id: str, amount_usd: float, description: str) -> bool:
    ...

def settle(session_id: str, actual_amount_usd: float) -> bool:
    ...
```

### How it fits into the call flow
```
Call completed, lead extracted
    ↓
sponge.start_session(budget=0.10)
    ↓
sponge.authorize(session_id, 0.05, "Browser Use form submission")
    ↓
Browser Use submits contact form
    ↓
sponge.settle(session_id, actual_cost)
```

---

## .env Keys Needed
```
SPONGE_API_KEY=
SPONGE_BASE_URL=https://api.sponge.so  # confirm with hackathon organizers
```

## Priority
Low for demo functionality — Browser Use already works without it. High for hackathon pitch story ("AI agent pays for its own compute"). Implement after E2E is stable and Sponge docs are obtained.

## Pitch Angle
> "LeadSaver doesn't just capture leads — it pays for its own costs. Every Browser Use session is funded autonomously by the agent via Sponge, with no manual invoicing or batch billing."
