-- Справочные SQL-запросы результатов и статистики (PostgreSQL). Владелец: БД.
-- В коде те же выборки уже реализованы через ORM:
--   GET /api/attempts/my           -> backend/app/routers/attempts.py (my_attempts)
--   GET /api/courses/{id}/stats    -> backend/app/routers/courses.py  (course_stats)
-- Здесь — тот же результат «чистым» SQL: для проверки, отчёта и ручной отладки (psql -v user_id=3 -f ...).
-- Правильность ответа в БД не хранится: берётся из answer_options.is_correct.

-- 1. Мои результаты (студент): все попытки, свежие сверху.
--    percent = score * 100 / total_questions, у незавершённой попытки score и percent = NULL.
SELECT a.id, a.course_id, c.title AS course_title, a.status, a.started_at, a.finished_at,
       a.total_questions, a.score,
       ROUND(a.score * 100.0 / a.total_questions, 1) AS percent
FROM attempts a
JOIN courses c ON c.id = a.course_id
WHERE a.user_id = :user_id
ORDER BY a.started_at DESC, a.id DESC;

-- 2. Статистика курса для создателя: сводка.
--    average_percent — по завершённым попыткам (0, если таких нет).
SELECT COUNT(*)                                    AS attempts_count,
       COUNT(*) FILTER (WHERE status = 'finished') AS finished_count,
       COALESCE(ROUND(AVG(score * 100.0 / total_questions)
                      FILTER (WHERE status = 'finished'), 1), 0) AS average_percent
FROM attempts
WHERE course_id = :course_id;

-- 3. Статистика курса по вопросам: доля правильных ответов (0..1), где чаще ошибаются.
--    Считаются все данные ответы, включая незавершённые попытки.
SELECT q.id AS question_id, q.text,
       COUNT(aa.id) AS answers_count,
       COALESCE(ROUND(AVG(CASE WHEN o.is_correct THEN 1.0 ELSE 0.0 END), 3), 0) AS correct_rate
FROM questions q
LEFT JOIN attempt_answers aa ON aa.question_id = q.id
LEFT JOIN answer_options o   ON o.id = aa.option_id
WHERE q.course_id = :course_id
GROUP BY q.id, q.text, q.position
ORDER BY q.position;

-- 4. Лучший результат пользователя по каждому курсу.
SELECT DISTINCT ON (a.course_id)
       a.course_id, c.title, a.score, a.total_questions,
       ROUND(a.score * 100.0 / a.total_questions, 1) AS percent
FROM attempts a
JOIN courses c ON c.id = a.course_id
WHERE a.user_id = :user_id AND a.status = 'finished'
ORDER BY a.course_id, a.score DESC, a.finished_at DESC;
