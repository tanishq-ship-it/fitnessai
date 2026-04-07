import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import asyncpg
from fastapi import HTTPException, Request

from config import settings

# ── Password Hashing ──

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


# ── JWT Access Token ──

ACCESS_TOKEN_EXPIRE_MINUTES = 15


def create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])


# ── Refresh Token ──

REFRESH_TOKEN_EXPIRE_DAYS = 90


def generate_refresh_token() -> str:
    return secrets.token_hex(32)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ── FastAPI Dependency ──

async def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = auth_header.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload["sub"]
    pool: asyncpg.Pool = request.app.state.db_pool
    user = await pool.fetchrow(
        "SELECT id, email FROM users WHERE id = $1",
        uuid.UUID(user_id),
    )
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {"user_id": str(user["id"]), "email": user["email"]}
