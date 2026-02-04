import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List
from collections import Counter
import json

class Analytics:
    def __init__(self, db_path: str = "night_whisper.db"):
        self.db_path = db_path
        self._init_analytics_tables()
    
    def _init_analytics_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS analytics_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event_type TEXT,
                    event_data TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS conversation_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER,
                    topic TEXT,
                    sentiment TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_events_type ON analytics_events(event_type);
                CREATE INDEX IF NOT EXISTS idx_events_date ON analytics_events(timestamp);
            """)
    
    def log_event(self, user_id: int, event_type: str, data: dict = None):
        """Логирование событий: message_sent, premium_bought, story_generated, etc."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO analytics_events (user_id, event_type, event_data) VALUES (?, ?, ?)",
                (user_id, event_type, json.dumps(data) if data else None)
            )
    
    def get_stats(self, days: int = 7) -> Dict:
        """Статистика за последние N дней"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            date_since = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Всего пользователей
            c.execute("SELECT COUNT(*) FROM users WHERE created_at > ?", (date_since,))
            new_users = c.fetchone()[0]
            
            # Всего сообщений
            c.execute("SELECT COUNT(*) FROM conversations WHERE timestamp > ?", (date_since,))
            messages = c.fetchone()[0]
            
            # Покупки Premium
            c.execute("SELECT COUNT(*), SUM(CASE WHEN is_premium THEN 1 ELSE 0 END) FROM users WHERE created_at > ?", (date_since,))
            total, premium = c.fetchone()
            
            # По языкам
            c.execute("SELECT language, COUNT(*) FROM users GROUP BY language")
            languages = dict(c.fetchall())
            
            # Распределение по часам (когда активность)
            c.execute("""
                SELECT strftime('%H', timestamp) as hour, COUNT(*) 
                FROM conversations 
                WHERE timestamp > ? 
                GROUP BY hour
            """, (date_since,))
            hourly_activity = {int(k): v for k, v in c.fetchall()}
            
            return {
                "period_days": days,
                "new_users": new_users,
                "total_messages": messages,
                "premium_conversion": f"{(premium/total*100):.1f}%" if total else "0%",
                "languages": languages,
                "hourly_activity": hourly_activity,
                "avg_messages_per_user": round(messages/new_users, 1) if new_users else 0
            }
    
    def get_conversation_summary(self, limit: int = 50) -> List[Dict]:
        """Последние диалоги для анализа (без персональных данных)"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                SELECT c.id, c.timestamp, 
                       LENGTH(c.content) as msg_length,
                       u.language
                FROM conversations c
                JOIN users u ON c.user_id = u.user_id
                ORDER BY c.timestamp DESC
                LIMIT ?
            """, (limit,))
            return [{"id": r[0], "time": r[1], "length": r[2], "lang": r[3]} for r in c.fetchall()]

analytics = Analytics()