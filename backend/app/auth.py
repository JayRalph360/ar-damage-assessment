"""User authentication (Login / Access System use case)."""
import hashlib
import hmac
import os
import secrets
from typing import Optional

from fastapi import Cookie, Header, HTTPException

from .db import connect, row

COOKIE_NAME = "arinspect_session"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"pbkdf2${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 200_000)
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with connect() as con:
        con.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
    return token


def delete_session(token: str):
    with connect() as con:
        con.execute("DELETE FROM sessions WHERE token = ?", (token,))


def public_user(u: dict) -> dict:
    return {k: u[k] for k in ("id", "username", "full_name", "role", "created_at")}


def current_user(
    arinspect_session: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
) -> dict:
    token = arinspect_session
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:]
    if not token:
        raise HTTPException(401, "Not logged in")
    with connect() as con:
        u = row(con.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?", (token,)
        ).fetchone())
    if not u:
        raise HTTPException(401, "Session expired, please log in again")
    u["_token"] = token
    return u


def ensure_demo_user():
    """Create a default account so the system can be demonstrated immediately."""
    with connect() as con:
        if con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            con.execute(
                "INSERT INTO users (username, full_name, role, password_hash) VALUES (?, ?, ?, ?)",
                ("inspector", "Demo Inspector", "Inspector", hash_password("inspect123")),
            )
