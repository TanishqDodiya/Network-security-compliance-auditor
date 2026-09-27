import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Local dev: forward API calls to the backend so the frontend can use
    // same-origin relative URLs (matching production rewrites).
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
