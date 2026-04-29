# backend/main.py
import asyncio
import secrets
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from bson import ObjectId
from jose import jwt, JWTError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.database import database, households_col, history_col, users_col
from backend.models import HouseholdCreate, VetoRequest
from backend.assignment import assign_plans
from backend.auth import (
    hash_password, verify_password, create_access_token, get_current_user,
    SECRET_KEY, ALGORITHM
)
from backend.telegram_bot import run_telegram_bot
from backend.email_utils import send_email

# ------------------------------
# Scheduler für automatische Aufgaben
# ------------------------------
scheduler = AsyncIOScheduler()

async def weekly_assignment_job():
    """Jede Woche (Standard: Montag 02:00) für alle Haushalte neue Zuteilung berechnen."""
    async for household in households_col.find({}):
        try:
            assignments = await assign_plans(household)
            await households_col.update_one(
                {"_id": household["_id"]},
                {"$set": {
                    "current_week.assignments": assignments,
                    "current_week.week_start": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "current_week.deadline": (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%dT23:59:59"),
                    "veto_requests": []
                }}
            )
            print(f"Neue Zuteilung für Haushalt {household['_id']} berechnet.")
        except Exception as e:
            print(f"Fehler bei Zuteilung für {household['_id']}: {e}")

async def send_reminders_job():
    """Jeden Samstag 19:00 Uhr: E‑Mail‑Erinnerungen an alle Mitglieder mit offenen Räumen/Aufgaben."""
    now = datetime.now(timezone.utc)
    if now.weekday() != 5:  # 5 = Samstag
        return
    async for household in households_col.find({}):
        for username in household.get("members", []):
            user_doc = await users_col.find_one({"username": username})
            if not user_doc or not user_doc.get("email"):
                continue
            # Offene Räume/Aufgaben ermitteln
            open_items = []
            assignments = household.get("current_week", {}).get("assignments", {})
            for assigned_user, items in assignments.items():
                if assigned_user != username:
                    continue
                for item in items:
                    # Prüfung, ob in dieser Woche bereits erledigt
                    completed = await history_col.find_one({
                        "household_id": household["_id"],
                        "week_start": household["current_week"]["week_start"],
                        "user": username,
                        "$or": [{"plan_id": item}, {"task_id": item}],
                        "completed": True
                    })
                    if not completed:
                        # Versuche, einen schöneren Namen zu finden
                        plan_name = item
                        for plan in household.get("cleaning_plans", []):
                            if plan["id"] == item:
                                plan_name = plan["name"]
                                break
                        open_items.append(plan_name)
            if open_items:
                subject = f"Putzplan-Erinnerung für {username}"
                body = "Hallo,\n\nmorgen läuft die Putzplan-Woche ab! Bitte erledige:\n- " + "\n- ".join(open_items)
                send_email(user_doc["email"], subject, body)

# ------------------------------
# Lifespan (Start/Stop des Schedulers & Telegram-Bot)
# ------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    asyncio.create_task(run_telegram_bot())
    scheduler.add_job(weekly_assignment_job, CronTrigger(day_of_week='mon', hour=2, minute=0), id='weekly_assignment')
    scheduler.add_job(send_reminders_job, CronTrigger(day_of_week='sat', hour=19, minute=0), id='send_reminders')
    scheduler.start()
    print("Scheduler gestartet.")
    yield
    # Shutdown
    scheduler.shutdown()

# ------------------------------
# FastAPI‑App erstellen
# ------------------------------
app = FastAPI(lifespan=lifespan)

# Statische Dateien (Frontend) ausliefern
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def index():
    return FileResponse("frontend/index.html")

# ------------------------------
# Authentifizierung
# ------------------------------
@app.post("/register")
async def register(payload: dict):
    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        raise HTTPException(400, "Benutzername und Passwort erforderlich")
    if await users_col.find_one({"username": username}):
        raise HTTPException(400, "Benutzer existiert bereits")
    hashed = hash_password(password)
    await users_col.insert_one({
        "username": username,
        "hashed_password": hashed,
        "email": None,
        "telegram_chat_id": None
    })
    return {"message": "Registrierung erfolgreich"}

@app.post("/token")
async def login(payload: dict):
    username = payload.get("username")
    password = payload.get("password")
    user_doc = await users_col.find_one({"username": username})
    if not user_doc or not verify_password(password, user_doc["hashed_password"]):
        raise HTTPException(401, "Anmeldedaten ungültig")
    token = create_access_token(data={"sub": username})
    return {"access_token": token, "token_type": "bearer"}

# ------------------------------
# Benutzer‑E‑Mail speichern
# ------------------------------
@app.put("/users/me/email")
async def update_my_email(payload: dict, user: str = Depends(get_current_user)):
    email = payload.get("email")
    if not email:
        raise HTTPException(400, "E‑Mail‑Adresse erforderlich")
    await users_col.update_one(
        {"username": user},
        {"$set": {"email": email}}
    )
    return {"message": "E‑Mail‑Adresse gespeichert"}

# ------------------------------
# Haushalts‑Routen (alle geschützt)
# ------------------------------
@app.post("/households", status_code=201)
async def create_household(data: HouseholdCreate, user: str = Depends(get_current_user)):
    if user not in data.members:
        data.members.append(user)
    # Einladungscode generieren (6 Hex‑Zeichen + Bindestrich + 3 Ziffern)
    while True:
        code = f"{secrets.token_hex(3)}-{secrets.randbelow(1000):03d}"
        if not await households_col.find_one({"invite_code": code}):
            break
    doc = {
        "name": data.name,
        "members": data.members,
        "cleaning_plans": [plan.dict() for plan in data.cleaning_plans],
        "allocation_mode": data.allocation_mode,
        "created_by": user,
        "invite_code": code,
        "current_week": {
            "week_start": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "deadline": (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%dT23:59:59"),
            "assignments": {}
        },
        "veto_requests": []
    }
    result = await households_col.insert_one(doc)
    household = await households_col.find_one({"_id": result.inserted_id})
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
    if user not in household.get("members", []):
        raise HTTPException(403, "Du bist kein Mitglied dieses Haushalts")
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
            "current_week.week_start": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "current_week.deadline": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        }}
    )
    return {"message": "Neue Zuteilung"}

@app.post("/households/{hid}/veto")
async def request_veto(hid: str, veto: VetoRequest, user: str = Depends(get_current_user)):
    household = await households_col.find_one({"_id": ObjectId(hid)})
    if not household:
        raise HTTPException(404)
    if veto.by_user not in household["members"]:
        raise HTTPException(400, "Nutzer nicht im Haushalt")
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
    voter = payload.get("user", user)
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
async def complete_plan(hid: str, payload: dict, user: str = Depends(get_current_user)):
    plan_id = payload.get("plan_id")
    username = payload.get("user")  # Wer die Aufgabe erledigt hat (normalerweise eingeloggter Benutzer)
    if not plan_id or not username:
        raise HTTPException(400, "plan_id und user erforderlich")
    household = await households_col.find_one({"_id": ObjectId(hid)})
    if not household:
        raise HTTPException(404)
    # Prüfen, ob der Raum dem Nutzer zugewiesen ist
    assignments = household.get("current_week", {}).get("assignments", {})
    if plan_id not in assignments.get(username, []):
        raise HTTPException(400, "Raum nicht zugewiesen")
    await history_col.insert_one({
        "household_id": household["_id"],
        "week_start": household["current_week"]["week_start"],
        "user": username,
        "plan_id": plan_id,
        "completed": True
    })
    return {"message": "Raum als erledigt markiert"}

@app.delete("/households/{hid}")
async def delete_household(hid: str, user: str = Depends(get_current_user)):
    try:
        oid = ObjectId(hid)
    except:
        raise HTTPException(400, "Ungültige ID")
    household = await households_col.find_one({"_id": oid})
    if not household:
        raise HTTPException(404)
    # Löschrecht: entweder created_by stimmt überein, oder (bei alten Haushalten ohne created_by) jedes Mitglied darf löschen
    if household.get("created_by") and household["created_by"] != user:
        raise HTTPException(403, "Nur der Ersteller des Haushalts darf ihn löschen")
    elif not household.get("created_by") and user not in household["members"]:
        raise HTTPException(403, "Du bist kein Mitglied dieses Haushalts")
    await households_col.delete_one({"_id": oid})
    return {"message": "Haushalt gelöscht"}

@app.post("/households/{hid}/members")
async def add_member(hid: str, payload: dict, user: str = Depends(get_current_user)):
    username = payload.get("username")
    if not username:
        raise HTTPException(400, "Username erforderlich")
    # Existiert der Benutzer?
    if not await users_col.find_one({"username": username}):
        raise HTTPException(400, "Dieser Benutzer existiert nicht")
    household = await households_col.find_one({"_id": ObjectId(hid)})
    if not household:
        raise HTTPException(404)
    if user not in household["members"]:
        raise HTTPException(403, "Nur Mitglieder können andere hinzufügen")
    if username in household["members"]:
        raise HTTPException(400, "Bereits Mitglied")
    household["members"].append(username)
    await households_col.update_one(
        {"_id": household["_id"]},
        {"$set": {"members": household["members"]}}
    )
    return {"message": f"{username} hinzugefügt"}

@app.delete("/households/{hid}/members/{username}")
async def remove_member(hid: str, username: str, user: str = Depends(get_current_user)):
    household = await households_col.find_one({"_id": ObjectId(hid)})
    if not household:
        raise HTTPException(404)
    if username not in household["members"]:
        raise HTTPException(400, "Mitglied nicht gefunden")
    household["members"].remove(username)
    await households_col.update_one(
        {"_id": household["_id"]},
        {"$set": {"members": household["members"]}}
    )
    return {"message": f"Mitglied {username} entfernt"}

@app.put("/households/{hid}/plans")
async def update_cleaning_plans(hid: str, payload: dict, user: str = Depends(get_current_user)):
    household = await households_col.find_one({"_id": ObjectId(hid)})
    if not household:
        raise HTTPException(404)
    if user not in household["members"]:
        raise HTTPException(403)
    new_plans = payload.get("cleaning_plans", [])
    await households_col.update_one(
        {"_id": household["_id"]},
        {"$set": {"cleaning_plans": new_plans}}
    )
    return {"message": "Pläne aktualisiert"}

# ------------------------------
# Einladungs‑Routen
# ------------------------------
@app.get("/invite/{code}")
async def get_invite_info(code: str):
    household = await households_col.find_one({"invite_code": code})
    if not household:
        raise HTTPException(404, "Einladungscode ungültig")
    return {
        "household_id": str(household["_id"]),
        "name": household["name"],
        "members": household["members"]
    }

@app.post("/invite/{code}/join")
async def join_household_by_code(code: str, user: str = Depends(get_current_user)):
    household = await households_col.find_one({"invite_code": code})
    if not household:
        raise HTTPException(404, "Einladungscode ungültig")
    if user in household["members"]:
        raise HTTPException(400, "Bereits Mitglied")
    household["members"].append(user)
    await households_col.update_one(
        {"_id": household["_id"]},
        {"$set": {"members": household["members"]}}
    )
    household["_id"] = str(household["_id"])
    return household

# ------------------------------
# WebSocket für Echtzeit‑Updates
# ------------------------------
connected_clients = {}

@app.websocket("/ws/{household_id}")
async def websocket_endpoint(ws: WebSocket, household_id: str, token: str = None):
    if not token:
        await ws.close(code=1008)
        return
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except JWTError:
        await ws.close(code=1008)
        return

    await ws.accept()
    if household_id not in connected_clients:
        connected_clients[household_id] = []
    connected_clients[household_id].append(ws)

    try:
        household = await households_col.find_one({"_id": ObjectId(household_id)})
        if household:
            household["_id"] = str(household["_id"])
            await ws.send_json(household)
    except:
        pass

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
        connected_clients[household_id].remove(ws)

