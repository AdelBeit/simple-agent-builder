# LeadSaver

AI-powered missed-call lead capture for small businesses. When a customer calls and the owner misses it, an AI answers, collects lead info, and automatically submits it to the business's contact form.

Built at a hackathon. Target customers: plumbers, roofers, contractors.

---

## Status

| Component | Status |
|---|---|
| Peak Flow Plumbing demo site | ✅ Built |
| FastAPI skeleton (all 5 files) | ✅ Built |
| AgentPhone agent provisioned | ✅ Live — `+1 (231) 867-0908` |
| Gemini 2.5 Flash conversation logic | ✅ Built |
| Browser Use form submission | ✅ Built |
| SQLite lead storage | ✅ Built |
| Python deps + Playwright installed | ✅ Done |
| ngrok persistent domain configured | ✅ `syenitic-lila-uneffusively.ngrok-free.dev` |
| End-to-end call test | ⬜ Not yet run |

---

## How It Works

**Live flow:**
1. Customer calls `+1 (231) 867-0908` (Peak Flow Plumbing's AgentPhone number)
2. AgentPhone forwards the call webhook to LeadSaver
3. Gemini 2.5 Flash answers as the business, collects name / phone / service / urgency
4. Browser Use automatically fills and submits the contact form at `localhost:3000`
5. Owner sees the lead appear in `submissions.csv` in real time

**Setup flow (post-MVP):**
- Business owner calls an AgentPhone number → Gemini runs onboarding interview
- Browser Use scrapes their website → Supermemory stores their business profile
- AgentMail sends a config summary → owner replies to tweak it

**Billing:** $49/mo Stripe subscription sent in the welcome email.

---

## Architecture

Two independent servers:

| Server | Stack | Port | Purpose |
|---|---|---|---|
| `demo-business/` | Node/Express | 3000 | Demo plumber site — Browser Use submits forms here |
| `leadsaver/` | Python/FastAPI | 8000 | LeadSaver backend — handles webhooks, runs Gemini + Browser Use |

Only the FastAPI server needs ngrok (for AgentPhone to reach it). Browser Use runs locally and hits `http://localhost:3000` directly.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Language | Python 3.14 |
| Framework | FastAPI + uvicorn |
| AI | Gemini 2.5 Flash (`google-genai` SDK) |
| Voice | AgentPhone (webhook mode) |
| Browser automation | Browser Use + Playwright/Chromium |
| Memory | Hardcoded dict → Supermemory (post-MVP) |
| Email | AgentMail (post-MVP) |
| RAG | Moss (post-MVP) |
| Payments | Stripe link → Sponge micropayments (post-MVP) |
| DB | SQLite (stdlib) |
| Tunnel | ngrok (persistent domain) |

---

## Project Structure

```
demo-business/              # Peak Flow Plumbing demo site
├── index.html              # Single-page site with contact form
├── server.js               # Express — serves static + POST /contact → submissions.csv
└── submissions.csv         # Lead submissions land here

leadsaver/                  # LeadSaver FastAPI backend
├── main.py                 # App entry — 3 webhooks + GET /leads + background orchestration
├── config.py               # Env vars + hardcoded Peak Flow Plumbing profile
├── agent.py                # Gemini 2.5 Flash conversation logic
├── browser_submit.py       # Browser Use → fills and submits contact form
├── models.py               # SQLite init + save_lead / mark_form_submitted / get_all_leads
├── agent.md                # Receptionist persona spec (system prompt source of truth)
├── requirements.txt        # Python deps
└── .venv/                  # Virtual environment (gitignored)

plans/                      # Architecture notes and build log
```

---

## AgentPhone Agent

| Field | Value |
|---|---|
| Agent ID | `cmpa92in80d4djz00jx56l5z2` |
| Phone number | `+1 (231) 867-0908` |
| Voice mode | `webhook` — calls your `/webhook/call` |
| Begin message | "Hi, thanks for calling Peak Flow Plumbing! ..." |

---

## Webhooks

All async — return immediately, process in background:

```
POST /webhook/call          ← AgentPhone: inbound call turn
POST /webhook/email-reply   ← AgentMail: owner config reply (post-MVP)
POST /webhook/browser-done  ← Browser Use: form submission callback (post-MVP)
GET  /leads                 ← View all collected leads as JSON
```

---

## Data Model

```python
businesses:
  id, name, phone, website_url, contact_form_url,
  profile_text, agentphone_number, created_at

leads:
  id, business_id, caller_phone, caller_name,
  issue_description, call_transcript,
  form_submitted (bool), created_at
```

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
yarn ngrok         # https://syenitic-lila-uneffusively.ngrok-free.dev → localhost:8000

# Terminal 4 — register webhook with AgentPhone (run once after ngrok is up)
yarn agentphone
```

`.env` keys required:
```
AGENT_PHONE_KEY=
AGENTPHONE_AGENT_ID=
AGENTPHONE_NUMBER=
GEMINI_API_KEY=
NGROK_WEBSITE=
```

---

## Demo Checklist

- [ ] `yarn demo` → Peak Flow Plumbing loads at `localhost:3000`
- [ ] Contact form submits to `submissions.csv`
- [ ] `uvicorn main:app` starts at `localhost:8000`
- [ ] `yarn ngrok` tunnel is up
- [ ] `yarn agentphone` → "Webhook updated."
- [ ] Call `+1 (231) 867-0908` — AI answers as Peak Flow Plumbing within 2s
- [ ] AI collects name, phone, service type in under 3 turns
- [ ] Browser Use fills and submits the contact form
- [ ] New row appears in `submissions.csv`
- [ ] `GET /leads` returns collected leads as JSON

---

## Post-MVP Backlog

- AgentMail onboarding interview flow ✅ built
- Browser Use scraping during onboarding ✅ built
- Moss RAG over scraped business website (currently runs against SQLite `profile_text` — flat string, works for demo, degrades at scale)
- Sponge per-session micropayments
- Stripe subscription link in welcome email
- Supermemory (swap in as vector store backing Moss RAG when profiles get large or multi-tenant scale matters)
