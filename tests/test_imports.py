# tests/test_imports.py
def test_main_imports():
    # Dieser Test schlägt fehl, wenn ein Import in main.py nicht geht
    from backend.main import app
    assert app is not None