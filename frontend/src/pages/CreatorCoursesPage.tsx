import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Course } from "../api/types";

export function CreatorCoursesPage() {
  const navigate = useNavigate();

  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  const loadCourses = async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await api.getMyCourses({ limit: 100, offset: 0 });
      setCourses(page.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось загрузить ваши курсы");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadCourses();
  }, []);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (title.trim().length < 3) {
      setError("Название курса должно содержать минимум 3 символа");
      return;
    }

    setCreating(true);
    setError(null);
    try {
      const created = await api.createCourse({
        title: title.trim(),
        description: description.trim(),
      });
      setTitle("");
      setDescription("");
      navigate(`/creator/courses/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось создать курс");
    } finally {
      setCreating(false);
    }
  };

  const handleTogglePublish = async (course: Course) => {
    setBusyId(course.id);
    setError(null);
    try {
      const updated = await api.updateCourse(course.id, {
        is_published: !course.is_published,
      });
      setCourses((prev) => prev.map((c) => (c.id === course.id ? updated : c)));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Не удалось изменить статус публикации (возможно, в курсе ещё нет вопросов)"
      );
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (course: Course) => {
    const ok = window.confirm(
      `Удалить курс «${course.title}» вместе со всеми вопросами и результатами?`
    );
    if (!ok) return;

    setBusyId(course.id);
    setError(null);
    try {
      await api.deleteCourse(course.id);
      setCourses((prev) => prev.filter((c) => c.id !== course.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось удалить курс");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Кабинет создателя</h1>
          <p className="page-subtitle">Создавайте курсы, добавляйте вопросы и смотрите статистику</p>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card" style={{ marginBottom: 24 }}>
        <h2 style={{ marginTop: 0, fontSize: 18 }}>Новый курс</h2>
        <form className="form-stack" onSubmit={handleCreate}>
          <div className="field">
            <label htmlFor="course-title">Название курса</label>
            <input
              id="course-title"
              className="input"
              type="text"
              required
              minLength={3}
              maxLength={200}
              placeholder="Например: История России"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="course-desc">Описание</label>
            <textarea
              id="course-desc"
              className="textarea"
              maxLength={5000}
              placeholder="Кратко расскажите, о чём этот курс..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div>
            <button type="submit" className="btn btn-primary" disabled={creating}>
              {creating ? "Создаём..." : "Создать и перейти к вопросам"}
            </button>
          </div>
        </form>
      </div>

      <h2 style={{ fontSize: 20, marginBottom: 14 }}>Мои курсы</h2>

      {loading ? (
        <div className="empty-state">Загружаем список...</div>
      ) : courses.length === 0 ? (
        <div className="card empty-state">У вас пока нет созданных курсов.</div>
      ) : (
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
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "flex-start" }}>
                  <h3 className="course-card-title">{course.title}</h3>
                  {course.is_published ? (
                    <span className="badge badge-green">Опубликован</span>
                  ) : (
                    <span className="badge badge-yellow">Черновик</span>
                  )}
                </div>

                <p className="course-card-desc">
                  {course.description || "Описание не указано."}
                </p>

                <div className="course-card-meta">
                  <span>Вопросов: {course.questions_count}</span>
                </div>

                <div className="course-card-actions">
                  <Link to={`/creator/courses/${course.id}`} className="btn btn-primary btn-sm">
                    Редактировать
                  </Link>
                  <Link to={`/creator/courses/${course.id}/stats`} className="btn btn-secondary btn-sm">
                    Статистика
                  </Link>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={busyId === course.id}
                    onClick={() => handleTogglePublish(course)}
                  >
                    {course.is_published ? "Снять с публикации" : "Опубликовать"}
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    disabled={busyId === course.id}
                    onClick={() => handleDelete(course)}
                  >
                    Удалить
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}