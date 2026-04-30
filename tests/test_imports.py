# tests/test_imports.py
import os

def test_database_import():
    from backend.database import client, database
    assert client is not None
    assert database is not None

def test_models_import():
    from backend.models import Task, CleaningPlan, HouseholdCreate, VetoRequest
    assert Task is not None

def test_auth_import():
    from backend.auth import hash_password, create_access_token, get_current_user
    assert hash_password is not None

def test_assignment_import():
    from backend.assignment import assign_plans
    assert assign_plans is not None

def test_main_import():
    from backend.main import app
    assert app is not None

def test_working_directory_exists():
    # Dieser Test stellt sicher, dass das Arbeitsverzeichnis existiert
    # und die Haupt-Python-Datei vorhanden ist
    assert os.path.exists("backend/main.py")

def test_event_loop_configured():
    import os
    config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pytest.ini")
    with open(config_file) as f:
        content = f.read()
    assert "asyncio_default_fixture_loop_scope = session" in content, \
        "pytest.ini muss 'asyncio_default_fixture_loop_scope = session' enthalten"