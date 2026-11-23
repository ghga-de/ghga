/**
 * Test the interceptor for sessions that the backend has ended
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';
import { AuthService } from './auth';
import { sessionEndedInterceptor } from './session-ended';

const API_URL = 'http://mock.dev/api/some/path';

/**
 * Mock the auth service as needed by the interceptor
 */
class MockAuthService {
  sessionEnded = vitest.fn().mockResolvedValue(undefined);
  handlesSessionErrors = vitest.fn(() => false);
}

describe('sessionEndedInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let authService: MockAuthService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([sessionEndedInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
      ],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
  });

  afterEach(() => {
    httpMock.verify();
  });

  /**
   * Send a request that fails with the given status and detail
   * @param status - the status code of the response
   * @param detail - the detail in the response body
   * @returns the status of the error passed on to the caller
   */
  async function fail(status: number, detail: string): Promise<number> {
    const request = firstValueFrom(http.get(API_URL));
    httpMock.expectOne(API_URL).flush({ detail }, { status, statusText: 'Error' });
    try {
      await request;
    } catch (error) {
      return (error as { status: number }).status;
    }
    throw new Error('The request should have failed');
  }

  it('should forget the user when the account has been deleted', async () => {
    expect(await fail(401, 'User account has been deleted')).toBe(401);
    expect(authService.sessionEnded).toHaveBeenCalledExactlyOnceWith(false);
  });

  it('should forget the user when the session has ended', async () => {
    expect(await fail(401, 'Session has ended')).toBe(401);
    expect(authService.sessionEnded).toHaveBeenCalledExactlyOnceWith(false);
  });

  it('should forget the user and tell when the account is disabled', async () => {
    expect(await fail(403, 'User account is disabled')).toBe(403);
    expect(authService.sessionEnded).toHaveBeenCalledExactlyOnceWith(true);
  });

  it('should ignore other errors', async () => {
    expect(await fail(403, 'Not authorized')).toBe(403);
    expect(await fail(401, 'User account is disabled')).toBe(401);
    expect(authService.sessionEnded).not.toHaveBeenCalled();
  });

  it('should leave endpoints that handle session errors alone', async () => {
    authService.handlesSessionErrors.mockReturnValue(true);
    expect(await fail(401, 'Session has ended')).toBe(401);
    expect(authService.handlesSessionErrors).toHaveBeenCalledWith(API_URL);
    expect(authService.sessionEnded).not.toHaveBeenCalled();
  });
});
