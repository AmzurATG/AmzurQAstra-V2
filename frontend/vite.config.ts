import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@common': path.resolve(__dirname, './src/common'),
      '@features': path.resolve(__dirname, './src/features'),
    },
  },
  build: {
    outDir: '../backend/static',
    emptyOutDir: true,
  },
  server: {
    port: 3001,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      // FastAPI mounts screenshots at /screenshots (not under /api)
      '/screenshots': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
})
