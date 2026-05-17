from browser_use import Agent as BrowserAgent, Browser
from langchain_google_genai import ChatGoogleGenerativeAI
from config import GEMINI_API_KEY, BUSINESS


def _get_llm():
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GEMINI_API_KEY)


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

    browser = Browser()
    agent = BrowserAgent(task=task, llm=_get_llm(), browser=browser)

    try:
        await agent.run()
        await browser.close()
        return True
    except Exception as e:
        print(f"[BROWSER] Form submission failed: {e}")
        await browser.close()
        return False


async def scrape_business_website(url: str) -> str:
    """Scrape a business website and return a plain-text profile summary."""
    task = f"""
    Go to {url}.
    Extract the following information from the website:
    - Business name and tagline
    - Services offered (list all)
    - Business hours
    - Phone number and address
    - Any pricing information
    - Any FAQs or common questions answered

    Return a clean plain-text summary with sections. No markdown, no HTML.
    """

    browser = Browser()
    agent = BrowserAgent(task=task, llm=_get_llm(), browser=browser)

    try:
        result = await agent.run()
        await browser.close()
        # browser-use returns the final agent message as the result
        return str(result) if result else ""
    except Exception as e:
        print(f"[BROWSER] Website scrape failed: {e}")
        await browser.close()
        return ""
