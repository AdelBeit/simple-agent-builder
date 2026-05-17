# Hire a Receptionist
> LeadSaver — AI-powered missed-call lead capture for small businesses When a customer calls and the owner misses it, an AI answers, collects lead info, and automatically submits it to the business's contact form.

Built at a hackathon. Target customers: plumbers, roofers, contractors.

---

## Flow Diagrams

### Current MVP Flow (What's Built)

```
┌─────────────┐
│  Customer   │  Calls business phone number
│   Caller    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│          AgentPhone (Receptionist Agent)                │
│               (webhook mode)                             │
└──────┬──────────────────────────────────────────────────┘
       │ POST /webhook/call
       │ {"event": "call.started", "callId": "...", "text": "..."}
       ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend (port 8000)                │
│              via ngrok tunnel                            │
├─────────────────────────────────────────────────────────┤
│  1. Receive webhook → extract caller utterance          │
│  2. Build conversation history for this call            │
│  3. Send to Gemini 2.5 Flash with system prompt         │
│  4. Get AI response                                      │
│  5. Return {"text": "...", "hangup": false}             │
└──────┬──────────────────────────────────────────────────┘
       │
       ├─ (if hangup) ──────────────────────────────┐
       │                                             │
       │                                             ▼
       │                              ┌──────────────────────────┐
       │                              │  Background Processing   │
       │                              ├──────────────────────────┤
       │                              │ 1. Extract lead info     │
       │                              │    from transcript       │
       │                              │ 2. Save to SQLite        │
       │                              │ 3. Trigger Browser Use   │
       │                              └──────┬───────────────────┘
       │                                     │
       │                                     ▼
       │                      ┌──────────────────────────────────┐
       │                      │    Browser Use (Playwright)      │
       │                      ├──────────────────────────────────┤
       │                      │ 1. Launch Chromium               │
       │                      │ 2. Navigate to localhost:3000    │
       │                      │ 3. Fill contact form fields      │
       │                      │ 4. Click submit                  │
       │                      └──────┬───────────────────────────┘
       │                             │
       │                             ▼
       │              ┌─────────────────────────────────────────┐
       │              │   Express Server (port 3000)            │
       │              │   Peak Flow Plumbing Demo Site          │
       │              ├─────────────────────────────────────────┤
       │              │ POST /contact                           │
       │              │ → Append to submissions.csv             │
       │              └─────────────────────────────────────────┘
       │
       └──► (continues conversation until caller hangs up)
```

**Result:** Business owner opens `submissions.csv` and sees the captured lead.

---

### Planned Full E2E Flow (Post-MVP Vision)

```
┌─────────────────┐
│ Business Owner  │  Calls LeadSaver main number
└────────┬────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│           [1] Greeter Agent (hosted mode)              │
│  "Thanks for calling LeadSaver, the AI receptionist    │
│   service for small businesses. Want to sign up?"      │
└────────┬───────────────────────────────────────────────┘
         │
         │ (owner says yes)
         │
         ▼ TRANSFER
┌────────────────────────────────────────────────────────┐
│       [2] Onboarding Agent (webhook mode)              │
│  POST /webhook/onboarding                              │
├────────────────────────────────────────────────────────┤
│ 1. "What's your business name and website?"            │
│ 2. Gemini conducts interview                           │
│ 3. Browser Use scrapes their website                   │
│ 4. Save business profile to SQLite                     │
│ 5. Call AgentPhone API:                                │
│    POST /v1/agents → create new receptionist agent     │
│    POST /v1/numbers → provision dedicated number       │
│ 6. Set new agent webhook to /webhook/call              │
│ 7. Send AgentMail config summary email                 │
└────────┬───────────────────────────────────────────────┘
         │
         │ "Your receptionist is ready!"
         │ "Your dedicated number is +1 (XXX) XXX-XXXX."
         │ "Want me to transfer you there for a demo?"
         │
         ▼ TRANSFER (if yes)
┌────────────────────────────────────────────────────────┐
│    [3] Custom Receptionist Agent                       │
│    (newly provisioned, webhook → /webhook/call)        │
├────────────────────────────────────────────────────────┤
│ • Answers as the business                              │
│ • Uses Moss RAG over scraped profile                   │
│ • Collects fake lead info from owner (demo)            │
│ • Browser Use submits to their contact form            │
│ • AgentMail sends lead notification                    │
└────────────────────────────────────────────────────────┘
         │
         ▼
   Owner experiences the full customer journey on one call
```

**Result:** Owner gets a working AI receptionist + dedicated phone number in under 5 minutes.

---


## Tech Stack

**Core:** Python 3.14, FastAPI, Gemini 2.5 Flash, AgentPhone, Browser Use (Playwright), SQLite

**Future:** AgentMail, Moss RAG, Supermemory, Stripe/Sponge billing

---


## Running Locally

```bash
# Terminal 1 — demo site
yarn demo          # Express on http://localhost:3000

# Terminal 2 — LeadSaver backend (first time: set up venv)
cd leadsaver
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload --port 8000

# Terminal 3 — ngrok tunnel
yarn ngrok         # Exposes localhost:8000 to AgentPhone webhooks

# Terminal 4 — register webhook with AgentPhone (run once after ngrok is up)
yarn agentphone
```

`.env` keys required:
```
AGENT_PHONE_KEY=<your_agentphone_api_key>
AGENTPHONE_AGENT_ID=<your_agent_id>
AGENTPHONE_NUMBER=<your_phone_number>
GEMINI_API_KEY=<your_gemini_api_key>
NGROK_WEBSITE=<your_ngrok_domain>
```

---

## Testing

Call the provisioned number → Agent answers → Collects lead info → Form submitted to `demo-business/submissions.csv`
