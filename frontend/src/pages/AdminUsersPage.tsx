import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { Role, User } from "../api/types";
import { useAuth } from "../context/AuthContext";

const ROLE_OPTIONS: { value: Role; label: string }[] = [
  { value: "user", label: "Студент (user)" },
  { value: "creator", label: "Создатель (creator)" },
  { value: "admin", label: "Админ (admin)" },
];

export function AdminUsersPage() {
  const { user: currentUser } = useAuth();

  const [users, setUsers] = useState<User[]>([]);
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<Role | "">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .getUsers({
        search: searchQuery || undefined,
        role: roleFilter || undefined,
        limit: 100,
        offset: 0,
      })
      .then((page) => {
        if (!cancelled) setUsers(page.items);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Не удалось загрузить пользователей");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [searchQuery, roleFilter]);

  const handleSearch = (e: FormEvent) => {
    e.preventDefault();
    setSearchQuery(searchInput.trim());
  };

  const handleRoleChange = async (target: User, newRole: Role) => {
    setBusyId(target.id);
    setError(null);
    try {
      const updated = await api.updateUser(target.id, { role: newRole });
      setUsers((prev) => prev.map((u) => (u.id === target.id ? updated : u)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось обновить роль");
    } finally {
      setBusyId(null);
    }
  };

  const handleToggleActive = async (target: User) => {
    setBusyId(target.id);
    setError(null);
    try {
      const updated = await api.updateUser(target.id, { is_active: !target.is_active });
      setUsers((prev) => prev.map((u) => (u.id === target.id ? updated : u)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось изменить статус блокировки");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Админ-панель</h1>
          <p className="page-subtitle">Управление пользователями, ролями и доступом</p>
        </div>
      </div>

      <form className="toolbar" onSubmit={handleSearch}>
        <input
          className="input"
          type="search"
          placeholder="Поиск по имени или email..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        <select
          className="select"
          style={{ width: "auto", minWidth: 180 }}
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value as Role | "")}
        >
          <option value="">Все роли</option>
          {ROLE_OPTIONS.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
        <button type="submit" className="btn btn-primary">
          Найти
        </button>
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="empty-state">Загружаем пользователей...</div>
      ) : users.length === 0 ? (
        <div className="card empty-state">Пользователи не найдены.</div>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Имя</th>
                <th>Email</th>
                <th>Роль</th>
                <th>Статус</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isSelf = currentUser?.id === u.id;
                const isBusy = busyId === u.id;

                return (
                  <tr key={u.id}>
                    <td>{u.id}</td>
                    <td>
                      <strong>{u.full_name}</strong> {isSelf && <span className="badge badge-blue">Вы</span>}
                    </td>
                    <td>{u.email}</td>
                    <td>
                      <select
                        className="select"
                        style={{ padding: "6px 10px", fontSize: 13 }}
                        value={u.role}
                        disabled={isSelf || isBusy}
                        onChange={(e) => handleRoleChange(u, e.target.value as Role)}
                      >
                        {ROLE_OPTIONS.map((r) => (
                          <option key={r.value} value={r.value}>
                            {r.label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      {u.is_active ? (
                        <span className="badge badge-green">Активен</span>
                      ) : (
                        <span className="badge badge-red">Заблокирован</span>
                      )}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <button
                        type="button"
                        className={u.is_active ? "btn btn-danger btn-sm" : "btn btn-secondary btn-sm"}
                        disabled={isSelf || isBusy}
                        onClick={() => handleToggleActive(u)}
                      >
                        {u.is_active ? "Заблокировать" : "Разблокировать"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}