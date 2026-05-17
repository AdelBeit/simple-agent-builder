I'm building a SaaS called LeadSaver at a hackathon today. It's a missed-call lead capture service for small businesses (plumbers, roofers, contractors). Here's the full product flow:

Setup: Business owner calls an AgentPhone number → Gemini (2.5 Flash) conducts onboarding interview → Browser Use scrapes their website → Supermemory stores the business profile → AgentMail sends a config summary email → owner replies to tweak it → Supermemory updates
Live: Customer calls, owner misses it → AgentPhone forwards to my AI → Moss does sub-10ms RAG over the business's knowledge base → Gemini collects lead info → Browser Use submits it to the business's public contact form
Billing: Stripe subscription ($49/mo) sent as a link in the welcome email. Sponge handles agent-autonomous micropayments for per-session Browser Use costs.

My stack: Python or Node (undecided), AWS for hosting, all tools above have APIs/SDKs.
I need you to help me with the following before I write a single line of code:

Implementation priority — what is the strict build order? What is the MVP that still makes a compelling demo if I run out of time?
Unknowns to resolve — what are the 5–10 biggest technical unknowns or integration risks I need to spike on before committing to this architecture?
Data model — what does my core data schema look like? What needs to be persisted (Supermemory vs. a simple database vs. in-memory)?
Webhook architecture — I have at least 3 inbound webhooks (AgentPhone call, AgentMail reply, Browser Use completion). How should I structure these so they don't block each other?
The demo path — what is the single happiest-path flow I need to guarantee works for the judges, and what can be faked or hardcoded behind the scenes?
Python vs Node — given this specific stack (AgentPhone, AgentMail, Moss, Browser Use, Supermemory, Stripe, Sponge), which language has better SDK support and will be faster to build in today?

Be opinionated. I don't have time for "it depends." Tell me what to do.

---

## Gap Tracker

### [GAP-2] No fallback when business has no contact form

**Description:** LeadSaver currently only submits leads via Browser Use filling out a contact form. If a business has no contact form on their site, the lead is lost. Add an AgentMail fallback so the custom agent can email the lead details directly to the business owner when no form is detected.