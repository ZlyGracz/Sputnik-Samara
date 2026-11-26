import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const ROLE_LABELS: Record<string, string> = {
  user: "Студент",
  creator: "Создатель курсов",
  admin: "Администратор",
};

export function Layout() {
  const { user, logout } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const navigate = useNavigate();

  const close = () => setDrawerOpen(false);

  const handleLogout = () => {
    logout();
    close();
    navigate("/");
  };

  const canCreate = user?.role === "creator" || user?.role === "admin";
  const isAdmin = user?.role === "admin";

  return (
    <>
      <header className="topbar">
        <div className="topbar-left">
          <button
            type="button"
            className="icon-btn"
            aria-label="Открыть меню"
            onClick={() => setDrawerOpen(true)}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <Link to="/" className="topbar-brand">
            Спутник
          </Link>
        </div>

        <div className="topbar-right">
          {user ? (
            <div className="topbar-user">
              <span className="topbar-user-name">{user.full_name}</span>
              <button
                type="button"
                className="icon-btn"
                title={`${user.full_name} (${ROLE_LABELS[user.role] ?? user.role})`}
                aria-label="Профиль"
                onClick={() => setDrawerOpen(true)}
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 12c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm0 2c-3.33 0-10 1.67-10 5v3h20v-3c0-3.33-6.67-5-10-5z" />
                </svg>
              </button>
            </div>
          ) : (
            <Link to="/login" className="icon-btn" title="Войти" aria-label="Войти">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 12c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm0 2c-3.33 0-10 1.67-10 5v3h20v-3c0-3.33-6.67-5-10-5z" />
              </svg>
            </Link>
          )}
        </div>
      </header>

      {drawerOpen && (
        <>
          <div className="drawer-backdrop" onClick={close} />
          <aside className="drawer" aria-label="Навигация">
            <div className="drawer-header">
              <span className="drawer-title">Спутник</span>
              <button type="button" className="drawer-close" onClick={close} aria-label="Закрыть меню">
                ×
              </button>
            </div>

            <nav className="drawer-nav">
              <NavLink to="/" end className={({ isActive }) => `drawer-link${isActive ? " active" : ""}`} onClick={close}>
                Главная
              </NavLink>
              <NavLink to="/courses" className={({ isActive }) => `drawer-link${isActive ? " active" : ""}`} onClick={close}>
                Каталог курсов
              </NavLink>
              {user && (
                <NavLink to="/attempts" className={({ isActive }) => `drawer-link${isActive ? " active" : ""}`} onClick={close}>
                  Мои результаты
                </NavLink>
              )}
              {canCreate && (
                <NavLink to="/creator" className={({ isActive }) => `drawer-link${isActive ? " active" : ""}`} onClick={close}>
                  Кабинет создателя
                </NavLink>
              )}
              {isAdmin && (
                <NavLink to="/admin" className={({ isActive }) => `drawer-link${isActive ? " active" : ""}`} onClick={close}>
                  Админ-панель
                </NavLink>
              )}
            </nav>

            <div className="drawer-footer">
              {user ? (
                <>
                  <div style={{ fontSize: 14 }}>
                    <strong>{user.full_name}</strong>
                    <div style={{ color: "var(--text-muted)", fontSize: 12 }}>
                      {user.email} · {ROLE_LABELS[user.role] ?? user.role}
                    </div>
                  </div>
                  <button type="button" className="btn btn-secondary btn-block" onClick={handleLogout}>
                    Выйти
                  </button>
                </>
              ) : (
                <>
                  <Link to="/login" className="btn btn-primary btn-block" onClick={close}>
                    Войти
                  </Link>
                  <Link to="/register" className="btn btn-secondary btn-block" onClick={close}>
                    Регистрация
                  </Link>
                </>
              )}
            </div>
          </aside>
        </>
      )}

      <main>
        <Outlet />
      </main>
    </>
  );
}