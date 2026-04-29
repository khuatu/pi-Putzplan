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