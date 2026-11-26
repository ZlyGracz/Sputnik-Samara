"""Зависимости FastAPI: текущий пользователь и RBAC (docs/openapi.yaml, «Роли и права»)."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_token
from app.models import Course, User

_bearer = HTTPBearer(auto_error=False, description="JWT из /api/auth/login или /api/auth/register")

ADMIN, CREATOR, USER = "admin", "creator", "user"


def _unauthorized() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "Недействительный токен", headers={"WWW-Authenticate": "Bearer"})


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)
) -> User | None:
    """Токен необязателен. Если он есть, но неверный — 401."""
    if creds is None:
        return None
    user_id = decode_token(creds.credentials)
    user = db.get(User, user_id) if user_id is not None else None
    # роль и активность — из БД, а не из токена: смена роли и блокировка действуют сразу
    if user is None or not user.is_active:
        raise _unauthorized()
    return user


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise _unauthorized()
    return user


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
        return user

    return checker


require_admin = require_roles(ADMIN)
require_creator = require_roles(CREATOR, ADMIN)


def can_manage(user: User | None, course: Course) -> bool:
    """Админ управляет любым курсом, создатель — только своим."""
    return user is not None and (user.role == ADMIN or (user.role == CREATOR and course.author_id == user.id))


def get_visible_course(db: Session, course_id: int, user: User | None) -> Course:
    """Опубликованный курс виден всем, черновик — владельцу и админу; остальным 404."""
    course = db.get(Course, course_id)
    if course is None or not (course.is_published or can_manage(user, course)):
        raise HTTPException(404, "Курс не найден")
    return course


def get_managed_course(db: Session, course_id: int, user: User) -> Course:
    """Курс для изменения: видимый, но не свой -> 403; чужой черновик -> 404."""
    course = get_visible_course(db, course_id, user)
    if not can_manage(user, course):
        raise HTTPException(403, "Недостаточно прав")
    return course
