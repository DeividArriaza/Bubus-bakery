import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Fuera de Compose apunta a la API publicada en el host; Compose define API_PROXY_TARGET=http://api:8000.
export function apiProxyTarget(env: Record<string, string | undefined>) {
  return env.API_PROXY_TARGET?.trim() || "http://127.0.0.1:8100";
}

export default defineConfig({
  plugins: [react()],
  server: { host: "0.0.0.0", port: 5173, proxy: { "/api": apiProxyTarget(process.env) } },
  test: { environment: "jsdom", setupFiles: "./src/test-setup.ts" },
});
