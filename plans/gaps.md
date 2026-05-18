# LeadSaver — Gap Tracker

---

### [GAP-2] No fallback when business has no contact form
**Description:** LeadSaver only submits leads via Browser Use filling out a contact form. If a business has no contact form, the lead is lost. Add an AgentMail fallback so the agent emails lead details directly to the business owner when no form is detected.
**Priority:** Medium — affects real businesses without contact forms
**Files:** `leadsaver/main.py` → `process_completed_call()`, `leadsaver/agentmail.py`

---

### [GAP-3] Browser Use not inferring service from scraped website
**Description:** The contact form `service` field defaults to "Drain Cleaning" or "Emergency Plumbing" based on urgency, ignoring the actual service the caller mentioned. Browser Use should infer the correct service dropdown value from the call transcript, matched against the services listed in the business's scraped profile.
**Priority:** Medium — affects form submission quality for judges
**Files:** `leadsaver/main.py` → `process_completed_call()`, `leadsaver/agent.py` → `extract_lead_info()`
**Fix:** Add `service` field to `extract_lead_info()` output and pass it through to `submit_lead_to_form()`.

---

### [GAP-4] Greeter flow too short — no optional sales pitch for interested owners
**Description:** The greeter/onboarding flow asks one question and moves on. There's no path for a business owner who wants to hear more — no longer explanation of how the service works, pricing details, or a guided walkthrough. Add an optional sales pitch branch where curious owners can explore features, ask questions, and hear a fuller pitch before deciding to sign up.
**Priority:** Medium — affects conversion of interested but hesitant owners
**Files:** `leadsaver/agent.py` → greeter system prompt, `leadsaver/main.py` → greeter webhook handler
