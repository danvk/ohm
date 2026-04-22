import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

declare const process: { env: Record<string, string> };

// https://vitejs.dev/config/
export default defineConfig({
  base: process.env.WHM ? '/whm3/' : '/ohm/',
  plugins: [react()],
});
