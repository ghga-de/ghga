/**
 * Setup Jest for Angular
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

// setup-jest.ts
import { setupZonelessTestEnv } from 'jest-preset-angular/setup-env/zoneless';

// add extended jest matchers
import '@testing-library/jest-dom';

// suppress console output during tests
global.console = {
  ...console,
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
};

// configure a test environment that doesn't use zone.js
setupZonelessTestEnv();

// Minimal polyfills for browser APIs used by deferrable views during tests
if (!(globalThis as any).IntersectionObserver) {
  (globalThis as any).IntersectionObserver = class {
    observe = (): void => {};
    unobserve = (): void => {};
    disconnect = (): void => {};
    takeRecords = (): unknown[] => {
      return [];
    };
  };
}

// Ensure idle callbacks exist; Angular will fall back to setTimeout if absent,
// but providing a minimal shim makes idle defers deterministic.
if (!(globalThis as any).requestIdleCallback) {
  (globalThis as any).requestIdleCallback = (
    cb: (deadline: { didTimeout: boolean; timeRemaining: () => number }) => void,
  ) => cb({ didTimeout: false, timeRemaining: () => 50 });
}
if (!(globalThis as any).cancelIdleCallback) {
  (globalThis as any).cancelIdleCallback = () => {};
}
