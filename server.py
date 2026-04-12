import time
import aiosqlite
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 СОЗДАНИЕ БАЗЫ
@app.on_event("startup")
async def startup():
    async with aiosqlite.connect("db.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            money REAL DEFAULT 0,
            fuel REAL DEFAULT 0,
            rig_level INTEGER DEFAULT 1,
            last_update INTEGER
        )
        """)
        await db.commit()

FUEL_PRICE = 2
UPGRADE_BASE = 100

def upgrade_cost(level):
    return UPGRADE_BASE * (level ** 2)

async def update(user_id):
    async with aiosqlite.connect("db.db") as db:
        cur = await db.execute(
            "SELECT rig_level, last_update FROM users WHERE user_id=?",
            (user_id,)
        )
        row = await cur.fetchone()

        now = int(time.time())

        if not row:
            await db.execute(
                "INSERT INTO users VALUES (?,0,0,1,?)",
                (user_id, now)
            )
            await db.commit()
            return

        lvl, last = row
        hours = (now - last) / 3600
        fuel = hours * lvl * 10

        await db.execute(
            "UPDATE users SET fuel = fuel + ?, last_update=? WHERE user_id=?",
            (fuel, now, user_id)
        )
        await db.commit()

@app.get("/")
async def root():
    return {"status": "ok"}

@app.get("/sync")
async def sync(user_id: int):
    await update(user_id)

    async with aiosqlite.connect("db.db") as db:
        cur = await db.execute(
            "SELECT money, fuel, rig_level FROM users WHERE user_id=?",
            (user_id,)
        )
        m, f, lvl = await cur.fetchone()

    return {"money": m, "fuel": f, "level": lvl}

@app.post("/sell")
async def sell(user_id: int):
    await update(user_id)

    async with aiosqlite.connect("db.db") as db:
        cur = await db.execute(
            "SELECT fuel FROM users WHERE user_id=?",
            (user_id,)
        )
        fuel = (await cur.fetchone())[0]

        if fuel < 1:
            return {"ok": False}

        money = fuel * FUEL_PRICE

        await db.execute("""
            UPDATE users 
            SET money = money + ?, fuel = 0, last_update=? 
            WHERE user_id=?
        """, (money, int(time.time()), user_id))

        await db.commit()

    return {"ok": True, "earned": money}

@app.post("/upgrade")
async def upgrade(user_id: int):
    await update(user_id)

    async with aiosqlite.connect("db.db") as db:
        cur = await db.execute(
            "SELECT money, rig_level FROM users WHERE user_id=?",
            (user_id,)
        )
        money, lvl = await cur.fetchone()

        cost = upgrade_cost(lvl)

        if money < cost:
            return {"ok": False}

        await db.execute("""
            UPDATE users 
            SET money = money - ?, rig_level = rig_level + 1
            WHERE user_id=?
        """, (cost, user_id))

        await db.commit()

    return {"ok": True}