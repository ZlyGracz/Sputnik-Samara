import { Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../context/AuthContext";
import type { Role } from "../api/types";

interface ProtectedRouteProps {
  children: ReactNode;
  roles?: Role[];
}

export function ProtectedRoute({ children, roles }: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="container">
        <div className="empty-state">Загрузка...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  if (roles && !roles.includes(user.role)) {
    return (
      <div className="container">
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Недостаточно прав</h2>
          <p style={{ color: "var(--text-muted)" }}>
            У вашей учётной записи нет доступа к этому разделу.
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}