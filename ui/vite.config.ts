import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The build lands inside the Python package so the wheel serves it (ADR 0008).
export default defineConfig({
  plugins: [react()],
  build: { outDir: '../src/flight_recorder/static', emptyOutDir: true },
  server: { port: 5321, strictPort: true, proxy: { '/api': 'http://127.0.0.1:5320' } },
})
