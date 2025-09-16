import sqlite3
from pathlib import Path
from config.config import DEFAULT_ADMIN
import bcrypt

DB_PATH = Path(__file__).parent / "app.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE,
        password_hash TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        is_approved INTEGER DEFAULT 0,
        otp_code TEXT,
        otp_expiry INTEGER,
        failed_attempts INTEGER DEFAULT 0,
        is_blocked INTEGER DEFAULT 0,
        last_attempt INTEGER
    );
    """)
    conn.commit()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS login_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        attempted_at INTEGER,
        success INTEGER,
        ip TEXT,
        note TEXT
    );
    """)
    conn.commit()

    ...

    cur.execute("SELECT * FROM users WHERE username = ?", (DEFAULT_ADMIN["username"],))
    if cur.fetchone() is None:
        pw = DEFAULT_ADMIN["password"].encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(pw, salt)
        cur.execute("""
            INSERT INTO users (username, email, password_hash, is_admin, is_approved)
            VALUES (?, ?, ?, 1, 1)
        """, (DEFAULT_ADMIN["username"], None, hashed.decode()))
        conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("DB initialized.")
