import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// dev：vite 跑在 5173，/api 代理到 Flask 后端（python -m stocklook.webapp，8000 端口）
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 600,
  },
})