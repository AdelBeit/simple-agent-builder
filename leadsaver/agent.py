import json
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL, BUSINESS

client = genai.Client(api_key=GEMINI_API_KEY)

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

DONE_SIGNALS = ["have a great day", "call you back shortly", "goodbye", "take care", "talk soon"]


def get_reply(conversation_history: list[dict], new_message: str) -> tuple[str, bool]:
    """Returns (reply_text, call_complete)."""
    history = [
        types.Content(role=turn["role"], parts=[types.Part(text=turn["parts"][0])])
        for turn in conversation_history
    ]

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=history + [types.Content(role="user", parts=[types.Part(text=new_message)])],
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
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
