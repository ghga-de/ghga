/**
 * Create a mock service worker for the web browser
 *
 * The mock service worker is used to create mock responses for local testing.
 */

import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

export const worker = setupWorker(...handlers);
