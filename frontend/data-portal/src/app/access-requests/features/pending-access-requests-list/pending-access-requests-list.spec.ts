/**
 * Tests for the Pending Access Request List Component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { TestBed } from '@angular/core/testing';
import { accessRequests } from '@app/../mocks/data';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { render, RenderResult, screen } from '@testing-library/angular';
import { PendingAccessRequestsList } from './pending-access-requests-list';

describe('PendingAccessRequestsList', () => {
  let result: RenderResult<PendingAccessRequestsList>;
  let accessRequestService: AccessRequestService;

  beforeEach(async () => {
    result = await render(PendingAccessRequestsList, {
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
      ],
      routes: [],
    });
    accessRequestService = TestBed.inject(AccessRequestService);
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
    const pending = accessRequests.filter((ar) => ar.status === 'pending');
    expect(screen.getAllByRole('listitem')).toHaveLength(pending.length);
    expect(
      screen.getAllByRole('link', { name: pending[0].dataset_id })[0],
    ).toHaveAttribute('href', `/dataset/${pending[0].dataset_id}`);
  });

  it('should fetch the access requests again when refreshed', () => {
    const reload = vitest.spyOn(accessRequestService, 'reloadUserAccessRequests');
    result.fixture.componentInstance.refresh();
    expect(reload).toHaveBeenCalledTimes(1);
  });
});
