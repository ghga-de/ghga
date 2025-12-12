/**
 * Test the IVA service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { TestBed } from '@angular/core/testing';

import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { computed, signal } from '@angular/core';
import { allIvas, allIvasOfDoe, allIvasOfRoe } from '@app/../mocks/data';
import { AuthService } from '@app/auth/services/auth';
import { ConfigService } from '@app/shared/services/config';
import { HttpCacheManager } from '@ngneat/cashew';
import { firstValueFrom } from 'rxjs';
import { IvaType } from '../models/iva';
import { IvaService } from './iva';

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

  const httpCache = {
    delete: vitest.fn(),
  };

  beforeEach(() => {
    testBed = TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useClass: MockAuthService },
        { provide: ConfigService, useClass: MockConfigService },
        { provide: HttpCacheManager, useValue: httpCache },
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
      teardown: { destroyAfterEach: false },
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
    expect(service.userIvas.isLoading()).toBe(false);
    expect(service.allIvas.isLoading()).toBe(false);
    testBed.tick();
    // at this point loaders should have been called
    expect(service.userIvas.isLoading()).toBe(false);
    expect(service.userIvas.value()).toEqual([]);
    expect(service.allIvas.isLoading()).toBe(false);
    expect(service.allIvas.value()).toEqual([]);
    // and httpMock.verify() should report an error
  });

  it('should get the IVAs of the current user', async () => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.tick();
    expect(service.userIvas.isLoading()).toBe(false);
    service.loadUserIvas();
    expect(service.userIvas.isLoading()).toBe(true);
    expect(service.userIvas.error()).toBeUndefined();
    expect(service.userIvas.value()).toEqual([]);
    expect(service.allIvas.isLoading()).toBe(false);
    testBed.tick();
    const req = httpMock.expectOne('http://mock.dev/auth/users/doe@test.dev/ivas');
    expect(req.request.method).toBe('GET');
    req.flush(allIvasOfDoe);
    await Promise.resolve(); // wait for loader to return
    expect(service.userIvas.isLoading()).toBe(false);
    expect(service.userIvas.error()).toBeUndefined();
    expect(service.userIvas.value()).toEqual(allIvasOfDoe);
  });

  it('should not get IVAs of current user if not authenticated', async () => {
    currentUserId.set(null); // mock logout
    testBed.tick();
    expect(service.userIvas.isLoading()).toBe(false);
    service.loadUserIvas();
    expect(service.userIvas.isLoading()).toBe(false);
    expect(service.userIvas.error()).toBeUndefined();
    expect(service.userIvas.value()).toEqual([]);
    expect(service.allIvas.isLoading()).toBe(false);
    testBed.tick();
    await Promise.resolve();
    expect(service.userIvas.isLoading()).toBe(false);
    expect(service.userIvas.error()).toBeUndefined();
    expect(service.userIvas.value()).toEqual([]);
  });

  it('should get the IVAs of another user', async () => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.tick();
    service.loadUserIvas('roe@test.dev');
    expect(service.userIvas.isLoading()).toBe(true);
    expect(service.userIvas.error()).toBeUndefined();
    expect(service.userIvas.value()).toEqual([]);
    expect(service.allIvas.isLoading()).toBe(false);
    testBed.tick();
    const req = httpMock.expectOne('http://mock.dev/auth/users/roe@test.dev/ivas');
    expect(req.request.method).toBe('GET');
    req.flush(allIvasOfRoe);
    await Promise.resolve(); // wait for loader to return
    expect(service.userIvas.isLoading()).toBe(false);
    expect(service.userIvas.error()).toBeUndefined();
    expect(service.userIvas.value()).toEqual(allIvasOfRoe);
  });

  it('should reload the IVAs of the current user', async () => {
    vitest.spyOn(httpCache, 'delete');
    currentUserId.set('doe@test.dev');
    service.loadUserIvas();
    testBed.tick();
    const url = 'http://mock.dev/auth/users/doe@test.dev/ivas';
    const r1 = httpMock.expectOne(url);
    expect(r1.request.method).toBe('GET');
    r1.flush([]);
    await Promise.resolve();
    expect(service.userIvas.value()).toEqual([]);
    expect(httpCache.delete).not.toHaveBeenCalled();
    service.reloadUserIvas();
    expect(httpCache.delete).toHaveBeenCalledWith(url);
    testBed.tick();
    const r2 = httpMock.expectOne(url);
    expect(r2.request.method).toBe('GET');
    r2.flush(allIvasOfDoe);
    await Promise.resolve();
    expect(service.userIvas.value()).toEqual(allIvasOfDoe);
  });

  it('should pass authorization errors when getting IVAs of a user', async () => {
    service.loadUserIvas('roe@test.dev');
    expect(service.userIvas.isLoading()).toBe(true);
    expect(service.userIvas.error()).toBeUndefined();
    expect(service.userIvas.value()).toEqual([]);
    expect(service.allIvas.isLoading()).toBe(false);
    testBed.tick();
    const req = httpMock.expectOne('http://mock.dev/auth/users/roe@test.dev/ivas');
    expect(req.request.method).toBe('GET');
    req.flush('Mock Error', { status: 401, statusText: 'Unauthorized' });
    await Promise.resolve(); // wait for loader to return
    expect(service.userIvas.isLoading()).toBe(false);
    const error = service.userIvas.error() as HttpErrorResponse;
    expect(error).toBeDefined();
    expect(error.status).toBe(401);
    expect(() => service.userIvas.value()).toThrow();
  });

  it('should get all IVAs', async () => {
    service.loadAllIvas();
    expect(service.allIvas.isLoading()).toBe(true);
    expect(service.allIvas.error()).toBeUndefined();
    expect(service.allIvas.value()).toEqual([]);
    expect(service.userIvas.isLoading()).toBe(false);
    testBed.tick();
    const req = httpMock.expectOne('http://mock.dev/auth/ivas');
    expect(req.request.method).toBe('GET');
    req.flush(allIvas);
    await Promise.resolve(); // wait for loader to return
    expect(service.allIvas.isLoading()).toBe(false);
    expect(service.allIvas.error()).toBeUndefined();
    expect(service.allIvas.value()).toEqual(allIvas);
  });

  it('should pass server errors when getting all IVAs', async () => {
    service.loadAllIvas();
    expect(service.allIvas.isLoading()).toBe(true);
    expect(service.allIvas.error()).toBeUndefined();
    expect(service.allIvas.value()).toEqual([]);
    expect(service.userIvas.isLoading()).toBe(false);
    testBed.tick();
    const req = httpMock.expectOne('http://mock.dev/auth/ivas');
    expect(req.request.method).toBe('GET');
    req.flush('Mock Error', { status: 401, statusText: 'Server Error' });
    await Promise.resolve(); // wait for loader to return
    expect(service.allIvas.isLoading()).toBe(false);
    const error = service.allIvas.error() as HttpErrorResponse;
    expect(error).toBeDefined();
    expect(error.status).toBe(401);
    expect(error.statusText).toBe('Server Error');
    expect(() => service.allIvas.value()).toThrow();
  });

  it('should create an IVA for the current user', async () => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.tick();
    const idPromise = firstValueFrom(
      service.createIva({ type: IvaType.Phone, value: '123/456' }),
    );
    const req = httpMock.expectOne('http://mock.dev/auth/users/doe@test.dev/ivas');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ type: IvaType.Phone, value: '123/456' });
    req.flush({ id: 'TEST123456' });
    expect(await idPromise).toEqual('TEST123456');
  });

  it('should return an error if IVA to be created is missing a value', async () => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.tick();
    let message = 'none';
    try {
      await firstValueFrom(service.createIva({ type: IvaType.Phone, value: '' }));
    } catch (e) {
      message = (e as Error).message;
    }
    expect(message).toBe('IVA type or value missing');
  });

  it('should return an error if IVA is created while not logged in', async () => {
    currentUserId.set(null); // mock logout
    testBed.tick();
    let message = 'none';
    try {
      await firstValueFrom(
        service.createIva({ type: IvaType.Phone, value: '123/456' }),
      );
    } catch (e) {
      message = (e as Error).message;
    }
    expect(message).toBe('Not authenticated');
  });

  it('should pass a server error when IVA is created', async () => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.tick();
    const creationPromise = firstValueFrom(
      service.createIva({ type: IvaType.Phone, value: '123/456' }),
    );

    const req = httpMock.expectOne('http://mock.dev/auth/users/doe@test.dev/ivas');
    expect(req.request.method).toBe('POST');
    req.flush('Mock Error', { status: 500, statusText: 'Server Error' });
    let status = 0;
    try {
      await creationPromise;
    } catch (e) {
      status = (e as HttpErrorResponse).status;
    }
    expect(status).toBe(500);
  });

  it('should delete an IVA for the current user', async () => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.tick();
    const deletionPromise = firstValueFrom(service.deleteIva({ ivaId: 'TEST123456' }));
    const req = httpMock.expectOne(
      'http://mock.dev/auth/users/doe@test.dev/ivas/TEST123456',
    );
    expect(req.request.method).toBe('DELETE');
    expect(req.request.body).toBeNull();
    req.flush(null);
    expect(await deletionPromise).toBeNull();
  });

  it('should return an error if the IVA to be deleted has no ID', async () => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.tick();
    let message = 'none';
    try {
      await firstValueFrom(service.deleteIva({ ivaId: '' }));
    } catch (error) {
      message = (error as Error).message;
    }
    expect(message).toBe('IVA ID missing');
  });

  it('should return an error if IVA is deleted while not logged in', async () => {
    currentUserId.set(null); // mock logout
    testBed.tick();
    let message = 'none';
    try {
      await firstValueFrom(service.deleteIva({ ivaId: 'TEST123456' }));
    } catch (error) {
      message = (error as Error).message;
    }
    expect(message).toBe('Not authenticated');
  });

  it('should pass a server error when IVA is deleted', async () => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.tick();
    const deletionPromise = firstValueFrom(service.deleteIva({ ivaId: 'TEST123456' }));
    const req = httpMock.expectOne(
      'http://mock.dev/auth/users/doe@test.dev/ivas/TEST123456',
    );

    expect(req.request.method).toBe('DELETE');
    req.flush('Mock Error', { status: 500, statusText: 'Server Error' });
    let status = 0;
    try {
      await deletionPromise;
    } catch (error) {
      status = (error as HttpErrorResponse).status;
    }
    expect(status).toBe(500);
  });

  it('should unverify an IVA for the current user', async () => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.tick();
    const unverifyPromise = firstValueFrom(service.unverifyIva('TEST123456'));
    const req = httpMock.expectOne('http://mock.dev/auth/rpc/ivas/TEST123456/unverify');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toBeNull();
    req.flush(null);
    expect(await unverifyPromise).toBeNull();
  });

  it('should request verification of an IVA for the current user', async () => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.tick();
    const codePromise = firstValueFrom(
      service.requestCodeForIva('TEST123456', IvaType.Phone),
    );
    const req = httpMock.expectOne(
      'http://mock.dev/auth/rpc/ivas/TEST123456/request-code',
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toBeNull();
    req.flush(null);
    expect(await codePromise).toBeNull();
  });

  it('should create a verification code for an IVA of the current user', async () => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.tick();
    const codePromise = firstValueFrom(service.createCodeForIva('TEST123456'));

    const req = httpMock.expectOne(
      'http://mock.dev/auth/rpc/ivas/TEST123456/create-code',
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toBeNull();
    req.flush({ verification_code: 'CODE789' });
    expect(await codePromise).toBe('CODE789');
  });

  it('should confirm transmission of IVA verification for the current user', async () => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.tick();
    const confirmPromise = firstValueFrom(
      service.confirmTransmissionForIva('TEST123456'),
    );
    const req = httpMock.expectOne(
      'http://mock.dev/auth/rpc/ivas/TEST123456/code-transmitted',
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toBeNull();
    req.flush(null);
    expect(await confirmPromise).toBeNull();
  });

  it('should validate an IVA verification for the current user', async () => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.tick();
    const validatePromise = firstValueFrom(
      service.validateCodeForIva('TEST123456', 'CODE789'),
    );
    const req = httpMock.expectOne(
      'http://mock.dev/auth/rpc/ivas/TEST123456/validate-code',
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ verification_code: 'CODE789' });
    req.flush(null);
    expect(await validatePromise).toBeNull();
  });

  it('should pass error status for an invalid IVA verification code', async () => {
    currentUserId.set('doe@test.dev'); // mock login
    testBed.tick();
    const validatePromise = firstValueFrom(
      service.validateCodeForIva('TEST123456', 'CODE789'),
    );
    const req = httpMock.expectOne(
      'http://mock.dev/auth/rpc/ivas/TEST123456/validate-code',
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ verification_code: 'CODE789' });
    req.flush('Mock Error', { status: 403, statusText: 'Forbidden' });
    let status = 0;
    try {
      await validatePromise;
    } catch (error) {
      status = (error as HttpErrorResponse).status;
    }
    expect(status).toBe(403);
  });
});
