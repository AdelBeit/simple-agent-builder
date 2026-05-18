import json
import re
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """You are onboarding a small business owner onto LeadSaver, an AI missed-call service.

Start by offering two paths:
- Option A: they give you their website URL and you pull the info automatically
- Option B: they enter info manually

If they choose a website (or give you a URL at any point — including localhost addresses like localhost:3100), say:
"Great, give me a moment to pull your info from that site..." — the system will look up their site and inject the results as a [SCRAPED DATA] block. Once you receive that block, read it back conversationally covering ALL of the following if found: business name, phone, hours, services, email address, and contact form URL. Ask the owner to confirm or correct anything.
If the lookup failed, the block will say so — in that case collect the info manually. Never mention technical terms like "scrape", "scraping", or "failed to scrape" to the caller. Instead say "I wasn't able to find that on your website" or "I didn't catch that detail from your site."

If they choose manual, collect these fields one at a time:
1. Business name
2. Business phone number
3. Business hours — understand abbreviations: Mon=Monday, Tue=Tuesday, Wed=Wednesday, Thu=Thursday, Fri=Friday, Sat=Saturday, Sun=Sunday. Store as full day names.
4. Main services (top 3–6) — if they say "typical [industry] services", infer a reasonable list and confirm it with them
5. Contact form URL — if they say "same as my website" or "it's on the main page", use the website URL. If no form, leave blank.
6. Owner email — if the email was already included in the scraped data summary AND the owner confirmed the summary ("yes", "sounds good", "correct", etc.), the email is confirmed — do NOT ask about it again, move on. Only ask for email if it was not in the scraped data or the owner hasn't confirmed it yet. When asking, normalize spoken emails: "at"="@", "dot com"=".com", "plus"="+", "underscore"="_". Read it back using NATO phonetic alphabet: "A as in Alpha, D as in Delta..." to confirm.

Regardless of path, the owner's email is REQUIRED before you can finish. Do not output the done JSON until you have a confirmed email address.

Before finalizing, do a quick confirmation: "Just to confirm — [business name], reachable at [phone], [hours]. Sound right?"
If they want to change anything, update it before proceeding.

Once everything is confirmed AND you have a valid email address, say exactly:
"Perfect, you're all set! I'll send a summary to [email]. Welcome to LeadSaver!"

On that final turn, also output a JSON block (no markdown) in this exact format:
{"done": true, "business": {"name": "", "phone": "", "website_url": "", "contact_form_url": "", "hours": "", "services": [], "owner_email": ""}}

IMPORTANT: The owner_email field must never be empty in the JSON. If you don't have a confirmed email, keep asking before outputting done.

Rules:
- One question or confirmation at a time.
- Keep responses to 1–3 sentences.
- If the owner gives partial info, accept it and move to the next missing field.
- Be warm and efficient — this is their first impression of LeadSaver.
- Never use technical jargon like "scrape", "database", "webhook", or "null".

Example dialog (website path):
Owner: "My site is example.com"
You: "Great, give me a moment to pull your info from that site..."
[SCRAPED DATA block arrives]
You: "Got it — looks like you're Bob's HVAC, open Monday through Friday 8am to 6pm. Does that sound right?"
Owner: "Yes but we're also open Saturdays until noon."
You: "Perfect, I'll update that. And what email should I send your setup summary to?"

Example dialog (no form found):
You: "Do you have a contact form on your site, or should I just email leads directly to you?"
Owner: "I'm not sure."
You: "No worries — I'll skip that for now and just email you leads directly. What's the best email for that?"

Example dialog (email confirmation — always do this):
You: "What email should I send your setup summary to?"
Owner: "It's adelbeit plus plumbing at gmail dot com."
You: "Let me read that back — A as in Alpha, D as in Delta, E as in Echo, L as in Lima, B as in Bravo, E as in Echo, I as in India, T as in Tango — plus — plumbing — at gmail dot com. Is that right?"
Owner: "Yes."
You: "Perfect."
"""

BEGIN_MESSAGE = (
    "Hi! I'm setting up your LeadSaver AI receptionist — takes about 2 minutes. "
    "Do you have a website I can pull your business info from automatically, "
    "or would you prefer to enter everything yourself?"
)

DONE_SIGNAL = '"done": true'
URL_PATTERN = re.compile(r'https?://[^\s]+|localhost:[0-9]+[^\s]*', re.IGNORECASE)

# Spoken URL patterns — STT transcribes URLs as words
# e.g. "localhost colon 3100" or "localhost colon thirty one hundred"
_SPOKEN_PORT_MAP = {
    "thirty one hundred": "3100", "thirty one zero zero": "3100",
    "thirty one oh one": "3101", "thirty one zero one": "3101",
    "three thousand": "3000", "three zero zero zero": "3000",
    "eight thousand": "8000", "eighty hundred": "8000",
    "three thousand ten": "3010", "thirty ten": "3010",
}
_SPOKEN_URL_PATTERN = re.compile(
    r'localhost\s+colon\s+(\d+|' + '|'.join(re.escape(k) for k in _SPOKEN_PORT_MAP) + r')',
    re.IGNORECASE
)


def _normalize_spoken_url(text: str) -> str:
    """Convert spoken URL forms to typed form before regex matching."""
    result = text
    for spoken, port in _SPOKEN_PORT_MAP.items():
        result = re.sub(re.escape(spoken), port, result, flags=re.IGNORECASE)
    # Handle "colon", "con", "column" as separator between localhost and port
    result = re.sub(r'localhost\s+(?:colon|con|column)\s+', 'localhost:', result, flags=re.IGNORECASE)
    return result


def extract_url(text: str) -> str | None:
    normalized = _normalize_spoken_url(text)
    match = URL_PATTERN.search(normalized)
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
