/**
 * The Data Access service a mock
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
// eslint-disable-next-line boundaries/element-types
import { accessGrants, accessRequests } from '@app/../mocks/data';
import { AccessGrantFilter } from '../models/access-requests';

/**
 * Mock for the Access Request Service
 */
export class MockAccessRequestService {
  accessRequest = {
    isLoading: signal(false),
    error: signal(undefined),
    value: signal(accessRequests[4]),
  };
  allAccessRequests = {
    isLoading: signal(false),
    error: signal(undefined),
    value: signal(accessRequests),
  };
  userAccessRequests = {
    isLoading: signal(false),
    error: signal(undefined),
    value: signal(accessRequests.filter((ar) => ar.user_id === 'doe@test.dev')),
  };
  grantedUserAccessRequests = signal(
    accessRequests.filter((ar) => ar.status === 'approved'),
  );
  pendingUserAccessRequests = signal(
    accessRequests.filter((ar) => ar.status === 'pending'),
  );
  loadAllAccessGrants = () => {};
  allAccessGrantsFilter = () => ({
    status: undefined,
    user: undefined,
    dataset_id: undefined,
  });
  setAllAccessGrantsFilter = (filter: AccessGrantFilter) => {};
  allAccessGrantsFiltered = () => accessGrants;
}
