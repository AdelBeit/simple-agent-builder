import sqlite3
from config import DB_PATH


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
