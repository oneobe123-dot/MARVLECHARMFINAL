import aiosqlite
from config.config import START_BALANCE, REF_BONUS, DAILY_BONUS

DB = "data/users.db"

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER,
                ref_by INTEGER,
                last_daily TEXT,
                ref_count INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def get_or_create_user(user_id: int, ref: int | None = None):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if row:
            return row[0]
        balance = START_BALANCE
        await db.execute(
            "INSERT INTO users (user_id, balance, ref_by, last_daily, ref_count) VALUES (?, ?, ?, ?, ?)",
            (user_id, balance, ref, None, 0)
        )
        await db.commit()
        if ref:
            await add_balance(ref, REF_BONUS)
            await db.execute("UPDATE users SET ref_count = ref_count + 1 WHERE user_id=?", (ref,))
            await db.commit()
        return balance

async def get_balance(user_id: int):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else None

async def add_balance(user_id: int, amount: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id)
        )
        await db.commit()

async def give_daily(user_id: int):
    import datetime
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT last_daily FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        today = datetime.date.today()
        if row and row[0]:
            last_date = datetime.date.fromisoformat(row[0])
            if last_date >= today:
                return 0
        await add_balance(user_id, DAILY_BONUS)
        await db.execute("UPDATE users SET last_daily=? WHERE user_id=?", (datetime.date.today().isoformat(), user_id))
        await db.commit()
        return DAILY_BONUS
