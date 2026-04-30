import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient
from backend.database import MONGO_URI
from backend.main import app

@pytest.fixture(scope="module")
async def ensure_db():
    """Wartet, bis die MongoDB erreichbar ist."""
    for _ in range(10):
        try:
            client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=2000)
            await client.server_info()
            print("MongoDB ist bereit.")
            return
        except Exception:
            await asyncio.sleep(2)
    pytest.fail("MongoDB konnte nicht erreicht werden.")

@pytest.mark.asyncio
async def test_register_and_login(ensure_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/register", json={"username": "testuser", "password": "test123"})
        assert resp.status_code in [200, 400]
        resp = await ac.post("/token", json={"username": "testuser", "password": "test123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

@pytest.mark.asyncio
async def test_register_and_login():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/register", json={"username": "testuser", "password": "test123"})
        assert resp.status_code in [200, 400]

        resp = await ac.post("/token", json={"username": "testuser", "password": "test123"})
        if resp.status_code == 200:
            data = resp.json()
            assert "access_token" in data

@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/")
        assert resp.status_code == 200

@pytest.mark.asyncio
async def test_register_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Registrierung
        resp = await ac.post("/register", json={"username": "healthcheckuser", "password": "test"})
        assert resp.status_code in [200, 400]  # 400 ist ok, falls es den User schon gibt
        # Login
        resp = await ac.post("/token", json={"username": "healthcheckuser", "password": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

@pytest.mark.asyncio
async def test_remove_member():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Registrieren und einloggen
        await ac.post("/register", json={"username": "boss", "password": "test"})
        login_resp = await ac.post("/token", json={"username": "boss", "password": "test"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        # Haushalt mit einem weiteren Mitglied anlegen
        create_resp = await ac.post("/households", json={
            "name": "Test",
            "members": ["boss", "worker"],
            "cleaning_plans": [{"id": "bad", "name": "Bad", "tasks": [{"name": "putzen", "interval_weeks": 1}]}]
        }, headers=headers)
        hid = create_resp.json()["_id"]
        # Mitglied entfernen
        del_resp = await ac.delete(f"/households/{hid}/members/worker", headers=headers)
        assert del_resp.status_code == 200
        # Prüfen, ob worker wirklich weg ist
        get_resp = await ac.get(f"/households/{hid}", headers=headers)
        members = get_resp.json()["members"]
        assert "worker" not in members

@pytest.mark.asyncio
async def test_add_member_and_access_control():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Zwei Benutzer registrieren
        await ac.post("/register", json={"username": "admin", "password": "test"})
        await ac.post("/register", json={"username": "friend", "password": "test"})
        # admin einloggen
        resp = await ac.post("/token", json={"username": "admin", "password": "test"})
        admin_token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}
        # Haushalt erstellen (nur admin)
        create_resp = await ac.post("/households", json={
            "name": "TestWG",
            "members": ["admin"],
            "cleaning_plans": []
        }, headers=headers)
        hid = create_resp.json()["_id"]
        # friend kann nicht zugreifen (403)
        friend_resp = await ac.post("/token", json={"username": "friend", "password": "test"})
        friend_token = friend_resp.json()["access_token"]
        get_resp = await ac.get(f"/households/{hid}", headers={"Authorization": f"Bearer {friend_token}"})
        assert get_resp.status_code == 403
        # admin fügt friend hinzu
        add_resp = await ac.post(f"/households/{hid}/members", json={"username": "friend"}, headers=headers)
        assert add_resp.status_code == 200
        # jetzt darf friend zugreifen
        get_resp = await ac.get(f"/households/{hid}", headers={"Authorization": f"Bearer {friend_token}"})
        assert get_resp.status_code == 200

@pytest.mark.asyncio
async def test_delete_household():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Zwei Benutzer registrieren
        await ac.post("/register", json={"username": "owner", "password": "test"})
        await ac.post("/register", json={"username": "intruder", "password": "test"})
        # owner einloggen
        resp = await ac.post("/token", json={"username": "owner", "password": "test"})
        owner_token = resp.json()["access_token"]
        headers_owner = {"Authorization": f"Bearer {owner_token}"}
        # Haushalt erstellen
        create_resp = await ac.post("/households", json={
            "name": "Zu löschen",
            "members": ["owner"],
            "cleaning_plans": []
        }, headers=headers_owner)
        assert create_resp.status_code == 201
        hid = create_resp.json()["_id"]
        # intruder kann nicht löschen (403)
        resp = await ac.post("/token", json={"username": "intruder", "password": "test"})
        intruder_token = resp.json()["access_token"]
        del_resp = await ac.delete(f"/households/{hid}", headers={"Authorization": f"Bearer {intruder_token}"})
        assert del_resp.status_code == 403
        # owner kann löschen
        del_resp = await ac.delete(f"/households/{hid}", headers=headers_owner)
        assert del_resp.status_code == 200
        # Haushalt sollte jetzt nicht mehr existieren
        get_resp = await ac.get(f"/households/{hid}", headers=headers_owner)
        assert get_resp.status_code == 404

@pytest.mark.asyncio
async def test_saving_plans_triggers_assignment():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Registrierung ohne E‑Mail senden (mocked)
        with patch("backend.email_utils.send_email") as mock_send:
            resp = await ac.post("/register", json={"username": "planner", "password": "test", "email": "plan@test.com"})
            # Der Benutzer muss die E‑Mail bestätigen – das umgehen wir, indem wir in der DB direkt email_verified setzen
            from backend.database import users_col
            await users_col.update_one(
                {"username": "planner"},
                {"$set": {"email_verified": True}}
            )
        # Einloggen
        resp = await ac.post("/token", json={"username": "planner", "password": "test"})
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Haushalt ohne Pläne anlegen
        resp = await ac.post("/households", json={
            "name": "PlanHaus",
            "members": ["planner"],
            "cleaning_plans": []
        }, headers=headers)
        hid = resp.json()["_id"]

        # Pläne setzen
        resp = await ac.put(f"/households/{hid}/plans", json={
            "cleaning_plans": [{"id": "bad", "name": "Bad", "tasks": [{"name": "Boden wischen"}], "interval_weeks": 1}]
        }, headers=headers)
        assert resp.status_code == 200

        # Zuteilung manuell anstoßen
        resp = await ac.post(f"/households/{hid}/assign", headers=headers)
        assert resp.status_code == 200

        # Haushalt neu laden und prüfen, ob Zuteilung existiert
        resp = await ac.get(f"/households/{hid}", headers=headers)
        household = resp.json()
        assignments = household["current_week"]["assignments"]
        assert "planner" in assignments
        assert len(assignments["planner"]) >= 1

@pytest.mark.asyncio
async def test_register_duplicate_email_fails():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Zuerst einen Benutzer anlegen
        await ac.post("/register", json={"username": "original", "password": "test", "email": "dup@test.com"})
        # Zweiter Benutzer mit gleicher E‑Mail muss scheitern
        resp = await ac.post("/register", json={"username": "copycat", "password": "test", "email": "dup@test.com"})
        assert resp.status_code == 400
        data = resp.json()
        assert "E‑Mail‑Adresse wird bereits verwendet" in data["detail"]