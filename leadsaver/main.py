from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from models import (
    init_db, save_lead, mark_form_submitted, get_all_leads,
    save_business, get_business, get_business_by_number, update_business_profile,
)
from agent import get_reply, extract_lead_info, BEGIN_MESSAGE, build_begin_message
from onboarding import get_onboarding_reply, BEGIN_MESSAGE as ONBOARDING_BEGIN, extract_url
from browser_submit import submit_lead_to_form, scrape_business_website
from agentmail import create_inbox, register_reply_webhook, send_config_summary, send_lead_notification
from agentphone_provision import provision_business_agent

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

    caller_number = data.get("from") or payload.get("from", "")

    if call_id not in active_calls:
        begin = build_begin_message(business or {}, caller_number)
        # Seed history with the begin message AgentPhone already played
        active_calls[call_id] = {
            "history": [{"role": "model", "parts": [begin]}],
            "transcript": f"\nAgent: {begin}",
            "business": business,
            "caller_number": caller_number,
        }
        # AgentPhone plays beginMessage itself — don't double it
        if event in ("call.started", "call_started", "new_call"):
            return JSONResponse({"text": "", "hangup": False})

    caller_text = data.get("transcript") or payload.get("text") or payload.get("transcript") or payload.get("message", "")
    if not caller_text:
        return JSONResponse({"text": "", "hangup": False})

    state = active_calls.setdefault(call_id, {"history": [], "transcript": "", "business": business, "caller_number": caller_number})
    state["transcript"] += f"\nCaller: {caller_text}"

    reply, call_complete = get_reply(state["history"], caller_text, business=state.get("business"), caller_number=state.get("caller_number"))

    state["history"].append({"role": "user", "parts": [caller_text]})
    state["history"].append({"role": "model", "parts": [reply]})
    state["transcript"] += f"\nAgent: {reply}"

    if call_complete:
        background_tasks.add_task(process_completed_call, call_id, state["transcript"], state.get("business"))
        active_calls.pop(call_id, None)

    return JSONResponse({"text": reply, "hangup": call_complete})


# ---------------------------------------------------------------------------
# Webhook: Greeter agent (pitches LeadSaver, transfers to onboarding)
# ---------------------------------------------------------------------------
GREETER_SYSTEM_PROMPT = """You are the sales representative for LeadSaver, an AI receptionist service for small businesses.

About LeadSaver:
- LeadSaver answers missed calls 24/7 as a virtual receptionist for any small business (plumbers, roofers, contractors, salons, etc.)
- When a customer calls and the owner misses it, LeadSaver's AI answers, collects the caller's name, phone number, and what they need
- It then automatically submits that lead to the business's contact form and emails the owner
- Pricing: $49/month flat rate. No setup fees. No per-call charges.
- Setup takes 2 minutes over the phone — we pull info from their website automatically

Your job:
- Answer any questions about LeadSaver warmly and concisely
- If the caller is a business owner interested in signing up, offer to transfer them to setup
- If they ask about pricing, tell them $49/month
- If they ask how it works, give a 2-sentence summary
- Keep responses to 1-2 sentences
- When the caller is ready to sign up, say: "Let me connect you with our setup team right now!"

Transfer signals — if the caller says things like "yes", "sign me up", "let's do it", "I'm interested", "set me up", "get me started" — respond with your transfer line and end with TRANSFER_NOW
If not interested after 3 turns, politely end the call."""

active_greeter: dict[str, dict] = {}


@app.post("/webhook/greeter")
async def handle_greeter(request: Request):
    payload = await request.json()
    data = payload.get("data", payload)
    event = payload.get("event") or payload.get("type", "")
    session_id = data.get("callId") or payload.get("callId") or "unknown"

    if event == "agent.call_ended":
        active_greeter.pop(session_id, None)
        return JSONResponse({"status": "ok"})

    if session_id not in active_greeter:
        active_greeter[session_id] = {"history": [], "turns": 0}
        return JSONResponse({"text": "", "hangup": False})

    caller_text = data.get("transcript") or payload.get("text", "")
    if not caller_text:
        return JSONResponse({"text": "", "hangup": False})

    state = active_greeter[session_id]
    state["turns"] += 1

    from google import genai as _genai
    from google.genai import types as _types
    from config import GEMINI_API_KEY, GEMINI_MODEL
    _client = _genai.Client(api_key=GEMINI_API_KEY)

    history = [
        _types.Content(role=t["role"], parts=[_types.Part(text=t["parts"][0])])
        for t in state["history"]
    ]
    response = _client.models.generate_content(
        model=GEMINI_MODEL,
        contents=history + [_types.Content(role="user", parts=[_types.Part(text=caller_text)])],
        config=_types.GenerateContentConfig(system_instruction=GREETER_SYSTEM_PROMPT),
    )
    reply = response.text.strip()

    state["history"].append({"role": "user", "parts": [caller_text]})
    state["history"].append({"role": "model", "parts": [reply]})

    if "TRANSFER_NOW" in reply:
        reply = reply.replace("TRANSFER_NOW", "").strip()
        active_greeter.pop(session_id, None)
        return JSONResponse({"text": reply, "action": "transfer"})

    if state["turns"] >= 5:
        active_greeter.pop(session_id, None)
        return JSONResponse({"text": "Thanks for calling LeadSaver! Give us a call back anytime. Have a great day!", "hangup": True})

    return JSONResponse({"text": reply, "hangup": False})


# ---------------------------------------------------------------------------
# Webhook: AgentPhone onboarding call (business setup interview)
# ---------------------------------------------------------------------------
@app.post("/webhook/onboarding")
async def handle_onboarding(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    data = payload.get("data", payload)
    event = payload.get("event") or payload.get("type", "")
    session_id = data.get("callId") or payload.get("callId") or payload.get("id", "unknown")
    caller_text_log = data.get("transcript") or payload.get("text", "")
    print(f"[ONBOARDING] event={event} session={session_id[-8:]} awaiting_transfer={active_onboarding.get(session_id, {}).get('awaiting_transfer')} text={caller_text_log!r}")

    if event == "agent.call_ended":
        active_onboarding.pop(session_id, None)
        return JSONResponse({"status": "ok"})

    if session_id not in active_onboarding:
        # Seed history with begin message AgentPhone already plays — don't double it
        active_onboarding[session_id] = {
            "history": [{"role": "model", "parts": [ONBOARDING_BEGIN]}],
            "transcript": f"\nAgent: {ONBOARDING_BEGIN}",
            "awaiting_transfer": False,
            "transfer_number": "",
        }
        return JSONResponse({"text": "", "hangup": False})

    # Handle transfer confirmation turn
    state = active_onboarding[session_id]
    if state.get("awaiting_transfer"):
        caller_text = data.get("transcript") or payload.get("text", "")
        yes_signals = ["yes", "yeah", "sure", "yep", "go ahead", "connect", "transfer", "sounds good", "please", "absolutely"]
        print(f"[ONBOARDING] Transfer confirmation — caller said: {caller_text!r}")
        if any(s in caller_text.lower() for s in yes_signals):
            active_onboarding.pop(session_id, None)
            return JSONResponse({"text": "Connecting you now!", "action": "transfer", "transferNumber": state["transfer_number"]})
        else:
            active_onboarding.pop(session_id, None)
            return JSONResponse({"text": "No problem! We'll send a summary to your email shortly — your receptionist is live and ready to take calls. Have a great day!", "hangup": True})

    caller_text = data.get("transcript") or payload.get("text") or payload.get("transcript") or payload.get("message", "")
    if not caller_text:
        return JSONResponse({"text": "", "hangup": False})

    state["transcript"] += f"\nOwner: {caller_text}"

    # Detect URL in caller's message and scrape immediately
    scraped_data = None
    url = extract_url(caller_text)
    if url and not state.get("scraped"):
        state["scraped"] = True
        state["website_url"] = url
        scraped_data = await scrape_business_website(url)
        if not scraped_data:
            # TODO: remove localhost exception after demo — production should reject unreachable URLs
            scraped_data = f"(Could not scrape {url} automatically — please collect business info manually from the caller)"

    reply, business_data = get_onboarding_reply(state["history"], caller_text, scraped_data=scraped_data)
    state["history"].append({"role": "user", "parts": [caller_text]})
    state["history"].append({"role": "model", "parts": [reply]})
    state["transcript"] += f"\nAgent: {reply}"

    if business_data:
        # Provision agent synchronously so we have the number for the transfer offer
        agent_number = ""
        try:
            from agentphone_provision import provision_business_agent
            provisioned = provision_business_agent(business_data)
            agent_number = provisioned["phone_number"]
            business_data["agentphone_agent_id"] = provisioned["agent_id"]
            business_data["agentphone_number"] = agent_number
        except Exception as e:
            print(f"[ONBOARDING] Provisioning failed: {e}")

        background_tasks.add_task(complete_onboarding, session_id, business_data)

        if agent_number:
            fmt = f"{agent_number[-10:-7]}-{agent_number[-7:-4]}-{agent_number[-4:]}" if len(agent_number) >= 10 else agent_number
            transfer_msg = (
                f"You're all set! Your receptionist is live at {fmt}. "
                "Want me to connect you now so you can hear how it sounds?"
            )
            state["awaiting_transfer"] = True
            state["transfer_number"] = agent_number
            return JSONResponse({"text": transfer_msg, "hangup": False})
        else:
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
            # TODO: remove localhost exception after demo — production should reject unreachable URLs
            scraped_data = f"(Could not scrape {url} automatically — please collect business info manually from the caller)"

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

    # 5. Persist agent provisioning info (already provisioned in webhook if via phone)
    agent_id = data.get("agentphone_agent_id", "")
    agent_number = data.get("agentphone_number", "")
    if agent_id:
        conn = get_db()
        conn.execute(
            "UPDATE businesses SET agentphone_agent_id=?, agentphone_number=? WHERE id=?",
            (agent_id, agent_number, biz_id)
        )
        conn.commit()
        conn.close()
        print(f"[ONBOARDING] Agent saved: {agent_id} / {agent_number}")
    else:
        # HTTP chat path — provision here
        try:
            provisioned = provision_business_agent(get_business(biz_id))
            agent_id = provisioned["agent_id"]
            agent_number = provisioned["phone_number"]
            conn = get_db()
            conn.execute(
                "UPDATE businesses SET agentphone_agent_id=?, agentphone_number=? WHERE id=?",
                (agent_id, agent_number, biz_id)
            )
            conn.commit()
            conn.close()
            print(f"[ONBOARDING] Agent provisioned: {agent_id} / {agent_number}")
        except Exception as e:
            print(f"[ONBOARDING] Agent provisioning failed (non-fatal): {e}")

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
    info = extract_lead_info(transcript, business.get("services") if business else None)
    caller_name = info.get("caller_name", "")
    caller_phone = info.get("caller_phone", "")
    caller_email = info.get("caller_email", "")
    issue = info.get("issue_description", "")
    is_urgent = info.get("is_urgent", False)
    extracted_service = info.get("service", "")

    lead_id = save_lead(caller_name=caller_name, caller_phone=caller_phone,
                        issue=issue, transcript=transcript)
    print(f"[LEAD] Saved lead #{lead_id}: {caller_name} / {caller_phone} / {issue}")

    contact_form_url = business.get("contact_form_url") if business else "http://localhost:3000/#contact"
    available_services = business.get("services", []) if business else []
    if extracted_service and extracted_service in available_services:
        service = extracted_service
    elif available_services:
        service = "Emergency Plumbing" if is_urgent else available_services[0]
    else:
        service = "Emergency Plumbing" if is_urgent else "Drain Cleaning"
    message = f"{issue}{' [URGENT]' if is_urgent else ''}"

    success = await submit_lead_to_form(
        name=caller_name, phone=caller_phone, email=caller_email,
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
                     "caller_email": caller_email,
                     "issue_description": issue, "is_urgent": is_urgent}
        ok = send_lead_notification(business["inbox_id"], business["owner_email"],
                                    lead_data, business.get("name", ""),
                                    contact_form_url=contact_form_url if success else "")
        print(f"[LEAD] Owner notification email {'sent' if ok else 'FAILED'}")
