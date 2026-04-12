import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 SUPABASE CONFIG
SUPABASE_URL = "https://dcrutnuamskjbdkutqfr.supabase.co"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRjcnV0bnVhbXNramJka3V0cWZyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjAwNjM0MywiZXhwIjoyMDkxNTgyMzQzfQ.ZmL58xaRyuUG2JzxUUzT_bKSRGFfElJTXoWcXPs6Ybk
SUPABASE_KEY = ""

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🧠 CREATE USER IF NOT EXISTS
def get_user(user_id: int):
    res = supabase.table("users").select("*").eq("user_id", user_id).execute()

    if len(res.data) == 0:
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

# 🔄 OFFLINE PROGRESS
def update_user(user):
    now = int(time.time())
    last = user["last_update"]

    delta = now - last
    fuel_gain = (delta / 3600) * user["level"] * 10

    supabase.table("users").update({
        "fuel": user["fuel"] + fuel_gain,
        "last_update": now
    }).eq("user_id", user["user_id"]).execute()

# 📊 SYNC
@app.get("/sync")
def sync(user_id: int):
    user = get_user(user_id)
    update_user(user)
    user = get_user(user_id)
    return user

# 💰 SELL
@app.post("/sell")
def sell(user_id: int):
    user = get_user(user_id)
    update_user(user)
    user = get_user(user_id)

    money = user["fuel"] * 2

    supabase.table("users").update({
        "money": user["money"] + money,
        "fuel": 0
    }).eq("user_id", user_id).execute()

    return {"ok": True}

# ⬆️ UPGRADE
@app.post("/upgrade")
def upgrade(user_id: int):
    user = get_user(user_id)

    cost = user["level"] * user["level"] * 100

    if user["money"] < cost:
        return {"ok": False}

    supabase.table("users").update({
        "money": user["money"] - cost,
        "level": user["level"] + 1
    }).eq("user_id", user_id).execute()

    return {"ok": True}