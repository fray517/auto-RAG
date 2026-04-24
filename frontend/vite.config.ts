import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Загрузка VITE_* из .env в корне монорепозитория
  envDir: '..',
  server: {
    port: 3000,
  },
})
