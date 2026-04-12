import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 ВСТАВЬ СВОИ (лучше через ENV на Render)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- USER ----------
def get_user(user_id: int):
    res = supabase.table("users").select("*").eq("user_id", user_id).execute()

    if not res.data:
        user = {
            "user_id": user_id,
            "money": 0,
            "fuel": 0,
            "level": 1,
            "last_update": int(time.time())
        }
        supabase.table("users").insert(user).execute()
        return user

    return res.data[0]

# ---------- UPDATE ----------
def update_user(user):
    now = int(time.time())
    delta = now - user["last_update"]

    income_per_sec = user["level"] * 0.05
    fuel_gain = delta * income_per_sec

    supabase.table("users").update({
        "fuel": user["fuel"] + fuel_gain,
        "last_update": now
    }).eq("user_id", user["user_id"]).execute()

# ---------- ROOT ----------
@app.get("/")
def root():
    return {"status": "ok"}

# ---------- SYNC ----------
@app.get("/sync")
def sync(user_id: int):
    user = get_user(user_id)
    update_user(user)
    user = get_user(user_id)
    return user

# ---------- SELL ----------
@app.post("/sell")
def sell(user_id: int):
    user = get_user(user_id)
    update_user(user)
    user = get_user(user_id)

    money = user["fuel"] * 3

    supabase.table("users").update({
        "money": user["money"] + money,
        "fuel": 0
    }).eq("user_id", user_id).execute()

    return {"ok": True, "money": money}

# ---------- UPGRADE ----------
@app.post("/upgrade")
def upgrade(user_id: int):
    user = get_user(user_id)

    cost = int(user["level"] ** 2 * 150)

    if user["money"] < cost:
        return {"ok": False}

    supabase.table("users").update({
        "money": user["money"] - cost,
        "level": user["level"] + 1
    }).eq("user_id", user_id).execute()

    return {"ok": True}
