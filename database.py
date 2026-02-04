import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

class Database:
    def __init__(self, db_path: str = "night_whisper.db"):
        self.db_path = db_path
        self._init_db()
    
    def _get_conn(self):
        return sqlite3.connect(self.db_path)
    
    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    language TEXT DEFAULT 'en',
                    premium_until TIMESTAMP,
                    is_premium BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    night_messages_count INTEGER DEFAULT 0,
                    last_night_date TEXT,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_messages INTEGER DEFAULT 0,
                    referrer_id INTEGER,
                    referral_count INTEGER DEFAULT 0,
                    bonus_messages INTEGER DEFAULT 0,
                    is_blocked BOOLEAN DEFAULT 0,
                    trial_until TIMESTAMP,
                    trial_used BOOLEAN DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    is_confessional BOOLEAN DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    session_id INTEGER,
                    content TEXT,
                    is_user BOOLEAN,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_confessional BOOLEAN DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS analytics_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event_type TEXT,
                    event_data TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    converted_at TIMESTAMP,
                    bonus_given BOOLEAN DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS retention_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message_type TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    opened BOOLEAN DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS admin_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action_type TEXT,
                    target_user_id INTEGER,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_users_active ON users(last_active);
                CREATE INDEX IF NOT EXISTS idx_analytics_time ON analytics_events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_referrals_ref ON referrals(referrer_id);
            """)
    
    def add_user(self, user_id: int, username: str, lang: str = "en", referrer_id: int = None):
        with self._get_conn() as conn:
            try:
                trial_end = (datetime.now() + timedelta(days=3)).isoformat()
                conn.execute(
                    """INSERT INTO users (user_id, username, language, referrer_id, trial_until) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (user_id, username, lang, referrer_id, trial_end)
                )
                
                if referrer_id and referrer_id != user_id:
                    conn.execute(
                        "INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)",
                        (referrer_id, user_id)
                    )
                return True
            except sqlite3.IntegrityError:
                return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            if row:
                return {
                    "user_id": row[0], "username": row[1], "language": row[2],
                    "premium_until": row[3], "is_premium": row[4], "created_at": row[5],
                    "night_messages_count": row[6], "last_night_date": row[7],
                    "last_active": row[8], "total_messages": row[9], "referrer_id": row[10],
                    "referral_count": row[11], "bonus_messages": row[12], "is_blocked": row[13],
                    "trial_until": row[14], "trial_used": row[15]
                }
            return None
    
    def set_language(self, user_id: int, lang: str):
        with self._get_conn() as conn:
            conn.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
    
    def get_language(self, user_id: int) -> str:
        user = self.get_user(user_id)
        return user.get("language", "en") if user else "en"
    
    def update_last_active(self, user_id: int):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE users SET last_active = ?, total_messages = total_messages + 1 WHERE user_id = ?",
                (datetime.now().isoformat(), user_id)
            )
    
    def block_user(self, user_id: int, blocked: bool = True):
        with self._get_conn() as conn:
            conn.execute("UPDATE users SET is_blocked = ? WHERE user_id = ?", (blocked, user_id))
    
    def is_blocked(self, user_id: int) -> bool:
        user = self.get_user(user_id)
        return user.get("is_blocked", False) if user else False
    
    def check_and_reset_night_counter(self, user_id: int) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT last_night_date, night_messages_count, bonus_messages FROM users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            if not row:
                return 0
            
            last_date, count, bonus = row[0], row[1], row[2] or 0
            
            if last_date != today:
                conn.execute(
                    "UPDATE users SET night_messages_count = 0, last_night_date = ? WHERE user_id = ?",
                    (today, user_id)
                )
                return 0
            
            return count - bonus
    
    def increment_night_counter(self, user_id: int):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE users SET night_messages_count = night_messages_count + 1 WHERE user_id = ?",
                (user_id,)
            )
    
    def add_bonus_messages(self, user_id: int, count: int):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE users SET bonus_messages = bonus_messages + ? WHERE user_id = ?",
                (count, user_id)
            )
    
    def is_premium(self, user_id: int) -> bool:
        user = self.get_user(user_id)
        if not user or not user.get("is_premium"):
            return False
        if user.get("premium_until"):
            return datetime.fromisoformat(user["premium_until"]) > datetime.now()
        return False
    
    def is_trial_active(self, user_id: int) -> bool:
        user = self.get_user(user_id)
        if not user or user.get("trial_used"):
            return False
        if user.get("trial_until"):
            return datetime.fromisoformat(user["trial_until"]) > datetime.now()
        return False
    
    def end_trial(self, user_id: int):
        with self._get_conn() as conn:
            conn.execute("UPDATE users SET trial_used = 1 WHERE user_id = ?", (user_id,))
    
    def add_premium(self, user_id: int, days: int = 30):
        now = datetime.now()
        user = self.get_user(user_id)
        if user and user.get("premium_until") and datetime.fromisoformat(user["premium_until"]) > now:
            new_date = datetime.fromisoformat(user["premium_until"]) + timedelta(days=days)
        else:
            new_date = now + timedelta(days=days)
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE users SET premium_until = ?, is_premium = 1 WHERE user_id = ?",
                (new_date.isoformat(), user_id)
            )
    
    def remove_premium(self, user_id: int):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE users SET is_premium = 0, premium_until = NULL WHERE user_id = ?",
                (user_id,)
            )
    
    def start_session(self, user_id: int, is_confessional: bool = False) -> int:
        with self._get_conn() as conn:
            c = conn.cursor()
            end = datetime.now() + timedelta(minutes=40)
            c.execute(
                "INSERT INTO sessions (user_id, is_confessional, end_time) VALUES (?, ?, ?)",
                (user_id, is_confessional, end)
            )
            return c.lastrowid
    
    def get_active_session(self, user_id: int) -> Optional[Dict]:
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT * FROM sessions WHERE user_id = ? AND is_active = 1 ORDER BY id DESC LIMIT 1",
                (user_id,)
            )
            row = c.fetchone()
            if row:
                return {"id": row[0], "is_confessional": row[5]}
            return None
    
    def end_session(self, session_id: int):
        with self._get_conn() as conn:
            conn.execute("UPDATE sessions SET is_active = 0 WHERE id = ?", (session_id,))
    
    def add_message(self, user_id: int, session_id: int, content: str, is_user: bool, is_confessional: bool = False):
        if is_confessional:
            return
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO conversations (user_id, session_id, content, is_user, is_confessional) VALUES (?, ?, ?, ?, ?)",
                (user_id, session_id, content, is_user, is_confessional)
            )
    
    def get_referral_link(self, user_id: int) -> str:
        return f"https://t.me/night_whisper_ai_bot?start=ref{user_id}"
    
    def process_referral_conversion(self, user_id: int):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT referrer_id FROM referrals WHERE referred_id = ? AND status = 'pending'", (user_id,))
            row = c.fetchone()
            if row:
                referrer_id = row[0]
                c.execute(
                    "UPDATE referrals SET status = 'converted', converted_at = ? WHERE referred_id = ?",
                    (datetime.now().isoformat(), user_id)
                )
                c.execute(
                    "UPDATE users SET referral_count = referral_count + 1, bonus_messages = bonus_messages + 5 WHERE user_id = ?",
                    (referrer_id,)
                )
                return referrer_id
            return None
    
    def get_referral_stats(self, user_id: int) -> Dict:
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT COUNT(*), SUM(CASE WHEN status = 'converted' THEN 1 ELSE 0 END) FROM referrals WHERE referrer_id = ?",
                (user_id,)
            )
            total, converted = c.fetchone()
            return {"total": total or 0, "converted": converted or 0}
    
    def log_event(self, user_id: int, event_type: str, data: str = None):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO analytics_events (user_id, event_type, event_data) VALUES (?, ?, ?)",
                (user_id, event_type, data)
            )
    
    def get_stats(self, days: int = 7) -> Dict:
        with self._get_conn() as conn:
            c = conn.cursor()
            since = (datetime.now() - timedelta(days=days)).isoformat()
            
            c.execute("SELECT COUNT(*) FROM users WHERE created_at > ?", (since,))
            new_users = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type = 'message_sent' AND timestamp > ?", (since,))
            messages = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*), SUM(CASE WHEN is_premium THEN 1 ELSE 0 END) FROM users")
            total, premium = c.fetchone()
            
            c.execute("SELECT language, COUNT(*) FROM users GROUP BY language")
            langs = dict(c.fetchall())
            
            c.execute("SELECT COUNT(*), SUM(CASE WHEN status = 'converted' THEN 1 ELSE 0 END) FROM referrals WHERE created_at > ?", (since,))
            refs_total, refs_conv = c.fetchone()
            
            return {
                "period_days": days,
                "new_users": new_users,
                "total_messages": messages,
                "total_users": total,
                "premium_users": premium or 0,
                "languages": langs,
                "referrals_total": refs_total or 0,
                "referrals_converted": refs_conv or 0,
                "conversion_rate": f"{(refs_conv/refs_total*100):.1f}%" if refs_total else "0%"
            }
    
    def get_inactive_users(self, days: int) -> List[Tuple]:
        with self._get_conn() as conn:
            c = conn.cursor()
            since = (datetime.now() - timedelta(days=days)).isoformat()
            c.execute(
                "SELECT user_id, username, language, last_active FROM users WHERE last_active < ? AND is_blocked = 0",
                (since,)
            )
            return c.fetchall()
    
    def log_admin_action(self, admin_id: int, action_type: str, target_user_id: int, details: str):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) VALUES (?, ?, ?, ?)",
                (admin_id, action_type, target_user_id, details)
            )

db = Database()