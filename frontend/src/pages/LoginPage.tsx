import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from || "/courses";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login({ email: email.trim(), password });
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось выполнить вход");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="container-narrow">
      <div className="card">
        <h1 className="page-title" style={{ marginBottom: 6 }}>
          Вход
        </h1>
        <p className="page-subtitle" style={{ marginBottom: 20 }}>
          Войдите, чтобы проходить курсы и сохранять результаты
        </p>

        {error && <div className="alert alert-error">{error}</div>}

        <form className="form-stack" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="login-email">Email</label>
            <input
              id="login-email"
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
            <label htmlFor="login-password">Пароль</label>
            <input
              id="login-password"
              className="input"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
            {submitting ? "Входим..." : "Войти"}
          </button>
        </form>

        <p style={{ marginTop: 18, marginBottom: 0, fontSize: 14, color: "var(--text-muted)", textAlign: "center" }}>
          Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
        </p>
      </div>
    </div>
  );
}