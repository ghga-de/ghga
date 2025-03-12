/**
 * Tests for the Umami Tracker Service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { TestBed } from '@angular/core/testing';

import { ConfigService } from './config.service';
import { UmamiService } from './umami.service';

/**
 * This mock contains the backend url and website id for the Umami service.
 */
class MockConfigService {
  umami_url = 'https://umami.test';
  umami_website_id = 'test-website-id';
}

/**
 * We don't really need to test the Umami service for anything other than to check if it constructs.
 * All other functionality is internal and therefore a black box for our considerations.
 * Integration into our application is only done by injecting the service and by adding data-umami-events to clickable elements.
 */
describe('UmamiService', () => {
  let service: UmamiService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [{ provide: ConfigService, useClass: MockConfigService }],
    });
    service = TestBed.inject(UmamiService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
