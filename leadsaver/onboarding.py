import json
import re
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """You are the inbound agent for LeadSaver, an AI receptionist service for small businesses ($49/month).

Your job has two phases — handle both in one conversation:

PHASE 1 — QUALIFY
If the caller asks what LeadSaver is: "LeadSaver answers your missed calls 24/7, collects the caller's name, number, and what they need, then emails it to you automatically."
If they ask about pricing: "$49/month, no setup fees."
When they're ready to set up, ask: "Do you have a website I can pull your info from, or would you prefer to go through it step by step?"

PHASE 2 — ONBOARD
Website path:
- Accept ANY URL the caller gives — including localhost addresses like localhost:3100, localhost:8000, or any local/dev address. Never say a URL is invalid.
- Say "Give me a moment to pull your info from that site..." — the system injects a [SCRAPED DATA] block.
- Read it back naturally covering: name, phone, hours, services, email, contact form. Ask owner to confirm.
- If the URL was completely garbled and unrecognizable, ask them to spell it clearly.
- NEVER say "give me a moment" unless you have a confirmed URL.

Manual path — collect one at a time:
1. Business name
2. Phone number
3. Hours (Mon/Tue/etc → full day names)
4. Services (top 3–6; infer from industry if they say "typical ones")
5. Contact form URL (use website URL if "same page"; blank if none)
6. Email — if already confirmed in scraped summary, skip. Otherwise ask once, read back with NATO phonetic alphabet: "A as in Alpha..."

FINISH
Once all info confirmed with a valid email, say a natural 1-2 sentence summary then: "I'll send a summary to [email]. Welcome to LeadSaver!"
Then on a new line output: [DATA]{"done": true, "business": {"name": "", "phone": "", "website_url": "", "contact_form_url": "", "hours": "", "services": [], "owner_email": ""}}
The [DATA] tag is never spoken — only text before it is read aloud.

Rules:
- One question at a time. 1–2 sentences per response.
- Never say "scrape", "database", "webhook", or "null".
- Never output [SCRAPED DATA] blocks yourself — they're system-injected.
- owner_email must never be empty in the JSON. Keep asking until confirmed.
- If owner asks to spell their email, do it immediately with NATO phonetic alphabet.
"""

BEGIN_MESSAGE = (
    "Hi! I'm setting up your LeadSaver AI receptionist — takes about 2 minutes. "
    "Do you have a website I can pull your business info from automatically, "
    "or would you prefer to enter everything yourself?"
)

DONE_SIGNAL = '[DATA]'
URL_PATTERN = re.compile(r'https?://[^\s]+|localhost:[0-9]+[^\s]*', re.IGNORECASE)


def extract_url(text: str) -> str | None:
    """Extract a typed URL from text. Spoken/garbled URLs are handled by Gemini asking for clarification."""
    match = URL_PATTERN.search(text)
    if match:
        url = match.group(0).rstrip('.,)')
        if not url.startswith('http'):
            url = 'http://' + url
        return url
    return None


def get_onboarding_reply(history: list[dict], message: str,
                         scraped_data: str | None = None) -> tuple[str, dict | None]:
    """
    Returns (reply_text, business_data_or_None).
    Pass scraped_data to inject website extraction results mid-conversation.
    """
    contents = [
        types.Content(role=turn["role"], parts=[types.Part(text=turn["parts"][0])])
        for turn in history
    ]

    user_text = message
    if scraped_data:
        user_text = f"{message}\n\n[SCRAPED DATA]\n{scraped_data}"

    contents.append(types.Content(role="user", parts=[types.Part(text=user_text)]))

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )

    reply = response.text.strip()

    # Strip any hallucinated [SCRAPED DATA] blocks Gemini might generate
    if "[SCRAPED DATA]" in reply:
        reply = reply[:reply.index("[SCRAPED DATA]")].strip()

    if DONE_SIGNAL in reply:
        try:
            spoken_reply, _, json_part = reply.partition("[DATA]")
            spoken_reply = spoken_reply.strip()
            data = json.loads(json_part.strip())
            return spoken_reply, data.get("business")
        except Exception:
            pass

    return reply, None
