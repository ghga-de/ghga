/**
 * Mock service worker setup
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { isCommonAssetRequest } from 'msw';
import { setupWorker, type StartOptions } from 'msw/browser';
import { HttpNetworkFrame } from 'msw/experimental';
import { handlers } from './handlers';

/**
 * Create a mock service worker for the web browser
 *
 * The mock service worker is used to create mock responses for local testing.
 */

export const worker = setupWorker(...handlers);

/**
 * Options for starting the mock service worker
 */
export const startOptions: StartOptions = {
  /**
   * Warn about unhandled requests other than page navigations and static assets
   *
   * Only API requests are mocked, so app routes, the OIDC redirect, fonts and
   * the like pass through silently.
   * @param args the unhandled frame and the default strategies
   * @param args.frame the unhandled network frame
   * @param args.defaults the default strategies for unhandled frames
   */
  onUnhandledFrame({ frame, defaults }) {
    if (!(frame instanceof HttpNetworkFrame)) return defaults.warn();
    const { request } = frame.data;
    if (request.mode !== 'navigate' && !isCommonAssetRequest(request)) defaults.warn();
  },
};
