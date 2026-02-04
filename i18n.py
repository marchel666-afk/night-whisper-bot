import json
import os
from typing import Dict

class I18n:
    def __init__(self, locales_dir: str = "locales"):
        self.locales_dir = locales_dir
        self.translations: Dict[str, Dict] = {}
        self.default_lang = "en"
        self.supported_langs = ["ru", "en", "es", "de"]
        self._load_translations()
    
    def _load_translations(self):
        for lang in self.supported_langs:
            try:
                with open(f"{self.locales_dir}/{lang}.json", "r", encoding="utf-8") as f:
                    self.translations[lang] = json.load(f)
            except:
                self.translations[lang] = {}
    
    def get(self, key: str, lang: str = "en", **kwargs) -> str:
        lang = lang if lang in self.supported_langs else self.default_lang
        text = self.translations.get(lang, {}).get(key)
        if not text:
            text = self.translations.get(self.default_lang, {}).get(key, key)
        return text.format(**kwargs) if kwargs else text
    
    def get_language_name(self, code: str) -> str:
        names = {
            "ru": "🇷🇺 Русский",
            "en": "🇺🇸 English",
            "es": "🇪🇸 Español",
            "de": "🇩🇪 Deutsch"
        }
        return names.get(code, code)

i18n = I18n()