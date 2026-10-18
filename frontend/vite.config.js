import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, /api/* is proxied to the FastAPI server (default http://localhost:8101).
export default defineConfig({
  plugins: [react()],
  build: { sourcemap: true },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY || "http://localhost:8101",
        changeOrigin: true,
      },
    },
  },
});
