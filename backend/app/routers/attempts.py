"""Прохождение курса: /courses/{id}/attempts, /attempts/*. Владелец: бэкенд.

Контракт: docs/openapi.yaml (тег «Attempts»). Пути пишутся полностью после /api.
Правильность ответа в БД не хранится: считается через answer_options.is_correct.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app import schemas
from app.core.db import get_db
from app.core.deps import get_current_user, get_visible_course
from app.models import AnswerOption, Attempt, AttemptAnswer, Course, Question, User
from app.routers.common import media_url

router = APIRouter(prefix="/api", tags=["Attempts"])


def _percent(a: Attempt) -> float | None:
    return round(a.score * 100 / a.total_questions, 1) if a.score is not None else None


def _own_attempt(db: Session, attempt_id: int, user: User) -> Attempt:
    """Чужая попытка -> 404 (изоляция данных; админ тоже видит только свои)."""
    a = db.get(Attempt, attempt_id)
    if a is None or a.user_id != user.id:
        raise HTTPException(404, "Попытка не найдена")
    return a


def _selected(db: Session, attempt: Attempt) -> dict[int, tuple[int, bool]]:
    """question_id -> (выбранный option_id, верно ли)."""
    rows = db.execute(
        select(AttemptAnswer.question_id, AttemptAnswer.option_id, AnswerOption.is_correct)
        .join(AnswerOption, AnswerOption.id == AttemptAnswer.option_id)
        .where(AttemptAnswer.attempt_id == attempt.id)
    ).all()
    return {q: (o, ok) for q, o, ok in rows}


def _detail(db: Session, a: Attempt) -> schemas.AttemptDetail:
    course = db.get(Course, a.course_id)
    selected = _selected(db, a)
    questions = []
    for q in course.questions:
        sel = selected.get(q.id)
        questions.append(schemas.AttemptQuestion(
            id=q.id, position=q.position, text=q.text,
            image_url=media_url(q.image_media_id), audio_url=media_url(q.audio_media_id),
            options=[schemas.AttemptOption.model_validate(o) for o in q.options],
            selected_option_id=sel[0] if sel else None,
            is_correct=sel[1] if sel else None,
            # правильный вариант раскрываем только после ответа на этот вопрос
            correct_option_id=next(o.id for o in q.options if o.is_correct) if sel else None,
        ))
    return schemas.AttemptDetail(
        id=a.id, course_id=a.course_id, course_title=course.title, status=a.status, started_at=a.started_at,
        finished_at=a.finished_at, total_questions=a.total_questions, answered_count=len(selected),
        score=a.score, percent=_percent(a), questions=questions,
    )


@router.post("/courses/{course_id}/attempts", response_model=schemas.AttemptDetail, status_code=status.HTTP_201_CREATED,
             summary="Начать прохождение курса")
def start_attempt(course_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Только опубликованный курс (иначе 404, даже владельцу). Если у пользователя уже есть
    незавершённая попытка по этому курсу — возвращается она (продолжение)."""
    course = db.get(Course, course_id)
    if course is None or not course.is_published:
        raise HTTPException(404, "Курс не найден")
    attempt = db.scalar(select(Attempt).where(
        Attempt.user_id == user.id, Attempt.course_id == course_id, Attempt.status == "in_progress"))
    if attempt is None:
        total = len(course.questions)
        if total == 0:
            raise HTTPException(409, "В курсе нет вопросов")
        attempt = Attempt(user_id=user.id, course_id=course_id, total_questions=total)
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
    return _detail(db, attempt)


@router.get("/attempts/my", response_model=schemas.AttemptPage, summary="История моих попыток")
def my_attempts(
    course_id: int | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cond = [Attempt.user_id == user.id]
    if course_id is not None:
        cond.append(Attempt.course_id == course_id)
    total = db.scalar(select(func.count()).select_from(Attempt).where(*cond))
    rows = db.execute(
        select(Attempt, Course.title).join(Course, Course.id == Attempt.course_id).where(*cond)
        .order_by(Attempt.started_at.desc(), Attempt.id.desc()).limit(limit).offset(offset)
    ).all()
    items = [
        schemas.AttemptSummary(
            id=a.id, course_id=a.course_id, course_title=title, status=a.status, started_at=a.started_at,
            finished_at=a.finished_at, total_questions=a.total_questions, score=a.score, percent=_percent(a),
        )
        for a, title in rows
    ]
    return schemas.AttemptPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/attempts/{attempt_id}", response_model=schemas.AttemptDetail, summary="Попытка с вопросами и ответами")
def get_attempt(attempt_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _detail(db, _own_attempt(db, attempt_id, user))


@router.post("/attempts/{attempt_id}/answers", response_model=schemas.AnswerResult,
             status_code=status.HTTP_201_CREATED, summary="Ответить на вопрос")
def answer(
    attempt_id: int, data: schemas.AnswerRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    # блокируем строку попытки: параллельные ответы/finish не обгонят друг друга
    a = db.scalar(select(Attempt).where(Attempt.id == attempt_id).with_for_update())
    if a is None or a.user_id != user.id:
        raise HTTPException(404, "Попытка не найдена")
    if a.status == "finished":
        raise HTTPException(409, "Попытка уже завершена")
    q = db.get(Question, data.question_id)
    if q is None or q.course_id != a.course_id:
        raise HTTPException(422, "Вопрос не относится к этому курсу")
    chosen = next((o for o in q.options if o.id == data.option_id), None)
    if chosen is None:
        raise HTTPException(422, "Вариант не относится к этому вопросу")
    db.add(AttemptAnswer(attempt_id=a.id, question_id=q.id, option_id=chosen.id))
    try:
        db.commit()
    except IntegrityError:  # uq_attempt_answers_attempt_question
        db.rollback()
        raise HTTPException(409, "На этот вопрос уже дан ответ")
    correct = next(o.id for o in q.options if o.is_correct)
    return schemas.AnswerResult(
        question_id=q.id, selected_option_id=chosen.id, is_correct=chosen.is_correct, correct_option_id=correct
    )


@router.post("/attempts/{attempt_id}/finish", response_model=schemas.AttemptDetail,
             summary="Завершить попытку и получить результат")
def finish(attempt_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a = db.scalar(select(Attempt).where(Attempt.id == attempt_id).with_for_update())
    if a is None or a.user_id != user.id:
        raise HTTPException(404, "Попытка не найдена")
    if a.status == "in_progress":
        correct = sum(1 for _, ok in _selected(db, a).values() if ok)
        a.score = min(correct, a.total_questions)  # CHECK score <= total_questions (если курс дополнили после старта)
        a.status, a.finished_at = "finished", datetime.now(timezone.utc)
        db.commit()
    return _detail(db, a)
