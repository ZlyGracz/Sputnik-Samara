import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { AttemptDetail, AttemptQuestion } from "../api/types";

export function AttemptPage() {
  const { attemptId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const initialAttempt = (location.state as { initialAttempt?: AttemptDetail } | null)?.initialAttempt ?? null;

  const [attempt, setAttempt] = useState<AttemptDetail | null>(initialAttempt);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [loading, setLoading] = useState(!initialAttempt);
  const [error, setError] = useState<string | null>(null);
  const [answering, setAnswering] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [restarting, setRestarting] = useState(false);

  const numericId = Number(attemptId);

  useEffect(() => {
    if (!Number.isFinite(numericId)) {
      setError("Некорректный идентификатор попытки");
      setLoading(false);
      return;
    }

    if (initialAttempt && initialAttempt.id === numericId) {
      setAttempt(initialAttempt);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .getAttempt(numericId)
      .then((data) => {
        if (cancelled) return;
        setAttempt(data);
        const firstUnanswered = data.questions.findIndex((q) => q.selected_option_id === null);
        setCurrentIdx(firstUnanswered >= 0 ? firstUnanswered : 0);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Не удалось загрузить попытку");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [numericId, initialAttempt]);

  const handleSelectOption = async (question: AttemptQuestion, optionId: number) => {
    if (!attempt || attempt.status === "finished" || question.selected_option_id !== null || answering) {
      return;
    }

    setAnswering(true);
    setError(null);
    try {
      const result = await api.submitAnswer(attempt.id, {
        question_id: question.id,
        option_id: optionId,
      });

      setAttempt((prev) => {
        if (!prev) return prev;
        const updatedQuestions = prev.questions.map((q) =>
          q.id === question.id
            ? {
                ...q,
                selected_option_id: result.selected_option_id,
                is_correct: result.is_correct,
                correct_option_id: result.correct_option_id,
              }
            : q
        );
        const answeredCount = updatedQuestions.filter((q) => q.selected_option_id !== null).length;
        return {
          ...prev,
          answered_count: answeredCount,
          questions: updatedQuestions,
        };
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось отправить ответ");
    } finally {
      setAnswering(false);
    }
  };

  const handleFinish = async () => {
    if (!attempt || finishing) return;

    const unanswered = attempt.total_questions - attempt.answered_count;
    if (unanswered > 0) {
      const ok = window.confirm(
        `Остались вопросы без ответа (${unanswered}). Неотвеченные вопросы засчитываются как неверные. Завершить попытку?`
      );
      if (!ok) return;
    }

    setFinishing(true);
    setError(null);
    try {
      const finished = await api.finishAttempt(attempt.id);
      setAttempt(finished);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось завершить попытку");
    } finally {
      setFinishing(false);
    }
  };

  const handleRetryCourse = async () => {
    if (!attempt || restarting) return;
    setRestarting(true);
    setError(null);
    try {
      const nextAttempt = await api.startAttempt(attempt.course_id);
      setCurrentIdx(0);
      navigate(`/attempts/${nextAttempt.id}`, { state: { initialAttempt: nextAttempt } });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось начать новую попытку");
    } finally {
      setRestarting(false);
    }
  };

  if (loading) {
    return (
      <div className="container">
        <div className="empty-state">Загружаем тест...</div>
      </div>
    );
  }

  if (!attempt) {
    return (
      <div className="container">
        <div className="alert alert-error">{error ?? "Попытка не найдена"}</div>
        <Link to="/courses" className="btn btn-secondary">
          Вернуться к курсам
        </Link>
      </div>
    );
  }

  // Экран результатов после завершения попытки
  if (attempt.status === "finished") {
    const percentRounded = attempt.percent !== null ? Math.round(attempt.percent) : 0;

    return (
      <div className="container">
        <div className="page-header">
          <div>
            <h1 className="page-title">{attempt.course_title}</h1>
            <p className="page-subtitle">Попытка завершена</p>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button
              type="button"
              className="btn btn-primary"
              disabled={restarting}
              onClick={handleRetryCourse}
            >
              {restarting ? "Запускаем..." : "Пройти ещё раз"}
            </button>
            <Link to="/attempts" className="btn btn-secondary">
              Мои результаты
            </Link>
            <Link to="/courses" className="btn btn-secondary">
              К курсам
            </Link>
          </div>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">
              {attempt.score ?? 0} / {attempt.total_questions}
            </div>
            <div className="stat-label">Правильных ответов</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{percentRounded}%</div>
            <div className="stat-label">Итоговый результат</div>
          </div>
        </div>

        <div className="form-stack">
          {attempt.questions.map((q, index) => (
            <div key={q.id} className="card">
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
                <strong>Вопрос {index + 1}</strong>
                {q.selected_option_id === null ? (
                  <span className="badge badge-yellow">Без ответа</span>
                ) : q.is_correct ? (
                  <span className="badge badge-green">Верно</span>
                ) : (
                  <span className="badge badge-red">Неверно</span>
                )}
              </div>

              <p style={{ fontSize: 16, marginTop: 10, marginBottom: 8 }}>{q.text}</p>

              {q.image_url && <img src={q.image_url} alt="Иллюстрация к вопросу" className="question-media-img" />}
              {q.audio_url && <audio controls src={q.audio_url} className="question-media-audio" />}

              <div className="option-list">
                {q.options.map((opt) => {
                  let cls = "option-btn";
                  if (q.correct_option_id === opt.id) cls += " correct";
                  else if (q.selected_option_id === opt.id && q.is_correct === false) cls += " wrong";

                  return (
                    <button key={opt.id} type="button" className={cls} disabled>
                      <span>{opt.text}</span>
                      {q.correct_option_id === opt.id && <span>✓</span>}
                      {q.selected_option_id === opt.id && q.is_correct === false && <span>✕</span>}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const questions = attempt.questions;
  const currentQuestion = questions[currentIdx];

  if (!currentQuestion) {
    return (
      <div className="container">
        <div className="card empty-state">В этом курсе пока нет вопросов.</div>
      </div>
    );
  }

  const isAnswered = currentQuestion.selected_option_id !== null;
  const allAnswered = attempt.answered_count >= attempt.total_questions && attempt.total_questions > 0;

  return (
    <div className="container">
      <div className="page-header">
        <div>
          <h1 className="page-title">{attempt.course_title}</h1>
          <p className="page-subtitle">
            Отвечено: {attempt.answered_count} из {attempt.total_questions}
          </p>
        </div>
        <button
          type="button"
          className={allAnswered ? "btn btn-primary" : "btn btn-secondary"}
          disabled={finishing}
          onClick={handleFinish}
        >
          {finishing ? "Завершаем..." : "Завершить попытку"}
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Навигация по номерам вопросов */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 18 }}>
        {questions.map((q, idx) => {
          const isCurrent = idx === currentIdx;
          let bg = "#fff";
          let border = "var(--border)";
          let color = "var(--text-main)";

          if (q.selected_option_id !== null) {
            if (q.is_correct) {
              bg = "var(--success-bg)";
              border = "var(--success)";
              color = "var(--success)";
            } else {
              bg = "var(--danger-bg)";
              border = "var(--danger)";
              color = "var(--danger)";
            }
          }
          if (isCurrent) {
            border = "var(--blue-main)";
          }

          return (
            <button
              key={q.id}
              type="button"
              onClick={() => setCurrentIdx(idx)}
              style={{
                minWidth: 38,
                height: 38,
                borderRadius: 8,
                border: `2px solid ${border}`,
                background: bg,
                color,
                fontWeight: isCurrent ? 800 : 600,
                cursor: "pointer",
              }}
            >
              {idx + 1}
            </button>
          );
        })}
      </div>

      <div className="card">
        <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 8 }}>
          Вопрос {currentIdx + 1} из {questions.length}
        </div>

        <h2 style={{ marginTop: 0, fontSize: 20 }}>{currentQuestion.text}</h2>

        {currentQuestion.image_url && (
          <img
            src={currentQuestion.image_url}
            alt="Иллюстрация к вопросу"
            className="question-media-img"
          />
        )}

        {currentQuestion.audio_url && (
          <audio controls src={currentQuestion.audio_url} className="question-media-audio" />
        )}

        <div className="option-list">
          {currentQuestion.options.map((opt) => {
            let cls = "option-btn";
            if (isAnswered) {
              if (currentQuestion.correct_option_id === opt.id) cls += " correct";
              else if (currentQuestion.selected_option_id === opt.id && !currentQuestion.is_correct) cls += " wrong";
            }

            return (
              <button
                key={opt.id}
                type="button"
                className={cls}
                disabled={isAnswered || answering}
                onClick={() => handleSelectOption(currentQuestion, opt.id)}
              >
                <span>{opt.text}</span>
                {isAnswered && currentQuestion.correct_option_id === opt.id && <span>✓</span>}
                {isAnswered &&
                  currentQuestion.selected_option_id === opt.id &&
                  !currentQuestion.is_correct && <span>✕</span>}
              </button>
            );
          })}
        </div>

        {isAnswered && (
          <div
            className={`alert ${currentQuestion.is_correct ? "alert-success" : "alert-error"}`}
            style={{ marginTop: 18, marginBottom: 0 }}
          >
            {currentQuestion.is_correct ? "Правильный ответ!" : "Неверно. Правильный вариант выделен зелёным."}
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginTop: 22, flexWrap: "wrap" }}>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={currentIdx === 0}
            onClick={() => setCurrentIdx((i) => Math.max(0, i - 1))}
          >
            ← Предыдущий
          </button>

          {currentIdx < questions.length - 1 ? (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setCurrentIdx((i) => Math.min(questions.length - 1, i + 1))}
            >
              Следующий →
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-primary"
              disabled={finishing}
              onClick={handleFinish}
            >
              {finishing ? "Завершаем..." : "Завершить и увидеть результат"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}