import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Course, CourseStats } from "../api/types";

export function CourseStatsPage() {
  const { courseId } = useParams();
  const numericId = Number(courseId);

  const [course, setCourse] = useState<Course | null>(null);
  const [stats, setStats] = useState<CourseStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(numericId)) {
      setError("Некорректный ID курса");
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([api.getCourse(numericId), api.getCourseStats(numericId)])
      .then(([courseData, statsData]) => {
        if (cancelled) return;
        setCourse(courseData);
        setStats(statsData);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Не удалось загрузить статистику");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [numericId]);

  if (loading) {
    return (
      <div className="container">
        <div className="empty-state">Загружаем статистику...</div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Статистика курса</h1>
          <p className="page-subtitle">{course?.title ?? `Курс #${courseId}`}</p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <Link to={`/creator/courses/${courseId}`} className="btn btn-secondary">
            Редактор
          </Link>
          <Link to="/creator" className="btn btn-secondary">
            ← К моим курсам
          </Link>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {stats && (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{stats.attempts_count}</div>
              <div className="stat-label">Всего попыток</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.finished_count}</div>
              <div className="stat-label">Завершено попыток</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{Math.round(stats.average_percent)}%</div>
              <div className="stat-label">Средний результат</div>
            </div>
          </div>

          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Вопрос</th>
                  <th>Ответов</th>
                  <th>Доля верных</th>
                </tr>
              </thead>
              <tbody>
                {stats.questions.length === 0 ? (
                  <tr>
                    <td colSpan={4} style={{ textAlign: "center", color: "var(--text-muted)" }}>
                      Данных по вопросам пока нет.
                    </td>
                  </tr>
                ) : (
                  stats.questions.map((q, idx) => (
                    <tr key={q.question_id}>
                      <td>{idx + 1}</td>
                      <td>{q.text}</td>
                      <td>{q.answers_count}</td>
                      <td>
                        <strong>{Math.round(q.correct_rate * 100)}%</strong>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}