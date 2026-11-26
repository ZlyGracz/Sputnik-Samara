"""Начальные данные. Владелец: БД.

Запускается при старте контейнера (после миграций): `python -m seed.run`.
Идемпотентен: повторный запуск ничего не дублирует и не меняет существующие данные.

Что создаётся:
  - пользователи admin / creator / user (учётки — в seed/data.py и README);
  - демо-курс «История России»: 10 вопросов (3 с фото, 2 со звуком), у каждого 4 варианта;
  - файлы медиа в MEDIA_DIR/seed/ и строки в таблице media.

Отключить: SEED_ON_START=false.
"""
import uuid
from pathlib import Path

import bcrypt
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import AnswerOption, Course, Media, Question, User
from seed import data
from seed.media_gen import make_bell, make_png, make_salvo

ASSETS_DIR = Path(__file__).parent / "assets"
MEDIA_NS = uuid.UUID("5d0b6f6e-6c1a-4c55-9d0e-5a1f4b7e0a11")  # фиксированный: id медиа детерминированы
CONTENT_TYPES = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg",
}


def _media_file(key: str, spec: dict) -> tuple[bytes, str]:
    """Возвращает (байты, расширение): файл из seed/assets, иначе сгенерированная заглушка."""
    for path in sorted(ASSETS_DIR.glob(f"{key}.*")):
        if path.suffix.lower() in CONTENT_TYPES:
            return path.read_bytes(), path.suffix.lower()
    if spec["kind"] == "image":
        top, bottom, circle = spec["colors"]
        return make_png(640, 360, top, bottom, circle), ".png"
    return (make_bell() if key == "bell" else make_salvo()), ".wav"


def seed_users(db) -> dict[str, User]:
    users = {}
    for u in data.USERS:
        user = db.scalar(select(User).where(func.lower(User.email) == u["email"].lower()))
        if user is None:
            hashed = bcrypt.hashpw(u["password"].encode(), bcrypt.gensalt()).decode()
            user = User(email=u["email"], password_hash=hashed, full_name=u["full_name"], role=u["role"])
            db.add(user)
            db.flush()
            print(f"seed: пользователь {u['email']} ({u['role']})")
        users[u["email"]] = user
    return users


def seed_media(db, uploader_id: int) -> dict[str, uuid.UUID]:
    ids = {}
    for key, spec in data.MEDIA.items():
        content, ext = _media_file(key, spec)
        media_id = uuid.uuid5(MEDIA_NS, key)
        rel_path = f"seed/{key}{ext}"
        target = Path(settings.media_dir) / rel_path
        if not target.exists():  # файл мог пропасть вместе с томом, а строка в БД остаться
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        db.execute(
            pg_insert(Media).values(
                id=media_id, kind=spec["kind"], content_type=CONTENT_TYPES[ext],
                size_bytes=len(content), storage_path=rel_path, uploaded_by=uploader_id,
            ).on_conflict_do_nothing(index_elements=["id"])
        )
        ids[key] = media_id
    return ids


def seed_course(db, author: User, media: dict[str, uuid.UUID]) -> None:
    exists = db.scalar(
        select(Course.id).where(Course.author_id == author.id, Course.title == data.COURSE_TITLE)
    )
    if exists:
        print(f"seed: курс «{data.COURSE_TITLE}» уже есть")
        return
    course = Course(
        author_id=author.id, title=data.COURSE_TITLE, description=data.COURSE_DESCRIPTION,
        cover_media_id=media["cover"], is_published=True,
    )
    for pos, (text, image, audio, options, correct) in enumerate(data.QUESTIONS, start=1):
        assert len(options) == 4 and 0 <= correct < 4
        course.questions.append(Question(
            position=pos, text=text,
            image_media_id=media[image] if image else None,
            audio_media_id=media[audio] if audio else None,
            options=[
                AnswerOption(position=i, text=t, is_correct=(i - 1 == correct))
                for i, t in enumerate(options, start=1)
            ],
        ))
    db.add(course)
    print(f"seed: курс «{data.COURSE_TITLE}» — {len(data.QUESTIONS)} вопросов")


def main() -> None:
    if not settings.seed_on_start:
        print("seed: отключён (SEED_ON_START=false)")
        return
    with SessionLocal() as db:
        users = seed_users(db)
        creator = users[data.COURSE_AUTHOR]
        media = seed_media(db, creator.id)
        seed_course(db, creator, media)
        db.commit()
    print("seed: готово")


if __name__ == "__main__":
    main()
