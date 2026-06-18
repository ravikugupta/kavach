"""
Lightweight token-based authentication for the Kavach prototype.

In production this would use JWT/OAuth2. For the prototype we keep a simple
static token store so the demo works without any external auth service.

Roles
-----
* investigator  - read FIRs / accused, ask chat questions
* analyst       - all investigator perms + analytics + network
* supervisor    - full access including export and early-warning management

Usage
-----
Add ``Depends(require_role("analyst"))`` to any router endpoint.
The client must send: ``Authorization: Bearer <token>``
"""
from __future__ import annotations
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ---------------------------------------------------------------------------
# Static token store (replace with a DB / JWT in production)
# ---------------------------------------------------------------------------

TOKENS: dict[str, dict] = {
    "investigator-token-001": {"user_id": "user-001", "name": "Ravi Kumar",      "role": "investigator"},
    "analyst-token-002":      {"user_id": "user-002", "name": "Priya Sharma",    "role": "analyst"},
    "supervisor-token-003":   {"user_id": "user-003", "name": "DCP Venkatesh",   "role": "supervisor"},
    # Public demo token – grants investigator-level access without login
    "demo":                   {"user_id": "demo",     "name": "Demo User",       "role": "investigator"},
}

ROLE_HIERARCHY = {"investigator": 1, "analyst": 2, "supervisor": 3}

_bearer = HTTPBearer(auto_error=False)


def _get_user(credentials: Optional[HTTPAuthorizationCredentials]) -> Optional[dict]:
    if not credentials:
        return None
    return TOKENS.get(credentials.credentials)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
) -> Optional[dict]:
    """Return the user dict or None (unauthenticated requests still reach public endpoints)."""
    return _get_user(credentials)


def require_role(min_role: str):
    """
    FastAPI dependency factory.
    Usage::

        @router.get("/secure")
        def secure(user=Depends(require_role("analyst"))):
            ...
    """
    min_level = ROLE_HIERARCHY.get(min_role, 99)

    def _dep(
        credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
    ) -> dict:
        user = _get_user(credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Provide a Bearer token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_level = ROLE_HIERARCHY.get(user["role"], 0)
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires role '{min_role}' or higher. Your role: '{user['role']}'.",
            )
        return user

    return _dep
