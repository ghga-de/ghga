/**
 * Test the global metadata stats service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { TestBed } from '@angular/core/testing';

import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ConfigService } from '@app/shared/services/config.service';
import { MetadataStatsService } from './metadata-stats.service';

/**
 * Mock the config service as needed by the metadata service
 */
class MockConfigService {
  metldataUrl = 'http://mock.dev/metldata';
}

describe('MetadataStatsService', () => {
  let service: MetadataStatsService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ConfigService, useClass: MockConfigService },
        { provide: MetadataStatsService },
      ],
    });
    service = TestBed.inject(MetadataStatsService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
