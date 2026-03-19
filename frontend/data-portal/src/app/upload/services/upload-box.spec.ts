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
import {
  BoxRetrievalResults,
  ResearchDataUploadBoxBase,
  ResearchDataUploadBoxUpdate,
  UploadBoxState,
  UploadBoxVirtualFilter,
} from '../models/box';
import { GrantWithBoxInfo, UploadGrant } from '../models/grant';
import { UploadBoxService } from './upload-box';

const TEST_BOX_RETRIEVAL_RESULTS: BoxRetrievalResults = {
  count: 3,
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
    {
      id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68003',
      version: 2,
      state: UploadBoxState.archived,
      title: 'Upload Box Gamma',
      description: 'Third upload box, archived',
      last_changed: '2025-03-01T12:00:00Z',
      changed_by: 'doe@test.dev',
      file_count: 0,
      size: 0,
      storage_alias: 'TUE01',
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

    const notArchived: UploadBoxVirtualFilter = 'not_archived';
    service.setUploadBoxesFilter({
      title: undefined,
      state: notArchived,
      location: undefined,
    });
    expect(service.filteredUploadBoxes()).toEqual([
      TEST_BOX_RETRIEVAL_RESULTS.boxes[0],
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

  it('should fetch a single upload box', async () => {
    const singleBox = TEST_BOX_RETRIEVAL_RESULTS.boxes[0];

    expect(service.uploadBox.isLoading()).toBe(false);
    expect(service.uploadBox.value()).toBeUndefined();

    service.loadUploadBox(singleBox.id);
    testBed.tick();

    expect(service.uploadBox.isLoading()).toBe(true);

    const req = httpMock.expectOne(`http://mock.dev/uos/box/${singleBox.id}`);
    expect(req.request.method).toBe('GET');
    req.flush(singleBox);

    await Promise.resolve();

    expect(service.uploadBox.isLoading()).toBe(false);
    expect(service.uploadBox.error()).toBeUndefined();
    expect(service.uploadBox.value()).toEqual(singleBox);
  });

  it('should expose an error when fetching a single upload box fails', async () => {
    const id = TEST_BOX_RETRIEVAL_RESULTS.boxes[0].id;

    service.loadUploadBox(id);
    testBed.tick();

    const req = httpMock.expectOne(`http://mock.dev/uos/box/${id}`);
    req.flush({ detail: 'not found' }, { status: 404, statusText: 'Not Found' });

    await Promise.resolve();

    expect(service.uploadBox.isLoading()).toBe(false);
    expect(service.uploadBox.error()).toBeInstanceOf(HttpErrorResponse);
  });

  it('should create an upload box and return its id', async () => {
    const newBoxData: ResearchDataUploadBoxBase = {
      title: 'New Test Box',
      description: 'A box created in a test',
      storage_alias: 'TUE01',
    };
    const createdId = '0a36607a-b53f-49ed-bf3e-a5f2dbc68099';

    let emittedId: string | undefined;
    service.createUploadBox(newBoxData).subscribe((id) => (emittedId = id));

    const req = httpMock.expectOne('http://mock.dev/uos/boxes');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(newBoxData);
    req.flush({ id: createdId }, { status: 201, statusText: 'Created' });

    expect(emittedId).toBe(createdId);
  });

  it('should propagate an error when creating an upload box fails', async () => {
    const newBoxData: ResearchDataUploadBoxBase = {
      title: 'Bad Box',
      description: 'A box that will fail',
      storage_alias: 'INVALID',
    };

    let caughtError: HttpErrorResponse | undefined;
    service
      .createUploadBox(newBoxData)
      .subscribe({ error: (err) => (caughtError = err) });

    const req = httpMock.expectOne('http://mock.dev/uos/boxes');
    expect(req.request.method).toBe('POST');
    req.flush(
      { detail: 'invalid storage alias' },
      { status: 422, statusText: 'Unprocessable Entity' },
    );

    expect(caughtError).toBeInstanceOf(HttpErrorResponse);
    expect(caughtError?.status).toBe(422);
  });

  it('should update an upload box', () => {
    const id = TEST_BOX_RETRIEVAL_RESULTS.boxes[0].id;
    const changes: ResearchDataUploadBoxUpdate = { version: 1, title: 'Updated Title' };

    let completed = false;
    service
      .updateUploadBox(id, changes)
      .subscribe({ complete: () => (completed = true) });

    const req = httpMock.expectOne(`http://mock.dev/uos/boxes/${id}`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual(changes);
    req.flush(null, { status: 204, statusText: 'No Content' });

    expect(completed).toBe(true);
  });

  it('should propagate an error when updating an upload box fails', () => {
    const id = TEST_BOX_RETRIEVAL_RESULTS.boxes[0].id;
    const changes: ResearchDataUploadBoxUpdate = { version: 1, title: 'Bad Update' };

    let caughtError: HttpErrorResponse | undefined;
    service
      .updateUploadBox(id, changes)
      .subscribe({ error: (err) => (caughtError = err) });

    const req = httpMock.expectOne(`http://mock.dev/uos/boxes/${id}`);
    expect(req.request.method).toBe('PATCH');
    req.flush({ detail: 'version conflict' }, { status: 409, statusText: 'Conflict' });

    expect(caughtError).toBeInstanceOf(HttpErrorResponse);
    expect(caughtError?.status).toBe(409);
  });

  describe('loadBoxGrants', () => {
    const BOX_ID = '0a36607a-b53f-49ed-bf3e-a5f2dbc68001';
    const GRANT: UploadGrant = {
      id: 'grant-box-001',
      user_id: 'user-abc',
      iva_id: null,
      box_id: BOX_ID,
      created: '2025-03-01T08:00:00Z',
      valid_from: '2025-03-01',
      valid_until: '2025-12-31',
      user_name: 'Alice Example',
      user_email: 'alice@test.dev',
      user_title: 'Dr.',
    };

    it('should request access-grants filtered by box_id', async () => {
      service.loadBoxGrants(BOX_ID);
      testBed.tick();

      const req = httpMock.expectOne(
        `http://mock.dev/uos/access-grants?box_id=${encodeURIComponent(BOX_ID)}`,
      );
      expect(req.request.method).toBe('GET');
      expect(req.request.url).toContain(`box_id=${encodeURIComponent(BOX_ID)}`);
      req.flush([GRANT]);

      await Promise.resolve();

      expect(service.boxGrants.value()).toEqual([GRANT]);
    });

    it('should not request grants when no box id has been set', () => {
      testBed.tick();
      httpMock.expectNone('http://mock.dev/uos/access-grants');
      expect(service.boxGrants.value()).toEqual([]);
    });
  });

  describe('getAccessGrants', () => {
    const TEST_GRANTS: GrantWithBoxInfo[] = [
      {
        id: 'grant-001',
        user_id: 'user-abc',
        iva_id: null,
        box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68001',
        created: '2025-03-01T08:00:00Z',
        valid_from: '2025-03-01T00:00:00Z',
        valid_until: '2025-06-01T00:00:00Z',
        user_name: 'Alice Example',
        user_email: 'alice@test.dev',
        user_title: 'Dr.',
        box_title: 'Upload Box Alpha',
        box_description: 'First upload box for stewardship tests',
      },
      {
        id: 'grant-002',
        user_id: 'user-xyz',
        iva_id: 'iva-001',
        box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
        created: '2025-04-01T08:00:00Z',
        valid_from: '2025-04-01T00:00:00Z',
        valid_until: '2025-04-30T00:00:00Z',
        user_name: 'Bob Example',
        user_email: 'bob@test.dev',
        user_title: null,
        box_title: 'Upload Box Beta',
        box_description: 'Second upload box for stewardship tests',
      },
    ];

    it('should fetch access grants without filters', () => {
      let result: GrantWithBoxInfo[] | undefined;
      service.getAccessGrants().subscribe((grants) => (result = grants));

      const req = httpMock.expectOne('http://mock.dev/uos/access-grants');
      expect(req.request.method).toBe('GET');
      expect(req.request.params.keys()).toHaveLength(0);
      req.flush(TEST_GRANTS);

      expect(result).toEqual(TEST_GRANTS);
    });

    it('should pass userid query param when userId is provided', () => {
      service.getAccessGrants({ userId: 'user-abc' }).subscribe();

      const req = httpMock.expectOne(
        'http://mock.dev/uos/access-grants?userid=user-abc',
      );
      expect(req.request.params.get('userid')).toBe('user-abc');
      expect(req.request.params.has('box_id')).toBe(false);
      expect(req.request.params.has('valid')).toBe(false);
      req.flush([]);
    });

    it('should pass box_id query param when boxId is provided', () => {
      const boxId = '0a36607a-b53f-49ed-bf3e-a5f2dbc68001';
      service.getAccessGrants({ boxId }).subscribe();

      const req = httpMock.expectOne(
        `http://mock.dev/uos/access-grants?box_id=${boxId}`,
      );
      expect(req.request.params.get('box_id')).toBe(boxId);
      expect(req.request.params.has('userid')).toBe(false);
      expect(req.request.params.has('valid')).toBe(false);
      req.flush([]);
    });

    it('should pass valid=true when valid is true', () => {
      service.getAccessGrants({ valid: true }).subscribe();

      const req = httpMock.expectOne('http://mock.dev/uos/access-grants?valid=true');
      expect(req.request.params.get('valid')).toBe('true');
      req.flush([]);
    });

    it('should pass valid=false when valid is false', () => {
      service.getAccessGrants({ valid: false }).subscribe();

      const req = httpMock.expectOne('http://mock.dev/uos/access-grants?valid=false');
      expect(req.request.params.get('valid')).toBe('false');
      req.flush([]);
    });

    it('should omit valid query param when valid is null', () => {
      service.getAccessGrants({ valid: null }).subscribe();

      const req = httpMock.expectOne('http://mock.dev/uos/access-grants');
      expect(req.request.params.has('valid')).toBe(false);
      req.flush([]);
    });

    it('should pass all filter params when all are provided', () => {
      const boxId = '0a36607a-b53f-49ed-bf3e-a5f2dbc68001';
      service.getAccessGrants({ userId: 'user-abc', boxId, valid: true }).subscribe();

      const req = httpMock.expectOne(
        (r) =>
          r.url === 'http://mock.dev/uos/access-grants' &&
          r.params.get('userid') === 'user-abc' &&
          r.params.get('box_id') === boxId &&
          r.params.get('valid') === 'true',
      );
      expect(req.request.method).toBe('GET');
      req.flush(TEST_GRANTS);
    });

    it('should propagate a 401 error when not authenticated', () => {
      let caughtError: HttpErrorResponse | undefined;
      service.getAccessGrants().subscribe({ error: (err) => (caughtError = err) });

      const req = httpMock.expectOne('http://mock.dev/uos/access-grants');
      req.flush(
        { detail: 'unauthorized' },
        { status: 401, statusText: 'Unauthorized' },
      );

      expect(caughtError).toBeInstanceOf(HttpErrorResponse);
      expect(caughtError?.status).toBe(401);
    });

    it('should propagate a 404 error when the endpoint is not found', () => {
      let caughtError: HttpErrorResponse | undefined;
      service.getAccessGrants().subscribe({ error: (err) => (caughtError = err) });

      const req = httpMock.expectOne('http://mock.dev/uos/access-grants');
      req.flush({ detail: 'not found' }, { status: 404, statusText: 'Not Found' });

      expect(caughtError).toBeInstanceOf(HttpErrorResponse);
      expect(caughtError?.status).toBe(404);
    });
  });

  describe('createUploadGrant', () => {
    const GRANT_PAYLOAD = {
      user_id: 'user-abc',
      iva_id: null,
      box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68001',
      valid_from: '2026-01-01',
      valid_until: '2026-12-31',
    };

    it('should POST to access-grants and return the new grant id', () => {
      const newId = 'grant-new-001';
      let result: { id: string } | undefined;
      service.createUploadGrant(GRANT_PAYLOAD).subscribe((r) => (result = r));

      const req = httpMock.expectOne('http://mock.dev/uos/access-grants');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(GRANT_PAYLOAD);
      req.flush({ id: newId }, { status: 201, statusText: 'Created' });

      expect(result).toEqual({ id: newId });
    });

    it('should propagate an error when creating a grant fails', () => {
      let caughtError: HttpErrorResponse | undefined;
      service
        .createUploadGrant(GRANT_PAYLOAD)
        .subscribe({ error: (err) => (caughtError = err) });

      const req = httpMock.expectOne('http://mock.dev/uos/access-grants');
      req.flush({ detail: 'conflict' }, { status: 409, statusText: 'Conflict' });

      expect(caughtError).toBeInstanceOf(HttpErrorResponse);
      expect(caughtError?.status).toBe(409);
    });
  });

  describe('revokeUploadGrant', () => {
    const GRANT_ID = 'grant-to-revoke-001';

    it('should DELETE the access-grant by id', () => {
      let completed = false;
      service
        .revokeUploadGrant(GRANT_ID)
        .subscribe({ complete: () => (completed = true) });

      const req = httpMock.expectOne(`http://mock.dev/uos/access-grants/${GRANT_ID}`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null, { status: 204, statusText: 'No Content' });

      expect(completed).toBe(true);
    });

    it('should propagate an error when revoking a grant fails', () => {
      let caughtError: HttpErrorResponse | undefined;
      service
        .revokeUploadGrant(GRANT_ID)
        .subscribe({ error: (err) => (caughtError = err) });

      const req = httpMock.expectOne(`http://mock.dev/uos/access-grants/${GRANT_ID}`);
      req.flush({ detail: 'not found' }, { status: 404, statusText: 'Not Found' });

      expect(caughtError).toBeInstanceOf(HttpErrorResponse);
      expect(caughtError?.status).toBe(404);
    });
  });

  describe('addGrantLocally', () => {
    const BOX_ID = '0a36607a-b53f-49ed-bf3e-a5f2dbc68001';
    const GRANT: UploadGrant = {
      id: 'grant-local-001',
      user_id: 'user-abc',
      iva_id: null,
      box_id: BOX_ID,
      created: '2026-01-01T00:00:00Z',
      valid_from: '2026-01-01',
      valid_until: '2026-12-31',
      user_name: 'Alice Example',
      user_email: 'alice@test.dev',
      user_title: null,
    };

    it('should append the grant to the in-memory list after loading', async () => {
      service.loadBoxGrants(BOX_ID);
      testBed.tick();

      const req = httpMock.expectOne(
        `http://mock.dev/uos/access-grants?box_id=${encodeURIComponent(BOX_ID)}`,
      );
      req.flush([]);
      await Promise.resolve();

      expect(service.boxGrants.value()).toHaveLength(0);
      service.addGrantLocally(GRANT);
      expect(service.boxGrants.value()).toEqual([GRANT]);
    });

    it('should not throw when boxGrants has not been loaded yet', () => {
      // No loadBoxGrants call, so boxGrants.error() would be undefined
      // and value() returns the defaultValue []
      expect(() => service.addGrantLocally(GRANT)).not.toThrow();
    });
  });

  describe('loadFileUploadsForBox', () => {
    const BOX_ID = '0a36607a-b53f-49ed-bf3e-a5f2dbc68001';

    it('should request file uploads filtered by box id', async () => {
      service.loadFileUploadsForBox(BOX_ID);
      testBed.tick();

      const req = httpMock.expectOne(
        `http://mock.dev/uos/boxes/${encodeURIComponent(BOX_ID)}/uploads`,
      );
      expect(req.request.method).toBe('GET');
      req.flush([]);

      await Promise.resolve();

      expect(service.boxFileUploads.value()).toEqual([]);
    });

    it('should not request file uploads when no box id has been set', () => {
      testBed.tick();
      // httpMock.verify() in afterEach ensures no unexpected requests were made
      expect(service.boxFileUploads.value()).toEqual([]);
    });
  });
});
