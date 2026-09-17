import { fileURLToPath, URL } from 'node:url';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
  },
  build: {
    sourcemap: true,
    // Mapbox GL and Highcharts are large and rarely change. Splitting them out
    // keeps the app chunk small, so a code change does not force users to
    // re-download several hundred kilobytes of vendor bundle.
    rollupOptions: {
      output: {
        manualChunks: {
          mapbox: ['mapbox-gl', 'react-map-gl', '@mapbox/mapbox-gl-draw'],
          charts: ['highcharts', 'highcharts-react-official'],
          vendor: ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
    // mapbox-gl alone is ~1.9 MB before gzip and cannot be split further.
    // It is lazily loaded with the map routes, so it never blocks first paint.
    chunkSizeWarningLimit: 2100,
  },
});
