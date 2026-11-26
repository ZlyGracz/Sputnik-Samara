"""Курсы: каталог, мои курсы, CRUD, статистика. Владелец: бэкенд.

Контракт: docs/openapi.yaml (тег «Courses»). Пути пишутся полностью после /api.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app import schemas
from app.core.db import get_db
from app.core.deps import get_managed_course, get_optional_user, get_visible_course, require_creator
from app.models import AnswerOption, Attempt, AttemptAnswer, Course, Question, User
from app.routers.common import check_media, media_url

router = APIRouter(prefix="/api", tags=["Courses"])


def _like(s: str) -> str:
    return "%" + s.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _serialize(db: Session, courses: list[Course]) -> list[schemas.Course]:
    counts = {}
    if courses:
        counts = dict(
            db.execute(
                select(Question.course_id, func.count()).where(Question.course_id.in_([c.id for c in courses]))
                .group_by(Question.course_id)
            ).all()
        )
    authors = {u.id: u for u in db.scalars(select(User).where(User.id.in_({c.author_id for c in courses})))}
    return [
        schemas.Course(
            id=c.id, title=c.title, description=c.description, cover_media_id=c.cover_media_id,
            cover_url=media_url(c.cover_media_id), is_published=c.is_published,
            author=schemas.UserBrief.model_validate(authors[c.author_id]),
            questions_count=counts.get(c.id, 0), created_at=c.created_at, updated_at=c.updated_at,
        )
        for c in courses
    ]


def _page(db: Session, cond: list, limit: int, offset: int) -> schemas.CoursePage:
    total = db.scalar(select(func.count()).select_from(Course).where(*cond))
    courses = db.scalars(
        select(Course).where(*cond).order_by(Course.created_at.desc(), Course.id.desc()).limit(limit).offset(offset)
    ).all()
    return schemas.CoursePage(items=_serialize(db, list(courses)), total=total, limit=limit, offset=offset)


@router.get("/courses", response_model=schemas.CoursePage, summary="Каталог опубликованных курсов")
def list_courses(
    search: str | None = Query(None, description="Поиск по названию и описанию"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    cond = [Course.is_published.is_(True)]
    if search and search.strip():
        cond.append(Course.title.ilike(_like(search), escape="\\") | Course.description.ilike(_like(search), escape="\\"))
    return _page(db, cond, limit, offset)


@router.post("/courses", response_model=schemas.Course, status_code=status.HTTP_201_CREATED, summary="Создать курс")
def create_course(data: schemas.CourseCreate, db: Session = Depends(get_db), user: User = Depends(require_creator)):
    check_media(db, data.cover_media_id, "image", "cover_media_id")
    course = Course(author_id=user.id, title=data.title, description=data.description,
                    cover_media_id=data.cover_media_id, is_published=False)
    db.add(course)
    db.commit()
    db.refresh(course)
    return _serialize(db, [course])[0]


@router.get("/courses/my", response_model=schemas.CoursePage, summary="Мои курсы (включая черновики)")
def my_courses(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_creator),
):
    return _page(db, [Course.author_id == user.id], limit, offset)


@router.get("/courses/{course_id}", response_model=schemas.Course, summary="Курс по id")
def get_course(course_id: int, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    return _serialize(db, [get_visible_course(db, course_id, user)])[0]


@router.patch("/courses/{course_id}", response_model=schemas.Course, summary="Изменить курс")
def update_course(
    course_id: int, data: schemas.CourseUpdate, db: Session = Depends(get_db), user: User = Depends(require_creator)
):
    course = get_managed_course(db, course_id, user)
    fields = data.model_fields_set
    if "cover_media_id" in fields:
        check_media(db, data.cover_media_id, "image", "cover_media_id")
        course.cover_media_id = data.cover_media_id
    if data.title is not None:
        course.title = data.title
    if data.description is not None:
        course.description = data.description
    if data.is_published is not None:
        if data.is_published and not db.scalar(select(func.count()).select_from(Question).where(Question.course_id == course.id)):
            raise HTTPException(409, "Нельзя опубликовать курс без вопросов")
        course.is_published = data.is_published
    db.commit()
    db.refresh(course)
    return _serialize(db, [course])[0]


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить курс")
def delete_course(course_id: int, db: Session = Depends(get_db), user: User = Depends(require_creator)):
    db.delete(get_managed_course(db, course_id, user))
    db.commit()
    return Response(status_code=204)


@router.get("/courses/{course_id}/stats", response_model=schemas.CourseStats, summary="Статистика прохождения курса")
def course_stats(course_id: int, db: Session = Depends(get_db), user: User = Depends(require_creator)):
    course = get_managed_course(db, course_id, user)
    attempts, finished, avg = db.execute(
        select(
            func.count(),
            func.count().filter(Attempt.status == "finished"),
            func.coalesce(func.avg(Attempt.score * 100.0 / Attempt.total_questions).filter(Attempt.status == "finished"), 0),
        ).where(Attempt.course_id == course.id)
    ).one()
    rows = db.execute(
        select(
            Question.id, Question.text,
            func.count(AttemptAnswer.id),
            func.coalesce(func.sum(case((AnswerOption.is_correct, 1), else_=0)), 0),
        )
        .outerjoin(AttemptAnswer, AttemptAnswer.question_id == Question.id)
        .outerjoin(AnswerOption, AnswerOption.id == AttemptAnswer.option_id)
        .where(Question.course_id == course.id)
        .group_by(Question.id, Question.text, Question.position)
        .order_by(Question.position)
    ).all()
    return schemas.CourseStats(
        course_id=course.id, attempts_count=attempts, finished_count=finished, average_percent=round(float(avg), 1),
        questions=[
            schemas.QuestionStat(question_id=qid, text=text, answers_count=n, correct_rate=round(ok / n, 4) if n else 0.0)
            for qid, text, n, ok in rows
        ],
    )
