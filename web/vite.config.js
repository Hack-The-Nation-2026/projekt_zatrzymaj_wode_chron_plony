import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // `npm run dev`: zapytania do API trafiają do serwera FastAPI (uvicorn na porcie 8000)
  server: {
    proxy: { "/api": "http://localhost:8000" },
  },
});
