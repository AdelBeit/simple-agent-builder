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
    """Fetch a business website and return clean text using BeautifulSoup only."""
    import httpx, re
    from bs4 import BeautifulSoup

    try:
        if not url.startswith("http"):
            url = "http://" + url
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "head"]):
            tag.decompose()

        # Extract emails
        emails = list(set(re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', resp.text)))

        # Check for contact form
        has_form = bool(soup.find("form")) or bool(soup.find(id=re.compile(r'contact', re.I)))
        contact_form_url = f"{url}#contact" if has_form else ""

        # Clean text
        raw = soup.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        text = "\n".join(lines[:150])  # first 150 lines covers most business info

        result = text
        if emails:
            result += f"\n\nEmail: {emails[0]}"
        if contact_form_url:
            result += f"\nContact Form URL: {contact_form_url}"

        return result

    except Exception as e:
        print(f"[SCRAPE] Failed for {url}: {e}")
        return ""
