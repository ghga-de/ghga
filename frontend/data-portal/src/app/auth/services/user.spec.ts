/**
 * User service tests
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ConfigService } from '@app/shared/services/config';
import { UserService } from './user';

/**
 * Mock ConfigService for testing
 */
class MockConfigService {
  authUrl = 'http://mock.dev/auth';
}

describe('UserService', () => {
  let service: UserService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        UserService,
        { provide: ConfigService, useClass: MockConfigService },
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(UserService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should have users resource with default empty array', () => {
    expect(service.users.value()).toEqual([]);
  });
});
