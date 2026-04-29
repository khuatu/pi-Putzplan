# tests/conftest.py
import pytest
from motor.motor_asyncio import AsyncIOMotorClient

# Macht pytest-asyncio verfügbar (kein extra marker nötig)
pytest_plugins = ("pytest_asyncio",)

@pytest.fixture
def anyio_backend():
    return "asyncio"