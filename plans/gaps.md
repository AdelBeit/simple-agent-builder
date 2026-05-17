# LeadSaver — Gap Tracker

---

### [GAP-1] Email format polish
**Description:** Lead notification and config summary emails are plain text with minimal formatting. Polish both templates to be more professional — clear sections, business name in subject line, readable layout, and a consistent signature.
**Priority:** Low — works, just rough
**Files:** `leadsaver/agentmail.py` → `send_config_summary()`, `send_lead_notification()`

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
