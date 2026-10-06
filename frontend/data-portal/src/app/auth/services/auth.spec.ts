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
import { NotificationService } from '@app/shared/services/notification';
import { AuthService } from './auth';

/**
 * Mock the config service as needed by the auth service
 */
class MockConfigService {
  authUrl = 'http://mock.dev/auth';
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
        { provide: NotificationService, useClass: MockNotificationService },
        provideRouter([
          { path: '', component: PageComponent, data: { name: 'home' } },
          { path: 'other', component: PageComponent, data: { name: 'other' } },
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
      const notify = TestBed.inject(
        NotificationService,
      ) as unknown as MockNotificationService;
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
});
