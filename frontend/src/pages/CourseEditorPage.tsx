import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Course, Question } from "../api/types";

interface QuestionFormState {
  editingId: number | null;
  text: string;
  imageMediaId: string | null;
  imageUrl: string | null;
  audioMediaId: string | null;
  audioUrl: string | null;
  options: [string, string, string, string];
  correctIndex: number;
}

const EMPTY_FORM: QuestionFormState = {
  editingId: null,
  text: "",
  imageMediaId: null,
  imageUrl: null,
  audioMediaId: null,
  audioUrl: null,
  options: ["", "", "", ""],
  correctIndex: 0,
};

export function CourseEditorPage() {
  const { courseId } = useParams();
  const numericId = Number(courseId);

  const [course, setCourse] = useState<Course | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Поля курса
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [coverMediaId, setCoverMediaId] = useState<string | null>(null);
  const [coverUrl, setCoverUrl] = useState<string | null>(null);
  const [savingCourse, setSavingCourse] = useState(false);

  // Форма вопроса
  const [qForm, setQForm] = useState<QuestionFormState>(EMPTY_FORM);
  const [uploadingMedia, setUploadingMedia] = useState(false);
  const [savingQuestion, setSavingQuestion] = useState(false);

  useEffect(() => {
    if (!Number.isFinite(numericId)) {
      setError("Некорректный ID курса");
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([api.getCourse(numericId), api.getCourseQuestions(numericId)])
      .then(([courseData, questionsData]) => {
        if (cancelled) return;
        setCourse(courseData);
        setTitle(courseData.title);
        setDescription(courseData.description);
        setCoverMediaId(courseData.cover_media_id ?? null);
        setCoverUrl(courseData.cover_url);
        setQuestions(questionsData);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Не удалось загрузить курс");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [numericId]);

  const handleUploadCover = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingMedia(true);
    setError(null);
    try {
      const media = await api.uploadMedia(file);
      setCoverMediaId(media.id);
      setCoverUrl(media.url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось загрузить обложку");
    } finally {
      setUploadingMedia(false);
      e.target.value = "";
    }
  };

  const handleSaveCourse = async (e: FormEvent) => {
    e.preventDefault();
    if (!course) return;

    setSavingCourse(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await api.updateCourse(course.id, {
        title: title.trim(),
        description: description.trim(),
        cover_media_id: coverMediaId,
      });
      setCourse(updated);
      setCoverUrl(updated.cover_url);
      setSuccess("Настройки курса сохранены");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось сохранить курс");
    } finally {
      setSavingCourse(false);
    }
  };

  const handleTogglePublish = async () => {
    if (!course) return;
    setSavingCourse(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await api.updateCourse(course.id, {
        is_published: !course.is_published,
      });
      setCourse(updated);
      setSuccess(updated.is_published ? "Курс опубликован" : "Курс переведён в черновики");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось изменить статус публикации");
    } finally {
      setSavingCourse(false);
    }
  };

  const handleUploadQuestionMedia = async (e: ChangeEvent<HTMLInputElement>, kind: "image" | "audio") => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingMedia(true);
    setError(null);
    try {
      const media = await api.uploadMedia(file);
      setQForm((prev) =>
        kind === "image"
          ? { ...prev, imageMediaId: media.id, imageUrl: media.url }
          : { ...prev, audioMediaId: media.id, audioUrl: media.url }
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось загрузить файл");
    } finally {
      setUploadingMedia(false);
      e.target.value = "";
    }
  };

  const handleOptionChange = (index: number, value: string) => {
    setQForm((prev) => {
      const next: [string, string, string, string] = [...prev.options] as [string, string, string, string];
      next[index] = value;
      return { ...prev, options: next };
    });
  };

  const handleSaveQuestion = async (e: FormEvent) => {
    e.preventDefault();
    if (!course) return;

    if (!qForm.text.trim()) {
      setError("Введите текст вопроса");
      return;
    }
    if (qForm.options.some((opt) => !opt.trim())) {
      setError("Заполните все 4 варианта ответа");
      return;
    }

    setSavingQuestion(true);
    setError(null);
    setSuccess(null);

    const payload = {
      text: qForm.text.trim(),
      image_media_id: qForm.imageMediaId,
      audio_media_id: qForm.audioMediaId,
      options: qForm.options.map((text, idx) => ({
        text: text.trim(),
        is_correct: idx === qForm.correctIndex,
      })),
    };

    try {
      if (qForm.editingId !== null) {
        const updated = await api.updateQuestion(qForm.editingId, payload);
        setQuestions((prev) => prev.map((q) => (q.id === updated.id ? updated : q)));
        setSuccess("Вопрос обновлён");
      } else {
        const created = await api.createQuestion(course.id, payload);
        setQuestions((prev) => [...prev, created]);
        setSuccess("Вопрос добавлен");
      }
      setQForm(EMPTY_FORM);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось сохранить вопрос");
    } finally {
      setSavingQuestion(false);
    }
  };

  const startEditQuestion = (q: Question) => {
    const texts: [string, string, string, string] = [
      q.options[0]?.text ?? "",
      q.options[1]?.text ?? "",
      q.options[2]?.text ?? "",
      q.options[3]?.text ?? "",
    ];
    const correctIdx = Math.max(
      0,
      q.options.findIndex((o) => o.is_correct)
    );

    setQForm({
      editingId: q.id,
      text: q.text,
      imageMediaId: q.image_media_id ?? null,
      imageUrl: q.image_url,
      audioMediaId: q.audio_media_id ?? null,
      audioUrl: q.audio_url,
      options: texts,
      correctIndex: correctIdx,
    });
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  };

  const handleDeleteQuestion = async (questionId: number) => {
    if (!window.confirm("Удалить этот вопрос?")) return;
    setError(null);
    setSuccess(null);
    try {
      await api.deleteQuestion(questionId);
      setQuestions((prev) => prev.filter((q) => q.id !== questionId));
      if (qForm.editingId === questionId) {
        setQForm(EMPTY_FORM);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось удалить вопрос");
    }
  };

  if (loading) {
    return (
      <div className="container">
        <div className="empty-state">Загружаем редактор...</div>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="container">
        <div className="alert alert-error">{error ?? "Курс не найден"}</div>
        <Link to="/creator" className="btn btn-secondary">
          Назад в кабинет
        </Link>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Редактор курса</h1>
          <p className="page-subtitle">
            {course.title} ·{" "}
            {course.is_published ? (
              <span className="badge badge-green">Опубликован</span>
            ) : (
              <span className="badge badge-yellow">Черновик</span>
            )}
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button
            type="button"
            className="btn btn-primary"
            disabled={savingCourse}
            onClick={handleTogglePublish}
          >
            {course.is_published ? "Снять с публикации" : "Опубликовать курс"}
          </button>
          <Link to={`/creator/courses/${course.id}/stats`} className="btn btn-secondary">
            Статистика
          </Link>
          <Link to="/creator" className="btn btn-secondary">
            ← К моим курсам
          </Link>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {/* Настройки курса */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h2 style={{ marginTop: 0, fontSize: 18 }}>Основные данные курса</h2>
        <form className="form-stack" onSubmit={handleSaveCourse}>
          <div className="field">
            <label htmlFor="edit-title">Название</label>
            <input
              id="edit-title"
              className="input"
              type="text"
              required
              minLength={3}
              maxLength={200}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="edit-desc">Описание</label>
            <textarea
              id="edit-desc"
              className="textarea"
              maxLength={5000}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div className="field">
            <label>Обложка (JPEG, PNG, WebP до 5 МБ)</label>
            {coverUrl && (
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                <img
                  src={coverUrl}
                  alt="Обложка"
                  style={{ width: 120, height: 72, objectFit: "cover", borderRadius: 8, border: "1px solid var(--border)" }}
                />
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    setCoverMediaId(null);
                    setCoverUrl(null);
                  }}
                >
                  Убрать обложку
                </button>
              </div>
            )}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={uploadingMedia}
              onChange={handleUploadCover}
            />
          </div>

          <div>
            <button type="submit" className="btn btn-primary" disabled={savingCourse || uploadingMedia}>
              {savingCourse ? "Сохраняем..." : "Сохранить настройки"}
            </button>
          </div>
        </form>
      </div>

      {/* Список вопросов */}
      <h2 style={{ fontSize: 20, marginBottom: 14 }}>Вопросы курса ({questions.length})</h2>

      {questions.length === 0 ? (
        <div className="card empty-state" style={{ marginBottom: 24 }}>
          Вопросов пока нет. Добавьте хотя бы один вопрос, чтобы опубликовать курс.
        </div>
      ) : (
        <div className="form-stack" style={{ marginBottom: 28 }}>
          {questions.map((q, idx) => (
            <div key={q.id} className="card">
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
                <strong>Вопрос {idx + 1}</strong>
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => startEditQuestion(q)}
                  >
                    Изменить
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    onClick={() => handleDeleteQuestion(q.id)}
                  >
                    Удалить
                  </button>
                </div>
              </div>

              <p style={{ fontSize: 16, margin: "10px 0" }}>{q.text}</p>

              {q.image_url && <img src={q.image_url} alt="Фото вопроса" className="question-media-img" />}
              {q.audio_url && <audio controls src={q.audio_url} className="question-media-audio" />}

              <ul style={{ margin: "10px 0 0", paddingLeft: 20 }}>
                {q.options.map((opt) => (
                  <li
                    key={opt.id}
                    style={{
                      color: opt.is_correct ? "var(--success)" : "var(--text-main)",
                      fontWeight: opt.is_correct ? 700 : 400,
                      marginBottom: 4,
                    }}
                  >
                    {opt.text} {opt.is_correct ? "✓" : ""}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {/* Форма добавления / редактирования вопроса */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>
            {qForm.editingId !== null ? "Редактировать вопрос" : "Добавить вопрос"}
          </h2>
          {qForm.editingId !== null && (
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setQForm(EMPTY_FORM)}>
              Отменить редактирование
            </button>
          )}
        </div>

        <form className="form-stack" onSubmit={handleSaveQuestion}>
          <div className="field">
            <label htmlFor="q-text">Текст вопроса</label>
            <textarea
              id="q-text"
              className="textarea"
              required
              maxLength={1000}
              placeholder="Например: Кто крестил Русь в 988 году?"
              value={qForm.text}
              onChange={(e) => setQForm((prev) => ({ ...prev, text: e.target.value }))}
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16 }}>
            <div className="field">
              <label>Фото к вопросу (необязательно, до 5 МБ)</label>
              {qForm.imageUrl && (
                <div style={{ marginBottom: 8 }}>
                  <img
                    src={qForm.imageUrl}
                    alt="Превью"
                    style={{ maxHeight: 140, borderRadius: 8, border: "1px solid var(--border)", marginBottom: 6 }}
                  />
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setQForm((prev) => ({ ...prev, imageMediaId: null, imageUrl: null }))}
                  >
                    Убрать фото
                  </button>
                </div>
              )}
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                disabled={uploadingMedia}
                onChange={(e) => handleUploadQuestionMedia(e, "image")}
              />
            </div>

            <div className="field">
              <label>Аудио к вопросу (необязательно, MP3/OGG/WAV до 10 МБ)</label>
              {qForm.audioUrl && (
                <div style={{ marginBottom: 8 }}>
                  <audio controls src={qForm.audioUrl} style={{ width: "100%", marginBottom: 6 }} />
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setQForm((prev) => ({ ...prev, audioMediaId: null, audioUrl: null }))}
                  >
                    Убрать аудио
                  </button>
                </div>
              )}
              <input
                type="file"
                accept="audio/mpeg,audio/ogg,audio/wav"
                disabled={uploadingMedia}
                onChange={(e) => handleUploadQuestionMedia(e, "audio")}
              />
            </div>
          </div>

          <div className="field">
            <label>Варианты ответа (выберите точкой один правильный)</label>
            <div className="form-stack" style={{ gap: 10 }}>
              {qForm.options.map((optText, idx) => (
                <div key={idx} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <input
                    type="radio"
                    name="correct-option"
                    checked={qForm.correctIndex === idx}
                    onChange={() => setQForm((prev) => ({ ...prev, correctIndex: idx }))}
                    aria-label={`Сделать вариант ${idx + 1} правильным`}
                  />
                  <input
                    className="input"
                    type="text"
                    required
                    maxLength={300}
                    placeholder={`Вариант ответа ${idx + 1}`}
                    value={optText}
                    onChange={(e) => handleOptionChange(idx, e.target.value)}
                  />
                </div>
              ))}
            </div>
          </div>

          <div>
            <button type="submit" className="btn btn-primary" disabled={savingQuestion || uploadingMedia}>
              {savingQuestion
                ? "Сохраняем..."
                : qForm.editingId !== null
                  ? "Сохранить изменения"
                  : "Добавить вопрос"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}