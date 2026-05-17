from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from models import (
    init_db, save_lead, mark_form_submitted, get_all_leads,
    save_business, get_business, get_business_by_number, update_business_profile,
)
from agent import get_reply, extract_lead_info, BEGIN_MESSAGE
from onboarding import get_onboarding_reply, BEGIN_MESSAGE as ONBOARDING_BEGIN
from browser_submit import submit_lead_to_form, scrape_business_website

app = FastAPI(title="LeadSaver")

# In-memory state keyed by call/session ID
active_calls: dict[str, dict] = {}
active_onboarding: dict[str, dict] = {}


@app.on_event("startup")
def startup():
    init_db()
    print("[LeadSaver] DB ready.")


# ---------------------------------------------------------------------------
# Webhook: AgentPhone inbound call (live lead capture)
# ---------------------------------------------------------------------------
@app.post("/webhook/call")
async def handle_call(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    call_id = payload.get("callId") or payload.get("id", "unknown")
    event = payload.get("event") or payload.get("type", "")
    agentphone_number = payload.get("to") or payload.get("toNumber", "")

    # Look up the business this number belongs to
    business = get_business_by_number(agentphone_number) if agentphone_number else None

    if event in ("call.started", "call_started", "new_call", ""):
        active_calls[call_id] = {"history": [], "transcript": "", "business": business}
        return JSONResponse({"text": BEGIN_MESSAGE, "hangup": False})

    caller_text = payload.get("text") or payload.get("transcript") or payload.get("message", "")
    if not caller_text:
        return JSONResponse({"text": "", "hangup": False})

    state = active_calls.setdefault(call_id, {"history": [], "transcript": "", "business": business})
    state["transcript"] += f"\nCaller: {caller_text}"

    reply, call_complete = get_reply(state["history"], caller_text, business=state.get("business"))

    state["history"].append({"role": "user", "parts": [caller_text]})
    state["history"].append({"role": "model", "parts": [reply]})
    state["transcript"] += f"\nAgent: {reply}"

    if call_complete:
        background_tasks.add_task(process_completed_call, call_id, state["transcript"], state.get("business"))
        active_calls.pop(call_id, None)

    return JSONResponse({"text": reply, "hangup": call_complete})


# ---------------------------------------------------------------------------
# Webhook: AgentPhone onboarding call (business setup interview)
# ---------------------------------------------------------------------------
@app.post("/webhook/onboarding")
async def handle_onboarding(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    session_id = payload.get("callId") or payload.get("id", "unknown")
    event = payload.get("event") or payload.get("type", "")

    if event in ("call.started", "call_started", "new_call", ""):
        active_onboarding[session_id] = {"history": [], "transcript": ""}
        return JSONResponse({"text": ONBOARDING_BEGIN, "hangup": False})

    caller_text = payload.get("text") or payload.get("transcript") or payload.get("message", "")
    if not caller_text:
        return JSONResponse({"text": "", "hangup": False})

    state = active_onboarding.setdefault(session_id, {"history": [], "transcript": ""})
    state["transcript"] += f"\nOwner: {caller_text}"

    reply, business_data = get_onboarding_reply(state["history"], caller_text)

    state["history"].append({"role": "user", "parts": [caller_text]})
    state["history"].append({"role": "model", "parts": [reply]})
    state["transcript"] += f"\nAgent: {reply}"

    if business_data:
        background_tasks.add_task(complete_onboarding, session_id, business_data)
        active_onboarding.pop(session_id, None)
        return JSONResponse({"text": reply, "hangup": True})

    return JSONResponse({"text": reply, "hangup": False})


# ---------------------------------------------------------------------------
# POST /onboarding/start — trigger onboarding via HTTP (test without AgentPhone)
# ---------------------------------------------------------------------------
@app.post("/onboarding/start")
async def onboarding_start():
    return {"session_id": "test", "message": ONBOARDING_BEGIN}


@app.post("/onboarding/message")
async def onboarding_message(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    session_id = body.get("session_id", "test")
    message = body.get("message", "")

    state = active_onboarding.setdefault(session_id, {"history": [], "transcript": ""})
    reply, business_data = get_onboarding_reply(state["history"], message)

    state["history"].append({"role": "user", "parts": [message]})
    state["history"].append({"role": "model", "parts": [reply]})

    if business_data:
        background_tasks.add_task(complete_onboarding, session_id, business_data)
        active_onboarding.pop(session_id, None)
        return {"reply": reply, "done": True, "business": business_data}

    return {"reply": reply, "done": False}


# ---------------------------------------------------------------------------
# Webhook: AgentMail reply — owner tweaks their config
# ---------------------------------------------------------------------------
@app.post("/webhook/email-reply")
async def handle_email_reply(request: Request):
    payload = await request.json()
    print(f"[EMAIL] Reply received: {payload}")
    return {"status": "accepted"}


# ---------------------------------------------------------------------------
# Webhook: Browser Use completion callback
# ---------------------------------------------------------------------------
@app.post("/webhook/browser-done")
async def handle_browser_done(request: Request):
    payload = await request.json()
    lead_id = payload.get("lead_id")
    success = payload.get("success", False)
    if lead_id and success:
        mark_form_submitted(int(lead_id))
    return {"status": "accepted"}


# ---------------------------------------------------------------------------
# GET /leads — view collected leads
# ---------------------------------------------------------------------------
@app.get("/leads")
def list_leads():
    return get_all_leads()


# ---------------------------------------------------------------------------
# GET /businesses — view onboarded businesses
# ---------------------------------------------------------------------------
@app.get("/businesses")
def list_businesses():
    from models import get_db
    conn = get_db()
    rows = conn.execute("SELECT * FROM businesses ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Background: complete onboarding — scrape website + save business
# ---------------------------------------------------------------------------
async def complete_onboarding(session_id: str, data: dict):
    print(f"[ONBOARDING {session_id}] Saving business: {data.get('name')}")

    biz_id = save_business(
        name=data.get("name", ""),
        phone=data.get("phone", ""),
        website_url=data.get("website_url", ""),
        contact_form_url=data.get("contact_form_url", ""),
        hours=data.get("hours", ""),
        services=data.get("services", []),
        owner_email=data.get("owner_email", ""),
    )
    print(f"[ONBOARDING] Business saved as ID #{biz_id}")

    if data.get("website_url"):
        print(f"[ONBOARDING] Scraping {data['website_url']} ...")
        profile_text = await scrape_business_website(data["website_url"])
        if profile_text:
            update_business_profile(biz_id, profile_text)
            print(f"[ONBOARDING] Profile enriched from website ({len(profile_text)} chars)")

    print(f"[ONBOARDING] Done for business #{biz_id}")


# ---------------------------------------------------------------------------
# Background: process completed lead call
# ---------------------------------------------------------------------------
async def process_completed_call(call_id: str, transcript: str, business: dict | None):
    print(f"[CALL {call_id}] Processing completed call.")
    info = extract_lead_info(transcript)

    caller_name = info.get("caller_name", "Unknown")
    caller_phone = info.get("caller_phone", "")
    issue = info.get("issue_description", "")
    is_urgent = info.get("is_urgent", False)

    lead_id = save_lead(caller_name=caller_name, caller_phone=caller_phone,
                        issue=issue, transcript=transcript)
    print(f"[LEAD] Saved lead #{lead_id}: {caller_name} / {caller_phone} / {issue}")

    contact_form_url = business.get("contact_form_url") if business else "http://localhost:3000/#contact"
    service = "Emergency Plumbing" if is_urgent else "Drain Cleaning"
    message = f"{issue}{' [URGENT]' if is_urgent else ''}"

    success = await submit_lead_to_form(
        name=caller_name, phone=caller_phone, email="",
        service=service, message=message, form_url=contact_form_url,
    )

    if success:
        mark_form_submitted(lead_id)
        print(f"[LEAD] Form submitted for lead #{lead_id}")
    else:
        print(f"[LEAD] Form submission FAILED for lead #{lead_id}")
