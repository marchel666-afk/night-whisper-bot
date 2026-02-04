from database import db
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_USERNAME = "NIGHT_WHISPER_Z_BOT"

class ReferralSystem:
    @staticmethod
    def get_referral_link(user_id: int) -> str:
        return f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
    
    @staticmethod
    def get_referral_keyboard(lang: str, user_id: int) -> InlineKeyboardMarkup:
        texts = {
            "ru": {"share": "📤 Поделиться", "stats": "📊 Моя статистика", "back": "🔙 Назад"},
            "en": {"share": "📤 Share", "stats": "📊 My stats", "back": "🔙 Back"},
            "es": {"share": "📤 Compartir", "stats": "📊 Mis estadísticas", "back": "🔙 Volver"},
            "de": {"share": "📤 Teilen", "stats": "📊 Meine Statistik", "back": "🔙 Zurück"}
        }
        t = texts.get(lang, texts["en"])
        
        # Ссылка для шаринга
        share_text = "🌙 Night Whisper — ночной психолог, который помогает с тревогой и бессонницей. Попробуй бесплатно!"
        share_url = f"https://t.me/share/url?url={ReferralSystem.get_referral_link(user_id)}&text={share_text}"
        
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t["share"], url=share_url)],
            [InlineKeyboardButton(text=t["stats"], callback_data="show_referral_stats")],
            [InlineKeyboardButton(text=t["back"], callback_data="back_to_menu")]
        ])
    
    @staticmethod
    def get_referral_stats_keyboard(lang: str, user_id: int) -> InlineKeyboardMarkup:
        """Клавиатура для возврата со статистики"""
        texts = {
            "ru": {"back": "🔙 Назад к рефералам", "menu": "🏠 Главное меню"},
            "en": {"back": "🔙 Back to referrals", "menu": "🏠 Main menu"},
            "es": {"back": "🔙 Volver a referidos", "menu": "🏠 Menú principal"},
            "de": {"back": "🔙 Zurück zu Empfehlungen", "menu": "🏠 Hauptmenü"}
        }
        t = texts.get(lang, texts["en"])
        
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t["back"], callback_data="back_to_referral")],
            [InlineKeyboardButton(text=t["menu"], callback_data="back_to_menu")]
        ])
    
    @staticmethod
    def get_referral_bonus_text(lang: str) -> str:
        texts = {
            "ru": """🎁 *Пригласи друга и получи бонусы!*

За каждого друга:
• +5 бесплатных сообщений сразу
• +3 дня Premium, если друг купит подписку

Твоя персональная ссылка:""",
            "en": """🎁 *Invite a friend and get bonuses!*

For each friend:
• +5 free messages instantly
• +3 days Premium if they subscribe

Your personal link:""",
            "es": """🎁 *¡Invita a un amigo y obtén bonos!*

Por cada amigo:
• +5 mensajes gratis al instante
• +3 días Premium si se suscriben

Tu enlace personal:""",
            "de": """🎁 *Lade einen Freund ein und erhalte Boni!*

Pro Freund:
• +5 kostenlose Nachrichten sofort
• +3 Tage Premium bei Abonnement

Dein persönlicher Link:"""
        }
        return texts.get(lang, texts["en"])
    
    @staticmethod
    def get_referral_stats_text(lang: str, stats: dict, user_id: int) -> str:
        """Текст статистики рефералов"""
        texts = {
            "ru": """📊 *Ваша реферальная статистика*

Приглашено друзей: {total}
Активных (купили Premium): {converted}

Ваши бонусы:
• +{messages} сообщений за рефералов
• +{days} дней Premium за конверсии

Ваша ссылка:
`{link}`""",
            "en": """📊 *Your Referral Statistics*

Friends invited: {total}
Active (bought Premium): {converted}

Your bonuses:
• +{messages} messages from referrals
• +{days} days Premium from conversions

Your link:
`{link}`"""
        }
        
        t = texts.get(lang, texts["en"])
        return t.format(
            total=stats['total'],
            converted=stats['converted'],
            messages=stats['total'] * 5,
            days=stats['converted'] * 3,
            link=ReferralSystem.get_referral_link(user_id)
        )
    
    @staticmethod
    def parse_referral_start(start_param: str) -> int:
        if start_param and start_param.startswith("ref"):
            try:
                return int(start_param[3:])
            except:
                return None
        return None

referral_system = ReferralSystem()