import json
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL, BUSINESS

client = genai.Client(api_key=GEMINI_API_KEY)

DONE_SIGNALS = ["have a great day", "call you back shortly", "goodbye", "take care", "talk soon"]


def _build_system_prompt(business: dict, caller_number: str = "") -> str:
    services = business.get("services", [])
    services_str = ", ".join(services) if isinstance(services, list) else services
    caller_note = f"\nCaller ID shows {caller_number} — offer this as their callback number, they just need to confirm or give a different one." if caller_number else ""
    return f"""You are the virtual receptionist for {business['name']}.{caller_note}

Collect these four things, in order, one at a time:
1. Caller's name
2. Callback number — if caller ID is available, offer it and ask "is that the best number?" Don't repeat the number back digit by digit.
3. What they need help with — one short follow-up question max if unclear
4. Urgency — only ask if not obvious from context

Tone and pacing rules:
- Sound like a warm, calm human receptionist, not a bot reading a checklist.
- Use natural sentence rhythm. Write commas where you'd naturally pause if speaking aloud — this controls TTS pacing.
- Use "..." for a longer pause where it feels natural, e.g. "Got it... and what's the issue?"
- Keep each response to 1–2 short sentences. No bullet points, no lists.
- Don't confirm every detail back verbatim. A brief acknowledgment is enough — "Got it," or "Perfect."
- Only do a full summary confirmation at the very end, right before goodbye, and keep it to one sentence.
- Never ask more than one question at a time.
- Never quote prices. Say "the owner will go over that when they call back."
- Never schedule appointments.
- If asked if you're human: "I'm a virtual assistant for {business['name']}."

Services: {services_str}
Hours: {business.get('hours', 'contact us for hours')}
{f"Context: {business['profile_text']}" if business.get('profile_text') else ''}
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
