# LeadSaver — Plan v1: Full E2E Call Flow

## Goal
Complete the end-to-end call experience: a business owner calls one number, gets onboarded, gets a dedicated receptionist provisioned, and can demo it live on the same call.

---

## Full Flow

```
Business owner calls +1 (231) 867-0908
        ↓
[1] Greeter Agent (hosted mode, no webhook)
    "Thanks for calling LeadSaver — AI receptionist service..."
    Transfer to onboarding
        ↓
[2] Onboarding Agent (webhook → /webhook/onboarding)
    Collects business info (website scrape or manual)
    Provisions new AgentPhone agent + number
    Saves to SQLite, sends AgentMail config summary
    "Your receptionist is ready! Your number is +1 (XXX) XXX-XXXX.
     Want me to transfer you there for a demo?"
        ↓
[3] Business's own receptionist (webhook → /webhook/call)
    Answers as their business
    Collects fake lead info
    Browser Use submits to their contact form
    Owner gets email notification
```

---

## Build Checklist

### Step 1 — Agent provisioning in complete_onboarding()
- [ ] Call `POST /v1/agents` with business name + system prompt built from their profile
- [ ] Call `POST /v1/numbers` to provision a number, attach to new agent
- [ ] Set webhook URL on new agent to `/webhook/call`
- [ ] Save `agentphone_agent_id` and `agentphone_number` to businesses table
- [ ] Add `agentphone_agent_id` column to SQLite schema

### Step 2 — Transfer offer at end of onboarding
- [ ] After provisioning, onboarding agent says:
  "Your receptionist is all set! Your number is {number}. Want me to transfer you there for a quick demo?"
- [ ] If yes → webhook returns `{"action": "transfer", "transferNumber": "{new_number}"}`
- [ ] If no → webhook returns `{"text": "...", "hangup": true}`

### Step 3 — Greeter agent (hosted mode)
- [ ] Create new AgentPhone agent via API:
  - `voiceMode: "hosted"`
  - `modelTier: "turbo"` (fast, simple task)
  - `systemPrompt`: pitch LeadSaver, ask if they want to sign up
  - `beginMessage`: "Thanks for calling LeadSaver..."
  - `transferNumber`: onboarding AgentPhone number (or same number w/ webhook routing)
- [ ] Point main number `+1 (231) 867-0908` at greeter

### Step 4 — Routing (same number, two agents)
Two options:
- **Option A (simple):** Two separate numbers — greeter on main number, onboarding on a second number. Greeter transfers to second number.
- **Option B (one number):** Webhook on main number handles both greeter and onboarding state in-memory, routes based on session state.

**Decision: Option A** — simpler, cleaner, easier to debug. Provision a second number for onboarding.

---

## Current State Before These Changes

| What | Status |
|---|---|
| Onboarding interview (Gemini + scrape) | ✅ built |
| SQLite save on onboarding complete | ✅ built |
| AgentMail inbox + config email | ✅ built |
| Lead capture webhook | ✅ built |
| Browser Use form submission | ✅ built |
| AgentPhone agent provisioning per business | ❌ not built |
| Transfer offer after onboarding | ❌ not built |
| Greeter agent | ❌ not built |
| End-to-end call tested | ❌ AgentPhone under repair |

---

## Files to Touch

| File | Change |
|---|---|
| `leadsaver/main.py` | Wire provisioning into `complete_onboarding()`, add transfer logic to onboarding webhook |
| `leadsaver/models.py` | Add `agentphone_agent_id` column |
| `leadsaver/agentphone_provision.py` | New file — create agent, provision number, set webhook |
| `leadsaver/agent.py` | `build_begin_message()` already dynamic — no change needed |
| API call (one-off) | Create greeter agent via curl/script |

---

## Post-Plan Backlog (unchanged)
- Moss RAG over scraped website content
- Stripe subscription link in welcome email
- Supermemory as vector store backing Moss
- Sponge per-session micropayments
