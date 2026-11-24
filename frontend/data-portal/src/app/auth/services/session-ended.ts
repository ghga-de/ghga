/**
 * Interceptor for sessions that the backend has ended
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  HttpErrorResponse,
  HttpHandlerFn,
  HttpInterceptorFn,
  HttpRequest,
} from '@angular/common/http';
import { inject, Injector } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from './auth';

/**
 * Error details with which the auth adapter ends a session during an API call
 */
const SESSION_ENDED = new Map<string, { status: number; accountDisabled: boolean }>([
  ['User account has been deleted', { status: 401, accountDisabled: false }],
  ['Session has ended', { status: 401, accountDisabled: false }],
  ['User account is disabled', { status: 403, accountDisabled: true }],
]);

/**
 * Find out how the backend ended the session, if a failed API call says it did
 * @param error - the error of the failed API call
 * @returns the details of the ended session, or undefined if it was not ended
 */
function getSessionEnded(
  error: unknown,
): { status: number; accountDisabled: boolean } | undefined {
  if (!(error instanceof HttpErrorResponse)) return undefined;
  const ended = SESSION_ENDED.get(error.error?.detail);
  return ended && ended.status === error.status ? ended : undefined;
}

/**
 * Check whether an API call failed because the backend has ended the session
 *
 * The interceptor already tells the user why the session ended,
 * so callers can use this to skip their own error message.
 * @param error - the error of the failed API call
 * @returns true if the backend has ended the session
 */
export function isSessionEnded(error: unknown): boolean {
  return getSessionEnded(error) !== undefined;
}

/**
 * Forget the user when an API call fails because the backend has ended the session
 *
 * The error is passed on unchanged, so that callers still see the failed request.
 * @param req - the outgoing request object to handle
 * @param next - the next interceptor in the chain
 * @returns an observable of the HTTP event
 */
export const sessionEndedInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
) => {
  // the auth service sends requests itself, so it can only be injected lazily
  const injector = inject(Injector);
  return next(req).pipe(
    catchError((error: unknown) => {
      const ended = getSessionEnded(error);
      if (ended) {
        const authService = injector.get(AuthService);
        if (!authService.handlesSessionErrors(req.url)) {
          authService
            .sessionEnded(ended.accountDisabled)
            .catch((reason) => console.error('Failed to end the session:', reason));
        }
      }
      return throwError(() => error);
    }),
  );
};
