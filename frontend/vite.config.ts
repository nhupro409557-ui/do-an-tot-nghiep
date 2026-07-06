import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig, loadEnv} from 'vite';

export default defineConfig(({mode}) => {
  const env = loadEnv(mode, '.', '');
  return {
    plugins: [react(), tailwindcss()],
    define: {
      'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY),
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modify - file watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id: string) {
            if (!id.includes('node_modules')) return undefined;
            if (id.includes('antd') || id.includes('@ant-design') || id.includes('@rc-component') || id.includes('/rc-') || id.includes('\\rc-')) return 'vendor-antd';
            if (id.includes('recharts') || id.includes('d3-')) return 'vendor-charts';
            if (id.includes('swiper')) return 'vendor-swiper';
            if (id.includes('motion')) return 'vendor-motion';
            if (id.includes('p5')) return 'vendor-p5';
            if (id.includes('leaflet')) return 'vendor-maps';
            if (id.includes('lucide-react')) return 'vendor-icons';
            return undefined;
          },
        },
      },
    },
  };
});
