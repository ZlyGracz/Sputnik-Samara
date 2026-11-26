import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (fullName.trim().length < 2) {
      setError("Имя должно содержать минимум 2 символа");
      return;
    }
    if (password.length < 8) {
      setError("Пароль должен содержать минимум 8 символов");
      return;
    }

    setSubmitting(true);
    try {
      await register({
        full_name: fullName.trim(),
        email: email.trim(),
        password,
      });
      navigate("/courses", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось зарегистрироваться");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="container-narrow">
      <div className="card">
        <h1 className="page-title" style={{ marginBottom: 6 }}>
          Регистрация
        </h1>
        <p className="page-subtitle" style={{ marginBottom: 20 }}>
          Создайте аккаунт студента Самарского университета
        </p>

        {error && <div className="alert alert-error">{error}</div>}

        <form className="form-stack" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="reg-name">Имя и фамилия</label>
            <input
              id="reg-name"
              className="input"
              type="text"
              required
              minLength={2}
              maxLength={120}
              placeholder="Иван Петров"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="reg-email">Email</label>
            <input
              id="reg-email"
              className="input"
              type="email"
              required
              autoComplete="email"
              placeholder="student@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="reg-password">Пароль (от 8 символов)</label>
            <input
              id="reg-password"
              className="input"
              type="password"
              required
              minLength={8}
              maxLength={72}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
            {submitting ? "Создаём аккаунт..." : "Зарегистрироваться"}
          </button>
        </form>

        <p style={{ marginTop: 18, marginBottom: 0, fontSize: 14, color: "var(--text-muted)", textAlign: "center" }}>
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </p>
      </div>
    </div>
  );
}