import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev-Proxy: /api → lokales FastAPI-Backend (Port 8140). In Produktion
// serviert FastAPI die gebaute SPA selbst, der Proxy wird dann nicht genutzt.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8140",
    },
  },
  build: {
    outDir: "dist",
  },
});
