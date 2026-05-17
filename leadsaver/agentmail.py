import re
import httpx
from config import AGENTMAIL_API_KEY, AGENTMAIL_BASE_URL, AGENTMAIL_DOMAIN, NGROK_DOMAIN, STRIPE_PAYMENT_LINK


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
    inbox_id = data.get("inbox_id") or data.get("email")
    email = data.get("email") or f"{username}@{AGENTMAIL_DOMAIN}"
    return {"id": inbox_id, "email": email}


def register_reply_webhook(inbox_id: str) -> bool:
    """Register webhook on the inbox so owner replies hit /webhook/email-reply."""
    webhook_url = f"https://{NGROK_DOMAIN}/webhook/email-reply"
    resp = httpx.post(
        f"{AGENTMAIL_BASE_URL}/webhooks",
        headers=_headers(),
        json={"url": webhook_url, "event_types": ["message.received"], "inbox_id": inbox_id},
    )
    return resp.status_code < 300


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------

def _html_wrap(title: str, body_html: str, footer: str = "— LeadSaver") -> str:
    return f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif; color:#1a1a1a; max-width:560px; margin:0 auto; padding:24px;">
<h2 style="color:#0a1f44;">{title}</h2>
{body_html}
<p style="color:#888; font-size:13px; margin-top:32px;">{footer}</p>
</body></html>"""


def send_config_summary(inbox_id: str, owner_email: str, business: dict) -> bool:
    """Send onboarding config summary email to the business owner."""
    services = business.get("services", [])
    services_str = "\n".join(f"  • {s}" for s in services) if isinstance(services, list) else services
    services_li = "".join(f"<li>{s}</li>" for s in services) if isinstance(services, list) else f"<li>{services}</li>"

    name = business["name"]
    text = f"""Hi there,

Your LeadSaver setup is complete. Here's what we've got on file:

  Business:      {name}
  Phone:         {business['phone']}
  Website:       {business.get('website_url', '—')}
  Contact form:  {business.get('contact_form_url', '—')}
  Hours:         {business.get('hours', '—')}
  Services:
{services_str}

Something off? Just reply to this email — we'll fix it right away.

To activate your subscription ($49/mo): {STRIPE_PAYMENT_LINK}

— LeadSaver
"""

    body_html = f"""<table cellpadding="8" cellspacing="0" style="border-collapse:collapse; font-size:15px;">
<tr><td style="font-weight:600; color:#555; width:140px;">Business</td><td>{name}</td></tr>
<tr><td style="font-weight:600; color:#555;">Phone</td><td>{business['phone']}</td></tr>
<tr><td style="font-weight:600; color:#555;">Website</td><td>{business.get('website_url', '—')}</td></tr>
<tr><td style="font-weight:600; color:#555;">Contact form</td><td>{business.get('contact_form_url', '—')}</td></tr>
<tr><td style="font-weight:600; color:#555;">Hours</td><td>{business.get('hours', '—')}</td></tr>
</table>
<h3 style="margin-top:20px; font-size:15px;">Services</h3>
<ul style="margin-top:4px;">{services_li}</ul>
<p style="margin-top:24px; color:#555;">Something off? Just reply to this email — we'll fix it right away.</p>
<p style="margin-top:16px;">
  <a href="{STRIPE_PAYMENT_LINK}" style="background:#0a1f44; color:#fff; padding:12px 24px; border-radius:6px; text-decoration:none; font-weight:600; font-size:15px;">
    Activate subscription — $49/mo
  </a>
</p>"""

    html = _html_wrap(f"Your AI receptionist is ready — {name} ✅", body_html)

    resp = httpx.post(
        f"{AGENTMAIL_BASE_URL}/inboxes/{inbox_id}/messages/send",
        headers=_headers(),
        json={
            "to": owner_email,
            "subject": f"Your LeadSaver setup for {name} ✅",
            "text": text,
            "html": html,
        },
    )
    return resp.status_code < 300


def send_lead_notification(inbox_id: str, owner_email: str, lead: dict, business_name: str, contact_form_url: str = "") -> bool:
    """Notify owner of a new lead by email."""
    caller = lead.get("caller_name", "—")
    phone = lead.get("caller_phone", "—")
    email = lead.get("caller_email", "—")
    issue = lead.get("issue_description", "—")
    urgent = "Yes" if lead.get("is_urgent") else "No"

    form_line_text = f"\nWe submitted their info to your contact form at {contact_form_url}.\n" if contact_form_url else "\nWe couldn't find a contact form on your site — follow up directly!\n"
    form_line_html = f'<p style="color:#555;">We submitted their info to your <a href="{contact_form_url}">contact form</a>.</p>' if contact_form_url else '<p style="color:#555;">We couldn\'t find a contact form on your site — follow up directly!</p>'

    text = f"""You've got a new lead for {business_name}:

  Name:    {caller}
  Phone:   {phone}
  Email:   {email}
  Issue:   {issue}
  Urgent:  {urgent}
{form_line_text}
— LeadSaver
"""

    body_html = f"""<table cellpadding="8" cellspacing="0" style="border-collapse:collapse; font-size:15px;">
<tr><td style="font-weight:600; color:#555; width:100px;">Name</td><td>{caller}</td></tr>
<tr><td style="font-weight:600; color:#555;">Phone</td><td>{phone}</td></tr>
<tr><td style="font-weight:600; color:#555;">Email</td><td>{email}</td></tr>
<tr><td style="font-weight:600; color:#555;">Issue</td><td>{issue}</td></tr>
<tr><td style="font-weight:600; color:#555;">Urgent</td><td>{"Yes" if lead.get("is_urgent") else "No"}</td></tr>
</table>
{form_line_html}"""

    html = _html_wrap(f"📞 New lead: {caller} — {business_name}", body_html)

    resp = httpx.post(
        f"{AGENTMAIL_BASE_URL}/inboxes/{inbox_id}/messages/send",
        headers=_headers(),
        json={
            "to": owner_email,
            "subject": f"📞 New lead: {caller} — {business_name}",
            "text": text,
            "html": html,
        },
    )
    return resp.status_code < 300
