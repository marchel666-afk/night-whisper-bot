import asyncio
import logging
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
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

# Тексты
TEXTS = {
    "ru": {
        "start_chat": "🌙 Начать разговор",
        "confessional": "⛪ Режим исповеди",
        "sleep_story": "📖 Сонная история",
        "buy_premium": "⭐ Купить Premium (150 ⭐)",
        "buy_session": "💫 Разовый сеанс (50 ⭐)",
        "referral": "🎁 Пригласить друга",
        "settings": "⚙️ Язык",
        "end": "❌ Завершить диалог",
        "welcome": "🌙 Night Whisper — ночной психолог\n\nЯ помогаю с тревогой и бессонницей.\n\n✨ Бесплатно каждую ночь:\n• 3 сообщения в чате\n• 1 режим исповеди\n• 1 сонная история\n\n💰 Premium даёт неограниченный доступ!",
        "not_night": "🌅 Я сплю с 08:00 до 21:00\n\nВозвращайся вечером — я буду рядом, когда станет тяжело.",
        "limit_reached": "🚫 Лимит исчерпан!\n\nКупи Premium (150 ⭐/мес) или разовый сеанс (50 ⭐) для продолжения.",
        "chat_started": "🌙 Разговор начат\n\nЯ слушаю. Пиши текстом или голосом.",
        "confessional_started": "⛪ Режим исповеди активирован\n\n⏱️ 40 минут\n🗑️ Сообщения удалятся после\n🔒 Я ничего не сохраняю",
        "story_generating": "🌙 Придумываю сонную историю...",
        "story_ready": "📖 Сонная история\n\n{text}\n\nЗакрывай глаза и представь это... 🌌",
        "premium_activated": "✨ Premium активирован!\n\nНеограниченные разговоры на 1 месяц.",
        "session_activated": "💫 Сеанс активирован!\n\n40 минут без лимитов.",
        "choose_language": "Выбери язык:",
        "language_set": "Язык изменён",
        "night_greeting_22": "🌙 Добрый вечер. Ночь только начинается...",
        "night_greeting_0": "🌌 Глубокая ночь. Ты не один.",
        "night_greeting_5": "🌅 Уже почти утро. Давай разберёмся с тревогами.",
        "trial_active": "🎁 У тебя 3 дня полного доступа!",
        "trial_ended": "⏰ Триал закончился. Купи Premium для продолжения.",
    },
    "en": {
        "start_chat": "🌙 Start conversation",
        "confessional": "⛪ Confessional mode",
        "sleep_story": "📖 Sleep story",
        "buy_premium": "⭐ Buy Premium (150 ⭐)",
        "buy_session": "💫 Single session (50 ⭐)",
        "referral": "🎁 Invite friend",
        "settings": "⚙️ Language",
        "end": "❌ End conversation",
        "welcome": "🌙 Night Whisper — night psychologist\n\nI help with anxiety and insomnia.\n\n✨ Free every night:\n• 3 chat messages\n• 1 confession\n• 1 sleep story\n\n💰 Premium gives unlimited access!",
        "not_night": "🌅 I sleep from 08:00 to 21:00\n\nCome back in the evening — I'll be here when it's hard.",
        "limit_reached": "🚫 Limit reached!\n\nBuy Premium (150 ⭐/month) or single session (50 ⭐) to continue.",
        "chat_started": "🌙 Conversation started\n\nI'm listening. Text or voice.",
        "confessional_started": "⛪ Confessional mode activated\n\n⏱️ 40 minutes\n🗑️ Messages will be deleted\n🔒 I save nothing",
        "story_generating": "🌙 Creating sleep story...",
        "story_ready": "📖 Sleep story\n\n{text}\n\nClose your eyes and imagine... 🌌",
        "premium_activated": "✨ Premium activated!\n\nUnlimited conversations for 1 month.",
        "session_activated": "💫 Session activated!\n\n40 minutes without limits.",
        "choose_language": "Choose language:",
        "language_set": "Language changed",
        "night_greeting_22": "🌙 Good evening. The night is just beginning...",
        "night_greeting_0": "🌌 Deep night. You are not alone.",
        "night_greeting_5": "🌅 Almost morning. Let's sort out your worries.",
        "trial_active": "🎁 You have 3 days of full access!",
        "trial_ended": "⏰ Trial ended. Buy Premium to continue.",
    }
}

def get_text(key: str, lang: str = "ru", **kwargs) -> str:
    text = TEXTS.get(lang, TEXTS["ru"]).get(key, key)
    return text.format(**kwargs) if kwargs else text

def get_main_menu(lang: str, is_premium: bool = False, in_session: bool = False):
    """Главное меню с кнопками покупок для бесплатных пользователей"""
    if in_session:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text("end", lang), callback_data="end_session")]
        ])
    
    # ВСЕГДА показываем кнопки покупок, если не премиум
    buttons = [
        [InlineKeyboardButton(text=get_text("start_chat", lang), callback_data="start_chat")],
        [InlineKeyboardButton(text=get_text("confessional", lang), callback_data="confessional")],
        [InlineKeyboardButton(text=get_text("sleep_story", lang), callback_data="sleep_story")],
        [InlineKeyboardButton(text=get_text("referral", lang), callback_data="referral")],
    ]
    
    # Кнопки покупок для НЕ премиум пользователей
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
        return f"🎁 Триал до {trial_end}"
    elif user_id in user_sessions and user_sessions[user_id].get("premium_temp"):
        return "💫 Разовый сеанс"
    return "🆓 Бесплатная версия"

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
                await bot.send_message(referrer_id, "🎁 Новый реферал! +5 сообщений.")
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
                trial_msg = f"🎁 Триал до {user['trial_until'][:10]}\n\n"
    
    # ПРОВЕРКА НОЧНОГО ВРЕМЕНИ 21:00-08:00
    if not is_night_time():
        await message.answer(get_text("not_night", lang))
        return
    
    greeting = get_text(get_night_greeting_key(), lang)
    welcome = get_text("welcome", lang)
    status = get_access_status(user_id)
    
    text = f"{greeting}\n\n{trial_msg}{welcome}\n\n📊 Статус: {status}"
    
    await message.answer(text, reply_markup=get_main_menu(lang, has_full_access(user_id)))

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
        
        await callback.message.edit_text(f"🕯️ Исповедь завершена\n\n{deleted} сообщений удалено.\nВсё осталось между нами.")
    elif session:
        db.end_session(session["id"])
        user_sessions.pop(user_id, None)
        await callback.message.edit_text("✅ Диалог завершён.", reply_markup=get_main_menu(lang, has_full_access(user_id)))
    else:
        await callback.message.edit_text("Нет активного диалога.", reply_markup=get_main_menu(lang, has_full_access(user_id)))

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
    text += f"\n\n🔗 Ссылка: {referral_system.get_referral_link(user_id)}"
    text += f"\n\n📊 Приглашено: {stats['total']} | Активных: {stats['converted']}"
    
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
            trial_msg = f"🎁 Триал до {user['trial_until'][:10]}\n\n"
    
    # Проверка ночи
    if not is_night_time():
        await callback.message.edit_text(get_text("not_night", lang))
        return
    
    greeting = get_text(get_night_greeting_key(), lang)
    welcome = get_text("welcome", lang)
    status = get_access_status(user_id)
    
    text = f"{greeting}\n\n{trial_msg}{welcome}\n\n📊 Статус: {status}"
    
    await callback.message.edit_text(text, reply_markup=get_main_menu(lang, has_full_access(user_id)))

# ===== МОНЕТИЗАЦИЯ =====

@dp.callback_query(F.data == "start_chat")
async def start_chat(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = db.get_language(user_id)
    
    # Проверка ночи
    if not is_night_time():
        await callback.message.edit_text(get_text("not_night", lang))
        return
    
    # ПРОВЕРКА ЛИМИТА для бесплатных
    if not has_full_access(user_id):
        count = db.check_and_reset_night_counter(user_id)
        if count >= 3:
            text = f"🚫 {get_text('limit_reached', lang)}\n\nВаш статус: {get_access_status(user_id)}"
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
    
    # Проверка ночи
    if not is_night_time():
        await callback.message.edit_text(get_text("not_night", lang))
        return
    
    # ПРОВЕРКА ЛИМИТА: 1 исповедь за ночь
    if not has_full_access(user_id):
        limits = check_and_init_limits(user_id)
        if limits["confessional_count"] >= 1:
            text = (
                f"🚫 Лимит исповеди достигнут!\n\n"
                f"Ваш статус: {get_access_status(user_id)}\n\n"
                f"Купите Premium (⭐ 150) или разовый сеанс (💫 50) для неограниченного доступа."
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
    
    # Проверка ночи
    if not is_night_time():
        await callback.message.edit_text(get_text("not_night", lang))
        return
    
    # ПРОВЕРКА ЛИМИТА: 1 история за ночь
    if not has_full_access(user_id):
        limits = check_and_init_limits(user_id)
        if limits["story_used"]:
            text = (
                f"🚫 Лимит историй достигнут!\n\n"
                f"Ваш статус: {get_access_status(user_id)}\n\n"
                f"Купите Premium (⭐ 150) или разовый сеанс (💫 50) для новой истории."
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
        await msg.edit_text("❌ Ошибка генерации. Попробуйте позже.")

# ===== ПЛАТЕЖИ =====

@dp.callback_query(F.data == "buy_premium")
async def buy_premium(callback: CallbackQuery):
    """Покупка Premium"""
    lang = db.get_language(callback.from_user.id)
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="⭐ Night Whisper Premium",
        description="Неограниченные разговоры на 1 месяц\n• Без лимитов\n• Приоритетная поддержка",
        payload="premium_1month",
        provider_token="",  # Пустой для Telegram Stars
        currency="XTR",
        prices=[LabeledPrice(label="Premium 1 месяц", amount=150)]
    )

@dp.callback_query(F.data == "buy_session")
async def buy_session(callback: CallbackQuery):
    """Покупка разового сеанса"""
    lang = db.get_language(callback.from_user.id)
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="💫 Глубокий сеанс",
        description="40 минут без лимитов\n• Неограниченные сообщения\n• Безлимитные истории и исповеди",
        payload="deep_session",
        provider_token="",  # Пустой для Telegram Stars
        currency="XTR",
        prices=[LabeledPrice(label="Сеанс 40 минут", amount=50)]
    )

@dp.pre_checkout_query()
async def process_pre_checkout(query):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    """Обработка успешной оплаты"""
    user_id = message.from_user.id
    lang = db.get_language(user_id)
    payload = message.successful_payment.invoice_payload
    
    if payload == "premium_1month":
        db.add_premium(user_id, 30)
        db.process_referral_conversion(user_id)
        await message.answer(get_text("premium_activated", lang))
        db.log_event(user_id, "purchase_premium", "150_stars")
        
    elif payload == "deep_session":
        session_id = db.start_session(user_id)
        user_sessions[user_id] = {
            "id": session_id,
            "confessional": False,
            "messages": [],
            "start_time": datetime.now(),
            "premium_temp": True
        }
        await message.answer(
            get_text("session_activated", lang) + "\n\n✨ В сеансе нет лимитов!",
            reply_markup=get_main_menu(lang, True, in_session=True)
        )
        db.log_event(user_id, "purchase_session", "50_stars")

# ===== ОБРАБОТКА СООБЩЕНИЙ =====

@dp.message(F.voice)
async def handle_voice(message: Message):
    user_id = message.from_user.id
    
    if db.is_blocked(user_id):
        return
    
    # Проверка ночи
    if not is_night_time():
        lang = db.get_language(user_id)
        await message.answer(get_text("not_night", lang))
        return
    
    session = user_sessions.get(user_id)
    if not session:
        lang = db.get_language(user_id)
        await message.answer("Выберите режим в меню:", reply_markup=get_main_menu(lang, has_full_access(user_id)))
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
            await message.reply(f"🎤 Распознано: {transcribed_text[:100]}...")
        
        await process_message(user_id, transcribed_text, is_voice=True)
        
    except Exception as e:
        print(f"Voice processing error: {e}")
        lang = db.get_language(user_id)
        await message.answer("🎤 Не удалось распознать голос. Попробуйте текстом.")

@dp.message(F.text)
async def handle_text(message: Message):
    user_id = message.from_user.id
    
    if db.is_blocked(user_id):
        return
    
    # Проверка ночи
    if not is_night_time():
        lang = db.get_language(user_id)
        await message.answer(get_text("not_night", lang))
        return
    
    await process_message(user_id, message.text, is_voice=False, original_message=message)

async def process_message(user_id: int, text: str, is_voice: bool = False, original_message: Message = None):
    check_and_init_limits(user_id)
    db.update_last_active(user_id)
    
    session = user_sessions.get(user_id)
    if not session:
        lang = db.get_language(user_id)
        msg = original_message or await bot.send_message(user_id, "Выберите режим:")
        await msg.answer("Выберите режим в меню:", reply_markup=get_main_menu(lang, has_full_access(user_id)))
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
            msg = original_message or await bot.send_message(user_id, "Лимит")
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
        fallback = "🌙 Я здесь. Расскажи подробнее, что тебя беспокоит?"
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
            await bot.send_message(user_id, "🕯️ Исповедь автоматически завершена (40 мин)\n\nВсе сообщения удалены.")
        except:
            pass

class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Bot is alive! Night Whisper running.')
    
    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(config.WEB_ADMIN_PORT) if hasattr(config, 'WEB_ADMIN_PORT') else 10000
    server = HTTPServer(('0.0.0.0', port), PingHandler)
    server.serve_forever()

async def main():
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    print(f"🌐 Web server started on port {config.WEB_ADMIN_PORT if hasattr(config, 'WEB_ADMIN_PORT') else 10000}")
    print(f"🕐 Ночной режим: 21:00 - 08:00")
    print(f"✅ Bot @{BOT_USERNAME} started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())