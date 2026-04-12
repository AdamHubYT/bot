import time
import aiosqlite
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = "db.db"

# 🧠 СОЗДАНИЕ БАЗЫ
@app.on_event("startup")
async def startup():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            money REAL DEFAULT 0,
            fuel REAL DEFAULT 0,
            level INTEGER DEFAULT 1,
            last_update INTEGER DEFAULT 0
        )
        """)
        await db.commit()

# 🔄 оффлайн доход
async def update_user(user_id):
    now = int(time.time())

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT level, last_update FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()

        if not row:
            await db.execute(
                "INSERT INTO users VALUES (?,?,?,?,?)",
                (user_id, 0, 0, 1, now)
            )
            await db.commit()
            return

        level, last = row

        delta = now - last
        fuel_gain = (delta / 3600) * level * 10

        await db.execute("""
            UPDATE users 
            SET fuel = fuel + ?, last_update = ?
            WHERE user_id = ?
        """, (fuel_gain, now, user_id))

        await db.commit()

# 📊 sync
@app.get("/sync")
async def sync(user_id: int):
    await update_user(user_id)

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT money, fuel, level FROM users WHERE user_id=?",
            (user_id,)
        )
        row = await cur.fetchone()

    if not row:
        return {"money": 0, "fuel": 0, "level": 1}

    return {
        "money": row[0],
        "fuel": row[1],
        "level": row[2]
    }

# 💰 sell
@app.post("/sell")
async def sell(user_id: int):
    await update_user(user_id)

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT fuel FROM users WHERE user_id=?", (user_id,))
        fuel = (await cur.fetchone())[0]

        if fuel <= 0:
            return {"ok": False}

        money = fuel * 2

        await db.execute("""
            UPDATE users 
            SET money = money + ?, fuel = 0
            WHERE user_id = ?
        """, (money, user_id))

        await db.commit()

    return {"ok": True, "money": money}

# ⬆️ upgrade
@app.post("/upgrade")
async def upgrade(user_id: int):
    await update_user(user_id)

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT money, level FROM users WHERE user_id=?", (user_id,))
        money, level = await cur.fetchone()

        cost = level * level * 100

        if money < cost:
            return {"ok": False}

        await db.execute("""
            UPDATE users
            SET money = money - ?, level = level + 1
            WHERE user_id = ?
        """, (cost, user_id))

        await db.commit()

    return {"ok": True}
