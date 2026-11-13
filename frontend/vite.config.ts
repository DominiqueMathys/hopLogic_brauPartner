import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

const proxyTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000'
const host = process.env.DEV_SERVER_HOST ?? '127.0.0.1'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host,
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
})
