"""SQL-запросы результатов и статистики. Владелец: БД.

Форма результатов совпадает со схемами docs/openapi.yaml (AttemptSummary, CourseStats),
так что роутеры могут отдавать их как есть. Проверку прав (владелец курса / admin,
изоляция попыток по user_id) делает вызывающий код; запрос «мои результаты»
фильтрует по user_id сам.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

# percent считается в SQL: score * 100 / total_questions, округление до 0.1
_MY_ATTEMPTS = text("""
    SELECT a.id, a.course_id, c.title AS course_title, a.status, a.started_at, a.finished_at,
           a.total_questions, a.score,
           CASE WHEN a.score IS NULL THEN NULL
                ELSE ROUND(a.score * 100.0 / a.total_questions, 1)::float END AS percent
    FROM attempts a
    JOIN courses c ON c.id = a.course_id
    WHERE a.user_id = :user_id
      AND (CAST(:course_id AS bigint) IS NULL OR a.course_id = :course_id)
    ORDER BY a.started_at DESC, a.id DESC
    LIMIT :limit OFFSET :offset
""")

_MY_ATTEMPTS_TOTAL = text("""
    SELECT COUNT(*) FROM attempts
    WHERE user_id = :user_id AND (CAST(:course_id AS bigint) IS NULL OR course_id = :course_id)
""")

_COURSE_SUMMARY = text("""
    SELECT COUNT(*)                                             AS attempts_count,
           COUNT(*) FILTER (WHERE status = 'finished')          AS finished_count,
           COALESCE(ROUND(AVG(score * 100.0 / total_questions)
                          FILTER (WHERE status = 'finished'), 1), 0)::float AS average_percent
    FROM attempts
    WHERE course_id = :course_id
""")

# correct_rate — доля правильных среди всех данных ответов (0..1).
# Правильность берётся из answer_options, в attempt_answers она не хранится.
_COURSE_QUESTIONS = text("""
    SELECT q.id AS question_id, q.text,
           COUNT(aa.id) AS answers_count,
           COALESCE(ROUND(AVG(CASE WHEN o.is_correct THEN 1.0 ELSE 0.0 END), 3), 0)::float AS correct_rate
    FROM questions q
    LEFT JOIN attempt_answers aa ON aa.question_id = q.id
    LEFT JOIN answer_options o   ON o.id = aa.option_id
    WHERE q.course_id = :course_id
    GROUP BY q.id, q.text, q.position
    ORDER BY q.position
""")


def my_attempts(db: Session, user_id: int, course_id: int | None = None,
                limit: int = 20, offset: int = 0) -> dict:
    """GET /api/attempts/my → AttemptPage."""
    params = {"user_id": user_id, "course_id": course_id, "limit": limit, "offset": offset}
    items = [dict(r) for r in db.execute(_MY_ATTEMPTS, params).mappings()]
    total = db.scalar(_MY_ATTEMPTS_TOTAL, {"user_id": user_id, "course_id": course_id})
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def course_stats(db: Session, course_id: int) -> dict:
    """GET /api/courses/{id}/stats → CourseStats."""
    summary = dict(db.execute(_COURSE_SUMMARY, {"course_id": course_id}).mappings().one())
    questions = [dict(r) for r in db.execute(_COURSE_QUESTIONS, {"course_id": course_id}).mappings()]
    return {"course_id": course_id, **summary, "questions": questions}
