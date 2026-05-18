from browser_use import Agent as BrowserAgent, ChatGoogle
from config import BUSINESS


def _get_llm():
    return ChatGoogle(model="gemini-2.5-flash")


async def submit_lead_to_form(name: str, phone: str, email: str, service: str,
                               message: str, form_url: str | None = None) -> bool:
    """Fill and submit a business contact form using Browser Use."""
    url = form_url or BUSINESS["contact_form_url"]

    task = f"""
    Go to {url}.
    Fill out the contact form with these exact values:
    - Name field: {name}
    - Phone field: {phone}
    - Email field: {email if email else 'leave blank if not required'}
    - Service dropdown: {service}
    - Message/Description field: {message}
    Click the Submit button and confirm the form was submitted successfully.
    """

    try:
        agent = BrowserAgent(task=task, llm=_get_llm())
        await agent.run()
        return True
    except Exception as e:
        print(f"[BROWSER] Form submission failed: {e}")
        return False


async def scrape_business_website(url: str) -> str:
    """Fetch a business website and extract a plain-text profile summary."""
    import httpx
    from bs4 import BeautifulSoup
    from google import genai as _genai
    from config import GEMINI_API_KEY, GEMINI_MODEL

    try:
        if not url.startswith("http"):
            url = "http://" + url
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "head"]):
            tag.decompose()
        raw_text = soup.get_text(separator="\n", strip=True)
        raw_text = "\n".join(line for line in raw_text.splitlines() if line.strip())[:8000]

        client_g = _genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""From this website text, extract a business profile summary with:
- Business name and tagline
- Services offered (list)
- Business hours
- Phone number and address
- Email address (if found anywhere on the page) — label as "Email:"
- Contact form URL — if a contact form exists on this page ({url}), the contact form URL is {url}#contact unless a different URL is explicitly mentioned. Label as "Contact Form URL:"
- Any pricing info

Website text:
{raw_text}

Return plain text, no markdown."""

        from google.genai import types as _types
        response = client_g.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=_types.GenerateContentConfig(
                thinking_config=_types.ThinkingConfig(thinking_budget=0)
            ),
        )
        return response.text.strip()

    except Exception as e:
        print(f"[SCRAPE] Failed for {url}: {e}")
        return ""
