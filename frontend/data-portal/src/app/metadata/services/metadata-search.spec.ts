/**
 * Test the metadata service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { TestBed } from '@angular/core/testing';

import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
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

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ConfigService, useClass: MockConfigService },
      ],
    });
    service = TestBed.inject(MetadataSearchService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should compute the search URL correctly for a range of parameters', () => {
    expect(
      service.urlFromParameters(
        '/',
        'EmbeddedDataset',
        {},
        'GHGAD33646518790164',
        0,
        10,
      ),
    ).toBe('/?class_name=EmbeddedDataset&query=GHGAD33646518790164&limit=10');
    expect(
      service.urlFromParameters(
        '/',
        'EmbeddedDataset',
        {},
        'GHGAD33646518790164',
        10,
        10,
      ),
    ).toBe('/?class_name=EmbeddedDataset&query=GHGAD33646518790164&limit=10&skip=10');
  });

  it('should compute an empty url if the class name is not set', () => {
    expect(service.urlFromParameters('/', '', {}, 'GHGAD33646518790164', 0, 10)).toBe(
      '',
    );
  });

  it('should url escape the query parameter', () => {
    expect(service.urlFromParameters('/', 'EmbeddedDataset', {}, 'test?', 0, 10)).toBe(
      '/?class_name=EmbeddedDataset&query=test%3F&limit=10',
    );
  });
});
