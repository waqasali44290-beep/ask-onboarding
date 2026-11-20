"""Passwords, sessions and the "who is calling?" dependencies used by every route."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app.models import User, UserSession

SESSION_COOKIE = "session"
PASSWORD_ITERATIONS = 200_000  # slow on purpose: makes guessing stolen hashes expensive

# Demo accounts created on first start (password: settings.demo_password).
DEMO_USERS = [
    ("employee", "Sara Khan", "employee"),
    ("manager", "Omar Malik", "manager"),
    ("admin", "Help Desk Admin", "admin"),
]


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PASSWORD_ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt = stored.split("$", 1)[0]
    # compare_digest takes the same time whether the first or last character differs
    return hmac.compare_digest(hash_password(password, salt), stored)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(session: Session, user: User) -> str:
    """Store a new session and return the random token for the cookie."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.session_days)
    session.add(UserSession(token_hash=token_hash(token), user_id=user.id, expires_at=expires_at))
    session.commit()
    return token


def current_user(
    session: Session = Depends(get_session),
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> User:
    """FastAPI dependency: the logged-in user, or 401."""
    if token:
        user = session.scalar(
            select(User)
            .join(UserSession, UserSession.user_id == User.id)
            .where(UserSession.token_hash == token_hash(token), UserSession.expires_at > func.now())
        )
        if user:
            return user
    raise HTTPException(401, "Please log in.")


def require_role(*roles: str):
    """Dependency factory: allow only users with one of `roles`, e.g. Depends(require_role("admin"))."""

    def check(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "You don't have permission to do this.")
        return user

    return check


def ensure_demo_users(session: Session) -> None:
    for username, display_name, role in DEMO_USERS:
        if session.scalar(select(User).where(User.username == username)) is None:
            session.add(User(username=username, display_name=display_name, role=role,
                             password_hash=hash_password(settings.demo_password)))
    session.commit()
