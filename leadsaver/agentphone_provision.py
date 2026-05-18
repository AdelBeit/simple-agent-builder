import httpx
from config import AGENT_PHONE_KEY, NGROK_DOMAIN, DEMO_MODE, AGENTPHONE_AGENT_ID, AGENTPHONE_ONBOARDING_NUMBER
from agent import _build_system_prompt, build_begin_message

AGENTPHONE_BASE = "https://api.agentphone.ai/v1"


def _headers():
    return {"Authorization": f"Bearer {AGENT_PHONE_KEY}", "Content-Type": "application/json"}


async def provision_business_agent(business: dict) -> dict:
    """
    Creates an AgentPhone agent + phone number for a newly onboarded business.
    Returns {"agent_id": str, "phone_number": str} or raises on failure.
    """

    if DEMO_MODE:
        # DEMO MODE: Reuses the existing onboarding number (+18145272190) instead of
        # provisioning a new number per business. Avoids per-number charges during testing.
        # The existing demo agent is patched with this business's prompt so it answers correctly.
        # TO RESTORE PRODUCTION BEHAVIOR: set DEMO_MODE=false in .env
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.patch(
                    f"{AGENTPHONE_BASE}/agents/{AGENTPHONE_AGENT_ID}",
                    headers=_headers(),
                    json={
                        "systemPrompt": _build_system_prompt(business),
                        "beginMessage": build_begin_message(business),
                    },
                )
            print(f"[PROVISION] Demo mode: patched agent {AGENTPHONE_AGENT_ID} for {business.get('name')}")
        except Exception as e:
            print(f"[PROVISION] Demo mode agent patch failed (non-fatal): {e}")
        return {"agent_id": AGENTPHONE_AGENT_ID, "phone_number": AGENTPHONE_ONBOARDING_NUMBER}

    # --- PRODUCTION PATH ---
    # Only runs when DEMO_MODE=false. Provisions a real per-business agent and number.
    # Each number costs money — do not run during testing.

    system_prompt = _build_system_prompt(business)
    begin_message = build_begin_message(business)
    webhook_url = f"https://{NGROK_DOMAIN}/webhook/call"

    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Create agent
        resp = await client.post(
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
        )
        resp.raise_for_status()
        agent = resp.json()
        agent_id = agent["id"]
        print(f"[PROVISION] Agent created: {agent_id} for {business['name']}")

        # 2. Provision a phone number attached to this agent
        resp = await client.post(
            f"{AGENTPHONE_BASE}/numbers",
            headers=_headers(),
            json={"country": "US", "agentId": agent_id},
        )
        resp.raise_for_status()
        number_data = resp.json()
        phone_number = number_data.get("phoneNumber", "")
        print(f"[PROVISION] Number provisioned: {phone_number}")

        # 3. Register webhook on the agent
        resp = await client.post(
            f"{AGENTPHONE_BASE}/webhooks",
            headers=_headers(),
            json={
                "url": webhook_url,
                "agentId": agent_id,
                "event_types": ["agent.message", "agent.call_ended"],
            },
        )
        if resp.status_code >= 300:
            print(f"[PROVISION] Webhook registration failed (non-fatal): {resp.status_code} {resp.text}")

    return {"agent_id": agent_id, "phone_number": phone_number}
