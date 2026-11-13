/**
 * Test the auth service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { TestBed } from '@angular/core/testing';

import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { Component, inject } from '@angular/core';
import { ActivatedRoute, provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { ConfigService } from '@app/shared/services/config';
import { ConfirmationService } from '@app/shared/services/confirmation';
import { Notifier } from '@app/shared/services/notification';
import { User as OidcUser, UserManager as OidcUserManager } from 'oidc-client-ts';
import { AuthService } from './auth';

const LOGIN_URL = 'http://mock.dev/auth/rpc/login';
const VERIFY_TOTP_URL = 'http://mock.dev/auth/rpc/verify-totp';

const DISABLED = { detail: 'User account is disabled' };
const FORBIDDEN = { status: 403, statusText: 'Forbidden' };
const UNAUTHORIZED = { status: 401, statusText: 'Unauthorized' };

/**
 * Mock the config service as needed by the auth service
 */
class MockConfigService {
  authUrl = 'http://mock.dev/auth';
  contactUrl = 'https://contact.mock.dev/';
}

/**
 * Mock the notification service as needed by the auth service
 */
class MockNotificationService {
  showWarning = vitest.fn();
  showError = vitest.fn();
  showSuccess = vitest.fn();
}

/**
 * Mock the confirmation service as needed by the auth service
 */
class MockConfirmationService {
  confirm = vitest.fn();
}

/**
 * A page that shows the name from its route data
 */
@Component({ template: '{{ name }}' })
class PageComponent {
  protected name = inject(ActivatedRoute).snapshot.data['name'];
}

describe('AuthService', () => {
  let service: AuthService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ConfigService, useClass: MockConfigService },
        { provide: Notifier, useClass: MockNotificationService },
        { provide: ConfirmationService, useClass: MockConfirmationService },
        provideRouter([
          { path: '', component: PageComponent, data: { name: 'home' } },
          { path: 'other', component: PageComponent, data: { name: 'other' } },
          {
            path: 'confirm-totp',
            component: PageComponent,
            data: { name: 'confirm-totp' },
          },
          {
            path: 'protected',
            component: PageComponent,
            data: { name: 'protected' },
            canActivate: [() => inject(AuthService).guardAuthenticated()],
          },
        ]),
      ],
    });
    service = TestBed.inject(AuthService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('as a guard without a session', () => {
    let router: Router;

    beforeEach(() => {
      router = TestBed.inject(Router);
      const httpMock = TestBed.inject(HttpTestingController);
      httpMock
        .expectOne('http://mock.dev/auth/rpc/login')
        .flush(null, { status: 404, statusText: 'Not Found' });
      expect(service.sessionState()).toBe('LoggedOut');
    });

    it('should send a user who opens a protected route directly to the home page', async () => {
      const harness = await RouterTestingHarness.create();
      await harness.navigateByUrl('/protected');
      await harness.fixture.whenStable();
      expect(router.url).toBe('/');
      expect(harness.routeNativeElement).toHaveTextContent('home');
      const notify = TestBed.inject(Notifier) as unknown as MockNotificationService;
      expect(notify.showWarning).toHaveBeenCalledWith(
        'Please login to continue the requested action.',
      );
    });

    it('should keep a user who navigates to a protected route on the current route', async () => {
      const harness = await RouterTestingHarness.create('/other');
      expect(router.url).toBe('/other');
      await harness.navigateByUrl('/protected');
      await harness.fixture.whenStable();
      expect(router.url).toBe('/other');
      expect(harness.routeNativeElement).toHaveTextContent('other');
    });
  });
  describe('with a disabled account', () => {
    let httpMock: HttpTestingController;
    let notify: MockNotificationService;
    let confirmation: MockConfirmationService;

    beforeEach(() => {
      httpMock = TestBed.inject(HttpTestingController);
      notify = TestBed.inject(Notifier) as unknown as MockNotificationService;
      confirmation = TestBed.inject(
        ConfirmationService,
      ) as unknown as MockConfirmationService;
      vitest.spyOn(OidcUserManager.prototype, 'removeUser').mockResolvedValue();
    });

    afterEach(() => {
      httpMock.verify();
      vitest.restoreAllMocks();
    });

    it('should tell the user when the session cookie belongs to a disabled account', () => {
      httpMock.expectOne(LOGIN_URL).flush(DISABLED, FORBIDDEN);

      expect(service.sessionState()).toBe('LoggedOut');
      expect(confirmation.confirm).toHaveBeenCalledTimes(1);
      expect(confirmation.confirm.mock.calls[0][0].title).toBe('Account disabled');
      expect(String(confirmation.confirm.mock.calls[0][0].message)).toContain(
        'https://contact.mock.dev/',
      );
      expect(notify.showError).not.toHaveBeenCalled();
    });

    it('should tell the user when logging in to a disabled account', async () => {
      httpMock
        .expectOne(LOGIN_URL)
        .flush(null, { status: 404, statusText: 'Not Found' });
      vitest.spyOn(OidcUserManager.prototype, 'getUser').mockResolvedValue(null);
      vitest.spyOn(OidcUserManager.prototype, 'signinCallback').mockResolvedValue({
        profile: { sub: 'john@aai.org' },
        expired: false,
        access_token: 'some-access-token',
      } as unknown as OidcUser);

      await service.guardCallback();

      const request = httpMock.expectOne(LOGIN_URL);
      expect(request.request.headers.get('X-Authorization')).toBe(
        'Bearer some-access-token',
      );
      request.flush(DISABLED, FORBIDDEN);

      expect(service.sessionState()).toBe('LoggedOut');
      expect(confirmation.confirm).toHaveBeenCalledTimes(1);
      expect(notify.showError).not.toHaveBeenCalled();
    });

    it('should not take another 403 for a disabled account', () => {
      httpMock.expectOne(LOGIN_URL).flush({ detail: 'RBAC: access denied' }, FORBIDDEN);

      expect(service.sessionState()).toBe('LoggedOut');
      expect(confirmation.confirm).not.toHaveBeenCalled();
    });
  });

  describe('when verifying a TOTP code', () => {
    let httpMock: HttpTestingController;

    beforeEach(() => {
      httpMock = TestBed.inject(HttpTestingController);
      vitest.spyOn(OidcUserManager.prototype, 'removeUser').mockResolvedValue();
      const session = {
        ext_id: 'john@aai.org',
        id: 'some-user-id',
        name: 'John Doe',
        email: 'john@home.org',
        state: 'HasTotpToken',
        roles: [],
        csrf: 'some-csrf-token',
      };
      httpMock.expectOne(LOGIN_URL).flush(null, {
        status: 204,
        statusText: 'No Content',
        headers: { 'X-Session': JSON.stringify(session) },
      });
      expect(service.sessionState()).toBe('HasTotpToken');
    });

    afterEach(() => {
      httpMock.verify();
      vitest.restoreAllMocks();
    });

    /**
     * Verify a code while the backend answers as given
     * @param body - the body of the response
     * @param options - the status of the response
     * @param options.status - the status code
     * @param options.statusText - the status text
     * @returns the outcome of the verification
     */
    async function verify(
      body: object | null,
      options: { status: number; statusText: string },
    ): Promise<string> {
      const verification = service.verifyTotpCode('123456');
      await Promise.resolve();
      httpMock.expectOne(VERIFY_TOTP_URL).flush(body, options);
      return verification;
    }

    it('should report a verified code', async () => {
      expect(await verify(null, { status: 204, statusText: 'No Content' })).toBe(
        'verified',
      );
      expect(service.sessionState()).toBe('Authenticated');
    });

    it('should report an invalid code and keep the session', async () => {
      expect(await verify({ detail: 'Invalid TOTP code' }, UNAUTHORIZED)).toBe(
        'invalid',
      );
      expect(service.sessionState()).toBe('HasTotpToken');
    });

    it('should report a locked session and forget the user', async () => {
      expect(await verify({ detail: 'Too many failed attempts' }, UNAUTHORIZED)).toBe(
        'locked',
      );
      expect(service.sessionState()).toBe('LoggedOut');
    });

    it('should report a disabled account and forget the user', async () => {
      expect(await verify(DISABLED, FORBIDDEN)).toBe('disabled');
      expect(service.sessionState()).toBe('LoggedOut');
    });
  });
});
