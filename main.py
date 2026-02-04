import os
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice, InlineKeyboardMarkup, 
    InlineKeyboardButton, PreCheckoutQuery, SuccessfulPayment
)
from aiogram.filters import Command

from config import config
from database import db
from ai_service import ai_service
from referral import referral_system, BOT_USERNAME
from admin_bot import admin_router
from utils import is_night_time, get_night_greeting_key

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()
dp.include_router(admin_router)

user_sessions = {}
user_limits = {}
confessional_messages = {}

# ==================== НОВЫЕ ТЕКСТЫ ПРИВЕТСТВИЙ ====================

TEXTS = {
    "ru": {
        "start_chat": "💬 Начать разговор",
        "confessional": "🕯️ Режим исповеди",
        "sleep_story": "🌙 Сонная история",
        "buy_premium": "⭐ Купить Premium (150 ⭐)",
        "buy_session": "💫 Разовый сеанс (50 ⭐)",
        "referral": "🎁 Пригласить друга",
        "settings": "⚙️ Язык",
        "end": "❌ Завершить диалог",
        
        # НОВОЕ ПРИВЕТСТВИЕ
        "welcome": """👋 *Добро пожаловать в Night Whisper*

Я — ваш личный AI-психолог, доступный 24/7. 
Здесь вы можете безопасно выговориться, получить поддержку или просто поговорить о том, что тревожит.

*Что я умею:*
• 💬 Поддерживающие диалоги
• 🕯️ Анонимный режим исповеди (автоудаление)
• 🌙 Сонные истории для расслабления
• 🎙️ Голосовые сообщения

*Бесплатно каждый день:*
• 3 сообщения
• 1 исповедь  
• 1 сонная история

*⭐ Premium — неограниченный доступ!*""",
        
        "morning_greeting": "🌅 Доброе утро! Надеюсь, вы хорошо выспались.",
        "day_greeting": "☀️ Добрый день! Как проходит ваш день?",
        "evening_greeting": "🌆 Добрый вечер! Время подвести итоги.",
        "night_greeting": "🌙 Доброй ночи. Я рядом, если нужно поговорить.",
        
        "limit_reached": "🚫 *Лимит исчерпан!*\n\nКупите Premium или разовый сеанс, чтобы продолжить разговор.",
        "chat_started": "💬 *Разговор начат*\n\nЯ вас слушаю. Пишите текстом или голосом — я отвечу с заботой и вниманием.",
        "confessional_started": "🕯️ *Режим исповеди активирован*\n\n⏱️ 40 минут анонимного разговора\n🗑️ Все сообщения удалятся после\n🔒 Я ничего не сохраняю\n\nМожете говорить откровенно.",
        "story_generating": "🌙 *Придумываю сонную историю...*",
        "story_ready": "📖 *Сонная история*\n\n{text}\n\nЗакройте глаза и представьте это... 🌌",
        "premium_activated": "🎉 *Premium активирован!*\n\nТеперь у вас неограниченный доступ на 30 дней.\nСпасибо за доверие! ⭐",
        "session_activated": "✨ *Сеанс активирован!*\n\n40 минут без ограничений. Начинайте!",
        "choose_language": "🌍 Выберите язык:",
        "language_set": "✅ Язык изменён",
        "trial_active": "🎁 У вас 3 дня полного доступа!",
        "trial_ended": "⏰ Пробный период закончился.",
        "not_night": "🌅 Бот доступен только ночью (21:00-08:00)",  # Оставлено на всякий случай
    },
    "en": {
        "start_chat": "💬 Start conversation",
        "confessional": "🕯️ Confessional mode",
        "sleep_story": "🌙 Sleep story",
        "buy_premium": "⭐ Buy Premium (150 ⭐)",
        "buy_session": "💫 Single session (50 ⭐)",
        "referral": "🎁 Invite friend",
        "settings": "⚙️ Language",
        "end": "❌ End conversation",
        
        "welcome": """👋 *Welcome to Night Whisper*

I'm your personal AI psychologist, available 24/7.
Here you can safely talk things through, get support, or just chat about what's bothering you.

*What I can do:*
• 💬 Supportive conversations
• 🕯️ Anonymous confessional mode (auto-delete)
• 🌙 Sleep stories for relaxation
• 🎙️ Voice messages

*Free daily:*
• 3 messages
• 1 confession
• 1 sleep story

*⭐ Premium — unlimited access!*""",
        
        "morning_greeting": "🌅 Good morning! Hope you slept well.",
        "day_greeting": "☀️ Good afternoon! How is your day going?",
        "evening_greeting": "🌆 Good evening! Time to wrap up the day.",
        "night_greeting": "🌙 Good night. I'm here if you need to talk.",
        
        "limit_reached": "🚫 *Limit reached!*\n\nBuy Premium or a single session to continue.",
        "chat_started": "💬 *Conversation started*\n\nI'm listening. Text or voice — I'll respond with care.",
        "confessional_started": "🕯️ *Confessional mode activated*\n\n⏱️ 40 minutes of anonymous chat\n🗑️ Messages will be deleted after\n🔒 I save nothing\n\nSpeak freely.",
        "story_generating": "🌙 *Creating a sleep story...*",
        "story_ready": "📖 *Sleep Story*\n\n{text}\n\nClose your eyes and imagine... 🌌",
        "premium_activated": "🎉 *Premium activated!*\n\nYou now have unlimited access for 30 days.\nThank you for your trust! ⭐",
        "session_activated": "✨ *Session activated!*\n\n40 minutes without limits. Start whenever you're ready!",
        "choose_language": "🌍 Choose language:",
        "language_set": "✅ Language changed",
        "trial_active": "🎁 You have 3 days of full access!",
        "trial_ended": "⏰ Trial period ended.",
        "not_night": "🌅 Bot is only available at night (21:00-08:00)",
    }
}

def get_text(key: str, lang: str = "ru", **kwargs) -> str:
    text = TEXTS.get(lang, TEXTS["ru"]).get(key, key)
    return text.format(**kwargs) if kwargs else text

def get_main_menu(lang: str, is_premium: bool = False, in_session: bool = False):
    """Главное меню"""
    if in_session:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text("end", lang), callback_data="end_session")]
        ])
    
    buttons = [
        [InlineKeyboardButton(text=get_text("start_chat", lang), callback_data="start_chat")],
        [InlineKeyboardButton(text=get_text("confessional", lang), callback_data="confessional")],
        [InlineKeyboardButton(text=get_text("sleep_story", lang), callback_data="sleep_story")],
        [InlineKeyboardButton(text=get_text("referral", lang), callback_data="referral")],
    ]
    
    if not is_premium:
        buttons.append([InlineKeyboardButton(text=get_text("buy_premium", lang), callback_data="buy_premium")])
        buttons.append([InlineKeyboardButton(text=get_text("buy_session", lang), callback_data="buy_session")])
    
    buttons.append([InlineKeyboardButton(text=get_text("settings", lang), callback_data="settings")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def check_and_init_limits(user_id: int):
    today = datetime.now().strftime("%Y-%m-%d")
    if user_id not in user_limits or user_limits[user_id].get("date") != today:
        user_limits[user_id] = {"date": today, "story_used": False, "confessional_count": 0}
    return user_limits[user_id]

def has_full_access(user_id: int) -> bool:
    """Полный доступ: Premium или Триал или Разовый сеанс"""
    return (
        db.is_premium(user_id) or 
        db.is_trial_active(user_id) or
        (user_id in user_sessions and user_sessions[user_id].get("premium_temp"))
    )

def get_access_status(user_id: int) -> str:
    if db.is_premium(user_id):
        return "⭐ Premium"
    elif db.is_trial_active(user_id):
        trial_end = db.get_user(user_id).get("trial_until", "")[:10]
        return f"🎁 Trial until {trial_end}"
    elif user_id in user_sessions and user_sessions[user_id].get("premium_temp"):
        return "💫 Single session"
    return "🆓 Free version"

# ==================== КОМАНДЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    
    if db.is_blocked(user_id):
        return
    
    check_and_init_limits(user_id)
    
    user = db.get_user(user_id)
    lang = message.from_user.language_code or "ru"
    if lang not in ["ru", "en"]:
        lang = "ru"
    
    # Рефералка
    referrer_id = None
    if message.text and len(message.text.split()) > 1:
        start_param = message.text.split()[1]
        referrer_id = referral_system.parse_referral_start(start_param)
    
    if not user:
        db.add_user(user_id, message.from_user.username, lang, referrer_id)
        if referrer_id and referrer_id != user_id:
            db.add_bonus_messages(referrer_id, 5)
            try:
                await bot.send_message(referrer_id, "🎁 New referral! +5 messages.")
            except:
                pass
        trial_msg = get_text("trial_active", lang) + "\n\n"
    else:
        lang = user.get("language", lang)
        db.update_last_active(user_id)
        
        trial_msg = ""
        if user.get("trial_until") and not user.get("trial_used"):
            if datetime.fromisoformat(user["trial_until"]) < datetime.now():
                db.end_trial(user_id)
                trial_msg = get_text("trial_ended", lang) + "\n\n"
            else:
                trial_msg = f"🎁 Trial until {user['trial_until'][:10]}\n\n"
    
    # ПРОВЕРКА ВРЕМЕНИ ОТКЛЮЧЕНА — РАБОТАЕМ 24/7
    # if not is_night_time():
    #     await message.answer(get_text("not_night", lang))
    #     return
    
    greeting = get_text(get_night_greeting_key(), lang)
    welcome = get_text("welcome", lang)
    status = get_access_status(user_id)
    
    text = f"{greeting}\n\n{trial_msg}{welcome}\n\n📊 Status: {status}"
    
    await message.answer(text, reply_markup=get_main_menu(lang, has_full_access(user_id)), parse_mode="Markdown")

@dp.callback_query(F.data == "end_session")
async def end_session(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = db.get_language(user_id)
    session = user_sessions.get(user_id)
    
    if session and session.get("confessional"):
        msg_ids = confessional_messages.get(user_id, [])
        deleted = 0
        for msg_id in msg_ids:
            try:
                await bot.delete_message(user_id, msg_id)
                deleted += 1
            except:
                pass
        
        confessional_messages[user_id] = []
        user_sessions.pop(user_id, None)
        
        await callback.message.edit_text(f"🕯️ Confession ended\n\n{deleted} messages deleted.\nWhat was said stays between us.")
    elif session:
        db.end_session(session["id"])
        user_sessions.pop(user_id, None)
        await callback.message.edit_text("✅ Conversation ended.", reply_markup=get_main_menu(lang, has_full_access(user_id)))
    else:
        await callback.message.edit_text("No active conversation.", reply_markup=get_main_menu(lang, has_full_access(user_id)))

@dp.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery):
    lang = db.get_language(callback.from_user.id)
    buttons = [
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru")],
        [InlineKeyboardButton(text="🇺🇸 English", callback_data="set_lang_en")],
    ]
    await callback.message.edit_text(get_text("choose_language", lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("set_lang_"))
async def set_language(callback: CallbackQuery):
    new_lang = callback.data.split("_")[-1]
    db.set_language(callback.from_user.id, new_lang)
    await callback.message.edit_text(get_text("language_set", new_lang), reply_markup=get_main_menu(new_lang, has_full_access(callback.from_user.id)))

@dp.callback_query(F.data == "referral")
async def show_referral(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = db.get_language(user_id)
    stats = db.get_referral_stats(user_id)
    
    text = referral_system.get_referral_bonus_text(lang)
    text += f"\n\n🔗 Link: {referral_system.get_referral_link(user_id)}"
    text += f"\n\n📊 Invited: {stats['total']} | Active: {stats['converted']}"
    
    await callback.message.edit_text(text, reply_markup=referral_system.get_referral_keyboard(lang, user_id))

@dp.callback_query(F.data == "show_referral_stats")
async def show_referral_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = db.get_language(user_id)
    stats = db.get_referral_stats(user_id)
    
    text = referral_system.get_referral_stats_text(lang, stats, user_id)
    
    await callback.message.edit_text(text, reply_markup=referral_system.get_referral_stats_keyboard(lang, user_id))

@dp.callback_query(F.data == "back_to_referral")
async def back_to_referral(callback: CallbackQuery):
    await show_referral(callback)

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = db.get_language(user_id)
    
    user = db.get_user(user_id)
    trial_msg = ""
    if user and user.get("trial_until") and not user.get("trial_used"):
        if datetime.fromisoformat(user["trial_until"]) < datetime.now():
            db.end_trial(user_id)
            trial_msg = get_text("trial_ended", lang) + "\n\n"
        else:
            trial_msg = f"🎁 Trial until {user['trial_until'][:10]}\n\n"
    
    greeting = get_text(get_night_greeting_key(), lang)
    welcome = get_text("welcome", lang)
    status = get_access_status(user_id)
    
    text = f"{greeting}\n\n{trial_msg}{welcome}\n\n📊 Status: {status}"
    
    await callback.message.edit_text(text, reply_markup=get_main_menu(lang, has_full_access(user_id)), parse_mode="Markdown")

# ==================== МОНЕТИЗАЦИЯ (TELEGRAM STARS) ====================

@dp.callback_query(F.data == "start_chat")
async def start_chat(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = db.get_language(user_id)
    
    # ПРОВЕРКА ЛИМИТА для бесплатных
    if not has_full_access(user_id):
        count = db.check_and_reset_night_counter(user_id)
        if count >= 3:
            text = f"🚫 {get_text('limit_reached', lang)}\n\nYour status: {get_access_status(user_id)}"
            await callback.message.edit_text(text, reply_markup=get_main_menu(lang, False))
            return
    
    session_id = db.start_session(user_id, is_confessional=False)
    user_sessions[user_id] = {
        "id": session_id,
        "confessional": False,
        "messages": [],
        "start_time": datetime.now(),
        "premium_temp": False
    }
    
    await callback.message.edit_text(get_text("chat_started", lang), reply_markup=get_main_menu(lang, has_full_access(user_id), in_session=True))

@dp.callback_query(F.data == "confessional")
async def start_confessional(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = db.get_language(user_id)
    
    # ПРОВЕРКА ЛИМИТА: 1 исповедь за день
    if not has_full_access(user_id):
        limits = check_and_init_limits(user_id)
        if limits["confessional_count"] >= 1:
            text = (
                f"🚫 Confession limit reached!\n\n"
                f"Your status: {get_access_status(user_id)}\n\n"
                f"Buy Premium (⭐ 150) or single session (💫 50) for unlimited access."
            )
            await callback.message.edit_text(text, reply_markup=get_main_menu(lang, False))
            return
    
    confessional_messages[user_id] = []
    
    user_sessions[user_id] = {
        "id": 0,
        "confessional": True,
        "messages": [],
        "start_time": datetime.now(),
        "premium_temp": False
    }
    
    if not has_full_access(user_id):
        user_limits[user_id]["confessional_count"] += 1
    
    await callback.message.edit_text(get_text("confessional_started", lang), reply_markup=get_main_menu(lang, has_full_access(user_id), in_session=True))

@dp.callback_query(F.data == "sleep_story")
async def generate_story(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = db.get_language(user_id)
    
    # ПРОВЕРКА ЛИМИТА: 1 история за день
    if not has_full_access(user_id):
        limits = check_and_init_limits(user_id)
        if limits["story_used"]:
            text = (
                f"🚫 Story limit reached!\n\n"
                f"Your status: {get_access_status(user_id)}\n\n"
                f"Buy Premium (⭐ 150) or single session (💫 50) for a new story."
            )
            await callback.message.edit_text(text, reply_markup=get_main_menu(lang, False))
            return
    
    msg = await callback.message.edit_text(get_text("story_generating", lang))
    
    try:
        story = await ai_service.generate_sleep_story(lang)
        await msg.edit_text(get_text("story_ready", lang, text=story))
        
        if not has_full_access(user_id):
            user_limits[user_id]["story_used"] = True
        
        db.log_event(user_id, "story_generated", lang)
        
    except Exception as e:
        print(f"Story error: {e}")
        await msg.edit_text("❌ Generation error. Please try later.")

# ===== ОПЛАТА TELEGRAM STARS (ИСПРАВЛЕННАЯ) =====

@dp.callback_query(F.data == "buy_premium")
async def buy_premium(callback: CallbackQuery):
    """Покупка Premium через Telegram Stars"""
    lang = db.get_language(callback.from_user.id)
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="⭐ Night Whisper Premium",
        description="Unlimited conversations for 30 days\n• No limits\n• Priority support\n• All features included",
        payload="premium_1month",
        provider_token="",  # ОБЯЗАТЕЛЬНО пустой для Stars
        currency="XTR",     # XTR = Telegram Stars
        prices=[LabeledPrice(label="Premium 30 days", amount=150)],
        start_parameter="buy_premium",  # Для глубоких ссылок
    )

@dp.callback_query(F.data == "buy_session")
async def buy_session(callback: CallbackQuery):
    """Покупка разового сеанса через Telegram Stars"""
    lang = db.get_language(callback.from_user.id)
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="💫 Deep Session",
        description="40 minutes unlimited access\n• Unlimited messages\n• Unlimited stories & confessions\n• No restrictions",
        payload="deep_session",
        provider_token="",  # ОБЯЗАТЕЛЬНО пустой для Stars
        currency="XTR",     # XTR = Telegram Stars
        prices=[LabeledPrice(label="Session 40 min", amount=50)],
        start_parameter="buy_session",
    )

@dp.pre_checkout_query()
async def process_pre_checkout(query: PreCheckoutQuery):
    """Обязательная проверка перед оплатой"""
    # Можно добавить проверку payload здесь
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    """Обработка успешной оплаты"""
    user_id = message.from_user.id
    lang = db.get_language(user_id)
    payment = message.successful_payment
    
    if payment.invoice_payload == "premium_1month":
        # Premium на 30 дней
        db.add_premium(user_id, 30)
        db.process_referral_conversion(user_id)
        
        await message.answer(
            get_text("premium_activated", lang),
            parse_mode="Markdown"
        )
        db.log_event(user_id, "purchase_premium", f"150_stars_{payment.telegram_payment_charge_id}")
        
    elif payment.invoice_payload == "deep_session":
        # Разовый сеанс
        session_id = db.start_session(user_id)
        user_sessions[user_id] = {
            "id": session_id,
            "confessional": False,
            "messages": [],
            "start_time": datetime.now(),
            "premium_temp": True
        }
        
        await message.answer(
            get_text("session_activated", lang) + "\n\n✨ No limits in this session!",
            reply_markup=get_main_menu(lang, True, in_session=True),
            parse_mode="Markdown"
        )
        db.log_event(user_id, "purchase_session", f"50_stars_{payment.telegram_payment_charge_id}")

# ==================== ОБРАБОТКА СООБЩЕНИЙ ====================

@dp.message(F.voice)
async def handle_voice(message: Message):
    user_id = message.from_user.id
    
    if db.is_blocked(user_id):
        return
    
    session = user_sessions.get(user_id)
    if not session:
        lang = db.get_language(user_id)
        await message.answer("Choose mode in menu:", reply_markup=get_main_menu(lang, has_full_access(user_id)))
        return
    
    if session.get("confessional"):
        if user_id not in confessional_messages:
            confessional_messages[user_id] = []
        confessional_messages[user_id].append(message.message_id)
    
    # Проверка лимитов
    if not has_full_access(user_id) and not session.get("confessional"):
        count = db.check_and_reset_night_counter(user_id)
        if count >= 3:
            lang = db.get_language(user_id)
            await message.answer(get_text("limit_reached", lang), reply_markup=get_main_menu(lang, False))
            return
        db.increment_night_counter(user_id)
    
    await bot.send_chat_action(user_id, "typing")
    
    try:
        voice_file = await bot.get_file(message.voice.file_id)
        voice_data = await bot.download_file(voice_file.file_path)
        transcribed_text = await ai_service.transcribe_voice(voice_data.read())
        
        if session.get("confessional"):
            await message.reply(f"🎤 Recognized: {transcribed_text[:100]}...")
        
        await process_message(user_id, transcribed_text, is_voice=True)
        
    except Exception as e:
        print(f"Voice processing error: {e}")
        lang = db.get_language(user_id)
        await message.answer("🎤 Could not recognize voice. Try text.")

@dp.message(F.text)
async def handle_text(message: Message):
    user_id = message.from_user.id
    
    if db.is_blocked(user_id):
        return
    
    await process_message(user_id, message.text, is_voice=False, original_message=message)

async def process_message(user_id: int, text: str, is_voice: bool = False, original_message: Message = None):
    check_and_init_limits(user_id)
    db.update_last_active(user_id)
    
    session = user_sessions.get(user_id)
    if not session:
        lang = db.get_language(user_id)
        msg = original_message or await bot.send_message(user_id, "Choose mode:")
        await msg.answer("Choose mode in menu:", reply_markup=get_main_menu(lang, has_full_access(user_id)))
        return
    
    if session.get("confessional") and original_message:
        if user_id not in confessional_messages:
            confessional_messages[user_id] = []
        confessional_messages[user_id].append(original_message.message_id)
    
    # Таймер исповеди
    if session.get("confessional"):
        elapsed = datetime.now() - session["start_time"]
        if elapsed > timedelta(minutes=40):
            await end_session_manual(user_id)
            return
    
    # Проверка лимитов
    is_premium_session = has_full_access(user_id)
    
    if not is_premium_session and not session.get("confessional"):
        count = db.check_and_reset_night_counter(user_id)
        if count >= 3:
            lang = db.get_language(user_id)
            msg = original_message or await bot.send_message(user_id, "Limit")
            await msg.answer(get_text("limit_reached", lang), reply_markup=get_main_menu(lang, False))
            return
        db.increment_night_counter(user_id)
    
    await bot.send_chat_action(user_id, "typing")
    
    history = session.get("messages", [])
    history.append({"role": "user", "content": text})
    
    try:
        response = await ai_service.get_response(
            history, 
            db.get_language(user_id),
            "confessional" if session.get("confessional") else "normal"
        )
        
        if original_message:
            sent_msg = await original_message.answer(response)
        else:
            sent_msg = await bot.send_message(user_id, response)
        
        if session.get("confessional"):
            confessional_messages[user_id].append(sent_msg.message_id)
        
        history.append({"role": "assistant", "content": response})
        session["messages"] = history[-10:]
        
        if not session.get("confessional"):
            db.add_message(user_id, session["id"], text, True)
            db.add_message(user_id, session["id"], response, False)
        
        db.log_event(user_id, "message_sent", db.get_language(user_id))
        
    except Exception as e:
        print(f"AI Error: {e}")
        lang = db.get_language(user_id)
        fallback = "🌙 I'm here. Tell me more about what's bothering you?"
        if original_message:
            await original_message.answer(fallback)
        else:
            await bot.send_message(user_id, fallback)

async def end_session_manual(user_id: int):
    lang = db.get_language(user_id)
    session = user_sessions.get(user_id)
    
    if session and session.get("confessional"):
        msg_ids = confessional_messages.get(user_id, [])
        for msg_id in msg_ids:
            try:
                await bot.delete_message(user_id, msg_id)
            except:
                pass
        
        confessional_messages[user_id] = []
        user_sessions.pop(user_id, None)
        
        try:
            await bot.send_message(user_id, "🕯️ Confession automatically ended (40 min)\n\nAll messages deleted.")
        except:
            pass

# ==================== ВЕБ-СЕРВЕР ДЛЯ RENDER ====================

class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Bot is alive! Night Whisper running 24/7.')
    
    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), PingHandler)
    print(f"🌐 Web server starting on port {port}")
    server.serve_forever()

async def main():
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    port = int(os.getenv("PORT", 8080))
    print(f"✅ Web server started on port {port}")
    print(f"🤖 Bot @{BOT_USERNAME} is running 24/7!")
    print(f"💳 Telegram Stars payments enabled")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())