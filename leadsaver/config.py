import os
from dotenv import load_dotenv

load_dotenv()

# AgentPhone
AGENT_PHONE_KEY = os.getenv("AGENT_PHONE_KEY")
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
    "contact_form_url": "http://localhost:3100/#contact",
    "services": [
        "Drain Cleaning",
        "Leak Repair",
        "Water Heater Install/Repair",
        "Pipe Replacement",
        "Emergency Plumbing",
        "Sewer Line Inspection",
    ],
}

# AgentMail
AGENTMAIL_API_KEY = os.getenv("AGENTMAIL_API_KEY")
AGENTMAIL_BASE_URL = "https://api.agentmail.to/v0"
AGENTMAIL_DOMAIN = "agentmail.to"
NGROK_DOMAIN = os.getenv("NGROK_WEBSITE", "").replace("https://", "").replace("http://", "")

# Server
DEMO_SITE_URL = "http://localhost:3000"
DB_PATH = "leadsaver.db"
