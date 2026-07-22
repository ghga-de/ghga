/**
 * Test the study service.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ConfigService } from '@app/shared/services/config';
import { FileIdMap, Study } from '../models/study';
import { StudyService } from './study';

const TEST_STUDIES: Study[] = [
  {
    id: 'GHGAS00000000000001',
    title: 'Test Study',
    description: 'A study with unmapped files',
    types: ['test_genomics'],
    affiliations: ['Test affiliation'],
    status: 'draft',
    num_datasets: 2,
    num_publications: 1,
    has_em: true,
    created: '2026-01-01T00:00:00Z',
    created_by: 'doe@test.dev',
    approved: null,
    approved_by: null,
    superseded_by_id: null,
  },
];

const TEST_FILE_IDS: FileIdMap = {
  GHGAF00000000000001: null,
  GHGAF00000000000002: 'd2c8b6a4-0000-4000-8000-000000000001',
};

/**
 * Mock the config service as needed for the study service.
 */
class MockConfigService {
  rsUrl = 'http://mock.dev/rs';
}

describe('StudyService', () => {
  let service: StudyService;
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
    service = TestBed.inject(StudyService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should not request studies before loadStudies is called', () => {
    testBed.tick();
    httpMock.expectNone('http://mock.dev/rs/studies?with_unmapped_files=true');
  });

  it('should load studies with unmapped files once triggered', async () => {
    service.loadStudies();
    testBed.tick();

    expect(service.studies.isLoading()).toBe(true);

    const req = httpMock.expectOne(
      'http://mock.dev/rs/studies?with_unmapped_files=true',
    );
    expect(req.request.method).toBe('GET');
    req.flush(TEST_STUDIES);

    await Promise.resolve();

    expect(service.studies.isLoading()).toBe(false);
    expect(service.studies.error()).toBeUndefined();
    expect(service.studies.value()).toEqual(TEST_STUDIES);
  });

  it('should load the file IDs for a study', () => {
    let result: FileIdMap | undefined;
    service.loadFileIds('GHGAS00000000000001').subscribe((map) => {
      result = map;
    });
    const req = httpMock.expectOne(
      'http://mock.dev/rs/studies/GHGAS00000000000001/file-ids',
    );
    expect(req.request.method).toBe('GET');
    req.flush(TEST_FILE_IDS);
    expect(result).toEqual(TEST_FILE_IDS);
  });

  it('should URL-encode the study ID when loading file IDs', () => {
    service.loadFileIds('GHGAS 0001/x').subscribe();
    const req = httpMock.expectOne(
      'http://mock.dev/rs/studies/GHGAS%200001%2Fx/file-ids',
    );
    expect(req.request.method).toBe('GET');
    req.flush({});
  });
});
