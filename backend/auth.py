# backend/auth.py
import os
from datetime import datetime, timedelta
from passlib.hash import bcrypt as pwd_bcrypt
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from backend.database import users_col

# Geheimnisse sollten aus Umgebungsvariablen kommen
SECRET_KEY = os.getenv("SECRET_KEY", "bitte_aendern_geheim")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 Stunden

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

def hash_password(password: str) -> str:
    return pwd_bcrypt.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_bcrypt.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = payload.get("sub")
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED)
        return user
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)