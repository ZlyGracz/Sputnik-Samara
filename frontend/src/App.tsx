import { useEffect, useState } from "react";

type Status = "loading" | "ok" | "error";

// Заглушка: проверяет связь фронтенда с бэкендом. Заменить реальными страницами.
export default function App() {
  const [status, setStatus] = useState<Status>("loading");

  useEffect(() => {
    fetch("/api/health")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => setStatus(d.status === "ok" ? "ok" : "error"))
      .catch(() => setStatus("error"));
  }, []);

  return (
    <main style={{ padding: "2rem" }}>
      <h1>Спутник Самарского университета</h1>
      <p>
        Связь с бэкендом:{" "}
        {status === "loading" && "проверяем…"}
        {status === "ok" && "работает ✅"}
        {status === "error" && "нет связи ❌"}
      </p>
    </main>
  );
}
