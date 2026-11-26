import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { AttemptSummary } from "../api/types";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function MyAttemptsPage() {
  const [attempts, setAttempts] = useState<AttemptSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .getMyAttempts({ limit: 50, offset: 0 })
      .then((page) => {
        if (!cancelled) setAttempts(page.items);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Не удалось загрузить историю попыток");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Мои результаты</h1>
          <p className="page-subtitle">История ваших прохождений курсов</p>
        </div>
        <Link to="/courses" className="btn btn-primary">
          Перейти к курсам
        </Link>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="empty-state">Загружаем историю...</div>
      ) : attempts.length === 0 ? (
        <div className="card empty-state">
          Вы ещё не проходили курсы. Выберите первый курс в каталоге!
        </div>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Курс</th>
                <th>Дата начала</th>
                <th>Статус</th>
                <th>Результат</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {attempts.map((a) => (
                <tr key={a.id}>
                  <td>
                    <strong>{a.course_title}</strong>
                  </td>
                  <td>{formatDate(a.started_at)}</td>
                  <td>
                    {a.status === "finished" ? (
                      <span className="badge badge-green">Завершён</span>
                    ) : (
                      <span className="badge badge-yellow">В процессе</span>
                    )}
                  </td>
                  <td>
                    {a.status === "finished" && a.score !== null && a.percent !== null
                      ? `${a.score} / ${a.total_questions} (${Math.round(a.percent)}%)`
                      : "—"}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <Link to={`/attempts/${a.id}`} className="btn btn-secondary btn-sm">
                      {a.status === "finished" ? "Разбор" : "Продолжить"}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}