import os
from dotenv import load_dotenv

load_dotenv()

# AgentPhone
AGENT_PHONE_KEY = os.getenv("AGENT_PHONE_KEY")
AGENTPHONE_GREETER_AGENT_ID = os.getenv("AGENTPHONE_GREETER_AGENT_ID", "cmpaf11es02ema00ecord129h")
AGENTPHONE_ONBOARDING_AGENT_ID = os.getenv("AGENTPHONE_ONBOARDING_AGENT_ID", "cmpaf0jts02e1a00e2wv77bjh")
AGENTPHONE_ONBOARDING_NUMBER = os.getenv("AGENTPHONE_ONBOARDING_NUMBER", "+18148948272")
AGENTPHONE_AGENT_ID = os.getenv("AGENTPHONE_AGENT_ID", "cmpa92in80d4djz00jx56l5z2")
AGENTPHONE_NUMBER = os.getenv("AGENTPHONE_NUMBER", "+12318670908")

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

# Demo business
BUSINESS = {
    "name": "Peak Flow Plumbing",
    "tagline": "Austin's Most Trusted Plumber Since 1998",
    "phone": "(512) 555-0187",
    "address": "4821 Burnet Rd, Austin, TX 78756",
    "email": "service@peakflowplumbing.com",
    "hours": "Mon–Fri 7am–7pm, Sat 8am–5pm, 24/7 Emergency",
    "contact_form_url": f"http://localhost:{os.getenv('PORT_PLUMBER', '3100')}/#contact",
    "services": [
        "Drain Cleaning",
        "Leak Repair",
        "Water Heater Install/Repair",
        "Pipe Replacement",
        "Emergency Plumbing",
        "Sewer Line Inspection",
    ],
}

# Stripe
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PAYMENT_LINK = os.getenv("STRIPE_PAYMENT_LINK", "https://buy.stripe.com/leadsaver")

# AgentMail
AGENTMAIL_API_KEY = os.getenv("AGENTMAIL_API_KEY")
AGENTMAIL_BASE_URL = "https://api.agentmail.to/v0"
AGENTMAIL_DOMAIN = "agentmail.to"
NGROK_DOMAIN = os.getenv("NGROK_WEBSITE", "").replace("https://", "").replace("http://", "")

# Ports
PORT_BACKEND = int(os.getenv("PORT_BACKEND", "8000"))
PORT_PLUMBER = int(os.getenv("PORT_PLUMBER", "3100"))
PORT_STYLIST = int(os.getenv("PORT_STYLIST", "3101"))
PORT_ONBOARDING = int(os.getenv("PORT_ONBOARDING", "3010"))

# Server
DB_PATH = "leadsaver.db"
