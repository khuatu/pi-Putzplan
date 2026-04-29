# tests/test_deployment.py
import os
import subprocess
import sys

def test_uvicorn_exists():
    """Stellt sicher, dass uvicorn in der venv installiert ist."""
    venv_uvicorn = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "venv", "bin", "uvicorn"
    )
    if sys.platform == "win32":
        venv_uvicorn = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "venv", "Scripts", "uvicorn.exe"
        )
    assert os.path.exists(venv_uvicorn), f"uvicorn nicht gefunden: {venv_uvicorn}"

def test_mongodb_reachable():
    """Prüft, ob MongoDB erreichbar ist (über motor)."""
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    async def check():
        client = AsyncIOMotorClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
        await client.server_info()  # Wirft Exception wenn nicht erreichbar
    try:
        asyncio.get_event_loop().run_until_complete(check())
    except Exception as e:
        pytest.fail(f"MongoDB nicht erreichbar: {e}")

def test_service_file_exists():
    """Prüft, ob die systemd-Unit-Datei existiert (nur auf Linux)."""
    if sys.platform == "linux":
        service_path = "/etc/systemd/system/putzplan.service"
        assert os.path.exists(service_path), f"Service-Datei fehlt: {service_path}"

def test_service_file_syntax():
    """Validierung der Service-Datei (nur auf Linux)."""
    if sys.platform == "linux":
        result = subprocess.run(
            ["systemd-analyze", "verify", "/etc/systemd/system/putzplan.service"],
            capture_output=True, text=True
        )
        # systemd-analyze gibt bei Erfolg keinen Fehler, exit code 0
        assert result.returncode == 0, f"Service-Syntaxfehler: {result.stderr}"