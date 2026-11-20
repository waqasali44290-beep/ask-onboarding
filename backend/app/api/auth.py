"""Routes: POST /api/auth/login, POST /api/auth/logout, GET /api/auth/me."""
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth import SESSION_COOKIE, create_session, current_user, token_hash, verify_password
from app.config import settings
from app.db import get_session
from app.models import User, UserSession
from app.schemas import LoginRequest, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
def login(request: LoginRequest, response: Response, session: Session = Depends(get_session)):
    user = session.scalar(select(User).where(User.username == request.username.lower()))
    # Same message for unknown user and wrong password, so usernames can't be probed.
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(401, "Wrong username or password.")
    response.set_cookie(
        SESSION_COOKIE,
        create_session(session, user),
        httponly=True,  # JavaScript can't read it, so an XSS bug can't steal the session
        samesite="lax",  # not sent on cross-site POSTs (basic CSRF protection)
        max_age=settings.session_days * 24 * 3600,
    )
    return user


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    session: Session = Depends(get_session),
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
):
    if token:
        session.execute(delete(UserSession).where(UserSession.token_hash == token_hash(token)))
        session.commit()
    response.delete_cookie(SESSION_COOKIE)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user
