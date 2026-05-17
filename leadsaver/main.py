import asyncio
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from models import init_db, save_lead, mark_form_submitted, get_all_leads
from agent import get_reply, extract_lead_info, BEGIN_MESSAGE
from browser_submit import submit_lead_to_form

app = FastAPI(title="LeadSaver")

# In-memory call state: call_id -> {history, transcript}
active_calls: dict[str, dict] = {}


@app.on_event("startup")
def startup():
    init_db()
    print("[LeadSaver] DB ready.")


# ---------------------------------------------------------------------------
# Webhook: AgentPhone inbound call
# ---------------------------------------------------------------------------
@app.post("/webhook/call")
async def handle_call(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    call_id = payload.get("callId") or payload.get("id", "unknown")
    event = payload.get("event") or payload.get("type", "")

    # New call — send the begin message
    if event in ("call.started", "call_started", "new_call", ""):
        active_calls[call_id] = {"history": [], "transcript": ""}
        return JSONResponse({"text": BEGIN_MESSAGE, "hangup": False})

    # Ongoing call — caller said something
    caller_text = payload.get("text") or payload.get("transcript") or payload.get("message", "")
    if not caller_text:
        return JSONResponse({"text": "", "hangup": False})

    state = active_calls.setdefault(call_id, {"history": [], "transcript": ""})
    state["transcript"] += f"\nCaller: {caller_text}"

    reply, call_complete = get_reply(state["history"], caller_text)

    state["history"].append({"role": "user", "parts": [caller_text]})
    state["history"].append({"role": "model", "parts": [reply]})
    state["transcript"] += f"\nAgent: {reply}"

    if call_complete:
        background_tasks.add_task(process_completed_call, call_id, state["transcript"])
        active_calls.pop(call_id, None)

    return JSONResponse({"text": reply, "hangup": call_complete})


# ---------------------------------------------------------------------------
# Webhook: AgentMail reply (post-MVP)
# ---------------------------------------------------------------------------
@app.post("/webhook/email-reply")
async def handle_email_reply(request: Request):
    payload = await request.json()
    print(f"[EMAIL] Reply received: {payload}")
    return {"status": "accepted"}


# ---------------------------------------------------------------------------
# Webhook: Browser Use completion callback (post-MVP)
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
# Background: extract lead info + submit form
# ---------------------------------------------------------------------------
async def process_completed_call(call_id: str, transcript: str):
    print(f"[CALL {call_id}] Processing completed call.")
    info = extract_lead_info(transcript)

    caller_name = info.get("caller_name", "Unknown")
    caller_phone = info.get("caller_phone", "")
    issue = info.get("issue_description", "")
    is_urgent = info.get("is_urgent", False)

    lead_id = save_lead(
        caller_name=caller_name,
        caller_phone=caller_phone,
        issue=issue,
        transcript=transcript,
    )
    print(f"[LEAD] Saved lead #{lead_id}: {caller_name} / {caller_phone} / {issue}")

    service = "Emergency Plumbing" if is_urgent else "Drain Cleaning"
    message = f"{issue}{' [URGENT]' if is_urgent else ''}"

    success = await submit_lead_to_form(
        name=caller_name,
        phone=caller_phone,
        email="",
        service=service,
        message=message,
    )

    if success:
        mark_form_submitted(lead_id)
        print(f"[LEAD] Form submitted for lead #{lead_id}")
    else:
        print(f"[LEAD] Form submission FAILED for lead #{lead_id}")
