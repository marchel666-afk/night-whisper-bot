import os
from dataclasses import dataclass
from datetime import time
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
    ADMIN_SECRET: str = os.getenv("ADMIN_SECRET", "admin123")
    WEB_ADMIN_PORT: int = int(os.getenv("WEB_ADMIN_PORT", "7860"))
    
    # Ночное время
    NIGHT_START: time = time(22, 0)
    NIGHT_END: time = time(6, 0)
    
    # Лимиты
    FREE_MESSAGES_PER_NIGHT: int = 3
    PREMIUM_PRICE_STARS: int = 150
    SESSION_PRICE_STARS: int = 50
    SESSION_DURATION_MINUTES: int = 40
    
    # Рефералы
    REFERRAL_BONUS_MESSAGES: int = 5  # Бонусных сообщений за реферала
    REFERRAL_BONUS_PREMIUM_DAYS: int = 3  # Дней премиума за реферала с оплатой
    
    # Удержание
    INACTIVE_DAYS_1: int = 1  # Первое напоминание
    INACTIVE_DAYS_3: int = 3  # Второе напоминание  
    INACTIVE_DAYS_7: int = 7  # Последнее напоминание

config = Config()