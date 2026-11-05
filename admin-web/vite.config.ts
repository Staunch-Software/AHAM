/// <reference types="vitest" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000' } },
  // `env` pins the Google key to empty so a developer's real admin-web/.env.local never changes test results
  test: { environment: 'jsdom', globals: true, setupFiles: ['./src/test/setup.ts'], css: false, env: { VITE_GOOGLE_MAPS_API_KEY: '' } },
})
