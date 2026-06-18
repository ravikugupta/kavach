"""
Unit tests for app.auth — token lookup and role enforcement.
Run with:  cd backend && source venv/bin/activate && python -m pytest tests/ -v
"""
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

# The module under test
from app.auth import TOKENS, ROLE_HIERARCHY, get_current_user, require_role


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


# ---------------------------------------------------------------------------
# TOKENS store
# ---------------------------------------------------------------------------

class TestTokenStore:
    def test_demo_token_exists(self):
        assert "demo" in TOKENS

    def test_all_tokens_have_required_keys(self):
        for token, info in TOKENS.items():
            assert "user_id" in info, f"Token {token} missing user_id"
            assert "role"    in info, f"Token {token} missing role"
            assert "name"    in info, f"Token {token} missing name"

    def test_roles_are_valid(self):
        for token, info in TOKENS.items():
            assert info["role"] in ROLE_HIERARCHY, (
                f"Token {token} has unknown role '{info['role']}'"
            )


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------

class TestGetCurrentUser:
    def test_valid_token_returns_user(self):
        creds = make_creds("demo")
        user  = get_current_user(creds)
        assert user is not None
        assert user["role"] == "investigator"

    def test_invalid_token_returns_none(self):
        creds = make_creds("not-a-real-token")
        user  = get_current_user(creds)
        assert user is None

    def test_no_credentials_returns_none(self):
        user = get_current_user(None)
        assert user is None

    def test_supervisor_token_returns_supervisor(self):
        creds = make_creds("supervisor-token-003")
        user  = get_current_user(creds)
        assert user["role"] == "supervisor"


# ---------------------------------------------------------------------------
# require_role
# ---------------------------------------------------------------------------

class TestRequireRole:
    def test_exact_role_passes(self):
        dep  = require_role("investigator")
        creds = make_creds("demo")
        user  = dep(creds)
        assert user["role"] == "investigator"

    def test_higher_role_passes_lower_requirement(self):
        dep   = require_role("investigator")
        creds = make_creds("supervisor-token-003")
        user  = dep(creds)
        assert user["role"] == "supervisor"

    def test_lower_role_raises_403(self):
        dep   = require_role("supervisor")
        creds = make_creds("demo")       # demo is investigator
        with pytest.raises(HTTPException) as exc_info:
            dep(creds)
        assert exc_info.value.status_code == 403

    def test_missing_token_raises_401(self):
        dep = require_role("investigator")
        with pytest.raises(HTTPException) as exc_info:
            dep(None)
        assert exc_info.value.status_code == 401

    def test_analyst_can_access_analyst_route(self):
        dep   = require_role("analyst")
        creds = make_creds("analyst-token-002")
        user  = dep(creds)
        assert user["role"] == "analyst"

    def test_analyst_cannot_access_supervisor_route(self):
        dep   = require_role("supervisor")
        creds = make_creds("analyst-token-002")
        with pytest.raises(HTTPException) as exc_info:
            dep(creds)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# ROLE_HIERARCHY ordering
# ---------------------------------------------------------------------------

class TestRoleHierarchy:
    def test_supervisor_outranks_analyst(self):
        assert ROLE_HIERARCHY["supervisor"] > ROLE_HIERARCHY["analyst"]

    def test_analyst_outranks_investigator(self):
        assert ROLE_HIERARCHY["analyst"] > ROLE_HIERARCHY["investigator"]

    def test_investigator_level_is_positive(self):
        assert ROLE_HIERARCHY["investigator"] >= 1
