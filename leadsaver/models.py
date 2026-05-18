import json
import sqlite3
from config import DB_PATH

_services_cache: dict[int, list[str]] = {}


def _parse_services_from_profile(business: dict) -> dict:
    biz_id = business.get("id")
    if business.get("services") and isinstance(business["services"], list):
        return business
    if biz_id and biz_id in _services_cache:
        business["services"] = _services_cache[biz_id]
        return business

    profile = business.get("profile_text", "")
    if profile:
        try:
            from google import genai
            from config import GEMINI_API_KEY, GEMINI_MODEL
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=f"Extract the list of services from this business profile. Return only a JSON array of strings, nothing else.\n\n{profile}",
            )
            services = json.loads(response.text.strip())
            if isinstance(services, list):
                business["services"] = services
                if biz_id:
                    _services_cache[biz_id] = services
                return business
        except Exception:
            pass

    business["services"] = []
    return business


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            website_url TEXT,
            contact_form_url TEXT,
            profile_text TEXT,
            agentphone_number TEXT,
            agentphone_agent_id TEXT,
            owner_email TEXT,
            inbox_id TEXT,
            inbox_email TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER,
            caller_phone TEXT,
            caller_name TEXT,
            issue_description TEXT,
            call_transcript TEXT,
            form_submitted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id)
        );
    """)
    conn.commit()
    conn.close()


def save_lead(caller_name: str, caller_phone: str, issue: str, transcript: str, form_submitted: bool = False) -> int:
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO leads (business_id, caller_name, caller_phone, issue_description, call_transcript, form_submitted)
           VALUES (1, ?, ?, ?, ?, ?)""",
        (caller_name, caller_phone, issue, transcript, int(form_submitted)),
    )
    conn.commit()
    lead_id = cur.lastrowid
    conn.close()
    return lead_id


def mark_form_submitted(lead_id: int):
    conn = get_db()
    conn.execute("UPDATE leads SET form_submitted = 1 WHERE id = ?", (lead_id,))
    conn.commit()
    conn.close()


def get_all_leads() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM leads ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_business(name: str, phone: str, website_url: str, contact_form_url: str,
                  hours: str, services: list[str], owner_email: str,
                  agentphone_number: str = "", inbox_id: str = "", inbox_email: str = "") -> int:
    profile_text = f"Business: {name}\nPhone: {phone}\nHours: {hours}\nServices: {', '.join(services)}"
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO businesses (name, phone, website_url, contact_form_url, profile_text,
                                   agentphone_number, owner_email, inbox_id, inbox_email)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, phone, website_url, contact_form_url, profile_text,
         agentphone_number, owner_email, inbox_id, inbox_email),
    )
    conn.commit()
    biz_id = cur.lastrowid
    conn.close()
    return biz_id


def update_business_profile(business_id: int, profile_text: str):
    conn = get_db()
    conn.execute("UPDATE businesses SET profile_text = ? WHERE id = ?", (profile_text, business_id))
    conn.commit()
    conn.close()


def get_business(business_id: int) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM businesses WHERE id = ?", (business_id,)).fetchone()
    conn.close()
    return _parse_services_from_profile(dict(row)) if row else None


def get_business_by_number(agentphone_number: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM businesses WHERE agentphone_number = ?", (agentphone_number,)).fetchone()
    conn.close()
    return _parse_services_from_profile(dict(row)) if row else None
