/**
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
} from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

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
 * Custom CSRF Interceptor
 */
@Injectable()
export class CsrfInterceptor implements HttpInterceptor {
  #csrf = inject(CsrfService);

  /**
   * Intercept all HTTP requests and add the CSRF token if needed
   * @param req the outgoing request object to handle
   * @param next the next interceptor in the chain
   * @returns an observable of the HTTP event
   */
  intercept(
    req: HttpRequest<unknown>,
    next: HttpHandler,
  ): Observable<HttpEvent<unknown>> {
    const method = req.method;
    if (method && /^(POST|PUT|PATCH|DELETE)$/.test(method)) {
      const csrfToken = this.#csrf.token;
      if (csrfToken) {
        req = req.clone({ setHeaders: { 'X-CSRF-Token': csrfToken } });
      }
    }
    return next.handle(req);
  }
}
