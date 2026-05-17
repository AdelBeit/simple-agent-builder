import json
import re
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """You are onboarding a small business owner onto LeadSaver, an AI missed-call service.

Start by offering two paths:
- Option A: they give you their website URL and you extract everything automatically
- Option B: they enter info manually

If they choose a website (or give you a URL at any point), say:
"Great, give me a moment to pull your info from that site..." — the system will scrape it and inject the results into this conversation as a [SCRAPED DATA] block. Once you receive that block, read it back to the owner and ask them to confirm or correct anything.

If they choose manual, collect these fields one at a time:
1. Business name
2. Business phone number
3. Business hours
4. Main services (top 3–6)
5. Contact form URL (or "same as website" / "no form")
6. Owner email

Regardless of path, always collect the owner's email at the end if not already known.

Once you have all fields confirmed, say exactly:
"Perfect, you're all set! I'll send a summary to [email]. Welcome to LeadSaver!"

On that final turn, also output a JSON block (no markdown) in this exact format:
{"done": true, "business": {"name": "", "phone": "", "website_url": "", "contact_form_url": "", "hours": "", "services": [], "owner_email": ""}}

Rules:
- One question or confirmation at a time.
- Keep responses to 1–3 sentences.
- If the owner gives partial info, accept it and move to the next missing field.
- Be warm and efficient.
"""

BEGIN_MESSAGE = (
    "Hi! I'm setting up your LeadSaver AI receptionist — takes about 2 minutes. "
    "Do you have a website I can pull your business info from automatically, "
    "or would you prefer to enter everything yourself?"
)

DONE_SIGNAL = '"done": true'
URL_PATTERN = re.compile(r'https?://[^\s]+|localhost:[0-9]+[^\s]*', re.IGNORECASE)


def extract_url(text: str) -> str | None:
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

    if DONE_SIGNAL in reply:
        try:
            json_str = reply[reply.index("{"):reply.rindex("}") + 1]
            data = json.loads(json_str)
            return reply, data.get("business")
        except Exception:
            pass

    return reply, None
