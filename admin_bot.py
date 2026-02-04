from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from config import config
from database import db

admin_router = Router()

def is_admin(user_id: int) -> bool:
    return user_id == config.ADMIN_ID

@admin_router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        """🔧 *Админ-панель*

Выберите действие:""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="👤 Найти пользователя", callback_data="admin_find_user")],
            [InlineKeyboardButton(text="✉️ Массовая рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="🎁 Выдать Premium", callback_data="admin_give_premium")],
            [InlineKeyboardButton(text="🚫 Заблокировать", callback_data="admin_block")],
        ]),
        parse_mode="Markdown"
    )

@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    stats = db.get_stats(7)
    
    text = f"""📊 *Статистика за 7 дней*

👥 Новых пользователей: {stats['new_users']}
💬 Всего сообщений: {stats['total_messages']}
👤 Всего пользователей: {stats['total_users']}
⭐ Premium: {stats['premium_users']}
🎁 Рефералов: {stats['referrals_total']} (конверсия: {stats['conversion_rate']})

🌍 Языки:
{chr(10).join([f"  {k}: {v}" for k, v in stats['languages'].items()])}"""
    
    await callback.message.edit_text(text, parse_mode="Markdown")

@admin_router.callback_query(F.data == "admin_give_premium")
async def give_premium_prompt(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    await callback.message.edit_text(
        "Введите команду:\n`/give_premium USER_ID ДНЕЙ`\n\nПример: `/give_premium 123456 30`",
        parse_mode="Markdown"
    )

@admin_router.message(Command("give_premium"))
async def give_premium(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        target_id = int(parts[1])
        days = int(parts[2])
        
        db.add_premium(target_id, days)
        db.log_admin_action(message.from_user.id, "give_premium", target_id, f"{days} days")
        
        await message.answer(f"✅ Выдан Premium пользователю {target_id} на {days} дней")
        
        # Уведомляем пользователя
        try:
            await message.bot.send_message(
                target_id,
                f"🎁 *Приятный сюрприз!*\n\nАдминистратор выдал вам Premium на {days} дней!\n\nПользуйтесь безлимитными разговорами всю ночь.",
                parse_mode="Markdown"
            )
        except:
            pass
            
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}\n\nИспользуйте: `/give_premium ID ДНЕЙ`")

@admin_router.message(Command("add_messages"))
async def add_messages(message: Message):
    """Добавить бесплатные сообщения пользователю"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        target_id = int(parts[1])
        count = int(parts[2])
        
        db.add_bonus_messages(target_id, count)
        
        await message.answer(f"✅ Добавлено {count} бонусных сообщений пользователю {target_id}")
        
        try:
            await message.bot.send_message(
                target_id,
                f"🎁 Вам добавлено *{count} бонусных сообщений*!\n\nИспользуйте их сегодня ночью.",
                parse_mode="Markdown"
            )
        except:
            pass
            
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@admin_router.message(Command("broadcast"))
async def broadcast(message: Message):
    """Массовая рассылка"""
    if not is_admin(message.from_user.id):
        return
    
    # Получаем текст после команды
    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        await message.answer("Используйте: `/broadcast ТЕКСТ СООБЩЕНИЯ`", parse_mode="Markdown")
        return
    
    # Получаем всех пользователей
    # Упрощенно — в реальности делай пагинацию
    await message.answer("📤 Рассылка начата... Это может занять время.")
    
    sent = 0
    failed = 0
    
    # Здесь должен быть код получения всех user_id из БД
    # и отправки сообщений с задержкой (чтобы не забанили)
    
    await message.answer(f"✅ Разослано: {sent}\n❌ Не доставлено: {failed}")

@admin_router.message(Command("block"))
async def block_user_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        target_id = int(message.text.split()[1])
        db.block_user(target_id, True)
        await message.answer(f"🚫 Пользователь {target_id} заблокирован")
    except:
        await message.answer("Используйте: `/block USER_ID`")