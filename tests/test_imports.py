# tests/test_imports.py

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