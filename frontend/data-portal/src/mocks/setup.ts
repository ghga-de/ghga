/**
 * Mock service worker setup
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

/**
 * Create a mock service worker for the web browser
 *
 * The mock service worker is used to create mock responses for local testing.
 */

export const worker = setupWorker(...handlers);
