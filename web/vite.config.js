import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base '/' — the site is served from the domain root (CNAME / Pages).
export default defineConfig({
  base: '/',
  plugins: [react()],
})
