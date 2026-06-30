import { defineConfig } from 'vitest/config';

// This file is only used when running `ng test --ui`.
// It allows the Vitest UI server (Vite) to be reachable from devcontainers/port-forwarding.
export default defineConfig({
  server: {
    host: '0.0.0.0',
  },
});
