from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

security = HTTPBearer(auto_error=False)

# Demo accounts — replace with SSO / directory in production
DEMO_USERS: dict[str, dict] = {
    "admin": {
        "password": "insight2026",
        "role": "admin",
        "name": "Operations HQ",
        "email": "executive@insight-ops.internal",
        "site_id": None,
    },
    "harbourview": {
        "password": "site2026",
        "role": "manager",
        "name": "Harbourview Site Manager",
        "email": "harbourview@insight-ops.internal",
        "site_id": "harbourview",
    },
    "northgate": {
        "password": "site2026",
        "role": "manager",
        "name": "Northgate Site Manager",
        "email": "northgate@insight-ops.internal",
        "site_id": "northgate",
    },
}


@dataclass
class User:
    username: str
    role: str
    name: str
    email: str
    site_id: str | None


def verify_password(username: str, password: str) -> bool:
    user = DEMO_USERS.get(username)
    return bool(user and user["password"] == password)


def user_from_username(username: str) -> User | None:
    raw = DEMO_USERS.get(username)
    if not raw:
        return None
    return User(
        username=username,
        role=raw["role"],
        name=raw["name"],
        email=raw["email"],
        site_id=raw.get("site_id"),
    )


def create_token(username: str, ttl_seconds: int = 86_400) -> str:
    settings = get_settings()
    payload = {"sub": username, "exp": int(time.time()) + ttl_seconds}
    data = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(settings.auth_secret.encode(), data.encode(), hashlib.sha256).hexdigest()
    return f"{data}.{sig}"


def decode_token(token: str) -> str:
    settings = get_settings()
    try:
        data, sig = token.rsplit(".", 1)
        expected = hmac.new(settings.auth_secret.encode(), data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        payload = json.loads(base64.urlsafe_b64decode(data.encode()))
        if payload.get("exp", 0) < time.time():
            raise ValueError("expired")
        return payload["sub"]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session") from e


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> User:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
    username = decode_token(creds.credentials)
    user = user_from_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
    return user


def require_site_access(user: User, site_id: str) -> None:
    if user.role == "admin":
        return
    if user.role == "manager" and user.site_id == site_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised for this site report")
