import re
import httpx
from config import AGENTMAIL_API_KEY, AGENTMAIL_BASE_URL, AGENTMAIL_DOMAIN, NGROK_DOMAIN


def _headers():
    return {"Authorization": f"Bearer {AGENTMAIL_API_KEY}", "Content-Type": "application/json"}


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]", "", name.lower().replace(" ", ""))
    return slug[:30] or "business"


# ---------------------------------------------------------------------------
# Inbox
# ---------------------------------------------------------------------------

def create_inbox(business_name: str) -> dict:
    """Create an AgentMail inbox for a business. Returns {id, email}."""
    username = _slugify(business_name)
    resp = httpx.post(
        f"{AGENTMAIL_BASE_URL}/inboxes",
        headers=_headers(),
        json={"username": username, "domain": AGENTMAIL_DOMAIN, "display_name": business_name},
    )
    resp.raise_for_status()
    data = resp.json()
    inbox_id = data.get("id") or data.get("inboxId")
    email = data.get("email") or f"{username}@{AGENTMAIL_DOMAIN}"
    return {"id": inbox_id, "email": email}


def register_reply_webhook(inbox_id: str) -> bool:
    """Register webhook on the inbox so owner replies hit /webhook/email-reply."""
    webhook_url = f"https://{NGROK_DOMAIN}/webhook/email-reply"
    resp = httpx.post(
        f"{AGENTMAIL_BASE_URL}/webhooks",
        headers=_headers(),
        json={"url": webhook_url, "event_type": "message.received", "inbox_id": inbox_id},
    )
    return resp.status_code < 300


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------

def send_config_summary(inbox_id: str, owner_email: str, business: dict) -> bool:
    """Send onboarding config summary email to the business owner."""
    services = business.get("services", [])
    services_str = "\n".join(f"  • {s}" for s in services) if isinstance(services, list) else services

    text = f"""Hi there,

Welcome to LeadSaver! Here's the configuration we collected for {business['name']}:

  Business name:  {business['name']}
  Phone:          {business['phone']}
  Website:        {business.get('website_url', '—')}
  Contact form:   {business.get('contact_form_url', '—')}
  Hours:          {business.get('hours', '—')}
  Services:
{services_str}

If anything looks wrong, just reply to this email with your corrections and we'll update your profile automatically.

— LeadSaver
"""

    resp = httpx.post(
        f"{AGENTMAIL_BASE_URL}/inboxes/{inbox_id}/messages/send",
        headers=_headers(),
        json={
            "to": owner_email,
            "subject": f"Your LeadSaver setup for {business['name']} ✅",
            "text": text,
        },
    )
    return resp.status_code < 300


def send_lead_notification(inbox_id: str, owner_email: str, lead: dict, business_name: str) -> bool:
    """Notify owner of a new lead by email."""
    text = f"""New lead captured for {business_name}!

  Name:     {lead.get('caller_name', '—')}
  Phone:    {lead.get('caller_phone', '—')}
  Issue:    {lead.get('issue_description', '—')}
  Urgent:   {'Yes' if lead.get('is_urgent') else 'No'}

The contact form has already been submitted on their behalf.

— LeadSaver
"""
    resp = httpx.post(
        f"{AGENTMAIL_BASE_URL}/inboxes/{inbox_id}/messages/send",
        headers=_headers(),
        json={
            "to": owner_email,
            "subject": f"📞 New lead: {lead.get('caller_name', 'Unknown')} — {business_name}",
            "text": text,
        },
    )
    return resp.status_code < 300
