# tests/test_auth.py
from backend.auth import create_access_token, get_current_user
from fastapi import HTTPException
import pytest

def test_create_and_verify_token():
    # Erstelle ein Token für einen Testnutzer
    token = create_access_token({"sub": "testuser"})
    assert token is not None and isinstance(token, str)

    # Die Validierung des Tokens funktioniert nur im Request-Kontext,
    # aber wir können manuell die Dekodierung testen
    from jose import jwt, JWTError
    from backend.auth import SECRET_KEY, ALGORITHM
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "testuser"
    except JWTError:
        pytest.fail("Valid token could not be decoded")