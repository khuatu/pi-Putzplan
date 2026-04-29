import pytest
from backend.auth import create_access_token, get_current_user
from jose import jwt, JWTError
from backend.auth import SECRET_KEY, ALGORITHM
from fastapi import HTTPException

def test_create_and_verify_token():
    token = create_access_token({"sub": "anna"})
    assert isinstance(token, str)

    # Manuelle Dekodierung
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "anna"
    assert "exp" in payload

@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user("ungueltiger.token.hier")
    assert exc_info.value.status_code == 401