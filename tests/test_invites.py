# tests/test_invites.py
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.database import households_col

@pytest.mark.asyncio
async def test_invite_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Registrieren und einloggen als Ersteller
        await ac.post("/register", json={"username": "creator", "password": "test"})
        login_resp = await ac.post("/token", json={"username": "creator", "password": "test"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        # Haushalt erstellen
        create_resp = await ac.post("/households", json={
            "name": "Test-Haushalt",
            "members": ["creator"],
            "cleaning_plans": []
        }, headers=headers)
        assert create_resp.status_code == 201
        household = create_resp.json()
        code = household.get("invite_code")
        assert code is not None
        # Einladungscode anzeigen
        resp = await ac.get(f"/invite/{code}")
        assert resp.status_code == 200
        info = resp.json()
        assert info["name"] == "Test-Haushalt"
        # Neuen Benutzer registrieren und beitreten
        await ac.post("/register", json={"username": "joiner", "password": "test"})
        login_resp = await ac.post("/token", json={"username": "joiner", "password": "test"})
        join_token = login_resp.json()["access_token"]
        join_headers = {"Authorization": f"Bearer {join_token}"}
        join_resp = await ac.post(f"/invite/{code}/join", headers=join_headers)
        assert join_resp.status_code == 200
        join_data = join_resp.json()
        assert "joiner" in join_data["members"]