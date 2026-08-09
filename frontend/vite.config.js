import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // Frontend calls /api/* directly; Vite forwards to FastAPI in dev so
      // there's no CORS dance and no hardcoded backend URL in client code.
      '/api': 'http://localhost:8000',
    },
  },
})
