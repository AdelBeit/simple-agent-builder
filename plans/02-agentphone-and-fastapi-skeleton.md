# Build Step 2 — AgentPhone Agent + FastAPI Skeleton

## What Was Built

### AgentPhone Agent
- Created agent "Peak Flow Plumbing" via `POST /v1/agents`
- **Agent ID:** `cmpa92in80d4djz00jx56l5z2`
- **Voice mode:** `webhook` — AgentPhone sends caller utterances to our `/webhook/call` endpoint, we respond with `{"text": "...", "hangup": false}`
- **Provisioned number:** `+1 (231) 867-0908` (no 512 area code available; US number attached to agent)
- API key + agent ID + number stored in `.env`

### leadsaver/ skeleton
All five Python files created:

| File | Purpose |
|---|---|
| `config.py` | All env vars + hardcoded Peak Flow Plumbing business profile |
| `models.py` | SQLite init + `save_lead`, `mark_form_submitted`, `get_all_leads` helpers |
| `agent.py` | Gemini 2.5 Flash chat logic — `get_reply()` drives the conversation, `extract_lead_info()` parses transcript at end |
| `browser_submit.py` | Browser Use async function — fills and submits the Peak Flow Plumbing contact form |
| `main.py` | FastAPI app — 3 webhooks + `GET /leads` + background task orchestration |

### agent.md
Full persona spec for the Peak Flow Plumbing receptionist agent — system prompt, begin message, goal, rules, and what NOT to do.

## Webhook Flow

```
AgentPhone → POST /webhook/call (event: call.started)
  → return {"text": BEGIN_MESSAGE, "hangup": false}

AgentPhone → POST /webhook/call (event: ongoing, text: "Hi I have a leak")
  → Gemini generates reply
  → return {"text": "...", "hangup": false}

AgentPhone → POST /webhook/call (call_complete detected)
  → return {"text": "goodbye...", "hangup": true}
  → background: extract_lead_info → save_lead → submit_lead_to_form
```

## Call State
In-memory dict `active_calls[call_id]` holds conversation history and running transcript for each active call. Cleaned up on hangup.

## Next Steps
- [ ] Set `GEMINI_API_KEY` in `.env` ✅ (done during session)
- [ ] `ngrok http 8000` → paste URL into AgentPhone agent webhook config
- [ ] Test with a real call to `+1 (231) 867-0908`
- [ ] Verify Browser Use submits to `localhost:3000/contact`
