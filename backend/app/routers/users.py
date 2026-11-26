"""Список пользователей, смена роли, блокировка (admin). Владелец: бэкенд.

Контракт: docs/openapi.yaml (тег «Users»). Пути пишутся полностью после /api.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import schemas
from app.core.db import get_db
from app.core.deps import require_admin
from app.models import User

router = APIRouter(prefix="/api", tags=["Users"])


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("/users", response_model=schemas.UserPage, summary="Список пользователей")
def list_users(
    search: str | None = Query(None, description="Поиск по email и имени"),
    role: schemas.Role | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    cond = []
    if role:
        cond.append(User.role == role)
    if search:
        like = f"%{_escape_like(search.strip())}%"
        cond.append(User.email.ilike(like, escape="\\") | User.full_name.ilike(like, escape="\\"))
    total = db.scalar(select(func.count()).select_from(User).where(*cond))
    items = db.scalars(select(User).where(*cond).order_by(User.id).limit(limit).offset(offset)).all()
    return schemas.UserPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/users/{user_id}", response_model=schemas.User, summary="Пользователь по id")
def get_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Пользователь не найден")
    return user


@router.patch("/users/{user_id}", response_model=schemas.User, summary="Выдать роль или заблокировать пользователя")
def update_user(
    user_id: int, data: schemas.UserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Пользователь не найден")
    if user.id == admin.id and (
        (data.role is not None and data.role != user.role) or data.is_active is False
    ):
        raise HTTPException(409, "Администратор не может сменить свою роль или заблокировать себя")
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    db.commit()
    return user
