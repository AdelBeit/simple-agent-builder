# Main Branch Changes Missing from Supermemory Branch

**Branch Comparison:** `supermemory` → `main`  
**Commits Missing:** 10 commits  
**Date:** 2026-05-18

## Summary

The supermemory branch was created from an older version of main. Main has received 10 commits with bug fixes and improvements that need to be merged into supermemory.

---

## Changes in Main (not in Supermemory)

### 🐛 Critical Bug Fixes

#### 1. **Fix greeter double-prompt bug** (commit 81b82ff)
**File:** `leadsaver/main.py`
**Issue:** Greeter wasn't processing the first caller message if the caller spoke immediately
**Fix:** Process first message immediately if caller already spoke on init event

```python
# NEW: Check for caller_text BEFORE checking if session exists
caller_text = data.get("transcript") or payload.get("text", "")

if session_id not in active_greeter:
    active_greeter[session_id] = {"history": [], "turns": 0}
    if not caller_text:
        # Pure init event — no caller speech yet
        return JSONResponse({"text": "", "hangup": False})
    # Caller already spoke — fall through and process immediately
```

#### 2. **Fix greeter→onboarding routing** (commit aaf6f91)
**File:** `leadsaver/main.py`
**Issue:** background_tasks not passed when routing to onboarding
**Fix:** 
```python
# Changed from:
return await handle_onboarding(request)
# To:
return await handle_onboarding(request, background_tasks)
```

#### 3. **Fix 3 background task bugs** (commit 97c02dc)
**Files:** `leadsaver/main.py`, `leadsaver/moss_rag.py`, `leadsaver/agentmail.py`

**3a. Import scope bug:**
```python
# Move get_db to top-level imports instead of importing in functions
from models import get_db  # at top
```

**3b. Moss IndexInfo object bug:**
```python
# Moss API returns IndexInfo objects, not dicts
def _ix_name(ix):
    if hasattr(ix, "name"): return ix.name
    if hasattr(ix, "get"): return ix.get("name") or ix.get("id")
    return str(ix)
existing = [_ix_name(ix) for ix in (indexes or [])]
```

**3c. AgentMail duplicate inbox bug:**
```python
# Add retry logic for 403 errors (inbox already exists)
for attempt, suffix in enumerate(["", f"-{int(time.time()) % 10000}"]):
    resp = httpx.post(...)
    if resp.status_code == 403 and attempt == 0:
        continue  # retry with timestamp suffix
```

#### 4. **Fix AgentMail retry logic** (commit 5b7c006)
**File:** `leadsaver/agentmail.py`
**Issue:** Only caught specific 'taken' text, not all 403s
**Fix:** Catch any 403 status code regardless of error message

---

### ✨ Feature Enhancements

#### 5. **Demo mode for AgentMail inboxes** (commit d26feb4)
**Files:** `leadsaver/agentmail.py`, `leadsaver/config.py`
**Purpose:** Avoid inbox sprawl during testing by reusing shared inbox

```python
# config.py - NEW
DEMO_INBOX_ID = "peak-flow-plumbing@agentmail.to"
DEMO_INBOX_EMAIL = "peak-flow-plumbing@agentmail.to"

# agentmail.py - NEW
if DEMO_MODE:
    return {"id": DEMO_INBOX_ID, "email": DEMO_INBOX_EMAIL}
```

#### 6. **Improve email copy** (commit 67f5066, 3cc55e3)
**File:** `leadsaver/agentmail.py`
**Changes:**
- Added context block above Stripe button with value prop
- Better pricing copy: "$49/month, no setup fees, cancel anytime"
- Table-based button layout prevents mobile email clipping
- More professional formatting with background colors

```html
<!-- NEW: Context box with value prop before CTA -->
<table cellpadding="0" cellspacing="0" width="100%" style="...">
  <tr><td style="padding:16px;">
    <p>Your AI receptionist for {name} is live.</p>
    <p>It will answer missed calls, collect lead info...</p>
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="background:#0a1f44;">
        <a href="{STRIPE_PAYMENT_LINK}">Activate — $49/mo</a>
      </td>
    </tr></table>
  </td></tr>
</table>
```

#### 7. **Force accept any URL in onboarding** (commit d4b797c)
**File:** `leadsaver/onboarding.py`
**Purpose:** Accept localhost URLs during demo/testing
**Change:** Updated system prompt to never reject URLs including localhost

```diff
+IMPORTANT: Accept ANY URL the caller provides, including localhost addresses. 
+Never tell the caller their URL is invalid or ask them to provide a different one.
```

---

### 🎨 UX Improvements

#### 8. **Increase greeter→onboarding pause to 2 seconds** (commit 2e99965)
**File:** `leadsaver/main.py`
**Purpose:** Let TTS finish greeter sign-off before onboarding begins

```python
# Increased from 1.5s to 2s
await asyncio.sleep(2)
return JSONResponse({"text": f"{reply} {ONBOARDING_BEGIN}", "hangup": False})
```

#### 9. **Rename 'setup team' to 'onboarding team'** (commit a711f24)
**File:** `leadsaver/main.py`
**Purpose:** Consistent terminology

```python
- "Let me connect you with our setup team — takes about 2 minutes!"
+ "Let me connect you with our onboarding team — takes about 2 minutes!"
```

---

## Files Modified in Main

| File | Changes |
|------|---------|
| `leadsaver/agentmail.py` | Demo mode, retry logic, email improvements (61 lines changed) |
| `leadsaver/config.py` | Demo inbox constants (4 lines changed) |
| `leadsaver/main.py` | Greeter fixes, routing fixes, import cleanup (24 lines changed) |
| `leadsaver/moss_rag.py` | IndexInfo object handling (7 lines changed) |
| `leadsaver/onboarding.py` | Accept any URL including localhost (5 lines changed) |

**Total:** 101 lines changed (+70, -31)

---

## Recommendation

✅ **All changes should be merged into supermemory branch**

All 10 commits are:
- Bug fixes (critical)
- Feature enhancements (valuable)
- UX improvements (polish)

**No conflicts expected with supermemory implementation** - supermemory changes are isolated to:
- New file: `supermemory.py`
- Minimal changes to: `agent.py`, `browser_submit.py`, `config.py`

**Merge strategy:**
1. Merge main into supermemory branch (or vice versa)
2. Test onboarding flow with supermemory enabled
3. Test greeter→onboarding routing
4. Verify email delivery and formatting
