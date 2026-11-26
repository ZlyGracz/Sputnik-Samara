import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Course } from "../api/types";
import { useAuth } from "../context/AuthContext";

const PAGE_SIZE = 12;

export function CoursesPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [courses, setCourses] = useState<Course[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startingId, setStartingId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .getCourses({ search: searchQuery || undefined, limit: PAGE_SIZE, offset })
      .then((page) => {
        if (cancelled) return;
        setCourses(page.items);
        setTotal(page.total);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Не удалось загрузить курсы");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [searchQuery, offset]);

  const handleSearch = (e: FormEvent) => {
    e.preventDefault();
    setOffset(0);
    setSearchQuery(searchInput.trim());
  };

  const handleStartCourse = async (courseId: number) => {
    if (!user) {
      navigate("/login", { state: { from: "/courses" } });
      return;
    }

    setStartingId(courseId);
    setError(null);
    try {
      const attempt = await api.startAttempt(courseId);
      navigate(`/attempts/${attempt.id}`, { state: { initialAttempt: attempt } });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось начать прохождение курса");
    } finally {
      setStartingId(null);
    }
  };

  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;

  return (
    <div className="container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Каталог курсов</h1>
          <p className="page-subtitle">Выберите курс, чтобы проверить свои знания</p>
        </div>
      </div>

      <form className="toolbar" onSubmit={handleSearch}>
        <input
          className="input"
          type="search"
          placeholder="Поиск по названию или описанию..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        <button type="submit" className="btn btn-primary">
          Найти
        </button>
        {searchQuery && (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              setSearchInput("");
              setSearchQuery("");
              setOffset(0);
            }}
          >
            Сбросить
          </button>
        )}
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="empty-state">Загружаем курсы...</div>
      ) : courses.length === 0 ? (
        <div className="card empty-state">
          {searchQuery ? "По вашему запросу курсы не найдены." : "Пока нет опубликованных курсов."}
        </div>
      ) : (
        <>
          <div className="courses-grid">
            {courses.map((course) => (
              <article key={course.id} className="course-card">
                <div className="course-cover">
                  {course.cover_url ? (
                    <img src={course.cover_url} alt={course.title} />
                  ) : (
                    <span>{course.title.slice(0, 24)}</span>
                  )}
                </div>

                <div className="course-card-body">
                  <h2 className="course-card-title">{course.title}</h2>
                  <p className="course-card-desc">
                    {course.description || "Описание курса пока не добавлено."}
                  </p>

                  <div className="course-card-meta">
                    <span>Автор: {course.author.full_name}</span>
                    <span className="badge badge-blue">Вопросов: {course.questions_count}</span>
                  </div>

                  <div className="course-card-actions">
                    <button
                      type="button"
                      className="btn btn-primary btn-block"
                      disabled={startingId === course.id}
                      onClick={() => handleStartCourse(course.id)}
                    >
                      {startingId === course.id
                        ? "Запускаем..."
                        : user
                          ? "Пройти курс"
                          : "Войти и пройти"}
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>

          {(hasPrev || hasNext) && (
            <div style={{ display: "flex", justifyContent: "center", gap: 12, marginTop: 28 }}>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={!hasPrev}
                onClick={() => setOffset((prev) => Math.max(0, prev - PAGE_SIZE))}
              >
                ← Назад
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={!hasNext}
                onClick={() => setOffset((prev) => prev + PAGE_SIZE)}
              >
                Вперёд →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}