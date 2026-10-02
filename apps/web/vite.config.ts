import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: { rollupOptions: { input: { main: "index.html", jobAnalysis: "src/features/job-analysis/demo.html" } } },
  server: { port: 5173, proxy: { "/api/f04": "http://127.0.0.1:8000" } },
});
