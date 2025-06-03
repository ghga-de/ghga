/**
 * Test the global metadata stats service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { TestBed } from '@angular/core/testing';

import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { ConfigService } from '@app/shared/services/config.service';
import { emptyGlobalSummary } from '../models/global-summary';
import { MetadataStatsService } from './metadata-stats.service';

import { metadataGlobalSummary } from '@app/../mocks/data';

/**
 * Mock the config service as needed by the metadata service
 */
class MockConfigService {
  metldataUrl = 'http://mock.dev/metldata';
}

describe('MetadataStatsService', () => {
  let service: MetadataStatsService;
  let httpMock: HttpTestingController;
  let testBed: TestBed;

  beforeEach(() => {
    testBed = TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ConfigService, useClass: MockConfigService },
        { provide: MetadataStatsService },
      ],
    });
    service = TestBed.inject(MetadataStatsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should load the stats', async () => {
    const stats = service.globalSummary;
    expect(stats.isLoading()).toBeTruthy();
    expect(stats.error()).toBeUndefined();
    expect(stats.value()).toEqual(emptyGlobalSummary);
    testBed.tick();
    const req = httpMock.expectOne('http://mock.dev/metldata/stats');
    expect(req.request.method).toBe('GET');
    req.flush(metadataGlobalSummary);
    await Promise.resolve(); // wait for loader to return
    expect(stats.isLoading()).toBe(false);
    expect(stats.error()).toBeUndefined();
    expect(stats.value()).toEqual(metadataGlobalSummary.resource_stats);
  });
});
