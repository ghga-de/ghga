/**
 * This module contains the tests for the GrantedAccessGrantsListComponent.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { provideHttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { ConfigService } from '@app/shared/services/config';
import { provideHttpCache } from '@ngneat/cashew';
import { render, RenderResult, screen } from '@testing-library/angular';
import { ActiveAccessGrantsListComponent } from './active-access-grants-list';

const MockConfigService = {
  auth_url: '/test/auth',
};

describe('ActiveAccessGrantsListComponent', () => {
  let result: RenderResult<ActiveAccessGrantsListComponent>;
  let accessRequestService: AccessRequestService;

  beforeEach(async () => {
    result = await render(ActiveAccessGrantsListComponent, {
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: ConfigService, useValue: MockConfigService },
        provideHttpClient(),
        provideHttpCache(),
      ],
    });
    accessRequestService = TestBed.inject(AccessRequestService);
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
    expect(
      screen.getByText('You do not yet have access to any datasets.'),
    ).toBeVisible();
  });

  it('should fetch the access grants again when refreshed', () => {
    const reload = vitest.spyOn(accessRequestService, 'reloadUserAccessGrants');
    result.fixture.componentInstance.refresh();
    expect(reload).toHaveBeenCalledTimes(1);
  });
});
