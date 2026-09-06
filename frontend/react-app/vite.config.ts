import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: `http://127.0.0.1:${process.env.VITE_BACKEND_PORT ?? "8000"}`,
        changeOrigin: true,
      },
    },
  },
});
