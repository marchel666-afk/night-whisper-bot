from datetime import datetime, time

def is_night_time() -> bool:
    """Бот работает 24/7 без ограничений по времени"""
    return True

def get_night_greeting_key() -> str:
    """Приветствие в зависимости от времени суток"""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning_greeting"
    elif 12 <= hour < 18:
        return "day_greeting"
    elif 18 <= hour < 22:
        return "evening_greeting"
    else:
        return "night_greeting"