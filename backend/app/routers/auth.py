"""Регистрация, вход, /auth/me. Владелец: бэкенд.

Контракт: docs/openapi.yaml (тег «Auth»). Пути пишутся полностью после /api.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User

router = APIRouter(prefix="/api", tags=["Auth"])


def _auth_response(user: User) -> schemas.AuthResponse:
    return schemas.AuthResponse(access_token=create_access_token(user.id), user=schemas.User.model_validate(user))


@router.post("/auth/register", response_model=schemas.AuthResponse, status_code=status.HTTP_201_CREATED,
             summary="Регистрация")
def register(data: schemas.RegisterRequest, db: Session = Depends(get_db)):
    """Создаёт пользователя с ролью `user` и сразу выдаёт токен. Роль повысить может только админ."""
    email = data.email.lower()
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Пользователь с таким email уже существует")
    user = User(email=email, full_name=data.full_name, password_hash=hash_password(data.password), role="user")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # гонка двух регистраций: уникальный индекс lower(email)
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Пользователь с таким email уже существует")
    db.refresh(user)
    return _auth_response(user)


@router.post("/auth/login", response_model=schemas.AuthResponse, summary="Вход")
def login(data: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == data.email.lower()))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Пользователь заблокирован")
    return _auth_response(user)


@router.get("/auth/me", response_model=schemas.User, summary="Текущий пользователь")
def me(user: User = Depends(get_current_user)):
    return user
