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
