# LeadSaver — Current State (Session 2 Handoff)

## What's Built and Working

### demo-business/ — Peak Flow Plumbing site
- Full single-page site: header, hero, 6 services, trust pillars, testimonials, contact form
- Express server on port 3000, saves submissions to `submissions.csv`
- Phone number updated to real AgentPhone number: **(231) 867-0908**

### leadsaver/ — FastAPI backend
All files written and imports verified clean:

| File | What it does |
|---|---|
| `main.py` | FastAPI app — `/webhook/call`, `/webhook/email-reply`, `/webhook/browser-done`, `GET /leads` |
| `config.py` | Env vars + hardcoded Peak Flow Plumbing business profile |
| `agent.py` | Gemini 2.5 Flash via `google-genai` SDK — `get_reply()` drives conversation, `extract_lead_info()` parses transcript |
| `browser_submit.py` | Browser Use async form filler — hits `localhost:3000/#contact` |
| `models.py` | SQLite `businesses` + `leads` tables, save/query helpers |
| `agent.md` | Receptionist persona spec — system prompt source of truth |
| `requirements.txt` | Uses `google-genai` (not deprecated `google-generativeai`) |

### AgentPhone
- Agent created: `cmpa92in80d4djz00jx56l5z2`
- Number provisioned: `+1 (231) 867-0908`
- Mode: `webhook` — sends each call turn to `/webhook/call`
- Webhook URL: set via `yarn agentphone` script (ngrok domain)

### Infrastructure
- Python venv created at `leadsaver/.venv/`
- All deps installed including Playwright + Chromium
- ngrok persistent domain: `syenitic-lila-uneffusively.ngrok-free.dev`
- `package.json` scripts: `yarn demo`, `yarn dev`, `yarn ngrok`, `yarn agentphone`

### .env keys (all filled)
- `AGENT_PHONE_KEY`
- `AGENTPHONE_AGENT_ID`
- `AGENTPHONE_NUMBER`
- `GEMINI_API_KEY`
- `NGROK_WEBSITE`

---

## What's NOT Done Yet

- **End-to-end call test** — no real call has been made yet
- **AgentPhone webhook payload shape** — assumed field names (`callId`, `event`, `text`); may need adjustment after first real call
- **browser-use API compatibility** — wrote against expected interface; verify imports/API on first run

---

## Startup Order

```bash
yarn demo                          # Terminal 1 — port 3000
cd leadsaver && source .venv/bin/activate && uvicorn main:app --reload --port 8000  # Terminal 2
yarn ngrok                         # Terminal 3
yarn agentphone                    # Terminal 4 (once, after ngrok is up)
```

Then call `+1 (231) 867-0908`.

---

## Most Likely First-Run Issues

1. **AgentPhone webhook payload** — log `payload` at top of `/webhook/call` and check field names on first call. Fix field names in `main.py` to match.
2. **browser-use `Browser`/`Agent` import** — if import fails, check `browser_use` version and adjust `browser_submit.py` accordingly.
3. **Gemini conversation history format** — if `get_reply()` errors, check that `types.Content` / `types.Part` usage matches installed `google-genai` version.

---

## Next Steps After First Call Works

1. Verify `submissions.csv` gets a new row after the call
2. Verify `GET /leads` returns the lead
3. Test edge cases: caller hangs up early, gives wrong phone number, speaks Spanish
4. Wire up `yarn agentphone` to run automatically on ngrok start (optional)
