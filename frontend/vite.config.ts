import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// В режиме разработки (`npm run dev`) запросы на /api уходят на бэкенд.
// По умолчанию — реальный бэкенд (docker compose, порт 8000).
// Для работы на mock-сервере по контракту: `npm run mock` и VITE_API_TARGET=http://127.0.0.1:4010
const target = process.env.VITE_API_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target, changeOrigin: true } },
  },
});
