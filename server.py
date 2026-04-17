import time
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Твои данные подключения
SUPABASE_URL = "https://dcrutnuamskjbdkutqfr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRjcnV0bnVhbXNramJka3V0cWZyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjAwNjM0MywiZXhwIjoyMDkxNTgyMzQzfQ.ZmL58xaRyuUG2JzxUUzT_bKSRGFfElJTXoWcXPs6Ybk"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- ECONOMY ----------------
BASE_OIL_PER_HOUR = 2
FUEL_PER_OIL = 0.1
FUEL_PRICE = 5.0
MAX_LEVEL = 10

# ---------------- USER ----------------
def get_user(user_id: int, name: str = "Player"):
    res = supabase.table("users").select("*").eq("user_id", user_id).execute()

    if not res.data:
        user = {
            "user_id": user_id,
            "name": name,
            "money": 0,
            "fuel": 0,
            "oil": 0,
            "level": 1,
            "ref_bonus": 0,
            "last_bonus": 0, # Добавлено для бонуса
            "last_update": int(time.time())
        }
        supabase.table("users").insert(user).execute()
        return user
    
    current_user = res.data[0]
    if name != "Player" and current_user.get("name") != name:
        supabase.table("users").update({"name": name}).eq("user_id", user_id).execute()
        current_user["name"] = name

    return current_user

# ---------------- OFFLINE ENGINE ----------------
def apply_offline(user):
    now = int(time.time())
    last = user.get("last_update", now)

    delta = min(max(0, now - last), 86400) # Максимум 24 часа
    hours = delta / 3600

    oil_gain = hours * BASE_OIL_PER_HOUR * user["level"]
    oil_gain *= (1 + user.get("ref_bonus", 0))

    supabase.table("users").update({
        "oil": user["oil"] + oil_gain,
        "last_update": now
    }).eq("user_id", user["user_id"]).execute()

# ---------------- ENDPOINTS ----------------

@app.get("/sync")
def sync(user_id: int, name: str = "Player"):
    user = get_user(user_id, name)
    apply_offline(user)
    
    # Снова берем данные, чтобы учесть оффлайн-начисления
    fresh_user = get_user(user_id, name)
    
    # Проверка: можно ли забрать бонус? (86400 сек = 24 часа)
    now = int(time.time())
    last_b = fresh_user.get("last_bonus", 0)
    fresh_user["can_claim_bonus"] = (now - last_b) >= 86400
    
    return fresh_user

@app.post("/daily")
def claim_daily(user_id: int):
    user = get_user(user_id)
    now = int(time.time())
    last_b = user.get("last_bonus", 0)
    
    # Если 24 часа еще не прошло
    if (now - last_b) < 86400:
        return {"ok": False, "message": "Бонус еще не готов!"}

    reward_money = 50
    reward_fuel = 10
    
    supabase.table("users").update({
        "money": user["money"] + reward_money,
        "fuel": user["fuel"] + reward_fuel,
        "last_bonus": now
    }).eq("user_id", user_id).execute()

    return {"ok": True, "reward_money": reward_money, "reward_fuel": reward_fuel}

@app.post("/process")
def process_oil(user_id: int):
    user = get_user(user_id)
    apply_offline(user)
    user = get_user(user_id)
    
    if user["oil"] > 0:
        oil_amount = user["oil"]
        fuel_gained = oil_amount * FUEL_PER_OIL
        
        supabase.table("users").update({
            "oil": 0,
            "fuel": user["fuel"] + fuel_gained
        }).eq("user_id", user_id).execute()
        return {"ok": True, "status": "processed", "gained": fuel_gained}
    return {"ok": False, "message": "No oil to process"}

@app.post("/sell")
def sell(user_id: int):
    user = get_user(user_id)
    if user["fuel"] > 0:
        money_gain = user["fuel"] * FUEL_PRICE
        supabase.table("users").update({
            "money": user["money"] + money_gain,
            "fuel": 0
        }).eq("user_id", user_id).execute()
        return {"ok": True, "gained": money_gain}
    return {"ok": False, "message": "No fuel to sell"}

@app.post("/upgrade")
def upgrade(user_id: int):
    user = get_user(user_id)
    if user["level"] >= MAX_LEVEL:
        return {"ok": False, "message": "Max level reached"}
    cost = user["level"] * 250
    if user["money"] < cost:
        return {"ok": False, "message": "Not enough money"}

    supabase.table("users").update({
        "money": user["money"] - cost,
        "level": user["level"] + 1
    }).eq("user_id", user_id).execute()
    return {"ok": True}

@app.get("/leaderboard")
def leaderboard():
    res = supabase.table("users") \
        .select("name, money") \
        .order("money", desc=True) \
        .limit(10) \
        .execute()
    return res.data

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
