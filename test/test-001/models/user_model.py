import time
import sqlite3
from db.database import get_conn
import bcrypt
import os
import random
import string
from config.config import OTP_EXPIRY

def create_user(username, email, password):
    pw = password.encode('utf-8')
    hashed = bcrypt.hashpw(pw, bcrypt.gensalt()).decode()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (username, email, password_hash, is_admin, is_approved, created_at)
            VALUES (?, ?, ?, 0, 0, ?)
        """, (username, email, hashed, int(time.time())))
        conn.commit()
        return True, None
    except sqlite3.IntegrityError as e:
        return False, str(e)
    finally:
        conn.close()

def get_user_by_username(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)

def verify_password(username, password):
    user = get_user_by_username(username)
    if not user:
        return False
    stored = user["password_hash"].encode()
    return bcrypt.checkpw(password.encode(), stored)

def set_otp(username, code, expiry_ts):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET otp_code = ?, otp_expiry = ? WHERE username = ?", (code, expiry_ts, username))
    conn.commit()
    conn.close()

def verify_otp(username, code):
    user = get_user_by_username(username)
    if not user:
        return False, "utente inesistente"
    if user["otp_code"] is None:
        return False, "OTP non inviato"
    now = int(time.time())
    if user["otp_expiry"] is None or now > user["otp_expiry"]:
        return False, "OTP scaduto"
    if user["otp_code"] != code:
        return False, "OTP errato"

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET otp_code = NULL, otp_expiry = NULL WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return True, None

def is_approved(username):
    user = get_user_by_username(username)
    return user and user["is_approved"] == 1

def list_pending_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, created_at FROM users WHERE is_approved = 0 AND is_admin = 0")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]   

def set_approval(user_id, approved: bool):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_approved = ? WHERE id = ?", (1 if approved else 0, user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, is_admin, is_approved, is_blocked, created_at FROM users")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]  

# Nuove helper:
def record_login_attempt(username, success: bool, ip=None, note=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO login_attempts (username, attempted_at, success, ip, note) VALUES (?, ?, ?, ?, ?)",
        (username, int(time.time()), 1 if success else 0, ip, note)
    )
    conn.commit()
    conn.close()

def increment_failed_attempt(username, threshold=5):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT failed_attempts FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return 0
    failed = (row["failed_attempts"] or 0) + 1
    cur.execute("UPDATE users SET failed_attempts = ?, last_attempt = ? WHERE username = ?", (failed, int(time.time()), username))
    conn.commit()
    conn.close()
    return failed

def reset_failed_attempts(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET failed_attempts = 0, last_attempt = ? WHERE username = ?", (int(time.time()), username))
    conn.commit()
    conn.close()

def block_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_blocked = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def unblock_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_blocked = 0, failed_attempts = 0 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_blocked_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, failed_attempts, last_attempt FROM users WHERE is_blocked = 1")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows] 

def get_login_attempts(limit=100):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM login_attempts ORDER BY attempted_at DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]  

def force_reset_password(user_id, new_password=None):
    if new_password is None:
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    pw = new_password.encode('utf-8')
    hashed = bcrypt.hashpw(pw, bcrypt.gensalt()).decode()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed, user_id))
    conn.commit()
    conn.close()
    return new_password
