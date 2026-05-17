# LeadSaver

AI-powered missed-call lead capture for small businesses. When a customer calls and the owner misses it, an AI answers, collects lead info, and automatically submits it to the business's contact form.

Built at a hackathon. Target customers: plumbers, roofers, contractors.

---

## How It Works

**Live flow:**
1. Customer calls the business, owner misses it
2. AgentPhone forwards the call to LeadSaver
3. Gemini 2.5 Flash answers as the business, collects name/phone/service needed
4. Browser Use automatically fills and submits the business's contact form
5. Owner sees the lead appear in real time

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

Only the FastAPI server needs an ngrok tunnel (for AgentPhone to reach it). Browser Use runs locally and hits `http://localhost:3000` directly.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Language | Python 3.12 |
| Framework | FastAPI + uvicorn |
| AI | Gemini 2.5 Flash (`google-generativeai`) |
| Voice | AgentPhone |
| Browser automation | Browser Use |
| Memory | Hardcoded dict → Supermemory (post-MVP) |
| Email | AgentMail (post-MVP) |
| RAG | Moss (post-MVP) |
| Payments | Stripe link → Sponge micropayments (post-MVP) |
| DB | SQLite |
| Demo tunnel | ngrok |

---

## Project Structure

```
demo-business/          # Fake plumber site (Peak Flow Plumbing)
├── index.html          # Single-page business site with contact form
├── server.js           # Express — serves static + handles POST /contact
└── submissions.csv     # Lead submissions land here (visible in demo)

leadsaver/              # LeadSaver backend
├── main.py             # FastAPI app, all routes
├── config.py           # Hardcoded business profile + env vars
├── agent.py            # Gemini conversation logic
├── browser_submit.py   # Browser Use → submits to localhost:3000/contact
└── models.py           # SQLite schema + helpers

plans/                  # Architecture notes and build plan
```

---

## Webhooks

Three inbound endpoints, all async (return 202 immediately, process in background):

```
POST /webhook/call          ← AgentPhone: new inbound call
POST /webhook/email-reply   ← AgentMail: owner replied to config email
POST /webhook/browser-done  ← Browser Use: form submission complete
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
# Terminal 1 — demo business site
cd demo-business
npm install
node server.js
# → http://localhost:3000

# Terminal 2 — LeadSaver backend
cd leadsaver
uv pip install -r requirements.txt
uvicorn main:app --reload
# → http://localhost:8000

# Terminal 3 — expose LeadSaver to AgentPhone
ngrok http 8000
# → copy HTTPS URL into AgentPhone dashboard as webhook
```

Copy `.env.example` to `.env` and fill in your API keys before starting.

---

## Demo Checklist

- [ ] Peak Flow Plumbing site loads at `localhost:3000`
- [ ] Contact form visible and submits to `submissions.csv`
- [ ] FastAPI running at `localhost:8000`
- [ ] ngrok URL set as AgentPhone webhook
- [ ] Test call: AI answers as "Peak Flow Plumbing" within 2s
- [ ] AI collects name, phone, service type in under 3 turns
- [ ] Browser Use fills and submits the contact form
- [ ] New row appears in `submissions.csv` with caller's info
- [ ] `GET /leads` returns collected leads as JSON

---

## Post-MVP Backlog

- Supermemory for persistent business profiles
- AgentMail onboarding interview flow
- Moss RAG over scraped business website
- Sponge per-session micropayments
- Stripe subscription link in welcome email
- Browser Use scraping during onboarding
