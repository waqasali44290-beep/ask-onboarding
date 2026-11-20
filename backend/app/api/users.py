"""Admin-only user management: list, create and update users and their reporting lines."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, aliased

from app.auth import hash_password, require_role
from app.db import get_session
from app.models import User, UserSession
from app.schemas import UserAdminOut, UserCreate, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserAdminOut])
def list_users(_: User = Depends(require_role("admin")), session: Session = Depends(get_session)):
    Manager = aliased(User)
    rows = session.execute(
        select(User, Manager.display_name)
        .outerjoin(Manager, Manager.id == User.manager_id)
        .order_by(User.display_name)
    ).all()
    # manager id -> number of people reporting to them
    teams = dict(session.execute(select(User.manager_id, func.count()).group_by(User.manager_id)).all())
    return [
        UserAdminOut.model_validate(user).model_copy(update={"manager_name": manager_name, "team_size": teams.get(user.id, 0)})
        for user, manager_name in rows
    ]


@router.post("", response_model=UserAdminOut, status_code=201)
def create_user(request: UserCreate, _: User = Depends(require_role("admin")), session: Session = Depends(get_session)):
    username = request.username.lower()
    if session.scalar(select(User).where(User.username == username)):
        raise HTTPException(400, "That username is taken.")
    user = User(username=username, display_name=request.display_name, role=request.role,
                password_hash=hash_password(request.password))
    session.add(user)
    session.flush()  # gives the new user an id for the manager check
    if request.manager_id is not None:
        _set_manager(session, user, request.manager_id)
    session.commit()
    return _out(session, user)


@router.patch("/{user_id}", response_model=UserAdminOut)
def update_user(
    user_id: int,
    request: UserUpdate,
    admin: User = Depends(require_role("admin")),
    session: Session = Depends(get_session),
):
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found.")
    changes = request.model_dump(exclude_unset=True)  # only the fields the admin actually sent

    # An admin must not lock themselves out of the user page.
    if user.id == admin.id and (changes.get("role", "admin") != "admin" or changes.get("is_active") is False):
        raise HTTPException(400, "You can't remove your own admin access.")

    if "display_name" in changes:
        user.display_name = request.display_name
    if "role" in changes:
        user.role = request.role
    if "manager_id" in changes:
        _set_manager(session, user, request.manager_id)
    if "password" in changes:
        user.password_hash = hash_password(request.password)
    if "is_active" in changes:
        user.is_active = request.is_active
    if changes.get("is_active") is False or "password" in changes:
        # Log them out everywhere: a deactivated user or a reset password ends old sessions.
        session.execute(delete(UserSession).where(UserSession.user_id == user.id))
    session.commit()
    return _out(session, user)


def _set_manager(session: Session, user: User, manager_id: int | None) -> None:
    if manager_id is None:
        user.manager_id = None
        return
    manager = session.get(User, manager_id)
    if manager is None or manager.role not in ("manager", "admin") or not manager.is_active:
        raise HTTPException(400, "The manager must be an active manager or admin.")
    # Walk up from the new manager; reaching this user would create a loop (A manages B manages A).
    boss = manager
    while boss is not None:
        if boss.id == user.id:
            raise HTTPException(400, "That would create a loop in the reporting lines.")
        boss = session.get(User, boss.manager_id) if boss.manager_id else None
    user.manager_id = manager_id


def _out(session: Session, user: User) -> UserAdminOut:
    manager = session.get(User, user.manager_id) if user.manager_id else None
    team_size = session.scalar(select(func.count()).where(User.manager_id == user.id))
    return UserAdminOut.model_validate(user).model_copy(
        update={"manager_name": manager.display_name if manager else None, "team_size": team_size}
    )
