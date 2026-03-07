import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "leads_db.sqlite")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            email TEXT PRIMARY KEY,
            name TEXT,
            source_url TEXT,
            niche TEXT,
            location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def email_exists(email: str) -> bool:
    email = email.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT 1 FROM leads WHERE email = ?', (email,))
    result = c.fetchone()
    conn.close()
    return result is not None

def save_lead(email: str, name: str, source_url: str, niche: str="", location: str=""):
    email = email.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO leads (email, name, source_url, niche, location)
            VALUES (?, ?, ?, ?, ?)
        ''', (email, name, source_url, niche, location))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Already exists
    conn.close()
