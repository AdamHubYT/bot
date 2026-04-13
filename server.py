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
            "last_update": int(time.time())
        }
        supabase.table("users").insert(user).execute()
        return user
    
    # Обновляем имя, если оно изменилось в Telegram
    current_user = res.data[0]
    if current_user.get("name") != name:
        supabase.table("users").update({"name": name}).eq("user_id", user_id).execute()
        current_user["name"] = name

    return current_user


# ---------------- OFFLINE ENGINE ----------------
def apply_offline(user):
    now = int(time.time())
    last = user.get("last_update", now)

    delta = min(max(0, now - last), 86400) # Максимум 24 часа оффлайна
    hours = delta / 3600

    oil_gain = hours * BASE_OIL_PER_HOUR * user["level"]
    fuel_gain = oil_gain * FUEL_PER_OIL

    fuel_gain *= (1 + user.get("ref_bonus", 0))

    supabase.table("users").update({
        "oil": user["oil"] + oil_gain,
        "fuel": user["fuel"] + fuel_gain,
        "last_update": now
    }).eq("user_id", user["user_id"]).execute()


# ---------------- SYNC ----------------
@app.get("/sync")
def sync(user_id: int, name: str = "Player"):
    user = get_user(user_id, name)
    apply_offline(user)
    return get_user(user_id, name)


# ---------------- SELL ----------------
@app.post("/sell")
def sell(user_id: int):
    # При продаже нам не нужно имя, get_user достанет его из БД
    user = get_user(user_id) 
    apply_offline(user)

    money_gain = user["fuel"] * FUEL_PRICE

    supabase.table("users").update({
        "money": user["money"] + money_gain,
        "fuel": 0
    }).eq("user_id", user_id).execute()

    return {"ok": True}


# ---------------- UPGRADE ----------------
@app.post("/upgrade")
def upgrade(user_id: int):
    user = get_user(user_id)

    if user["level"] >= MAX_LEVEL:
        return {"ok": False}

    cost = user["level"] * 250

    if user["money"] < cost:
        return {"ok": False}

    supabase.table("users").update({
        "money": user["money"] - cost,
        "level": user["level"] + 1
    }).eq("user_id", user_id).execute()

    return {"ok": True}


# ---------------- LEADERBOARD ----------------
@app.get("/leaderboard")
def leaderboard():
    # Теперь мы запрашиваем имя (name) вместо user_id
    res = supabase.table("users") \
        .select("name, money") \
        .order("money", desc=True) \
        .limit(10) \
        .execute()

    return res.data


# ---------------- REF ----------------
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

# ДОБАВЬ ЭТОТ КОД В SERVER.PY К ОСТАЛЬНЫМ ЭНДПОИНТАМ (@app.route)

@app.route('/process', methods=['POST'])
def process_oil():
    user_id = request.args.get('user_id')
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("SELECT oil FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    
    if row and row['oil'] > 0:
        oil_amount = row['oil']
        # Конвертация: 10 нефти = 1 топливо (меняй коэффициент на свой вкус)
        fuel_gained = oil_amount / 10.0 
        
        c.execute("UPDATE users SET oil=0, fuel=fuel+? WHERE user_id=?", (fuel_gained, user_id))
        conn.commit()
        
    conn.close()
    return jsonify({"status": "processed"})
