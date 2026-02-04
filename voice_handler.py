import aiohttp
from aiogram.types import Voice, Message

async def transcribe_voice(voice: Voice, bot) -> str:
    """Распознавание голоса через бесплатный API (или заглушка)"""
    # Скачиваем файл голоса
    file = await bot.get_file(voice.file_id)
    file_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
    
    # Здесь можно подключить Whisper API от Groq (платно) 
    # или использовать заглушку для MVP
    
    return "(🎤 Голосовое сообщение)"

# Альтернатива — используем Groq Whisper если есть деньги:
async def transcribe_with_groq(voice: Voice, bot, api_key: str) -> str:
    """Распознавание через Groq Whisper (стоит денег)"""
    file = await bot.get_file(voice.file_id)
    
    # Скачиваем файл
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}") as resp:
            voice_data = await resp.read()
    
    # Отправляем в Groq Whisper
    # Примечание: это стоит ~$0.006/минута, для MVP лучше заглушку
    return "(Голосовое сообщение распознано — текст недоступен в бесплатной версии)"