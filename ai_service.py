import aiohttp
from typing import List, Dict
from config import config

class AIService:
    def __init__(self):
        self.api_key = config.GROQ_API_KEY
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.whisper_url = "https://api.groq.com/openai/v1/audio/transcriptions"
        
        self.prompts = {
            "ru": "Ты — ночной психолог Луна. Мягкий, эмпатичный стиль. Помогай с тревогой и бессонницей. Отвечай кратко (2-4 предложения), с эмодзи.",
            "en": "You are night psychologist Luna. Gentle, empathetic style. Help with anxiety and insomnia. Reply briefly (2-4 sentences), with emojis.",
            "es": "Eres psicólogo nocturno Luna. Estilo gentil y empático. Ayuda con ansiedad e insomnio. Responde brevemente (2-4 frases), con emojis.",
            "de": "Du bist Nachtpsychologe Luna. Sanfter, einfühlsamer Stil. Hilfe bei Angst und Schlaflosigkeit. Antworte kurz (2-4 Sätze), mit Emojis.",
            "default": "You are night psychologist Luna. Help with anxiety and insomnia. Brief replies (2-4 sentences)."
        }
        
        self.story_prompts = {
            "ru": "Расскажи короткую сонную историю (3-5 предложений). Спокойная, без напряжения, про природу, тепло, мягкость.",
            "en": "Tell a short sleepy story (3-5 sentences). Calm, no tension, about nature, warmth, softness.",
            "es": "Cuenta un cuento corto para dormir (3-5 frases). Tranquilo, sin tensión, sobre naturaleza y calidez.",
            "de": "Erzähle eine kurze Schlafgeschichte (3-5 Sätze). Ruhig, ohne Spannung, über Natur und Wärme."
        }
    
    async def transcribe_voice(self, voice_data: bytes) -> str:
        """Распознавание голоса через Groq Whisper (бесплатно!)"""
        if not self.api_key:
            return "(голосовое сообщение)"
        
        try:
            async with aiohttp.ClientSession() as session:
                form = aiohttp.FormData()
                form.add_field('file', voice_data, filename='voice.ogg', content_type='audio/ogg')
                form.add_field('model', 'whisper-large-v3')
                form.add_field('language', 'ru')  # Автоопределение или указать явно
                
                headers = {"Authorization": f"Bearer {self.api_key}"}
                
                async with session.post(self.whisper_url, headers=headers, data=form) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("text", "(не распознано)")
                    else:
                        error = await resp.text()
                        print(f"Whisper error: {error}")
                        return "(голосовое сообщение — текст недоступен)"
        except Exception as e:
            print(f"Transcription error: {e}")
            return "(голосовое сообщение)"
    
    async def get_response(self, messages: List[Dict], lang: str = "en", mode: str = "normal") -> str:
        if not self.api_key:
            return self._fallback_response(lang)
            
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        system = self.prompts.get(lang, self.prompts["default"])
        
        if mode == "confessional":
            system += " Сейчас режим исповеди. Будь особенно бережным и тактичным."
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "system", "content": system}] + messages[-10:],
            "temperature": 0.7,
            "max_tokens": 250
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, headers=headers, json=payload, timeout=30) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result["choices"][0]["message"]["content"]
                    else:
                        return self._fallback_response(lang)
        except Exception as e:
            print(f"AI error: {e}")
            return self._fallback_response(lang)
    
    async def generate_sleep_story(self, lang: str = "en") -> str:
        prompt = self.story_prompts.get(lang, self.story_prompts["en"])
        return await self.get_response([{"role": "user", "content": prompt}], lang, "story")
    
    def _fallback_response(self, lang: str) -> str:
        fallbacks = {
            "ru": "🌙 Я здесь с тобой. Расскажи подробнее, что тебя беспокоит?",
            "en": "🌙 I'm here with you. Tell me more about what's bothering you?",
            "es": "🌙 Estoy aquí contigo. Cuéntame más sobre qué te preocupa?",
            "de": "🌙 Ich bin hier bei dir. Erzähle mir mehr von dem, was dich beunruhigt?"
        }
        return fallbacks.get(lang, fallbacks["en"])

ai_service = AIService()