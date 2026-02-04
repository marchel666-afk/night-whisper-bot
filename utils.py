from datetime import datetime, time

def is_night_time() -> bool:
    """Ночное время: 21:00 - 08:00"""
    now = datetime.now().time()
    start = time(21, 0)  # 21:00
    end = time(8, 0)     # 08:00
    
    if start < end:
        return start <= now < end
    else:  # Переход через полночь
        return now >= start or now < end

def get_night_greeting_key() -> str:
    hour = datetime.now().hour
    if 21 <= hour <= 23:
        return "night_greeting_22"
    elif 0 <= hour < 4:
        return "night_greeting_0"
    else:
        return "night_greeting_5"