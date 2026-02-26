import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

function normalizeBasePath(value: string) {
  if (!value || value === '/') return '/';
  const trimmed = value.replace(/^\/+|\/+$/g, '');
  return `/${trimmed}/`;
}

function normalizeApiPrefix(value: string) {
  if (!value || value === '/api') return '/api';
  const withLeadingSlash = value.startsWith('/') ? value : `/${value}`;
  return withLeadingSlash.replace(/\/+$/g, '');
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiPrefix = normalizeApiPrefix(env.VITE_LATEXLAB_API_PREFIX || '/api');
  const backendPort = Number(env.PORT || 8787);

  return {
    base: normalizeBasePath(env.VITE_LATEXLAB_BASE_PATH || '/'),
    plugins: [react()],
    server: {
      port: Number(env.VITE_PORT || 5173),
      proxy: {
        [apiPrefix]: {
          target: `http://localhost:${backendPort}`,
          changeOrigin: true,
          ws: true,
          xfwd: true,
          rewrite: (path) => {
            if (apiPrefix === '/api') return path;
            return `/api${path.slice(apiPrefix.length)}`;
          }
        },
        '/texlive': {
          target: 'https://texlive.swiftlatex.com',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/texlive/, '')
        }
      }
    }
  };
});
