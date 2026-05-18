# LeadSaver — Gap Tracker

---

### [GAP-2] No fallback when business has no contact form
**Description:** LeadSaver only submits leads via Browser Use filling out a contact form. If a business has no contact form, the lead is lost. Add an AgentMail fallback so the agent emails lead details directly to the business owner when no form is detected.
**Priority:** Medium — affects real businesses without contact forms
**Files:** `leadsaver/main.py` → `process_completed_call()`, `leadsaver/agentmail.py`

---

### [GAP-4] Greeter flow too short — no optional sales pitch for interested owners
**Description:** The greeter/onboarding flow asks one question and moves on. There's no path for a business owner who wants to hear more — no longer explanation of how the service works, pricing details, or a guided walkthrough. Add an optional sales pitch branch where curious owners can explore features, ask questions, and hear a fuller pitch before deciding to sign up.
**Priority:** Medium — affects conversion of interested but hesitant owners
**Files:** `leadsaver/agent.py` → greeter system prompt, `leadsaver/main.py` → greeter webhook handler
