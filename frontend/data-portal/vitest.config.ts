/**
 * Configure Vitest tests.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 *
 * Only needed when running Vitest directly.
 * Does not work for Angular specific tests.
 */

import { fileURLToPath } from 'url';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['setup-test.ts'],
    include: ['**/*.spec.ts'],
    reporters: ['default'],
    watch: false,
  },
  resolve: {
    alias: {
      '@app': fileURLToPath(new URL('./src/app', import.meta.url)),
    },
  },
});
