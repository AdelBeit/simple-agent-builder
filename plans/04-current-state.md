# LeadSaver — Current State (Session 3 Handoff)

## What's Working End-to-End

### Live Call Flow ✅
- AgentPhone calls `+1 (231) 867-0908` → webhooks hit `POST /webhook/call`
- Payload parsing fixed: all fields live under `data` key in AgentPhone payloads
- Gemini drives conversation: collects name, callback number (offers caller ID), issue, urgency
- Call closes with natural single-line goodbye: "Alright [name], I've got you down — someone will be in touch soon."
- On hangup (`agent.call_ended`): Gemini extracts lead → saves to SQLite → Browser Use submits contact form
- Lead confirmed saved: `[LEAD] Saved lead #3: Alex / 210-920-0016 / clogged bathtub`
- Form confirmed submitted: `[LEAD] Form submitted for lead #3`

### Onboarding Flow ✅
- Chat UI at `localhost:3010` drives Gemini interview
- Offers website scrape (httpx + BeautifulSoup + Gemini summary) or manual entry
- URL auto-detected anywhere in conversation
- On completion: saves business to SQLite, creates AgentMail inbox, registers reply webhook, sends config summary email
- `inbox_id` fix: field is `inbox_id` (email string) in AgentMail API response, not `id`
- Webhook registration fix: field is `event_types` (array), not `event_type`

### AgentMail ✅
- Base URL confirmed: `https://api.agentmail.to/v0` (not `.io`)
- Inbox created: `peakflowplumbingaustins1truste@agentmail.to`
- Config summary email sends to `owner_email` (per-business, collected during onboarding)
- Lead notification email sends to `owner_email` after each completed call
- Reply webhook registered — owner replies update business profile via Gemini extraction
- Each business has its own `owner_email` in SQLite — emails go to whoever signed up

### Browser Use ✅
- Fixed: use native `ChatGoogle` from `browser_use` package, not langchain wrapper
- `GOOGLE_API_KEY` required (not `GEMINI_API_KEY`) for browser-use
- Scraping replaced with httpx + BeautifulSoup (faster, more reliable for static content)
- Form submission tested and confirmed working with `ChatGoogle`

### Infrastructure
- Ports moved to `.env`: `PORT_BACKEND=8000`, `PORT_PLUMBER=3100`, `PORT_STYLIST=3101`, `PORT_ONBOARDING=3010`
- `.env.example` committed with all keys blank and ports pre-filled
- `yarn dev` runs FastAPI in bash with venv activated
- Screen session `leadsaver` + `/tmp/leadsaver.log` for background monitoring
- AgentPhone webhook URL must be set manually in dashboard to `/webhook/call` path

---

## Port Map

| Port | Service | Command |
|---|---|---|
| 8000 | LeadSaver FastAPI backend | `yarn dev` |
| 3100 | Peak Flow Plumbing demo site | `yarn demo:plumber` |
| 3101 | Goldfinch Barbershop demo site | `yarn demo:stylist` |
| 3010 | Onboarding chat UI | `yarn onboarding` |

---

## DB State (as of this session)

```
businesses: id=1, Peak Flow Plumbing, owner_email=adelbeit@gmail.com,
            inbox_id=peakflowplumbingaustins1truste@agentmail.to
leads: 3 leads captured from real calls
```

---

## Known Issues / Quirks

- Begin message occasionally splits mid-sentence in TTS ("Hi, thanks for calling Peak" / "Flow Plumbing") — AgentPhone TTS chunking, not our bug
- `yarn agentphone` script uses PATCH agent endpoint — webhook is actually a separate project-level resource; must be set manually in AgentPhone dashboard to `/webhook/call`
- Double begin message patched: AgentPhone plays `beginMessage` itself, we seed history with it but return empty text on call init

---

## What's NOT Built Yet (plan_v1)

| Step | Status |
|---|---|
| Agent provisioning per business (new AgentPhone agent + number on onboarding complete) | ❌ |
| Transfer offer at end of onboarding ("want to demo your receptionist?") | ❌ |
| Greeter agent (hosted mode, pitches LeadSaver, transfers to onboarding) | ❌ |

---

## Startup Order

```bash
screen -dmS leadsaver bash -c 'source leadsaver/.venv/bin/activate && uvicorn leadsaver/main:app --reload --port 8000 2>&1 | tee /tmp/leadsaver.log'
yarn demo          # ports 3100 + 3101
yarn onboarding    # port 3010
yarn ngrok         # persistent domain
# Set webhook in AgentPhone dashboard → https://syenitic-lila-uneffusively.ngrok-free.dev/webhook/call
```

---

## Next Steps

1. Build `agentphone_provision.py` — creates per-business agent + number on onboarding complete
2. Add transfer offer at end of onboarding webhook
3. Create greeter agent (hosted mode) on main number
4. Provision second number for onboarding agent
