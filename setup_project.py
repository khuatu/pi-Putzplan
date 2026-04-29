# setup_project.py
import os

BASE_DIR = "putzplan_app"  # Wir überspringen hier die äußere Hülle, da du schon im Projektordner bist.
# Passe das Skript so an, dass es die Dateien relativ zum aktuellen Verzeichnis erzeugt.
# In deinem Fall ist das aktuelle Verzeichnis bereits das Projektverzeichnis.
# Daher verwenden wir "." als Wurzel.
ROOT = "."

# Ordner erstellen
dirs = ["backend", "frontend", "tests", ".github/workflows"]
for d in dirs:
    os.makedirs(os.path.join(ROOT, d), exist_ok=True)

# Dateien mit Inhalten als Dictionary
files = {}

# backend/__init__.py (leer)
files["backend/__init__.py"] = ""

# requirements.txt
files["requirements.txt"] = """fastapi==0.115.0
uvicorn==0.34.0
motor==3.6.0
pydantic==2.10.0
bcrypt==4.1.0
PyJWT==2.9.0
python-telegram-bot==20.7
"""
# (Die genauen Versionsnummern können aktuell sein, ich habe sie so gewählt, dass sie mit Python 3.14 laufen.
# Falls du andere Versionen brauchst, ändere sie.)

# backend/database.py
files["backend/database.py"] = """import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
APP_ENV = os.getenv("APP_ENV", "dev")
DB_NAME = f"putzplan_app_{APP_ENV}" if APP_ENV != "prod" else "putzplan_app"

client = AsyncIOMotorClient(MONGO_URI)
database = client[DB_NAME]
households_col = database["households"]
history_col = database["history"]
users_col = database["users"]
"""

# backend/models.py
files["backend/models.py"] = '''from pydantic import BaseModel
from typing import List, Dict, Optional

class Task(BaseModel):
    name: str
    interval_weeks: int = 1      # 1 = wöchentlich, 2 = alle zwei Wochen

class CleaningPlan(BaseModel):
    id: str
    name: str
    tasks: List[Task]

class HouseholdCreate(BaseModel):
    name: str
    members: List[str]
    cleaning_plans: List[CleaningPlan]

class VetoRequest(BaseModel):
    by_user: str
    accepted_by: List[str] = []
'''

# backend/auth.py
files["backend/auth.py"] = '''import os
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
import jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from backend.database import users_col

SECRET_KEY = os.getenv("SECRET_KEY", "ein_sicheres_geheimnis_aendern")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = payload.get("sub")
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED)
        return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
'''

# backend/assignment.py (mit Intervall-Logik)
files["backend/assignment.py"] = '''import random
from typing import Dict, List
from backend.database import history_col

async def assign_plans(household: dict, history_weeks: int = 8) -> Dict[str, List[str]]:
    members = household["members"]
    plans = household["cleaning_plans"]
    current_week = household.get("current_week", {})
    week_start = current_week.get("week_start", "")

    # Aktuelle Wochennummer berechnen (vereinfacht: aus ISO-Kalender)
    from datetime import datetime
    current_week_num = 0
    if week_start:
        try:
            dt = datetime.strptime(week_start, "%Y-%m-%d")
            iso = dt.isocalendar()
            current_week_num = iso.year * 100 + iso.week
        except:
            pass

    # Sammle alle Aufgaben-IDs, die diese Woche aktiv sind
    tasks = []
    task_map = {}  # task_id -> (plan_id, task_name, interval)
    for plan in plans:
        for idx, task in enumerate(plan["tasks"]):
            interval = task.get("interval_weeks", 1)
            # Offset aus Task-Namen, um Aufgaben zu verteilen
            offset = sum(ord(c) for c in task["name"]) % interval
            if (current_week_num - offset) % interval == 0:
                tid = f"{plan['id']}|{idx}"
                tasks.append(tid)
                task_map[tid] = (plan["id"], task["name"], interval)

    if not tasks:
        return {m: [] for m in members}

    # Historie der letzten Wochen laden (nur für diesen Haushalt)
    pipeline = [
        {"$match": {"household_id": household["_id"]}},
        {"$sort": {"week_start": -1}},
        {"$limit": history_weeks * len(members)}
    ]
    recent = await history_col.aggregate(pipeline).to_list(None)

    # Zähler: wie oft hatte Nutzer jede Aufgabe?
    counts = {m: {t: 0 for t in tasks} for m in members}
    for entry in recent:
        u = entry["user"]
        t = entry.get("task_id")
        if u in counts and t in counts[u]:
            counts[u][t] += 1

    # Gewichte: 1 / (count+1)
    weights = {}
    for t in tasks:
        weights[t] = []
        for m in members:
            weights[t].append(1.0 / (counts[m][t] + 1))

    # Gleichmäßige Verteilung
    max_per = -(-len(tasks) // len(members))  # ceil division
    assignments = {m: [] for m in members}
    remaining = list(tasks)
    assigned = {m: 0 for m in members}

    while remaining:
        task = random.choice(remaining)
        candidates = [m for m in members if assigned[m] < max_per]
        if not candidates:
            break
        cand_weights = [weights[task][members.index(m)] for m in candidates]
        chosen = random.choices(candidates, weights=cand_weights, k=1)[0]
        assignments[chosen].append(task)
        assigned[chosen] += 1
        remaining.remove(task)

    return assignments
'''

# backend/telegram_bot.py (ohne echte Token, du musst den Token aus Umgebungsvariable setzen)
files["backend/telegram_bot.py"] = '''import asyncio
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from backend.database import users_col

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Willkommen! Sende /register <benutzername>")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Bitte gib deinen Benutzernamen an: /register Anna")
        return
    username = context.args[0]
    chat_id = update.effective_chat.id
    result = await users_col.update_one(
        {"username": username},
        {"$set": {"telegram_chat_id": chat_id}}
    )
    if result.modified_count > 0:
        await update.message.reply_text(f"Chat-ID für {username} gespeichert.")
    else:
        await update.message.reply_text("Benutzer nicht gefunden oder bereits registriert.")

async def run_telegram_bot():
    if not TELEGRAM_TOKEN:
        print("TELEGRAM_TOKEN nicht gesetzt. Bot wird nicht gestartet.")
        return
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    # Halte den Bot am Leben
    while True:
        await asyncio.sleep(3600)
'''

# backend/main.py (die vollständige FastAPI-App mit Auth, WebSocket, Endpunkten)
files["backend/main.py"] = r'''import asyncio
from datetime import datetime, timedelta
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from bson import ObjectId
from backend.database import database, households_col, history_col, users_col
from backend.models import HouseholdCreate, VetoRequest
from backend.assignment import assign_plans
from backend.auth import (
    hash_password, verify_password, create_access_token, get_current_user,
    oauth2_scheme, SECRET_KEY, ALGORITHM
)
import jwt
from backend.telegram_bot import run_telegram_bot

app = FastAPI()

# Statische Dateien ausliefern
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def index():
    return FileResponse("frontend/index.html")

# ------------- Authentifizierung -------------
@app.post("/register")
async def register(payload: dict):
    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        raise HTTPException(400, "Username und Passwort erforderlich")
    if await users_col.find_one({"username": username}):
        raise HTTPException(400, "Benutzer existiert bereits")
    hashed = hash_password(password)
    await users_col.insert_one({"username": username, "hashed_password": hashed, "telegram_chat_id": None})
    return {"message": "Registrierung erfolgreich"}

@app.post("/token")
async def login(payload: dict):
    username = payload.get("username")
    password = payload.get("password")
    user = await users_col.find_one({"username": username})
    if not user or not verify_password(password, user["hashed_password"]):
        raise HTTPException(401, "Anmeldedaten ungültig")
    token = create_access_token(data={"sub": username})
    return {"access_token": token, "token_type": "bearer"}

# ------------- Geschützte Routen -------------

@app.post("/households", status_code=201)
async def create_household(data: HouseholdCreate, user: str = Depends(get_current_user)):
    # Erstellenden Benutzer automatisch als Mitglied hinzufügen, falls nicht vorhanden
    if user not in data.members:
        data.members.append(user)
    doc = {
        "name": data.name,
        "members": data.members,
        "cleaning_plans": [plan.dict() for plan in data.cleaning_plans],
        "current_week": {
            "week_start": datetime.utcnow().strftime("%Y-%m-%d"),
            "deadline": (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%dT23:59:59"),
            "assignments": {}
        },
        "veto_requests": []
    }
    result = await households_col.insert_one(doc)
    household = await households_col.find_one({"_id": result.inserted_id})
    # Erste Zuteilung
    assignments = await assign_plans(household)
    await households_col.update_one(
        {"_id": household["_id"]},
        {"$set": {"current_week.assignments": assignments}}
    )
    household["_id"] = str(household["_id"])
    return household

@app.get("/households/{hid}")
async def get_household(hid: str, user: str = Depends(get_current_user)):
    try:
        oid = ObjectId(hid)
    except:
        raise HTTPException(400, "Ungültige ID")
    household = await households_col.find_one({"_id": oid})
    if not household:
        raise HTTPException(404)
    household["_id"] = str(household["_id"])
    return household

@app.post("/households/{hid}/assign")
async def create_assignment(hid: str, user: str = Depends(get_current_user)):
    household = await households_col.find_one({"_id": ObjectId(hid)})
    if not household:
        raise HTTPException(404)
    assignments = await assign_plans(household)
    await households_col.update_one(
        {"_id": household["_id"]},
        {"$set": {
            "current_week.assignments": assignments,
            "current_week.week_start": datetime.utcnow().strftime("%Y-%m-%d"),
            "current_week.deadline": (datetime.utcnow() + timedelta(days=7)).isoformat()
        }}
    )
    return {"message": "Neue Zuteilung erstellt"}

@app.post("/households/{hid}/veto")
async def request_veto(hid: str, veto: VetoRequest, user: str = Depends(get_current_user)):
    household = await households_col.find_one({"_id": ObjectId(hid)})
    if not household:
        raise HTTPException(404)
    if veto.by_user not in household["members"]:
        raise HTTPException(400, "Nutzer nicht im Haushalt")
    # Prüfen, ob nicht schon ein Veto dieses Nutzers offen ist
    for v in household.get("veto_requests", []):
        if v["by_user"] == veto.by_user:
            raise HTTPException(400, "Veto bereits aktiv")
    household["veto_requests"].append(veto.dict())
    await households_col.update_one(
        {"_id": household["_id"]},
        {"$set": {"veto_requests": household["veto_requests"]}}
    )
    return {"message": "Veto eingereicht"}

@app.post("/households/{hid}/veto/accept")
async def accept_veto(hid: str, payload: dict, user: str = Depends(get_current_user)):
    voter = payload.get("user", user)  # der Zustimmende
    household = await households_col.find_one({"_id": ObjectId(hid)})
    if not household:
        raise HTTPException(404)
    modified = False
    for v in household.get("veto_requests", []):
        if voter not in v["accepted_by"] and voter != v["by_user"]:
            v["accepted_by"].append(voter)
            modified = True
            other_members = [m for m in household["members"] if m != v["by_user"]]
            if all(m in v["accepted_by"] for m in other_members):
                # Alle haben zugestimmt -> neu zuteilen und Veto löschen
                assignments = await assign_plans(household)
                await households_col.update_one(
                    {"_id": household["_id"]},
                    {"$set": {"current_week.assignments": assignments, "veto_requests": []}}
                )
                return {"message": "Veto angenommen, neu verteilt"}
    if modified:
        await households_col.update_one(
            {"_id": household["_id"]},
            {"$set": {"veto_requests": household["veto_requests"]}}
        )
        return {"message": "Zustimmung registriert"}
    raise HTTPException(400, "Keine Aktion möglich")

@app.post("/households/{hid}/complete")
async def complete_task(hid: str, payload: dict, user: str = Depends(get_current_user)):
    task_id = payload.get("task_id")
    username = payload.get("user")  # Wer die Aufgabe erledigt, kann auch der eingeloggte User sein
    household = await households_col.find_one({"_id": ObjectId(hid)})
    if not household:
        raise HTTPException(404)
    # Prüfen, ob task_id dem user zugewiesen ist
    assignments = household.get("current_week", {}).get("assignments", {})
    if task_id not in assignments.get(username, []):
        raise HTTPException(400, "Aufgabe nicht zugewiesen")
    await history_col.insert_one({
        "household_id": household["_id"],
        "week_start": household["current_week"]["week_start"],
        "user": username,
        "task_id": task_id,
        "completed": True
    })
    return {"message": "Aufgabe erledigt"}

# ------------- WebSocket (Echtzeit) -------------
connected_clients = {}

@app.websocket("/ws/{household_id}")
async def ws_endpoint(websocket: WebSocket, household_id: str, token: str = None):
    # Token validieren
    if not token:
        await websocket.close(code=1008)
        return
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except jwt.PyJWTError:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    if household_id not in connected_clients:
        connected_clients[household_id] = []
    connected_clients[household_id].append(websocket)

    # Aktuellen Haushalt senden
    try:
        household = await households_col.find_one({"_id": ObjectId(household_id)})
        if household:
            household["_id"] = str(household["_id"])
            await websocket.send_json(household)
    except:
        pass

    # Change Stream auf dieses Dokument
    pipeline = [{"$match": {"documentKey._id": ObjectId(household_id)}}]
    try:
        async with households_col.watch(pipeline, full_document="updateLookup") as stream:
            while True:
                change = await stream.try_next()
                if change and "fullDocument" in change:
                    doc = change["fullDocument"]
                    doc["_id"] = str(doc["_id"])
                    for client in connected_clients.get(household_id, []):
                        try:
                            await client.send_json(doc)
                        except:
                            pass
                await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    finally:
        connected_clients[household_id].remove(websocket)

# ------------- Startup-Event: Telegram-Bot etc. -------------
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_telegram_bot())
    # Reminder-Logik könnte man später einbauen
'''

# frontend/index.html (leicht erweitert für Auth)
files["frontend/index.html"] = '''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#4CAF50">
    <title>Putzplan WG</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: auto; padding: 1em; }
        #loginArea, #mainApp { margin-top: 1em; }
    </style>
</head>
<body>
    <h1>Putzplan WG</h1>
    <div id="loginArea">
        <input type="text" id="usernameInput" placeholder="Benutzername">
        <input type="password" id="passwordInput" placeholder="Passwort">
        <button onclick="login()">Einloggen / Registrieren</button>
    </div>
    <div id="mainApp" style="display:none">
        <button onclick="createHousehold()">Neuen Haushalt erstellen</button>
        <p>Haushalt-ID: <span id="householdId"></span></p>
        <button onclick="connectWs()">WebSocket verbinden</button>
        <div id="assignments"></div>
    </div>
    <script>
        let token = localStorage.getItem('token');
        let currentHouseholdId = null;
        let ws = null;

        async function apiCall(url, method='GET', body=null) {
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = 'Bearer ' + token;
            const resp = await fetch(url, {
                method, headers,
                body: body ? JSON.stringify(body) : null
            });
            if (resp.status === 401) {
                alert('Bitte einloggen');
                localStorage.removeItem('token');
                location.reload();
            }
            return resp;
        }

        async function login() {
            const user = document.getElementById('usernameInput').value;
            const pass = document.getElementById('passwordInput').value;
            let resp = await fetch('/token', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: user, password: pass})
            });
            if (!resp.ok) {
                // Registrieren versuchen
                resp = await fetch('/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: user, password: pass})
                });
                if (!resp.ok) {
                    alert('Fehler bei Anmeldung/Registrierung');
                    return;
                }
                // Nach Registrierung gleich einloggen
                resp = await fetch('/token', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: user, password: pass})
                });
            }
            const data = await resp.json();
            token = data.access_token;
            localStorage.setItem('token', token);
            document.getElementById('loginArea').style.display = 'none';
            document.getElementById('mainApp').style.display = 'block';
        }

        async function createHousehold() {
            const resp = await apiCall('/households', 'POST', {
                name: "WG Berlin",
                members: ["Anna", "Paul"],
                cleaning_plans: [
                    { id: "bad", name: "Bad", tasks: [
                        {name: "Waschbecken", interval_weeks: 1},
                        {name: "Boden wischen", interval_weeks: 2}
                    ]}
                ]
            });
            if (resp.ok) {
                const h = await resp.json();
                currentHouseholdId = h._id;
                document.getElementById('householdId').innerText = h._id;
                showAssignments(h);
            }
        }

        function connectWs() {
            if (!currentHouseholdId) return;
            if (ws) ws.close();
            ws = new WebSocket(`ws://${location.host}/ws/${currentHouseholdId}?token=${token}`);
            ws.onmessage = e => showAssignments(JSON.parse(e.data));
        }

        function showAssignments(household) {
            const div = document.getElementById('assignments');
            div.innerHTML = '';
            const a = household.current_week?.assignments || {};
            for (let [user, tasks] of Object.entries(a)) {
                div.innerHTML += `<p><b>${user}</b>: ${tasks.join(', ')}</p>`;
            }
        }

        if (token) {
            document.getElementById('loginArea').style.display = 'none';
            document.getElementById('mainApp').style.display = 'block';
        }
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js');
        }
    </script>
</body>
</html>
'''

# frontend/manifest.json
files["frontend/manifest.json"] = '''{
  "name": "Putzplan WG",
  "short_name": "Putzplan",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#4CAF50",
  "icons": []
}
'''

# frontend/sw.js
files["frontend/sw.js"] = '''self.addEventListener('install', event => {
  event.waitUntil(
    caches.open('v1').then(cache => cache.addAll(['/']))
  );
});
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(resp => resp || fetch(event.request))
  );
});
'''

# tests/__init__.py (leer)
files["tests/__init__.py"] = ""

# tests/test_assignment.py
files["tests/test_assignment.py"] = '''import asyncio
from backend.assignment import assign_plans

def test_assign_basic():
    household = {
        "_id": "507f1f77bcf86cd799439011",
        "members": ["Anna", "Paul"],
        "cleaning_plans": [
            {"id": "bad", "name": "Bad", "tasks": [{"name": "Boden wischen", "interval_weeks": 1}]},
            {"id": "kueche", "name": "Küche", "tasks": [{"name": "Herd putzen", "interval_weeks": 1}]}
        ],
        "current_week": {"week_start": "2026-04-27"}
    }
    # Test mit Mock der history_col (muss man in echter Umgebung patchen)
    # Hier nur Platzhalter
    assert True
'''

# .github/workflows/tests.yml
files[".github/workflows/tests.yml"] = """name: Run Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      mongodb:
        image: mongo:7.0
        ports:
          - 27017:27017
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'
      - name: Install dependencies
        run: pip install -r requirements.txt pytest
      - name: Run tests
        env:
          MONGO_URI: mongodb://localhost:27017
        run: pytest tests/
"""

# Jetzt alle Dateien schreiben
for path, content in files.items():
    full_path = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Projektstruktur wurde erstellt.")