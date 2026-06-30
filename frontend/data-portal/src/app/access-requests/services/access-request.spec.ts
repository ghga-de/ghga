/**
 * Tests for the data access service.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ConfigService } from '@app/shared/services/config';
import { AccessGrant, AccessGrantStatus } from '../models/access-requests';
import { AccessRequestService } from './access-request';

/**
 * Mock the config service as needed by the auth service
 */
class MockConfigService {
  authUrl = 'http://mock.dev/auth';
  arsUrl = 'http://mock.dev/ars';
}

/**
 * Build a minimal access grant for the given user, dataset and validity period.
 * @param overrides - the distinguishing fields of the grant
 * @returns a fully populated access grant
 */
function makeGrant(overrides: Partial<AccessGrant> & { id: string }): AccessGrant {
  return {
    user_id: 'doe@test.dev',
    dataset_id: 'DS-1',
    created: '2025-01-01T00:00:00Z',
    valid_from: '2025-01-01T00:00:00Z',
    valid_until: '2025-12-31T00:00:00Z',
    dataset_title: 'Test dataset',
    user_email: 'doe@home.org',
    user_name: 'John Doe',
    user_title: 'Dr.',
    dac_alias: 'SOME-DAC',
    dac_email: 'dac@some.org',
    iva_id: null,
    ...overrides,
  };
}

describe('AccessRequestService', () => {
  let service: AccessRequestService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ConfigService, useClass: MockConfigService },
      ],
    });
    service = TestBed.inject(AccessRequestService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('aggregating the current access state of grants', () => {
    const day = 24 * 60 * 60 * 1000;
    const iso = (offsetDays: number): string =>
      new Date(Date.now() + offsetDays * day).toISOString();

    beforeEach(() => {
      service.allAccessGrantsResource.value.set([
        // DS-1: a renewal — an expired grant plus a currently active one
        makeGrant({
          id: 'g-expired',
          dataset_id: 'DS-1',
          created: iso(-400),
          valid_from: iso(-380),
          valid_until: iso(-20),
        }),
        makeGrant({
          id: 'g-active',
          dataset_id: 'DS-1',
          created: iso(-20),
          valid_from: iso(-10),
          valid_until: iso(355),
        }),
        // DS-2: a grant that has not started yet
        makeGrant({
          id: 'g-waiting',
          dataset_id: 'DS-2',
          created: iso(-5),
          valid_from: iso(10),
          valid_until: iso(375),
        }),
        // DS-3: a grant that has fully ended
        makeGrant({
          id: 'g-gone',
          dataset_id: 'DS-3',
          created: iso(-400),
          valid_from: iso(-380),
          valid_until: iso(-20),
        }),
      ]);
    });

    it('lets the most permissive state win across grants', () => {
      // active wins over the co-existing expired grant of the same dataset
      expect(service.grantStateFor('doe@test.dev', 'DS-1')).toBe(
        AccessGrantStatus.active,
      );
      expect(service.grantStateFor('doe@test.dev', 'DS-2')).toBe(
        AccessGrantStatus.waiting,
      );
      expect(service.grantStateFor('doe@test.dev', 'DS-3')).toBe(
        AccessGrantStatus.expired,
      );
    });

    it('returns no state when there is no matching grant', () => {
      expect(service.grantStateFor('doe@test.dev', 'DS-unknown')).toBeUndefined();
      expect(service.grantStateFor('other@test.dev', 'DS-1')).toBeUndefined();
    });

    it('returns all matching grants with their status, ordered by creation', () => {
      const grants = service.grantsFor('doe@test.dev', 'DS-1');
      expect(grants.map((g) => g.id)).toEqual(['g-expired', 'g-active']);
      expect(grants.map((g) => g.status)).toEqual([
        AccessGrantStatus.expired,
        AccessGrantStatus.active,
      ]);
    });
  });
});
