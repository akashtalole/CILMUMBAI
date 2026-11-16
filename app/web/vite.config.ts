import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the API runs separately (uvicorn on :8000); in production the API serves this build at /.
const api = process.env.HISHOB_API ?? "http://127.0.0.1:8000";
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(["/places", "/point", "/views", "/facts", "/sources", "/ask"].map((p) => [p, api])),
  },
  build: { chunkSizeWarningLimit: 1200 },
});
