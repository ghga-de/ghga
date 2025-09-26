/**
 * Tests for the data access service.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ConfigService } from '@app/shared/services/config';
import { AccessRequestService } from './access-request';

/**
 * Mock the config service as needed by the auth service
 */
class MockConfigService {
  authUrl = 'http://mock.dev/auth';
}

describe('AccessRequestService', () => {
  let service: AccessRequestService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ConfigService, useClass: MockConfigService },
      ],
    });
    service = TestBed.inject(AccessRequestService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
