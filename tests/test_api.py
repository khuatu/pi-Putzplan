# tests/test_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

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