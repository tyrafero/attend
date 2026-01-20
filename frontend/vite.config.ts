import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // Use /static/frontend/ only in production build, / for development
  base: mode === 'production' ? '/static/frontend/' : '/',
  server: {
    host: true,
    port: 3002,
    strictPort: true,
    hmr: {
      clientPort: 3002,
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
}))
