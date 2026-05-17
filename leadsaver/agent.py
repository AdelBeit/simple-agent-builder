import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL, BUSINESS

genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = f"""You are the virtual receptionist for {BUSINESS['name']}, a plumbing company in Austin, TX.

Your only job is to collect a missed-call lead. Collect these four things in order:
1. Caller's full name
2. Best callback phone number (read it back to confirm)
3. What plumbing issue they need help with
4. Urgency (emergency or can wait — only ask if not obvious)

Rules:
- Keep every response to 1–2 sentences max.
- Never ask more than one question at a time.
- Never quote prices. Say "the owner will go over pricing when they call back."
- Never schedule appointments.
- If asked if you're human, say: "I'm a virtual assistant for {BUSINESS['name']}."
- Once all four items are collected, confirm back and say goodbye.
- If caller mentions flooding, burst pipe, or no hot water, note it as urgent.

Services offered: {', '.join(BUSINESS['services'])}
"""

BEGIN_MESSAGE = (
    f"Hi, thanks for calling {BUSINESS['name']}! "
    "The owner is unavailable right now, but I can take your info and make sure someone gets back to you quickly. "
    "Can I get your name?"
)


def build_model():
    return genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT,
    )


def get_reply(conversation_history: list[dict], new_message: str) -> tuple[str, bool]:
    """
    Returns (reply_text, call_complete).
    call_complete=True when the agent has said goodbye and should hang up.
    """
    model = build_model()
    chat = model.start_chat(history=conversation_history)
    response = chat.send_message(new_message)
    reply = response.text.strip()

    done_signals = ["have a great day", "call you back shortly", "goodbye", "take care", "talk soon"]
    call_complete = any(sig in reply.lower() for sig in done_signals)

    return reply, call_complete


def extract_lead_info(transcript: str) -> dict:
    """Parse collected lead info from a full call transcript using Gemini."""
    model = genai.GenerativeModel(model_name=GEMINI_MODEL)
    prompt = f"""From this call transcript, extract:
- caller_name
- caller_phone
- issue_description
- is_urgent (true/false)

Return only valid JSON, no markdown.

Transcript:
{transcript}"""
    response = model.generate_content(prompt)
    import json
    try:
        return json.loads(response.text.strip())
    except Exception:
        return {"caller_name": "", "caller_phone": "", "issue_description": transcript[:200], "is_urgent": False}
