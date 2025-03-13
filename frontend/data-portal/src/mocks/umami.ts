/**
 * Mock the Umami tracker
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { http, RequestHandler } from 'msw';

const CONFIG = window.config;
let umamiUrl = CONFIG.umami_url;

umamiUrl = umamiUrl.slice(0, umamiUrl.indexOf('/', 8)) || 'http://umami.dev';
umamiUrl += '/*';

export const umamiHandler: RequestHandler = http.post(
  umamiUrl,
  async ({ request }: { request: Request }) => {
    const body = await request.json();
    const payload = body.payload;
    console.debug('Umami tracker called with this payload:', payload);
  },
);
