import os
import sys
import subprocess
import pytest

# Hilfsfunktion
def is_pi():
    """Nur auf einem echten Raspberry Pi ausführen (Linux & armv7l/aarch64)."""
    return sys.platform == "linux" and ("arm" in os.uname().machine or "aarch64" in os.uname().machine)

def test_uvicorn_exists():
    if not is_pi():
        pytest.skip("Nur auf dem Pi relevant")
    venv_uvicorn = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "venv", "bin", "uvicorn"
    )
    assert os.path.exists(venv_uvicorn), f"uvicorn nicht gefunden: {venv_uvicorn}"

def test_mongodb_reachable():
    if not is_pi():
        pytest.skip("Nur auf dem Pi relevant")
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    async def check():
        client = AsyncIOMotorClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
        await client.server_info()
    try:
        asyncio.run(check())
    except Exception as e:
        pytest.fail(f"MongoDB nicht erreichbar: {e}")

def test_service_file_exists():
    if not is_pi():
        pytest.skip("Nur auf dem Pi relevant")
    service_path = "/etc/systemd/system/putzplan.service"
    assert os.path.exists(service_path), f"Service-Datei fehlt: {service_path}"

def test_service_file_syntax():
    if not is_pi():
        pytest.skip("Nur auf dem Pi relevant")
    result = subprocess.run(
        ["systemd-analyze", "verify", "/etc/systemd/system/putzplan.service"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"Service-Syntaxfehler: {result.stderr}"

def test_port_8000_not_bound():
    if not is_pi():
        pytest.skip("Nur auf dem Pi relevant")
    result = subprocess.run(
        ["ss", "-tln"],
        capture_output=True, text=True
    )
    lines = [line for line in result.stdout.splitlines() if ":8000" in line]
    assert len(lines) <= 1, f"Port 8000 wird mehrfach belegt:\n{result.stdout}"

def test_sendgrid_env_in_service_file():
    if not is_pi():
        pytest.skip("Nur auf dem Pi relevant")
    import subprocess
    result = subprocess.run(
        "sudo systemctl show putzplan.service -p Environment | grep 'SENDGRID_API_KEY='",
        shell=True, capture_output=True, text=True
    )
    assert result.returncode == 0, "SENDGRID_API_KEY fehlt in der systemd‑Unit"
    assert "SG." in result.stdout, "SENDGRID_API_KEY enthält nicht das erwartete Format"