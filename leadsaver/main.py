from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from models import (
    init_db, save_lead, mark_form_submitted, get_all_leads,
    save_business, get_business, get_business_by_number, update_business_profile,
)
from agent import get_reply, extract_lead_info, BEGIN_MESSAGE
from onboarding import get_onboarding_reply, BEGIN_MESSAGE as ONBOARDING_BEGIN, extract_url
from browser_submit import submit_lead_to_form, scrape_business_website
from agentmail import create_inbox, register_reply_webhook, send_config_summary, send_lead_notification

app = FastAPI(title="LeadSaver")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3100", "http://localhost:3101", "http://localhost:3010"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    print(f"[CALL] Payload: {payload}")
    data = payload.get("data", payload)  # AgentPhone wraps fields in "data"
    event = payload.get("event") or payload.get("type", "")
    call_id = data.get("callId") or payload.get("callId") or payload.get("id", "unknown")
    agentphone_number = data.get("to") or payload.get("to") or payload.get("toNumber", "")

    # Ignore call_ended events
    if event == "agent.call_ended":
        return JSONResponse({"status": "ok"})

    # Look up the business this number belongs to
    business = get_business_by_number(agentphone_number) if agentphone_number else None

    if event in ("call.started", "call_started", "new_call") or call_id not in active_calls:
        active_calls[call_id] = {"history": [], "transcript": "", "business": business}
        return JSONResponse({"text": BEGIN_MESSAGE, "hangup": False})

    caller_text = data.get("transcript") or payload.get("text") or payload.get("transcript") or payload.get("message", "")
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

    # Detect URL in message — scrape immediately and inject results
    scraped_data = None
    url = extract_url(message)
    if url and not state.get("scraped"):
        state["scraped"] = True
        state["website_url"] = url
        scraped_data = await scrape_business_website(url)
        if not scraped_data:
            scraped_data = f"(Could not scrape {url} — may be unreachable or require login)"

    reply, business_data = get_onboarding_reply(state["history"], message, scraped_data=scraped_data)

    # Store message with scraped data appended so history is accurate
    stored_message = f"{message}\n\n[SCRAPED DATA]\n{scraped_data}" if scraped_data else message
    state["history"].append({"role": "user", "parts": [stored_message]})
    state["history"].append({"role": "model", "parts": [reply]})

    if business_data:
        if state.get("website_url") and not business_data.get("website_url"):
            business_data["website_url"] = state["website_url"]
        background_tasks.add_task(complete_onboarding, session_id, business_data)
        active_onboarding.pop(session_id, None)
        return {"reply": reply, "done": True, "business": business_data}

    return {"reply": reply, "done": False, "scraping": bool(scraped_data)}


# ---------------------------------------------------------------------------
# Webhook: AgentMail reply — owner tweaks their config
# ---------------------------------------------------------------------------
@app.post("/webhook/email-reply")
async def handle_email_reply(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    print(f"[EMAIL] Reply received: {payload}")
    background_tasks.add_task(process_email_reply, payload)
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
# Background: complete onboarding — scrape website + save + email summary
# ---------------------------------------------------------------------------
async def complete_onboarding(session_id: str, data: dict):
    print(f"[ONBOARDING {session_id}] Saving business: {data.get('name')}")

    # 1. Save business to DB first — always, regardless of downstream failures
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

    # 2. Create AgentMail inbox
    inbox_id, inbox_email = "", ""
    try:
        inbox = create_inbox(data.get("name", "business"))
        inbox_id = inbox["id"]
        inbox_email = inbox["email"]
        print(f"[ONBOARDING] Inbox created: {inbox_email}")
        from models import get_db
        conn = get_db()
        conn.execute("UPDATE businesses SET inbox_id=?, inbox_email=? WHERE id=?", (inbox_id, inbox_email, biz_id))
        conn.commit()
        conn.close()
        register_reply_webhook(inbox_id)
    except Exception as e:
        print(f"[ONBOARDING] AgentMail inbox creation failed (non-fatal): {e}")

    # 3. Scrape website
    if data.get("website_url"):
        print(f"[ONBOARDING] Scraping {data['website_url']} ...")
        profile_text = await scrape_business_website(data["website_url"])
        if profile_text:
            update_business_profile(biz_id, profile_text)
            print(f"[ONBOARDING] Profile enriched ({len(profile_text)} chars)")

    # 4. Send config summary email to owner
    business = get_business(biz_id)
    if inbox_id and data.get("owner_email") and business:
        try:
            ok = send_config_summary(inbox_id, data["owner_email"], business)
            print(f"[ONBOARDING] Config email {'sent' if ok else 'FAILED'} → {data['owner_email']}")
        except Exception as e:
            print(f"[ONBOARDING] Config email failed (non-fatal): {e}")

    print(f"[ONBOARDING] Complete for business #{biz_id}")


# ---------------------------------------------------------------------------
# Background: process owner email reply — update business profile
# ---------------------------------------------------------------------------
async def process_email_reply(payload: dict):
    # AgentMail wraps the message body — try common field names
    body = (payload.get("text") or payload.get("body") or
            payload.get("message", {}).get("text", ""))
    inbox_id = (payload.get("inboxId") or payload.get("inbox_id") or
                payload.get("message", {}).get("inboxId", ""))

    if not body or not inbox_id:
        print(f"[EMAIL] Could not parse reply payload: {payload}")
        return

    # Find the business by inbox ID
    conn = __import__("models").get_db()
    row = conn.execute("SELECT * FROM businesses WHERE inbox_id = ?", (inbox_id,)).fetchone()
    conn.close()
    if not row:
        print(f"[EMAIL] No business found for inbox {inbox_id}")
        return

    business = dict(row)
    print(f"[EMAIL] Owner reply for {business['name']}: {body[:100]}")

    # Use Gemini to extract what the owner wants to change
    from agent import client as gemini_client
    from config import GEMINI_MODEL
    prompt = f"""The owner of {business['name']} replied to their LeadSaver config email with:

"{body}"

Extract any corrections or updates as JSON with the same fields as the business profile:
name, phone, website_url, contact_form_url, hours, services (list).
Only include fields they actually mentioned changing. Return valid JSON only, no markdown."""

    response = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    try:
        import json
        updates = json.loads(response.text.strip())
        for field, value in updates.items():
            conn = __import__("models").get_db()
            conn.execute(f"UPDATE businesses SET {field} = ? WHERE id = ?", (str(value), business["id"]))
            conn.commit()
            conn.close()
        print(f"[EMAIL] Updated fields for business #{business['id']}: {list(updates.keys())}")
    except Exception as e:
        print(f"[EMAIL] Could not parse updates: {e}")


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

    # Email owner notification
    if business and business.get("inbox_id") and business.get("owner_email"):
        lead_data = {"caller_name": caller_name, "caller_phone": caller_phone,
                     "issue_description": issue, "is_urgent": is_urgent}
        ok = send_lead_notification(business["inbox_id"], business["owner_email"],
                                    lead_data, business.get("name", ""))
        print(f"[LEAD] Owner notification email {'sent' if ok else 'FAILED'}")
