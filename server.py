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
            "last_update": int(time.time())
        }
        supabase.table("users").insert(user).execute()
        return user

    return res.data[0]


# ---------------- OFFLINE FARM ----------------
def update_user(user):
    now = int(time.time())
    last = user["last_update"]
    delta = now - last

    hours = delta / 3600

    oil_gain = hours * user["level"] * 1
    fuel_gain = oil_gain * 7

    supabase.table("users").update({
        "oil": user["oil"] + oil_gain,
        "fuel": user["fuel"] + fuel_gain,
        "last_update": now
    }).eq("user_id", user["user_id"]).execute()


# ---------------- ROUTES ----------------
@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/sync")
def sync(user_id: int):
    user = get_user(user_id)
    update_user(user)
    return get_user(user_id)


@app.post("/sell")
def sell(user_id: int):
    user = get_user(user_id)
    update_user(user)

    money = user["fuel"] * 2.5

    supabase.table("users").update({
        "money": user["money"] + money,
        "fuel": 0
    }).eq("user_id", user_id).execute()

    return {"ok": True, "money": money}


@app.post("/upgrade")
def upgrade(user_id: int):
    user = get_user(user_id)

    cost = user["level"] * 150

    if user["money"] < cost:
        return {"ok": False, "error": "not enough money"}

    supabase.table("users").update({
        "money": user["money"] - cost,
        "level": user["level"] + 1
    }).eq("user_id", user_id).execute()

    return {"ok": True}
