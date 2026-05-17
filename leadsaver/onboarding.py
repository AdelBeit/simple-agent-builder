import json
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """You are onboarding a small business owner onto LeadSaver, an AI missed-call service.

Your job is to collect the following information in a friendly, conversational way:
1. Business name
2. Business phone number (their real number, not the LeadSaver number)
3. Website URL
4. Contact form URL (if different from website, or say "same page" / "no form")
5. Business hours
6. Main services offered (ask them to list the top 3–6)
7. Owner's email address (to send the config summary)

Rules:
- One question at a time.
- Keep responses to 1–2 sentences.
- Be warm and encouraging — this is their setup experience.
- If they give you multiple pieces of info at once, acknowledge all of it and move to the next missing item.
- Once you have all 7 items, say: "Perfect, I have everything I need! I'll send a summary to [email] shortly. Welcome to LeadSaver!"

When done, output ONLY a JSON block (no markdown) in this exact format on the final turn:
{"done": true, "business": {"name": "", "phone": "", "website_url": "", "contact_form_url": "", "hours": "", "services": [], "owner_email": ""}}
"""

BEGIN_MESSAGE = (
    "Hi! I'm going to help you set up LeadSaver for your business — it'll take about 2 minutes. "
    "Let's start with the basics: what's the name of your business?"
)

DONE_SIGNAL = '"done": true'


def get_onboarding_reply(history: list[dict], message: str) -> tuple[str, dict | None]:
    """
    Returns (reply_text, business_data_or_None).
    business_data is populated on the final turn when the interview is complete.
    """
    contents = [
        types.Content(role=turn["role"], parts=[types.Part(text=turn["parts"][0])])
        for turn in history
    ] + [types.Content(role="user", parts=[types.Part(text=message)])]

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
