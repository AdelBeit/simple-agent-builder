import httpx
from config import AGENT_PHONE_KEY, NGROK_DOMAIN
from agent import _build_system_prompt, build_begin_message

AGENTPHONE_BASE = "https://api.agentphone.ai/v1"


def _headers():
    return {"Authorization": f"Bearer {AGENT_PHONE_KEY}", "Content-Type": "application/json"}


def provision_business_agent(business: dict) -> dict:
    """
    Creates an AgentPhone agent + phone number for a newly onboarded business.
    Returns {"agent_id": str, "phone_number": str} or raises on failure.
    """
    system_prompt = _build_system_prompt(business)
    begin_message = build_begin_message(business)
    webhook_url = f"https://{NGROK_DOMAIN}/webhook/call"

    # 1. Create agent
    resp = httpx.post(
        f"{AGENTPHONE_BASE}/agents",
        headers=_headers(),
        json={
            "name": business["name"],
            "description": f"AI receptionist for {business['name']}",
            "voiceMode": "webhook",
            "systemPrompt": system_prompt,
            "beginMessage": begin_message,
            "sttMode": "accurate",
            "ambientSound": "office",
            "denoisingMode": "noise-cancellation",
            "voiceSpeed": 1.0,
            "interruptionSensitivity": 0.7,
        },
        timeout=30,
    )
    resp.raise_for_status()
    agent = resp.json()
    agent_id = agent["id"]
    print(f"[PROVISION] Agent created: {agent_id} for {business['name']}")

    # 2. Provision a phone number attached to this agent
    resp = httpx.post(
        f"{AGENTPHONE_BASE}/numbers",
        headers=_headers(),
        json={"country": "US", "agentId": agent_id},
        timeout=30,
    )
    resp.raise_for_status()
    number_data = resp.json()
    phone_number = number_data.get("phoneNumber", "")
    print(f"[PROVISION] Number provisioned: {phone_number}")

    # 3. Register webhook on the agent
    resp = httpx.post(
        f"{AGENTPHONE_BASE}/webhooks",
        headers=_headers(),
        json={
            "url": webhook_url,
            "agentId": agent_id,
            "event_types": ["agent.message", "agent.call_ended"],
        },
        timeout=30,
    )
    if resp.status_code >= 300:
        print(f"[PROVISION] Webhook registration failed (non-fatal): {resp.status_code} {resp.text}")

    return {"agent_id": agent_id, "phone_number": phone_number}
