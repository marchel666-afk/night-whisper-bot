from database import db
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_USERNAME = "NIGHT_WHISPER_Z_BOT"

class ReferralSystem:
    @staticmethod
    def get_referral_link(user_id: int) -> str:
        return f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
    
    @staticmethod
    def get_referral_keyboard(lang: str, user_id: int) -> InlineKeyboardMarkup:
        # Тексты кнопок
        share_text = "📤 Поделиться"
        stats_text = "📊 Моя статистика"
        back_text = "🔙 Назад"
        
        # Ссылка для шаринга
        link = ReferralSystem.get_referral_link(user_id)
        share_url = f"https://t.me/share/url?url={link}&text=🌙 Night Whisper - ночной психолог"
        
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=share_text, url=share_url)],
            [InlineKeyboardButton(text=stats_text, callback_data="show_referral_stats")],
            [InlineKeyboardButton(text=back_text, callback_data="back_to_menu")]
        ])
    
    @staticmethod
    def get_referral_stats_keyboard(lang: str, user_id: int) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к рефералам", callback_data="back_to_referral")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
        ])
    
    @staticmethod
    def get_referral_bonus_text(lang: str) -> str:
        texts = {
            "ru": "🎁 Пригласи друга и получи бонусы!\n\nЗа каждого друга:\n• +5 бесплатных сообщений\n• +3 дня Premium если купит",
            "en": "🎁 Invite a friend and get bonuses!\n\nFor each friend:\n• +5 free messages\n• +3 days Premium if they buy",
            "es": "🎁 Invita a un amigo y obtén bonos!\n\nPor cada amigo:\n• +5 mensajes gratis\n• +3 días Premium si compra",
            "de": "🎁 Lade einen Freund ein und erhalte Boni!\n\nPro Freund:\n• +5 kostenlose Nachrichten\n• +3 Tage Premium bei Kauf"
        }
        return texts.get(lang, texts["en"])
    
    @staticmethod
    def get_referral_stats_text(lang: str, stats: dict, user_id: int) -> str:
        link = ReferralSystem.get_referral_link(user_id)
        return f"""📊 Ваша статистика

Приглашено: {stats['total']}
Активных: {stats['converted']}

Ваши бонусы:
• +{stats['total'] * 5} сообщений
• +{stats['converted'] * 3} дней Premium

Ссылка:
{link}"""
    
    @staticmethod
    def parse_referral_start(start_param: str) -> int:
        if start_param and start_param.startswith("ref"):
            try:
                return int(start_param[3:])
            except:
                return None
        return None

referral_system = ReferralSystem()