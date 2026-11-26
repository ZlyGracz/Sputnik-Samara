"""Общие помощники роутеров."""
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Media


def media_url(media_id: UUID | None) -> str | None:
    return f"/api/media/{media_id}" if media_id else None


def check_media(db: Session, media_id: UUID | None, kind: str, field: str) -> None:
    """Медиафайл должен существовать и быть нужного типа (image / audio), иначе 422."""
    if media_id is None:
        return
    media = db.get(Media, media_id)
    if media is None:
        raise HTTPException(422, f"{field}: файл не найден")
    if media.kind != kind:
        raise HTTPException(422, f"{field}: ожидается файл типа {kind}")
