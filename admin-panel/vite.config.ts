/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// De beheeromgeving en rapporten worden geserveerd via FastAPI (zie main.py).
// Bij build worden assets geserveerd via /static/admin-panel/ zodat rapportages
// onder /rapport/* WAF-onafhankelijk van /admin/* blijven (#290).
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/static/admin-panel/' : '/',
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'build',
    sourcemap: false,
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts',
  },
}));
