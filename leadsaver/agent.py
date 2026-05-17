import json
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL, BUSINESS

client = genai.Client(api_key=GEMINI_API_KEY)

DONE_SIGNALS = ["have a great day", "call you back shortly", "goodbye", "take care", "talk soon"]


def _build_system_prompt(business: dict, caller_number: str = "") -> str:
    services = business.get("services", [])
    services_str = ", ".join(services) if isinstance(services, list) else services
    caller_note = f"\nThe caller's phone number from caller ID is {caller_number}. When collecting their callback number, mention this and ask if they'd like to use it or a different one." if caller_number else ""
    return f"""You are the virtual receptionist for {business['name']}.{caller_note}

Your only job is to collect a missed-call lead. Collect these four things in order:
1. Caller's full name
2. Best callback phone number (read it back to confirm)
3. What issue they need help with
4. Urgency (emergency or can wait — only ask if not obvious)

Rules:
- Keep every response to 1–2 sentences max.
- Never ask more than one question at a time.
- Never quote prices. Say "the owner will go over pricing when they call back."
- Never schedule appointments.
- If asked if you're human, say: "I'm a virtual assistant for {business['name']}."
- Once all four items are collected, confirm back and say goodbye.

Services offered: {services_str}
Business hours: {business.get('hours', 'contact us for hours')}
{f"Additional info: {business['profile_text']}" if business.get('profile_text') else ''}
"""


def build_begin_message(business: dict, caller_number: str = "") -> str:
    name = business.get("name") or BUSINESS["name"]
    base = (
        f"Hi, thanks for calling {name}! "
        "The owner is unavailable right now, but I can take a message. "
    )
    if caller_number:
        formatted = f"{caller_number[-10:-7]}-{caller_number[-7:-4]}-{caller_number[-4:]}" if len(caller_number) >= 10 else caller_number
        base += f"I see you're calling from {formatted} — is that the best number to reach you, or would you like to leave a different one? Either way, can I get your name first?"
    else:
        base += "Can I get your name?"
    return base


# Fallback for when no DB business is found — uses hardcoded config
BEGIN_MESSAGE = build_begin_message(BUSINESS)


def get_reply(conversation_history: list[dict], new_message: str, business: dict | None = None, caller_number: str = "") -> tuple[str, bool]:
    """Returns (reply_text, call_complete). Uses DB business if provided, else falls back to config."""
    biz = business or BUSINESS
    system_prompt = _build_system_prompt(biz, caller_number)

    history = [
        types.Content(role=turn["role"], parts=[types.Part(text=turn["parts"][0])])
        for turn in conversation_history
    ]

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=history + [types.Content(role="user", parts=[types.Part(text=new_message)])],
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )

    reply = response.text.strip()
    call_complete = any(sig in reply.lower() for sig in DONE_SIGNALS)
    return reply, call_complete


def extract_lead_info(transcript: str) -> dict:
    """Parse collected lead info from a full call transcript."""
    prompt = f"""From this call transcript, extract:
- caller_name
- caller_phone
- issue_description
- is_urgent (true/false)

Return only valid JSON, no markdown.

Transcript:
{transcript}"""

    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    try:
        return json.loads(response.text.strip())
    except Exception:
        return {"caller_name": "", "caller_phone": "", "issue_description": transcript[:200], "is_urgent": False}
