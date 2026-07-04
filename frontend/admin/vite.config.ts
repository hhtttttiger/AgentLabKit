import { fileURLToPath, URL } from 'node:url';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:5291';
  const voicesTarget = env.VITE_VOICES_PROXY_TARGET || apiTarget;

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) {
              return undefined;
            }

            if (
              id.includes('@xyflow')
              || id.includes('dagre')
              || id.includes('@dnd-kit')
            ) {
              return 'graph-vendor';
            }

            if (id.includes('@microsoft/signalr')) {
              return 'realtime-vendor';
            }

            if (id.includes('react') || id.includes('react-dom')) {
              return 'react-vendor';
            }

            if (id.includes('react-router')) {
              return 'router-vendor';
            }

            if (id.includes('@tanstack/react-query')) {
              return 'query-vendor';
            }

            if (id.includes('i18next') || id.includes('react-i18next')) {
              return 'i18n-vendor';
            }

            if (id.includes('zustand')) {
              return 'zustand-vendor';
            }

            if (id.includes('lucide-react')) {
              return 'icons-vendor';
            }
          },
        },
      },
    },
    server: {
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/realtime': {
          target: voicesTarget,
          changeOrigin: true,
          ws: true,
        },
      },
    },
  };
});
