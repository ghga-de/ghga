/**
 * User service tests
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { users } from '@app/../mocks/data';
import { ConfigService } from '@app/shared/services/config';
import { HttpCacheManager } from '@ngneat/cashew';
import { UserService } from './user';

/**
 * Mock ConfigService for testing
 */
class MockConfigService {
  authUrl = 'http://mock.dev/auth';
}

const USERS_URL = 'http://mock.dev/auth/users';

describe('UserService', () => {
  let service: UserService;
  let httpMock: HttpTestingController;
  let testBed: TestBed;

  const httpCache = {
    delete: vitest.fn(),
  };

  beforeEach(() => {
    httpCache.delete.mockClear();
    testBed = TestBed.configureTestingModule({
      providers: [
        UserService,
        { provide: ConfigService, useClass: MockConfigService },
        { provide: HttpCacheManager, useValue: httpCache },
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
      teardown: { destroyAfterEach: false },
    });
    service = TestBed.inject(UserService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should have users resource with default empty array', () => {
    expect(service.users.value()).toEqual([]);
  });

  it('should not request the users before they are loaded', () => {
    testBed.tick();
    httpMock.expectNone(USERS_URL);
    expect(service.users.isLoading()).toBe(false);
  });

  it('should request the users when they are loaded', async () => {
    service.loadUsers();
    expect(service.users.isLoading()).toBe(true);
    testBed.tick();
    const req = httpMock.expectOne(USERS_URL);
    expect(req.request.method).toBe('GET');
    req.flush(users);
    await Promise.resolve(); // wait for loader to return
    expect(service.users.isLoading()).toBe(false);
    expect(service.users.error()).toBeUndefined();
    expect(service.users.value().length).toBe(users.length);
    expect(service.users.value()[0].displayName).toBe('Dr. John Doe');
  });

  it('should request the users when reloading before the first load', async () => {
    // Reloading is what the User Manager does on initialization, so it must
    // start the first load instead of reloading a still idle resource.
    service.reloadUsers();
    expect(httpCache.delete).toHaveBeenCalledWith(USERS_URL);
    expect(service.users.isLoading()).toBe(true);
    testBed.tick();
    const req = httpMock.expectOne(USERS_URL);
    expect(req.request.method).toBe('GET');
    req.flush(users);
    await Promise.resolve(); // wait for loader to return
    expect(service.users.isLoading()).toBe(false);
    expect(service.users.error()).toBeUndefined();
    expect(service.users.value().length).toBe(users.length);
  });

  it('should request the users again when reloading after the first load', async () => {
    service.loadUsers();
    testBed.tick();
    httpMock.expectOne(USERS_URL).flush(users.slice(0, 1));
    await Promise.resolve(); // wait for loader to return
    expect(service.users.value().length).toBe(1);

    service.reloadUsers();
    expect(httpCache.delete).toHaveBeenCalledWith(USERS_URL);
    testBed.tick();
    httpMock.expectOne(USERS_URL).flush(users);
    await Promise.resolve(); // wait for loader to return
    expect(service.users.value().length).toBe(users.length);
  });
});
