import json
import re
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL, BUSINESS

client = genai.Client(api_key=GEMINI_API_KEY)

_NO_THINK = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=0)
)

# ---------------------------------------------------------------------------
# Onboarding — LeadSaver inbound agent (qualify + collect business info)
# ---------------------------------------------------------------------------

ONBOARDING_SYSTEM_PROMPT = """You are the inbound agent for LeadSaver, an AI receptionist service for small businesses ($49/month).

The caller already heard this opening before speaking to you:
"Hey, thanks for calling LeadSaver — where you'll never lose another lead again! Are you looking to hire an AI receptionist? It'll only take 2 minutes to get set up. Or I can tell you more about our service first."
Do NOT repeat that. Respond directly to whatever the caller says next.

PHASE 1 — QUALIFY
If they want to learn more: briefly explain — "LeadSaver answers your missed calls 24/7, collects the caller's name, number, and what they need, then emails it to you." Then ask again: "Ready to get set up?"
If they ask about pricing: "$49/month, no setup fees."
Only once they confirm they want to set up, ask: "Do you have a website I can pull your info from, or would you prefer to go through it step by step?"

PHASE 2 — ONBOARD
Website path:
- Accept ANY URL the caller gives — typed or spoken. "localhost thirty one hundred" means localhost:3100. Never say a URL is invalid.
- When you understand the URL, output it as a tag on its own line BEFORE your spoken response: [WEBSITE]http://localhost:3100[/WEBSITE]
  Then say: "Give me a moment to pull your info from that site..." — the system injects a [SCRAPED DATA] block.
- Read back the scraped info naturally. Ask owner to confirm.
- If URL is completely unrecognizable after two attempts, ask them to spell it out.
- NEVER say "give me a moment" without first outputting the [WEBSITE] tag.

Manual path — collect one at a time:
1. Business name
2. Phone number
3. Hours (Mon/Tue → full day names)
4. Services (top 3–6; infer from industry if they say "typical ones")
5. Contact form URL (use website URL if "same page"; blank if none)
6. Email — if already confirmed in scraped summary, skip. Otherwise ask once, read back with NATO phonetic alphabet: "A as in Alpha..."

FINISH
Once all info confirmed with a valid email, say a natural 1-2 sentence summary then: "I'll send a summary to [email]. Welcome to LeadSaver!"
Then on a new line: [DATA]{"done": true, "business": {"name": "", "phone": "", "website_url": "", "contact_form_url": "", "hours": "", "services": [], "owner_email": ""}}
The [DATA] tag is never spoken.

Rules:
- One question at a time. 1–2 sentences per response.
- Never say "scrape", "database", "webhook", or "null".
- Never output [SCRAPED DATA] blocks yourself — they're system-injected.
- owner_email must never be empty in the JSON.
- If owner asks to spell their email, do it immediately with NATO phonetic alphabet.
"""

ONBOARDING_BEGIN = (
    "Hi! I'm setting up your LeadSaver AI receptionist — takes about 2 minutes. "
    "Do you have a website I can pull your business info from automatically, "
    "or would you prefer to enter everything yourself?"
)

DONE_SIGNAL = '[DATA]'
URL_PATTERN = re.compile(r'https?://[^\s]+|localhost:[0-9]+[^\s]*', re.IGNORECASE)
WEBSITE_TAG = re.compile(r'\[WEBSITE\](.*?)\[/WEBSITE\]', re.IGNORECASE)


def gemini(prompt_or_contents, system: str | None = None) -> str:
    """Single wrapper for all Gemini calls — thinking always off."""
    cfg = types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_budget=0))
    if system:
        cfg = types.GenerateContentConfig(
            system_instruction=system,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
    resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt_or_contents, config=cfg)
    return resp.text.strip()


def extract_url(text: str) -> str | None:
    """Extracts a typed URL or a [WEBSITE]...[/WEBSITE] tag Gemini emits for spoken URLs."""
    m = URL_PATTERN.search(text)
    if m:
        url = m.group(0).rstrip('.,)')
        return url if url.startswith('http') else 'http://' + url
    m = WEBSITE_TAG.search(text)
    if m:
        url = m.group(1).strip()
        return url if url.startswith('http') else 'http://' + url
    return None


def get_onboarding_reply(history: list[dict], message: str,
                         scraped_data: str | None = None) -> tuple[str, dict | None]:
    contents = [
        types.Content(role=t["role"], parts=[types.Part(text=t["parts"][0])])
        for t in history
    ]
    user_text = f"{message}\n\n[SCRAPED DATA]\n{scraped_data}" if scraped_data else message
    contents.append(types.Content(role="user", parts=[types.Part(text=user_text)]))

    reply = gemini(contents, system=ONBOARDING_SYSTEM_PROMPT)

    if "[SCRAPED DATA]" in reply:
        reply = reply[:reply.index("[SCRAPED DATA]")].strip()

    if DONE_SIGNAL in reply:
        try:
            spoken, _, json_part = reply.partition("[DATA]")
            data = json.loads(json_part.strip())
            return spoken.strip(), data.get("business")
        except Exception:
            pass

    return reply, None


# ---------------------------------------------------------------------------
# Receptionist — live call handler for business agent
# ---------------------------------------------------------------------------

DONE_SIGNALS = ["have a great day", "call you back shortly", "goodbye", "take care", "talk soon"]


def _build_receptionist_prompt(business: dict, caller_number: str = "") -> str:
    services = business.get("services", [])
    services_str = ", ".join(services) if isinstance(services, list) else services
    caller_note = (
        f"\nCaller ID shows {caller_number} — offer this as their callback number, "
        "they just need to confirm or give a different one."
    ) if caller_number else ""
    return f"""You are the virtual receptionist for {business['name']}.{caller_note}

Collect these four things in order, one at a time:
1. Caller's name
2. Callback number — offer caller ID if available, ask "is that the best number?"
3. What they need help with — one follow-up max if unclear
4. Urgency — only ask if not obvious

Tone:
- Warm, calm, 1–2 short sentences per response.
- Use commas for TTS pacing, "..." for longer pauses.
- End with: "Alright [name], I've got you down — someone will be in touch soon. Have a good one!"
- Never quote prices. Never schedule appointments.
- If asked if you're human: "I'm a virtual assistant for {business['name']}."

Services: {services_str}
Hours: {business.get('hours', 'contact us for hours')}
{f"Context: {business['profile_text']}" if business.get('profile_text') else ''}
"""


def build_begin_message(business: dict, caller_number: str = "") -> str:
    name = business.get("name") or BUSINESS["name"]
    base = f"Hi, thanks for calling {name}! The owner is unavailable right now, but I can take a message. "
    if caller_number:
        fmt = f"{caller_number[-10:-7]}-{caller_number[-7:-4]}-{caller_number[-4:]}" if len(caller_number) >= 10 else caller_number
        base += f"I see you're calling from {fmt} — is that the best number, or would you like to leave a different one? Can I get your name first?"
    else:
        base += "Can I get your name?"
    return base


BEGIN_MESSAGE = build_begin_message(BUSINESS)


def get_reply(history: list[dict], message: str, business: dict | None = None,
              caller_number: str = "", moss_context: str = "") -> tuple[str, bool]:
    biz = business or BUSINESS
    user_text = f"{message}\n\n[Relevant business info]: {moss_context}" if moss_context else message
    contents = [
        types.Content(role=t["role"], parts=[types.Part(text=t["parts"][0])])
        for t in history
    ] + [types.Content(role="user", parts=[types.Part(text=user_text)])]

    reply = gemini(contents, system=_build_receptionist_prompt(biz, caller_number))
    return reply, any(s in reply.lower() for s in DONE_SIGNALS)


# ---------------------------------------------------------------------------
# Lead extraction — parse transcript after call ends
# ---------------------------------------------------------------------------

def extract_lead_info(transcript: str, services: list[str] | None = None) -> dict:
    services_str = ", ".join(services) if services else ""
    svc_note = f"\nMatch the caller's issue to the closest service from: [{services_str}]. Put it in 'service'." if services_str else ""
    prompt = f"""From this call transcript extract:
- caller_name
- caller_phone
- caller_email (if mentioned, else empty string)
- issue_description
- is_urgent (true/false)
- service{svc_note}

Return only valid JSON, no markdown.

Transcript:
{transcript}"""
    try:
        return json.loads(gemini(prompt))
    except Exception:
        return {"caller_name": "", "caller_phone": "", "caller_email": "",
                "issue_description": transcript[:200], "is_urgent": False, "service": ""}
