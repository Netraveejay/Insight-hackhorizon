from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import User, create_token, get_current_user, user_from_username, verify_password

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
def login(body: LoginRequest):
    username = body.username.strip().lower()
    if not verify_password(username, body.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    user = user_from_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return {
        "token": create_token(username),
        "user": {
            "username": user.username,
            "role": user.role,
            "name": user.name,
            "email": user.email,
            "site_id": user.site_id,
        },
    }


@router.get("/auth/me")
def me(user: User = Depends(get_current_user)):
    return {
        "username": user.username,
        "role": user.role,
        "name": user.name,
        "email": user.email,
        "site_id": user.site_id,
    }
