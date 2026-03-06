/**
 * Test the upload box service.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ConfigService } from '@app/shared/services/config';
import { BoxRetrievalResults, UploadBoxState } from '../models/box';
import { UploadBoxService } from './upload-box';

const TEST_BOX_RETRIEVAL_RESULTS: BoxRetrievalResults = {
  count: 2,
  boxes: [
    {
      id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68001',
      version: 1,
      state: UploadBoxState.open,
      title: 'Upload Box Alpha',
      description: 'First upload box for stewardship tests',
      last_changed: '2025-02-01T09:00:00Z',
      changed_by: 'doe@test.dev',
      file_count: 3,
      size: 123456789,
      storage_alias: 'TUE01',
    },
    {
      id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
      version: 4,
      state: UploadBoxState.locked,
      title: 'Upload Box Beta',
      description: 'Second upload box for stewardship tests',
      last_changed: '2025-02-02T10:00:00Z',
      changed_by: 'roe@test.dev',
      file_count: 12,
      size: 987654321,
      storage_alias: 'HD02',
    },
  ],
};

/**
 * Mock the config service as needed for the upload box service.
 */
class MockConfigService {
  uosUrl = 'http://mock.dev/uos';
  wkvsUrl = 'http://mock.dev/.well-known';
}

describe('UploadBoxService', () => {
  let service: UploadBoxService;
  let httpMock: HttpTestingController;
  let testBed: TestBed;

  beforeEach(() => {
    testBed = TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ConfigService, useClass: MockConfigService },
      ],
    });
    service = TestBed.inject(UploadBoxService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should fetch all upload boxes', async () => {
    expect(service.boxRetrievalResults.isLoading()).toBe(false);
    expect(service.boxRetrievalResults.error()).toBeUndefined();
    expect(service.boxRetrievalResults.value()).toEqual({ count: 0, boxes: [] });

    service.loadAllUploadBoxes();
    testBed.tick();

    expect(service.boxRetrievalResults.isLoading()).toBe(true);

    const req = httpMock.expectOne('http://mock.dev/uos/boxes');
    expect(req.request.method).toBe('GET');
    req.flush(TEST_BOX_RETRIEVAL_RESULTS);

    const labelsReq = httpMock.expectOne(
      'http://mock.dev/.well-known/values/storage_labels',
    );
    expect(labelsReq.request.method).toBe('GET');
    labelsReq.flush({
      storage_labels: { TUE01: 'Tübingen 1', HD02: 'Heidelberg 2' },
    });

    await Promise.resolve();

    expect(service.boxRetrievalResults.isLoading()).toBe(false);
    expect(service.boxRetrievalResults.error()).toBeUndefined();
    expect(service.boxRetrievalResults.value()).toEqual(TEST_BOX_RETRIEVAL_RESULTS);
    expect(service.uploadBoxes()).toEqual(TEST_BOX_RETRIEVAL_RESULTS.boxes);
  });

  it('should filter upload boxes by title, state, and location', async () => {
    service.loadAllUploadBoxes();
    testBed.tick();

    const req = httpMock.expectOne('http://mock.dev/uos/boxes');
    expect(req.request.method).toBe('GET');
    req.flush(TEST_BOX_RETRIEVAL_RESULTS);

    const labelsReq = httpMock.expectOne(
      'http://mock.dev/.well-known/values/storage_labels',
    );
    expect(labelsReq.request.method).toBe('GET');
    labelsReq.flush({
      storage_labels: { TUE01: 'Tübingen 1', HD02: 'Heidelberg 2' },
    });

    await Promise.resolve();

    service.setUploadBoxesFilter({
      title: 'alpha',
      state: undefined,
      location: undefined,
    });
    expect(service.filteredUploadBoxes()).toEqual([
      TEST_BOX_RETRIEVAL_RESULTS.boxes[0],
    ]);

    service.setUploadBoxesFilter({
      title: undefined,
      state: UploadBoxState.locked,
      location: undefined,
    });
    expect(service.filteredUploadBoxes()).toEqual([
      TEST_BOX_RETRIEVAL_RESULTS.boxes[1],
    ]);

    service.setUploadBoxesFilter({
      title: undefined,
      state: undefined,
      location: 'HD02',
    });
    expect(service.filteredUploadBoxes()).toEqual([
      TEST_BOX_RETRIEVAL_RESULTS.boxes[1],
    ]);
  });

  it('should resolve storage aliases to storage location labels', async () => {
    service.loadAllUploadBoxes();
    testBed.tick();

    const req = httpMock.expectOne('http://mock.dev/uos/boxes');
    req.flush(TEST_BOX_RETRIEVAL_RESULTS);

    const labelsReq = httpMock.expectOne(
      'http://mock.dev/.well-known/values/storage_labels',
    );
    labelsReq.flush({
      storage_labels: { TUE01: 'Tübingen 1', HD02: 'Heidelberg 2' },
    });

    await Promise.resolve();

    expect(service.getStorageLocationLabel('TUE01')).toBe('Tübingen 1');
    expect(service.getStorageLocationLabel('UNKNOWN')).toBe('UNKNOWN');
  });

  it('should expose empty upload box signals when upload box retrieval fails', async () => {
    service.loadAllUploadBoxes();
    testBed.tick();

    const req = httpMock.expectOne('http://mock.dev/uos/boxes');
    expect(req.request.method).toBe('GET');
    req.flush(
      { detail: 'upload box retrieval failed' },
      { status: 409, statusText: 'Conflict' },
    );

    const labelsReq = httpMock.expectOne(
      'http://mock.dev/.well-known/values/storage_labels',
    );
    expect(labelsReq.request.method).toBe('GET');
    labelsReq.flush({ storage_labels: { TUE01: 'Tübingen 1' } });

    await Promise.resolve();

    expect(service.boxRetrievalResults.isLoading()).toBe(false);
    expect(service.boxRetrievalResults.error()).toBeInstanceOf(HttpErrorResponse);
    expect(service.uploadBoxes()).toEqual([]);
    expect(service.filteredUploadBoxes()).toEqual([]);
  });
});
