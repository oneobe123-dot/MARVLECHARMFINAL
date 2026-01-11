import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config.config import BOT_TOKEN, ADMINS
from utils.db_utils import init_db, get_or_create_user, get_balance, add_balance, give_daily

# FSM для админа
class AdminAddBalance(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()

class AdminBroadcast(StatesGroup):
    waiting_message = State()

# Инициализация
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Кнопки
def main_menu(is_admin=False):
    buttons = [
        [InlineKeyboardButton("💰 Баланс", callback_data="balance"),
         InlineKeyboardButton("🎁 Ежедневный бонус", callback_data="daily")],
        [InlineKeyboardButton("📌 Пригласить", callback_data="ref"),
         InlineKeyboardButton("🏆 Лидеры по рефералам", callback_data="leaders_user")]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton("🛠 Админ панель", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_menu():
    buttons = [
        [InlineKeyboardButton("➕ Добавить баланс", callback_data="admin_add_balance")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🏅 Топ лидеров (все данные)", callback_data="admin_leaders_full")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    args = message.get_args()
    user_id = message.from_user.id
    ref_id = int(args) if args.isdigit() else None
    bal = await get_or_create_user(user_id, ref=ref_id)
    text = f"👋 Привет, <b>{message.from_user.first_name}</b>!\n💰 Баланс: <b>{bal}</b>\n"
    if ref_id:
        text += f"🎉 Ты пришёл по реферальной ссылке!\n"
    text += f"📌 Ваша ссылка:\nhttps://t.me/{(await bot.get_me()).username}?start={user_id}"
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=main_menu(user_id in ADMINS))

# Callback
@dp.callback_query()
async def callbacks(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    data = call.data

    # Пользовательские
    if data == "balance":
        bal = await get_balance(user_id)
        await call.message.answer(f"💰 Баланс: <b>{bal}</b>", parse_mode=ParseMode.HTML)
    elif data == "daily":
        bonus = await give_daily(user_id)
        if bonus:
            bal = await get_balance(user_id)
            await call.message.answer(f"🎁 Получено {bonus}!\n💰 Баланс: {bal}", parse_mode=ParseMode.HTML)
        else:
            await call.message.answer("❌ Бонус сегодня уже получен.")
    elif data == "ref":
        await call.message.answer(f"📌 Ваша ссылка:\nhttps://t.me/{(await bot.get_me()).username}?start={user_id}")
    elif data == "leaders_user":
        import aiosqlite
        async with aiosqlite.connect("data/users.db") as db:
            cur = await db.execute("SELECT user_id, ref_count FROM users ORDER BY ref_count DESC LIMIT 10")
            rows = await cur.fetchall()
        if not rows:
            await call.message.answer("Пока нет лидеров.")
            return
        text = "🏆 <b>Топ 10 по рефералам:</b>\n"
        for i, (uid, ref_count) in enumerate(rows, start=1):
            try:
                user = await bot.get_chat(uid)
                name = user.full_name
                link = f"<a href='tg://user?id={uid}'>{name}</a>"
            except:
                link = f"UserID: {uid}"
            text += f"{i}. {link} — {ref_count} приглашений\n"
        await call.message.answer(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    # Админ-панель
    elif data == "admin" and user_id in ADMINS:
        await call.message.answer("🛠 Админ панель:", reply_markup=admin_menu())
    elif data == "admin_add_balance" and user_id in ADMINS:
        await call.message.answer("Введите ID пользователя:")
        await state.set_state(AdminAddBalance.waiting_user_id)
    elif data == "admin_broadcast" and user_id in ADMINS:
        await call.message.answer("Введите текст рассылки:")
        await state.set_state(AdminBroadcast.waiting_message)
    elif data == "admin_leaders_full" and user_id in ADMINS:
        import aiosqlite
        async with aiosqlite.connect("data/users.db") as db:
            cur = await db.execute("SELECT user_id, balance, ref_count FROM users ORDER BY ref_count DESC")
            rows = await cur.fetchall()
        text = "🏅 <b>Все лидеры:</b>\n"
        for i, (uid, bal, ref_count) in enumerate(rows, start=1):
            try:
                user = await bot.get_chat(uid)
                name = user.full_name
                link = f"<a href='tg://user?id={uid}'>{name}</a>"
            except:
                link = f"UserID: {uid}"
            text += f"{i}. {link} — Баланс: {bal}, Приглашений: {ref_count}\n"
        await call.message.answer(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    else:
        await call.answer("❌ Нет доступа", show_alert=True)

# FSM админ
@dp.message(AdminAddBalance.waiting_user_id)
async def fsm_user_id(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Введите числовой ID")
        return
    await state.update_data(user_id=int(message.text))
    await message.answer("Введите сумму:")
    await state.set_state(AdminAddBalance.waiting_amount)

@dp.message(AdminAddBalance.waiting_amount)
async def fsm_amount(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Введите число")
        return
    data = await state.get_data()
    user_id = data["user_id"]
    amount = int(message.text)
    await add_balance(user_id, amount)
    await message.answer(f"✅ Добавлено {amount} пользователю {user_id}")
    await state.clear()

@dp.message(AdminBroadcast.waiting_message)
async def fsm_broadcast(message: types.Message, state: FSMContext):
    text = message.text
    import aiosqlite
    async with aiosqlite.connect("data/users.db") as db:
        async for row in db.execute("SELECT user_id FROM users"):
            try:
                await bot.send_message(row[0], text)
            except:
                continue
    await message.answer("✅ Рассылка завершена")
    await state.clear()

# Эхо
@dp.message()
async def echo(message: types.Message):
    await message.answer("Команда не распознана.", reply_markup=main_menu(message.from_user.id in ADMINS))

# Запуск
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
