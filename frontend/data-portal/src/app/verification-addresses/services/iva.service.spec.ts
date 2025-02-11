/**
 * Test the IVA service
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
import { allIvas, allIvasOfDoe, allIvasOfRoe } from '@app/../mocks/data';
import { AuthService } from '@app/auth/services/auth.service';
import { ConfigService } from '@app/shared/services/config.service';
import { IvaType } from '../models/iva';
import { IvaService } from './iva.service';

/**
 * Mock the config service as needed for the IVA service
 */
class MockConfigService {
  authUrl = 'http://mock.dev/auth';
}

/**
 * Signal that can be set to initialize the auth service mock
 * with a specific user ID, or null for not unauthenticated.
 */
const currentUserId = signal<string | null>(null);

/**
 * Mock the auth service as needed for the IVA service
 */
class MockAuthService {
  user = computed(() => ({ id: currentUserId() }));
}

describe('IvaService', () => {
  let service: IvaService;
  let httpMock: HttpTestingController;
  let testBed: TestBed;

  beforeEach(() => {
    testBed = TestBed.configureTestingModule({
      providers: [
        IvaService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: ConfigService, useClass: MockConfigService },
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(IvaService);
    httpMock = TestBed.inject(HttpTestingController);
    currentUserId.set(null); // not logged in
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', async () => {
    expect(service).toBeTruthy();
  });

  it('should not auto-load anything', async () => {
    expect(service.userIvasAreLoading()).toBe(false);
    expect(service.allIvasAreLoading()).toBe(false);
    testBed.flushEffects();
    // at this point loaders should have been called
    expect(service.userIvasAreLoading()).toBe(false);
    expect(service.userIvas()).toEqual([]);
    expect(service.allIvasAreLoading()).toBe(false);
    expect(service.allIvas()).toEqual([]);
    // and httpMock.verify() should report an error
  });

  it('should get the IVAs of the current user', async () => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.flushEffects();
    expect(service.userIvasAreLoading()).toBe(false);
    service.loadUserIvas();
    expect(service.userIvasAreLoading()).toBe(true);
    expect(service.userIvasError()).toBeUndefined();
    expect(service.userIvas()).toEqual([]);
    expect(service.allIvasAreLoading()).toBe(false);
    testBed.flushEffects();
    const req = httpMock.expectOne('http://mock.dev/auth/users/doe@test.dev/ivas');
    expect(req.request.method).toBe('GET');
    req.flush(allIvasOfDoe);
    await Promise.resolve(); // wait for loader to return
    expect(service.userIvasAreLoading()).toBe(false);
    expect(service.userIvasError()).toBeUndefined();
    expect(service.userIvas()).toEqual(allIvasOfDoe);
  });

  it('should not get IVAs of current user if not authenticated', async () => {
    currentUserId.set(null); // mock logout
    testBed.flushEffects();
    expect(service.userIvasAreLoading()).toBe(false);
    service.loadUserIvas();
    expect(service.userIvasAreLoading()).toBe(false);
    expect(service.userIvasError()).toBeUndefined();
    expect(service.userIvas()).toEqual([]);
    expect(service.allIvasAreLoading()).toBe(false);
    testBed.flushEffects();
    await Promise.resolve();
    expect(service.userIvasAreLoading()).toBe(false);
    expect(service.userIvasError()).toBeUndefined();
    expect(service.userIvas()).toEqual([]);
  });

  it('should get the IVAs of another user', async () => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.flushEffects();
    service.loadUserIvas('roe@test.dev');
    expect(service.userIvasAreLoading()).toBe(true);
    expect(service.userIvasError()).toBeUndefined();
    expect(service.userIvas()).toEqual([]);
    expect(service.allIvasAreLoading()).toBe(false);
    testBed.flushEffects();
    const req = httpMock.expectOne('http://mock.dev/auth/users/roe@test.dev/ivas');
    expect(req.request.method).toBe('GET');
    req.flush(allIvasOfRoe);
    await Promise.resolve(); // wait for loader to return
    expect(service.userIvasAreLoading()).toBe(false);
    expect(service.userIvasError()).toBeUndefined();
    expect(service.userIvas()).toEqual(allIvasOfRoe);
  });

  it('should pass authorization errors when getting IVAs of a user', async () => {
    service.loadUserIvas('roe@test.dev');
    expect(service.userIvasAreLoading()).toBe(true);
    expect(service.userIvasError()).toBeUndefined();
    expect(service.userIvas()).toEqual([]);
    expect(service.allIvasAreLoading()).toBe(false);
    testBed.flushEffects();
    const req = httpMock.expectOne('http://mock.dev/auth/users/roe@test.dev/ivas');
    expect(req.request.method).toBe('GET');
    req.flush('Mock Error', { status: 401, statusText: 'Unauthorized' });
    await Promise.resolve(); // wait for loader to return
    expect(service.userIvasAreLoading()).toBe(false);
    const error = service.userIvasError() as { status: number; statusText: string };
    expect(error).toBeDefined();
    expect(error.status).toBe(401);
    expect(error.statusText).toBe('Unauthorized');
    expect(service.userIvas()).toEqual([]);
  });

  it('should get all IVAs', async () => {
    service.loadAllIvas();
    expect(service.allIvasAreLoading()).toBe(true);
    expect(service.allIvasError()).toBeUndefined();
    expect(service.allIvas()).toEqual([]);
    expect(service.userIvasAreLoading()).toBe(false);
    testBed.flushEffects();
    const req = httpMock.expectOne('http://mock.dev/auth/ivas');
    expect(req.request.method).toBe('GET');
    req.flush(allIvas);
    await Promise.resolve(); // wait for loader to return
    expect(service.allIvasAreLoading()).toBe(false);
    expect(service.allIvasError()).toBeUndefined();
    expect(service.allIvas()).toEqual(allIvas);
  });

  it('should pass server errors when getting all IVAs', async () => {
    service.loadAllIvas();
    expect(service.allIvasAreLoading()).toBe(true);
    expect(service.allIvasError()).toBeUndefined();
    expect(service.allIvas()).toEqual([]);
    expect(service.userIvasAreLoading()).toBe(false);
    testBed.flushEffects();
    const req = httpMock.expectOne('http://mock.dev/auth/ivas');
    expect(req.request.method).toBe('GET');
    req.flush('Mock Error', { status: 401, statusText: 'Server Error' });
    await Promise.resolve(); // wait for loader to return
    expect(service.allIvasAreLoading()).toBe(false);
    const error = service.allIvasError() as { status: number; statusText: string };
    expect(error).toBeDefined();
    expect(error.status).toBe(401);
    expect(error.statusText).toBe('Server Error');
    expect(service.allIvas()).toEqual([]);
  });

  it('should create an IVA for the current user', (done) => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.flushEffects();
    service.createIva({ type: IvaType.Phone, value: '123/456' }).subscribe((id) => {
      expect(id).toEqual('TEST123456');
      done();
    });
    const req = httpMock.expectOne('http://mock.dev/auth/users/doe@test.dev/ivas');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ type: IvaType.Phone, value: '123/456' });
    req.flush({ id: 'TEST123456' });
  });

  it('should return an error if IVA to be created is missing a value', (done) => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.flushEffects();
    service.createIva({ type: IvaType.Phone, value: '' }).subscribe({
      error: (error) => {
        expect(error).toBeDefined();
        expect(error.message).toBe('IVA type or value missing');
        done();
      },
    });
  });

  it('should return an error if IVA is created while not logged in', (done) => {
    currentUserId.set(null); // mock logout
    testBed.flushEffects();
    service.createIva({ type: IvaType.Phone, value: '123/456' }).subscribe({
      error: (error) => {
        expect(error).toBeDefined();
        expect(error.message).toBe('Not authenticated');
        done();
      },
    });
  });

  it('should pass a server error when IVA is created', (done) => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.flushEffects();
    service.createIva({ type: IvaType.Phone, value: '123/456' }).subscribe({
      error: (error) => {
        expect(error).toBeDefined();
        expect(error.status).toBe(500);
        expect(error.statusText).toBe('Server Error');
        done();
      },
    });
    const req = httpMock.expectOne('http://mock.dev/auth/users/doe@test.dev/ivas');
    expect(req.request.method).toBe('POST');
    req.flush('Mock Error', { status: 500, statusText: 'Server Error' });
  });

  it('should delete an IVA for the current user', (done) => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.flushEffects();
    service.deleteIva({ ivaId: 'TEST123456' }).subscribe((ret) => {
      expect(ret).toBeNull();
      done();
    });
    const req = httpMock.expectOne(
      'http://mock.dev/auth/users/doe@test.dev/ivas/TEST123456',
    );
    expect(req.request.method).toBe('DELETE');
    expect(req.request.body).toBeNull();
    req.flush(null);
  });

  it('should return an error if the IVA to be deleted has no ID', (done) => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.flushEffects();
    service.deleteIva({ ivaId: '' }).subscribe({
      error: (error) => {
        expect(error).toBeDefined();
        expect(error.message).toBe('IVA ID missing');
        done();
      },
    });
  });

  it('should return an error if IVA is deleted while not logged in', (done) => {
    currentUserId.set(null); // mock logout
    testBed.flushEffects();
    service.deleteIva({ ivaId: 'TEST123456' }).subscribe({
      error: (error) => {
        expect(error).toBeDefined();
        expect(error.message).toBe('Not authenticated');
        done();
      },
    });
  });

  it('should pass a server error when IVA is deleted', (done) => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.flushEffects();
    service.deleteIva({ ivaId: 'TEST123456' }).subscribe({
      error: (error) => {
        expect(error).toBeDefined();
        expect(error.status).toBe(500);
        expect(error.statusText).toBe('Server Error');
        done();
      },
    });
    const req = httpMock.expectOne(
      'http://mock.dev/auth/users/doe@test.dev/ivas/TEST123456',
    );
    expect(req.request.method).toBe('DELETE');
    req.flush('Mock Error', { status: 500, statusText: 'Server Error' });
  });

  it('should unverify an IVA for the current user', (done) => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.flushEffects();
    service.unverifyIva('TEST123456').subscribe((ret) => {
      expect(ret).toBeNull();
      done();
    });
    const req = httpMock.expectOne('http://mock.dev/auth/rpc/ivas/TEST123456/unverify');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toBeNull();
    req.flush(null);
  });

  it('should request verification of an IVA for the current user', (done) => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.flushEffects();
    service.requestCodeForIva('TEST123456').subscribe((ret) => {
      expect(ret).toBeNull();
      done();
    });
    const req = httpMock.expectOne(
      'http://mock.dev/auth/rpc/ivas/TEST123456/request-code',
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toBeNull();
    req.flush(null);
  });

  it('should create a verification code for an IVA of the current user', (done) => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.flushEffects();
    service.createCodeForIva('TEST123456').subscribe((code) => {
      expect(code).toBe('CODE789');
      done();
    });
    const req = httpMock.expectOne(
      'http://mock.dev/auth/rpc/ivas/TEST123456/create-code',
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toBeNull();
    req.flush({ verification_code: 'CODE789' });
  });

  it('should confirm transmission of IVA verification for the current user', (done) => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.flushEffects();
    service.confirmTransmissionForIva('TEST123456').subscribe((ret) => {
      expect(ret).toBeNull();
      done();
    });
    const req = httpMock.expectOne(
      'http://mock.dev/auth/rpc/ivas/TEST123456/code-transmitted',
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toBeNull();
    req.flush(null);
  });

  it('should validate an IVA verification for the current user', (done) => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.flushEffects();
    service.validateCodeForIva('TEST123456', 'CODE789').subscribe({
      next: (ret) => {
        expect(ret).toBeNull();
        done();
      },
      error: (error) => {
        fail(`Unexpected error: ${error}`);
      },
    });
    const req = httpMock.expectOne(
      'http://mock.dev/auth/rpc/ivas/TEST123456/validate-code',
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ verification_code: 'CODE789' });
    req.flush(null);
  });

  it('should pass error status for an invalid IVA verification code', (done) => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.flushEffects();
    service.validateCodeForIva('TEST123456', 'CODE789').subscribe({
      next: (ret) => {
        fail(`Unexpected return value: ${ret}`);
        done();
      },
      error: (error) => {
        expect(error).toBeDefined();
        expect(error.status).toBe(403);
        expect(error.statusText).toBe('Forbidden');
        done();
      },
    });
    const req = httpMock.expectOne(
      'http://mock.dev/auth/rpc/ivas/TEST123456/validate-code',
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ verification_code: 'CODE789' });
    req.flush('Mock Error', { status: 403, statusText: 'Forbidden' });
  });
});
