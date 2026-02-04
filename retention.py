from datetime import datetime, timedelta
from typing import List, Dict
from database import db

class RetentionSystem:
    MESSAGES = {
        1: {  # Через 1 день
            "ru": {
                "text": "🌙 *Возвращайся в Ночной Разговор*\n\nНочь снова близко. Если тревога не дает покоя — я рядом.\n\nТвои 3 бесплатных сообщения ждут тебя.",
                "cta": "🌙 Начать разговор"
            },
            "en": {
                "text": "🌙 *Come back to Night Whisper*\n\nNight is near again. If anxiety haunts you — I'm here.\n\nYour 3 free messages are waiting.",
                "cta": "🌙 Start conversation"
            }
        },
        3: {  # Через 3 дня
            "ru": {
                "text": "🌌 *Ты долго не заглядывал*\n\nИногда просто выговориться — уже половина решения. Я здесь, чтобы слушать без осуждения.\n\n💫 *Специально для тебя: +2 бонусных сообщения*",
                "cta": "🎁 Получить бонус"
            },
            "en": {
                "text": "🌌 *You haven't visited in a while*\n\nSometimes just talking is half the solution. I'm here to listen without judgment.\n\n💫 *Special for you: +2 bonus messages*",
                "cta": "🎁 Get bonus"
            }
        },
        7: {  # Через 7 дней (последнее)
            "ru": {
                "text": "🕯️ *Я скучаю по нашим ночным разговорам*\n\nЗнаешь, многие возвращаются. И ты сможешь.\n\n*Последний подарок: +5 сообщений и скидка 50% на Premium*",
                "cta": "🌟 Вернуться со скидкой"
            },
            "en": {
                "text": "🕯️ *I miss our night talks*\n\nYou know, many people come back. And you can too.\n\n*Final gift: +5 messages and 50% off Premium*",
                "cta": "🌟 Come back with discount"
            }
        }
    }
    
    def get_inactive_users_for_retention(self) -> List[Dict]:
        """Получает пользователей для отправки retention-сообщений"""
        users_to_message = []
        
        for days in [1, 3, 7]:
            inactive = db.get_inactive_users(days)
            for user_id, username, lang, last_active in inactive:
                # Проверяем, не отправляли ли уже сегодня
                if not self._was_message_sent_recently(user_id, days):
                    msg_data = self.MESSAGES.get(days, {}).get(lang, self.MESSAGES[days]["en"])
                    users_to_message.append({
                        "user_id": user_id,
                        "days": days,
                        "text": msg_data["text"],
                        "cta": msg_data["cta"],
                        "bonus": days >= 3  # Бонус начиная с 3-го дня
                    })
        
        return users_to_message
    
    def _was_message_sent_recently(self, user_id: int, message_type: int) -> bool:
        """Проверял, отправляли ли уже такое сообщение"""
        # Упрощенно — в реальности проверяй таблицу retention_messages
        return False
    
    def mark_message_sent(self, user_id: int, message_type: str):
        db.log_event(user_id, "retention_sent", message_type)

retention_system = RetentionSystem()