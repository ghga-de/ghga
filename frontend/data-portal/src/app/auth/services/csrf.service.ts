/**
 * CSRF interceptor
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpHandlerFn, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

/**
 * A tiny service that just holds the CSRF token
 *
 * This is used by both the auth service and the CSRF interceptor.
 */
@Injectable({ providedIn: 'root' })
export class CsrfService {
  token: string | null = null;
}

/**
 * Intercept all HTTP requests and add the CSRF token if needed
 * @param req the outgoing request object to handle
 * @param next the next interceptor in the chain
 * @returns an observable of the HTTP event
 */
export const csrfInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
) => {
  const method = req.method;
  if (method && /^(POST|PUT|PATCH|DELETE)$/.test(method)) {
    const csrfService = inject(CsrfService);
    const csrfToken = csrfService.token;
    if (csrfToken) {
      req = req.clone({ headers: req.headers.set('X-Csrf-Token', csrfToken) });
    }
  }
  return next(req);
};
