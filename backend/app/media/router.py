"""Загрузка и выдача фото и аудио (POST /api/media, GET /api/media/{media_id}). Владелец: инфраструктура.

Контракт: docs/openapi.yaml (тег «Media»). Файлы хранятся в settings.media_dir
(в Docker — том media_data), метаданные — в таблице media.
"""
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.media.validator import detect_media_spec
from app.models.media import Media
from app.models.user import User

try:
    from app.core.deps import require_creator
except ImportError:
    # Временный fallback до вливания ветки backend-api в main (логика идентична app.core.deps)
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
    import jwt

    _bearer = HTTPBearer(auto_error=False, description="JWT из /api/auth/login или /api/auth/register")

    def require_creator(
        creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
        db: Session = Depends(get_db),
    ) -> User:
        unauthorized = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
        if creds is None:
            raise unauthorized
        try:
            payload = jwt.decode(
                creds.credentials,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
            user_id = int(payload["sub"])
        except (jwt.PyJWTError, KeyError, ValueError):
            raise unauthorized

        user = db.get(User, user_id)
        if user is None or not user.is_active:
            raise unauthorized
        if user.role not in ("creator", "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
            )
        return user


CHUNK_SIZE = 64 * 1024  # 64 КБ

router = APIRouter(prefix="/api", tags=["Media"])


class MediaResponse(BaseModel):
    id: uuid.UUID
    kind: str
    content_type: str
    size_bytes: int
    url: str


@router.post(
    "/media",
    status_code=status.HTTP_201_CREATED,
    response_model=MediaResponse,
    summary="Загрузить фото или аудио",
)
def upload_media(
    file: UploadFile = File(...),
    current_user: User = Depends(require_creator),
    db: Session = Depends(get_db),
) -> MediaResponse:
    try:
        first_chunk = file.file.read(CHUNK_SIZE)
        spec = detect_media_spec(first_chunk)
        if spec is None:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Неподдерживаемый тип файла. Разрешены JPEG, PNG, WebP, MP3, OGG, WAV",
            )

        media_root = Path(settings.media_dir).resolve()
        media_root.mkdir(parents=True, exist_ok=True)

        media_id = uuid.uuid4()
        storage_name = f"{media_id}{spec.extension}"
        dest_path = media_root / storage_name

        total_size = 0
        try:
            with dest_path.open("wb") as out:
                chunk = first_chunk
                while chunk:
                    total_size += len(chunk)
                    if total_size > spec.max_bytes:
                        limit_mb = spec.max_bytes // (1024 * 1024)
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Файл слишком большой (максимум {limit_mb} МБ)",
                        )
                    out.write(chunk)
                    chunk = file.file.read(CHUNK_SIZE)
        except Exception:
            dest_path.unlink(missing_ok=True)
            raise

        media = Media(
            id=media_id,
            kind=spec.kind,
            content_type=spec.content_type,
            size_bytes=total_size,
            storage_path=storage_name,
            uploaded_by=current_user.id,
        )
        try:
            db.add(media)
            db.commit()
        except Exception:
            db.rollback()
            dest_path.unlink(missing_ok=True)
            raise

        return MediaResponse(
            id=media.id,
            kind=media.kind,
            content_type=media.content_type,
            size_bytes=media.size_bytes,
            url=f"/api/media/{media.id}",
        )
    finally:
        file.file.close()


@router.get(
    "/media/{media_id}",
    summary="Получить файл",
)
def get_media(
    media_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> FileResponse:
    media = db.get(Media, media_id)
    if media is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден",
        )

    media_root = Path(settings.media_dir).resolve()
    file_path = (media_root / media.storage_path).resolve()
    if not file_path.is_relative_to(media_root) or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден",
        )

    return FileResponse(
        path=file_path,
        media_type=media.content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )