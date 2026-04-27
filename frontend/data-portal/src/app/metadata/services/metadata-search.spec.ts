/**
 * Test the metadata service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { TestBed } from '@angular/core/testing';

import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { ConfigService } from '@app/shared/services/config';
import { MetadataSearchService } from './metadata-search';

/**
 * Mock the config service as needed by the metadata service
 */
class MockConfigService {
  massUrl = 'http://mock.dev/mass';
}

describe('MetadataSearchService', () => {
  let service: MetadataSearchService;
  let httpController: HttpTestingController;
  let testBed: TestBed;

  beforeEach(() => {
    testBed = TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ConfigService, useClass: MockConfigService },
      ],
    });
    service = TestBed.inject(MetadataSearchService);
    httpController = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpController.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should compute the search URL correctly for a range of parameters', () => {
    service.loadQueryParameters('EmbeddedDataset', 10, 0, 'GHGAD33646518790164');
    testBed.tick();
    const req1 = httpController.expectOne(
      'http://mock.dev/mass/search?class_name=EmbeddedDataset&query=GHGAD33646518790164&limit=10',
    );
    req1.flush({});

    service.loadQueryParameters('EmbeddedDataset', 10, 10, 'GHGAD33646518790164');
    testBed.tick();
    const req2 = httpController.expectOne(
      'http://mock.dev/mass/search?class_name=EmbeddedDataset&query=GHGAD33646518790164&limit=10&skip=10',
    );
    req2.flush({});
  });

  it('should not make a request when class name is not set', () => {
    testBed.tick();
    httpController.expectNone('http://mock.dev/mass/search');
  });

  it('should url escape the query parameter', () => {
    service.loadQueryParameters('EmbeddedDataset', 10, 0, 'test?');
    testBed.tick();
    const req = httpController.expectOne(
      'http://mock.dev/mass/search?class_name=EmbeddedDataset&query=test%3F&limit=10',
    );
    req.flush({});
  });
});
