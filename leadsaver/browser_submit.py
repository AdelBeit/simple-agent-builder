from browser_use import Agent as BrowserAgent, Browser
from langchain_google_genai import ChatGoogleGenerativeAI
from config import GEMINI_API_KEY, BUSINESS


async def submit_lead_to_form(name: str, phone: str, email: str, service: str, message: str) -> bool:
    """Fill and submit the Peak Flow Plumbing contact form using Browser Use."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GEMINI_API_KEY)

    task = f"""
    Go to {BUSINESS['contact_form_url']}.
    Fill out the contact form with these exact values:
    - Name field: {name}
    - Phone field: {phone}
    - Email field: {email}
    - Service dropdown: {service}
    - Message/Description field: {message}
    Click the Submit button.
    Confirm the form was submitted successfully.
    """

    browser = Browser()
    agent = BrowserAgent(task=task, llm=llm, browser=browser)

    try:
        result = await agent.run()
        await browser.close()
        return True
    except Exception as e:
        print(f"[BROWSER] Form submission failed: {e}")
        await browser.close()
        return False
