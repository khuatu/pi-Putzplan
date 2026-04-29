# tests/test_api.py
import pytest
from httpx import AsyncClient
from backend.main import app

@pytest.mark.asyncio
async def test_register_and_login():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Registrieren
        resp = await ac.post("/register", json={"username": "testuser", "password": "test123"})
        assert resp.status_code in [200, 400]  # 400 falls schon existiert

        # Einloggen
        resp = await ac.post("/token", json={"username": "testuser", "password": "test123"})
        if resp.status_code == 200:
            data = resp.json()
            assert "access_token" in data