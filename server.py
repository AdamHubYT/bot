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

SUPABASE_URL = "https://dcrutnuamskjbdkutqfr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRjcnV0bnVhbXNramJka3V0cWZyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjAwNjM0MywiZXhwIjoyMDkxNTgyMzQzfQ.ZmL58xaRyuUG2JzxUUzT_bKSRGFfElJTXoWcXPs6Ybk"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- ECONOMY ----------------
BASE_OIL_PER_HOUR = 1
FUEL_PER_OIL = 8
FUEL_PRICE = 2.2
MAX_LEVEL = 10

# ---------------- USER ----------------
def get_user(user_id: int):
    res = supabase.table("users").select("*").eq("user_id", user_id).execute()

    if not res.data:
        user = {
            "user_id": user_id,
            "money": 0,
            "fuel": 0,
            "oil": 0,
            "level": 1,
            "ref_bonus": 0,
            "last_update": int(time.time())
        }
        supabase.table("users").insert(user).execute()
        return user

    return res.data[0]


# ---------------- OFFLINE ENGINE (FIXED) ----------------
def apply_offline(user):
    now = int(time.time())
    last = user.get("last_update", now)

    delta = max(0, now - last)

    # anti exploit (max 24h offline calc)
    delta = min(delta, 86400)

    hours = delta / 3600

    level = user["level"]

    oil_gain = hours * BASE_OIL_PER_HOUR * level
    fuel_gain = oil_gain * FUEL_PER_OIL

    # referral boost
    fuel_gain *= (1 + user.get("ref_bonus", 0))

    new_oil = user["oil"] + oil_gain
    new_fuel = user["fuel"] + fuel_gain

    supabase.table("users").update({
        "oil": new_oil,
        "fuel": new_fuel,
        "last_update": now
    }).eq("user_id", user["user_id"]).execute()


# ---------------- SYNC ----------------
@app.get("/sync")
def sync(user_id: int):
    user = get_user(user_id)
    apply_offline(user)
    return get_user(user_id)


# ---------------- SELL ----------------
@app.post("/sell")
def sell(user_id: int):
    user = get_user(user_id)
    apply_offline(user)

    money_gain = user["fuel"] * FUEL_PRICE

    supabase.table("users").update({
        "money": user["money"] + money_gain,
        "fuel": 0
    }).eq("user_id", user_id).execute()

    return {"ok": True, "money": money_gain}


# ---------------- UPGRADE ----------------
@app.post("/upgrade")
def upgrade(user_id: int):
    user = get_user(user_id)

    if user["level"] >= MAX_LEVEL:
        return {"ok": False, "error": "max level"}

    cost = user["level"] * 250

    if user["money"] < cost:
        return {"ok": False, "error": "not enough money"}

    supabase.table("users").update({
        "money": user["money"] - cost,
        "level": user["level"] + 1
    }).eq("user_id", user_id).execute()

    return {"ok": True, "new_level": user["level"] + 1}


# ---------------- REF SYSTEM FIXED ----------------
@app.get("/ref")
def ref(user_id: int, ref_id: int):
    if user_id == ref_id:
        return {"ok": False}

    ref_user = get_user(ref_id)

    new_bonus = min(ref_user.get("ref_bonus", 0) + 0.01, 0.20)

    supabase.table("users").update({
        "ref_bonus": new_bonus
    }).eq("user_id", ref_id).execute()

    return {"ok": True}
