# LeadSaver — Hackathon Plan v1

## Context
Solo hackathon build. LeadSaver captures missed-call leads for small businesses (plumbers, roofers, contractors). When a customer calls and the owner misses it, an AI answers, collects lead info, and submits it to the business's contact form automatically. Goal is MVP as fast as possible with heavy hardcoding; polish only after the core demo loop works.

---

## Opinionated Answers to Your Questions

### Language: Python (FastAPI)
Browser Use is Python-only — this decides it. FastAPI gives async webhooks with near-zero boilerplate. Use `uv` for package management (fast installs). No Node.

### Build Order (strict, cut here if time runs out)

| Priority | Step | Can fake/skip for demo? |
|---|---|---|
| 1 | Fake business website + contact form (static HTML) | No — this is your demo target |
| 2 | FastAPI skeleton with all 3 webhook stubs returning 200 | No — foundation |
| 3 | AgentPhone inbound call → Gemini 2.5 Flash collects lead | No — core value prop |
| 4 | Browser Use submits lead to fake contact form | No — the wow moment |
| 5 | Hardcoded business profile (name, phone, form URL) | Hardcode, don't build onboarding yet |
| 6 | SQLite leads table (persist collected leads) | Yes, can log to stdout for demo |
| 7 | Supermemory business profile RAG | Yes, hardcode profile string instead |
| 8 | AgentMail onboarding interview | Yes, skip entirely for demo |
| 9 | Moss RAG integration | Yes, replace with hardcoded profile |
| 10 | Stripe billing link | Yes, paste static link in email |
| 11 | Sponge micropayments | Yes, stub/fake it |

**MVP demo = steps 1–5 only.**

### Demo Path (guarantee this works)
1. Judge calls the AgentPhone number
2. AI answers: "Hi, you've reached [Fake Plumber Co]. The owner is unavailable. I can take your info."
3. AI collects: name, phone, what they need
4. Browser Use opens fake contact form, fills it, submits
5. Judges see the form submission appear live
6. Done. Everything else is bonus.

**What to hardcode**: One Python dict in `config.py` — mirrors the Peak Flow Plumbing identity above exactly. Browser Use reads `contact_form_url = "http://localhost:3000/#contact"` from this dict.

### Data Model (minimal)

```python
# SQLite tables (or just in-memory dicts for demo)

businesses:
  id, name, phone, website_url, contact_form_url,
  profile_text,  # replaces Supermemory for MVP
  agentphone_number, created_at

leads:
  id, business_id, caller_phone, caller_name,
  issue_description, call_transcript,
  form_submitted (bool), created_at
```

Use SQLite + SQLAlchemy (or raw sqlite3). No Postgres needed for hackathon.

### Webhook Architecture

Three inbound webhooks, all async, all return 202 immediately:

```
POST /webhook/call          ← AgentPhone: new inbound call
POST /webhook/email-reply   ← AgentMail: owner replied to config email
POST /webhook/browser-done  ← Browser Use: form submission complete (if async)
```

Pattern for each:
```python
@app.post("/webhook/call")
async def handle_call(payload: dict, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_call, payload)
    return {"status": "accepted"}
```

No Redis, no Celery — FastAPI BackgroundTasks is sufficient for a single-server hackathon demo.

### Top 5 Unknowns to Spike First (in order)

1. **AgentPhone voice API** — Does it stream audio to your endpoint in real-time? Does it support interruption? Is there a Python SDK or is it REST? **Spike: read their docs, make a test call before writing any logic.**
2. **Moss API shape** — Hackathon sponsor, unknown until you have keys. Likely REST. Spike: check if it needs a vector store pre-loaded or if it's a hosted service.
3. **Sponge API shape** — Same situation. Spike: confirm if it's real or purely aspirational for the pitch.
4. **Browser Use + form submission reliability** — Since you control the fake site, this should be 100% reliable. Build the fake form first so you can test BU immediately.
5. **Gemini 2.5 Flash latency on voice** — Real-time voice needs <500ms response. Test with a simple Q&A loop before building the full lead-collection flow.

---

## Tech Stack (final)

```
Language:    Python 3.12
Framework:   FastAPI + uvicorn
AI:          Gemini 2.5 Flash (google-generativeai)
Voice:       AgentPhone SDK/REST
Automation:  Browser Use (browser-use Python package)
Memory:      Hardcoded dict → Supermemory later
Email:       AgentMail SDK → skip for MVP
RAG:         Moss → skip for MVP (use hardcoded profile)
Payments:    Stripe link hardcoded → Sponge later
DB:          SQLite (sqlite3 stdlib)
Deploy:      localhost + ngrok for webhooks (demo day)
```

---

## Architecture Clarification: Two Separate Servers

These are **two independent processes** — do not conflate them:

| Server | Stack | Port | Purpose |
|---|---|---|---|
| **demo-contact-us/** | Node/Express (already exists) | 3000 | Fake plumber business site — Browser Use submits forms here |
| **leadsaver/** | Python/FastAPI | 8000 | LeadSaver product — handles AgentPhone webhooks, runs Gemini + Browser Use |

**ngrok**: Only the FastAPI server (port 8000) needs ngrok for AgentPhone to reach it. Browser Use runs locally and hits `http://localhost:3000` directly — no tunnel needed for the demo site.

---

## Demo Site: "Peak Flow Plumbing" (demo-contact-us/)

Fictional local plumber. Clone/expand the existing `index.html` into a full business site.

**Business identity** (hardcode these same values in `config.py`):
```
Name:     Peak Flow Plumbing
Tagline:  Austin's Most Trusted Plumber Since 1998
Phone:    (512) 555-0187
Address:  4821 Burnet Rd, Austin, TX 78756
Email:    service@peakflowplumbing.com
Hours:    Mon–Fri 7am–7pm, Sat 8am–5pm, 24/7 Emergency
```

**Site sections** (single-page HTML, no frameworks):
1. **Header** — logo text "Peak Flow Plumbing", phone number big + red, "Request Service" anchor button
2. **Hero** — dark blue bg, "Austin's #1 Trusted Plumber", subtext "Same-day service. Flat-rate pricing. No surprises.", two CTAs: Call Now + Get a Free Quote
3. **Services** — 6 cards: Drain Cleaning, Leak Repair, Water Heater Install/Repair, Pipe Replacement, Emergency Plumbing, Sewer Line Inspection
4. **Why Choose Us** — 3 columns: Licensed & Insured, Flat-Rate Pricing, 24/7 Emergency
5. **Testimonials** — 3 fake 5-star reviews (generated copy)
6. **Contact Form** (id="contactForm") — fields: Name, Phone, Email, Service Needed (dropdown matching services above), Message/Description, Submit button
7. **Footer** — address, phone, hours, copyright

**Contact form field names** (Browser Use targets these exactly):
```html
<input name="name">
<input name="phone">
<input name="email">
<select name="service"> <!-- Drain Cleaning | Leak Repair | Water Heater | Pipe Replacement | Emergency | Sewer Line --></select>
<textarea name="message">
```

**server.js update**: Add `phone` and `service` columns to CSV append. Keep `/contact` POST endpoint unchanged shape — just log all fields.

---

## File Structure

```
demo-contact-us/          # Already exists — expand index.html
├── index.html            # Full Peak Flow Plumbing site (single page)
├── server.js             # Express — serves static + handles POST /contact
└── submissions.csv       # Lead submissions land here (visible in demo)

leadsaver/                # Create this
├── main.py               # FastAPI app, all routes
├── config.py             # Hardcoded Peak Flow Plumbing profile + env vars
├── agent.py              # Gemini conversation logic
├── browser_submit.py     # Browser Use → POST to localhost:3000/contact
├── models.py             # SQLite schema + helpers
└── .env                  # API keys
```

---

## Verification / Demo Checklist

- [ ] `cd demo-contact-us && node server.js` → Peak Flow Plumbing site at localhost:3000
- [ ] Contact form visible, submits to `submissions.csv`
- [ ] `cd leadsaver && uvicorn main:app --reload` → FastAPI at localhost:8000
- [ ] `ngrok http 8000` → copy HTTPS URL into AgentPhone dashboard as webhook
- [ ] AgentPhone number forwarded to `https://<ngrok>/webhook/call`
- [ ] Test call: AI answers as "Peak Flow Plumbing" within 2s
- [ ] AI collects name, phone, service type in < 3 turns
- [ ] Browser Use fills and submits the contact form on localhost:3000
- [ ] New row appears in `submissions.csv` with caller's info
- [ ] `GET /leads` on FastAPI returns collected leads as JSON

---

## Post-MVP Backlog (only if time permits)
- Supermemory for business profiles
- AgentMail onboarding interview
- Moss RAG over scraped website
- Sponge per-session micropayments
- Stripe subscription link in welcome email
- Browser Use scraping the business website during onboarding
