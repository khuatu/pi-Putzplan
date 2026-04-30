import pytest
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

# Macht pytest-asyncio verfügbar (kein extra marker nötig)
pytest_plugins = ("pytest_asyncio",)

@pytest.fixture(scope="session")
def event_loop():
    """Erzeugt eine Event‑Loop, die für die gesamte Test‑Session bestehen bleibt."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()