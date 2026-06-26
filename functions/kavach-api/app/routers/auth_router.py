"""
Auth router: login / logout / current-user endpoints.

POST /api/auth/login   { "token": "<token>" }  -> user info
GET  /api/auth/me      Authorization: Bearer <token>  -> user info
POST /api/auth/logout  (stateless – client just discards token)
GET  /api/auth/roles   -> public list of available demo tokens
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from app.auth import TOKENS, get_current_user, ROLE_HIERARCHY

router = APIRouter(prefix="/api/auth", tags=["auth"])

_bearer = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    token: str


@router.post("/login")
def login(req: LoginRequest):
    user = TOKENS.get(req.token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token.")
    return {"status": "ok", "user": user, "token": req.token}


@router.get("/me")
def me(user: Optional[dict] = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return user


@router.post("/logout")
def logout():
    # Stateless prototype: client simply discards the token.
    return {"status": "logged_out"}


@router.get("/demo-tokens")
def demo_tokens():
    """Return available demo tokens and their roles (for the prototype login screen)."""
    return [
        {"token": token, "name": info["name"], "role": info["role"]}
        for token, info in TOKENS.items()
    ]
