from datetime import datetime, time
from config import config

def is_night_time() -> bool:
    """Временно отключено — работает всегда"""
    return True
    
    if start < end:
        return start <= now < end
    return now >= start or now < end

def get_night_greeting_key() -> str:
    """Возвращает ключ приветствия по времени"""
    hour = datetime.now().hour
    if 22 <= hour <= 23:
        return "night_greeting_22"
    elif 0 <= hour < 4:
        return "night_greeting_0"
    else:
        return "night_greeting_5"