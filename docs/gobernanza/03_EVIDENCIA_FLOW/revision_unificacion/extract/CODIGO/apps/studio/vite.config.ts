import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath } from 'node:url';

// El módulo virtual `flow-sdk` del entorno de Flow se resuelve a un stub simulado:
// la generación con proveedores externos queda desactivada en este entorno local.
//
// `base: '/studio/'` permite que el build del Studio se sirva bajo el mismo
// origen que neural.news (Next lo publica en /public/studio-app), de modo que la
// cookie de sesión (HttpOnly, SameSite=lax) acompaña a todas las llamadas sin
// depender de otro servidor ni de otro origen.
//
// El API editorial se sirve por proxy en desarrollo; en producción (mismo origen)
// el Studio llama a /api de neural.news directamente.
const apiProxy = {
  '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
};

export default defineConfig({
  base: '/studio/',
  plugins: [react(), tailwindcss()],
  server: { proxy: apiProxy },
  preview: { proxy: apiProxy },
  resolve: {
    alias: {
      'flow-sdk': fileURLToPath(new URL('./src/flow-sdk/index.ts', import.meta.url)),
    },
  },
  build: {
    outDir: '../web/public/studio',
    emptyOutDir: true,
  },
});
