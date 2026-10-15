import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Used only for `npm run dev`. In Docker, nginx does this proxying (see nginx.conf).
// The services must be running (docker compose up) so these ports are published.
const proxy = (target, prefix) => ({
  target,
  changeOrigin: true,
  rewrite: (path) => path.replace(new RegExp(`^${prefix}`), ""),
});

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api/tx": proxy("http://localhost:8001", "/api/tx"),
      "/api/anomaly": proxy("http://localhost:8003", "/api/anomaly"),
      "/api/agent": proxy("http://localhost:8004", "/api/agent"),
    },
  },
});