"""Вопросы и варианты: /courses/{id}/questions, /questions/{id}. Владелец: бэкенд.

Контракт: docs/openapi.yaml (тег «Questions»). Пути пишутся полностью после /api.
Вариантов всегда 4 (позиции 1..4), правильный ровно один — это проверяет схема запроса.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app import schemas
from app.core.db import get_db
from app.core.deps import get_managed_course, require_creator
from app.models import AnswerOption, Question, User
from app.routers.common import check_media, media_url

router = APIRouter(prefix="/api", tags=["Questions"])


def _out(q: Question) -> schemas.Question:
    return schemas.Question(
        id=q.id, course_id=q.course_id, position=q.position, text=q.text,
        image_media_id=q.image_media_id, image_url=media_url(q.image_media_id),
        audio_media_id=q.audio_media_id, audio_url=media_url(q.audio_media_id),
        options=[schemas.Option.model_validate(o) for o in q.options],
    )


def _renumber(db: Session, course_id: int, question: Question | None = None, position: int | None = None) -> None:
    """Выставляет позиции 1..n без пропусков; `question` ставится на `position` (или в конец)."""
    others = list(db.scalars(
        select(Question).where(Question.course_id == course_id, Question.id != (question.id if question else 0))
        .order_by(Question.position, Question.id)
    ))
    if question is not None:
        idx = len(others) if position is None else min(max(position, 1), len(others) + 1) - 1
        others.insert(idx, question)
    for i, q in enumerate(others, start=1):
        if q.position != i:
            q.position = i
    db.flush()  # уникальность (course_id, position) отложена до коммита


def _managed_question(db: Session, question_id: int, user: User) -> Question:
    q = db.get(Question, question_id)
    if q is None:
        raise HTTPException(404, "Вопрос не найден")
    get_managed_course(db, q.course_id, user)  # 404 / 403 по правилам курса
    return q


@router.get("/courses/{course_id}/questions", response_model=list[schemas.Question],
            summary="Вопросы курса с правильными ответами")
def list_questions(course_id: int, db: Session = Depends(get_db), user: User = Depends(require_creator)):
    course = get_managed_course(db, course_id, user)
    return [_out(q) for q in course.questions]


@router.post("/courses/{course_id}/questions", response_model=schemas.Question, status_code=status.HTTP_201_CREATED,
             summary="Добавить вопрос в курс")
def create_question(
    course_id: int, data: schemas.QuestionInput, db: Session = Depends(get_db), user: User = Depends(require_creator)
):
    course = get_managed_course(db, course_id, user)
    check_media(db, data.image_media_id, "image", "image_media_id")
    check_media(db, data.audio_media_id, "audio", "audio_media_id")
    # сначала в конец, затем (если указана позиция) переставляем — всё в одной транзакции
    last = len(course.questions)
    q = Question(course_id=course.id, position=last + 1, text=data.text,
                 image_media_id=data.image_media_id, audio_media_id=data.audio_media_id)
    q.options = [AnswerOption(position=i, text=o.text, is_correct=o.is_correct) for i, o in enumerate(data.options, 1)]
    db.add(q)
    db.flush()
    if data.position is not None and data.position <= last:
        _renumber(db, course.id, q, data.position)
    db.commit()
    db.refresh(q)
    return _out(q)


@router.put("/questions/{question_id}", response_model=schemas.Question, summary="Заменить вопрос целиком")
def replace_question(
    question_id: int, data: schemas.QuestionInput, db: Session = Depends(get_db), user: User = Depends(require_creator)
):
    q = _managed_question(db, question_id, user)
    check_media(db, data.image_media_id, "image", "image_media_id")
    check_media(db, data.audio_media_id, "audio", "audio_media_id")
    q.text, q.image_media_id, q.audio_media_id = data.text, data.image_media_id, data.audio_media_id
    # варианты обновляем НА МЕСТЕ по position (иначе каскадом удалятся ответы студентов, docs/db-schema.md).
    # Сначала снимаем is_correct со всех: частичный уникальный индекс «один правильный» не отложенный.
    db.execute(update(AnswerOption).where(AnswerOption.question_id == q.id).values(is_correct=False))
    db.flush()
    by_pos = {o.position: o for o in q.options}
    for i, new in enumerate(data.options, 1):
        o = by_pos[i]
        o.text, o.is_correct = new.text, new.is_correct
    if data.position is not None:
        _renumber(db, q.course_id, q, data.position)
    db.commit()
    db.refresh(q)
    return _out(q)


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить вопрос")
def delete_question(question_id: int, db: Session = Depends(get_db), user: User = Depends(require_creator)):
    q = _managed_question(db, question_id, user)
    course_id = q.course_id
    db.delete(q)
    db.flush()
    _renumber(db, course_id)
    db.commit()
    return Response(status_code=204)
