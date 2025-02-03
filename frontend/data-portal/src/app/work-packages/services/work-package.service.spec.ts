/**
 * Test test work package service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { TestBed } from '@angular/core/testing';

import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { computed, signal } from '@angular/core';
import { AuthService } from '@app/auth/services/auth.service';
import { ConfigService } from '@app/shared/services/config.service';
import { Dataset } from '../models/dataset';
import { WorkPackage, WorkPackageResponse } from '../models/work-package';
import { WorkPackageService } from './work-package.service';

const TEST_DATASET: Dataset = {
  id: 'test-dataset-id',
  title: 'dataset-title',
  description: 'dataset-description',
  stage: 'download',
  files: [],
};

const TEST_WORK_PACKAGE: WorkPackage = {
  dataset_id: 'test-dataset-id',
  file_ids: ['file-id-1', 'file-id-2'],
  type: 'download',
  user_public_crypt4gh_key: 'test-crypt4gh-key',
};

const TEST_WORK_PACKAGE_RESPONSE: WorkPackageResponse = {
  id: 'test-work-package-id',
  token: 'test-work-package-token',
};

/**
 * Mock the config service as needed for the work package service
 */
class MockConfigService {
  wpsUrl = 'http://mock.dev/wps';
}

const userId = signal<string | null>(null); // can be used by the test

/**
 * Mock the auth service as needed for the work package service
 */
class MockAuthService {
  user = computed(() => ({ id: userId() }));
}

describe('WorkPackageService', () => {
  let service: WorkPackageService;
  let httpMock: HttpTestingController;
  let testBed: TestBed;

  beforeEach(() => {
    testBed = TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ConfigService, useClass: MockConfigService },
        { provide: AuthService, useClass: MockAuthService },
        WorkPackageService,
      ],
    });
    service = TestBed.inject(WorkPackageService);
    httpMock = TestBed.inject(HttpTestingController);
    userId.set(null); // not logged in
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should return an error when not logged in and datasets are fetched', async () => {
    userId.set(null);
    testBed.flushEffects();
    expect(service.datasetsAreLoading()).toBe(true);
    expect(service.datasetsError()).toBe(undefined);
    expect(service.datasets()).toEqual([]);
    await Promise.resolve(); // wait for loader to return
    expect(service.datasetsAreLoading()).toBe(false);
    const error = service.datasetsError();
    expect(error).toBeInstanceOf(Error);
    expect((error as Error).message).toBe('User not authenticated');
    expect(service.datasets()).toEqual([]);
  });

  it('should get the datasets of an authenticated user', async () => {
    expect(service.datasetsAreLoading()).toBe(true);
    expect(service.datasetsError()).toBe(undefined);
    expect(service.datasets()).toEqual([]);
    userId.set('test-user-id');
    testBed.flushEffects();
    expect(service.datasetsAreLoading()).toBe(true);
    expect(service.datasetsError()).toBe(undefined);
    expect(service.datasets()).toEqual([]);
    const req = httpMock.expectOne('http://mock.dev/wps/users/test-user-id/datasets');
    expect(req.request.method).toBe('GET');
    req.flush([TEST_DATASET]);
    await Promise.resolve(); // wait for loader to return
    expect(service.datasetsAreLoading()).toBe(false);
    expect(service.datasetsError()).toBe(undefined);
    expect(service.datasets()).toEqual([TEST_DATASET]);
  });

  it('should create a work package for download', (done) => {
    service.createWorkPackage(TEST_WORK_PACKAGE).subscribe((response) => {
      expect(response).toEqual(TEST_WORK_PACKAGE_RESPONSE);
      done();
    });
    const req = httpMock.expectOne('http://mock.dev/wps/work-packages');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toBe(TEST_WORK_PACKAGE);
    req.flush(TEST_WORK_PACKAGE_RESPONSE);
  });
});
