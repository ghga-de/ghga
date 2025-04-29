/**
 * Test the well known value service
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
import { emptyStorageLabels } from '../models/well-known-values';
import { WellKnownValueService } from './well-known-value.service';

import { storageLabels } from '@app/../mocks/data';

/**
 * Mock the config service as needed by the metadata service
 */
class MockConfigService {
  wkvsUrl = 'http://mock.dev/.well-known';
}

describe('WellKnownValueService', () => {
  let service: WellKnownValueService;
  let httpMock: HttpTestingController;
  let testBed: TestBed;

  beforeEach(() => {
    testBed = TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ConfigService, useClass: MockConfigService },
        { provide: WellKnownValueService },
      ],
    });
    service = TestBed.inject(WellKnownValueService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should load the storage labels', async () => {
    const labels = service.storageLabels;
    expect(labels.isLoading()).toBeTruthy();
    expect(labels.error()).toBeUndefined();
    expect(labels.value()).toEqual(emptyStorageLabels);
    testBed.flushEffects();
    const req = httpMock.expectOne('http://mock.dev/.well-known/values/storage_labels');
    expect(req.request.method).toBe('GET');
    req.flush(storageLabels);
    await Promise.resolve(); // wait for loader to return
    expect(labels.isLoading()).toBe(false);
    expect(labels.error()).toBeUndefined();
    expect(labels.value()).toEqual(storageLabels.storage_labels);
  });
});
