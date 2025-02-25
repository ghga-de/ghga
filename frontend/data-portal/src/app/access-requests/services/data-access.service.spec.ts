/**
 * Tests for the data access service.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ConfigService } from '@app/shared/services/config.service';
import { DataAccessService } from './data-access.service';

/**
 * Mock the config service as needed by the auth service
 */
class MockConfigService {
  authUrl = 'http://mock.dev/auth';
}

describe('DataAccessService', () => {
  let service: DataAccessService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ConfigService, useClass: MockConfigService },
      ],
    });
    service = TestBed.inject(DataAccessService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
