/**
 * The Data Access service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient, httpResource } from '@angular/common/http';
import { computed, inject, Service, signal } from '@angular/core';
import { AuthService } from '@app/auth/services/auth';
import { ConfigService } from '@app/shared/services/config';
import { NotificationService } from '@app/shared/services/notification';
import { volatileCacheContext } from '@app/shared/utils/http-cache';
import { CacheBucket, HttpCacheManager } from '@ngneat/cashew';
import { Observable, tap } from 'rxjs';
import {
  AccessGrant,
  AccessGrantFilter,
  AccessGrantStatus,
  AccessRequest,
  AccessRequestDetailData,
  AccessRequestFilter,
  AccessRequestStatus,
} from '../models/access-requests';

/**
 *  This service handles state and management of access requests (to datasets)
 */
@Service()
export class AccessRequestService {
  #http = inject(HttpClient);
  #auth = inject(AuthService);
  #httpCache = inject(HttpCacheManager);
  #notification = inject(NotificationService);
  #userId = computed<string | undefined>(() => this.#auth.user()?.id || undefined);
  #config = inject(ConfigService);

  #arsBaseUrl = this.#config.arsUrl;
  #arsRequestsUrl = `${this.#arsBaseUrl}/access-requests`;
  #arsGrantUrl = `${this.#arsBaseUrl}/access-grants`;

  #userAccessRequestsUrl = (userId: string) =>
    `${this.#arsRequestsUrl}?user_id=${userId}`;
  #userAccessGrantsUrl = (userId: string) => `${this.#arsGrantUrl}?user_id=${userId}`;

  // GET responses are cached by the cashew interceptor (see app.config.ts), so
  // reloading a resource replays the cached body unless the corresponding cache
  // entries are dropped first. Each resource collects its keys in a bucket that
  // the reload methods below invalidate.
  #userRequestsBucket = new CacheBucket();
  #allRequestsBucket = new CacheBucket();
  #requestBucket = new CacheBucket();
  #userGrantsBucket = new CacheBucket();
  #allGrantsBucket = new CacheBucket();

  #userRequestsContext = volatileCacheContext(this.#userRequestsBucket);
  #allRequestsContext = volatileCacheContext(this.#allRequestsBucket);
  #requestContext = volatileCacheContext(this.#requestBucket);
  #userGrantsContext = volatileCacheContext(this.#userGrantsBucket);
  #allGrantsContext = volatileCacheContext(this.#allGrantsBucket);

  performAccessRequest = (data: AccessRequestDetailData) => {
    this.#http
      .post<void>(this.#arsRequestsUrl, {
        user_id: data.userId,
        dataset_id: data.datasetID,
        email: data.email,
        request_text: data.description,
        access_starts: data.fromDate?.toISOString(),
        access_ends: data.untilDate?.toISOString(),
      })
      .subscribe({
        next: () => {
          this.reloadUserAccessRequests();
          this.#notification.showSuccess(
            'Your access request has been submitted successfully.',
          );
        },
        error: (err) => {
          console.error(err);
          this.#notification.showError(
            'Your access request could not be submitted. Please try again later.',
          );
        },
      });
  };

  /**
   * Resource for loading the currently logged-in user's access requests
   */
  userAccessRequests = httpResource<AccessRequest[]>(
    () => {
      const userId = this.#userId();
      if (!userId) return undefined;
      return {
        url: this.#userAccessRequestsUrl(userId),
        context: this.#userRequestsContext,
      };
    },
    {
      parse: (raw) =>
        (raw as AccessRequest[]).filter(
          ({ status }) => status === 'pending' || status === 'allowed',
        ),
      defaultValue: [],
    },
  );

  /**
   * Drop all cached access request and grant responses after one of them has
   * been changed. Only some of the lists are patched locally, and allowing a
   * request creates a grant, so the two are always invalidated together.
   */
  #invalidateRequestsAndGrants(): void {
    this.#httpCache.delete(this.#userRequestsBucket);
    this.#httpCache.delete(this.#allRequestsBucket);
    this.#httpCache.delete(this.#requestBucket);
    this.#httpCache.delete(this.#userGrantsBucket);
    this.#httpCache.delete(this.#allGrantsBucket);
  }

  /**
   * Fetch the current user's access requests again, bypassing the HTTP cache.
   */
  reloadUserAccessRequests(): void {
    this.#httpCache.delete(this.#userRequestsBucket);
    this.userAccessRequests.reload();
  }

  /**
   * Fetch the current user's access grants again, bypassing the HTTP cache.
   */
  reloadUserAccessGrants(): void {
    this.#httpCache.delete(this.#userGrantsBucket);
    this.userAccessGrants.reload();
  }

  /**
   * This function computes the number of full days between now and the date provided
   * @param dateUntil The reference date.
   * @returns The number of full days.
   */
  daysUntil(dateUntil: Date): number {
    const date = new Date();
    const diffTime = dateUntil.getTime() - date.getTime();
    return Math.floor(diffTime / (1000 * 60 * 60 * 24));
  }

  /**
   * The list of pending requests of the current user
   */
  pendingUserAccessRequests = computed(() =>
    this.userAccessRequests
      .value()
      .filter((ar: AccessRequest) => ar.status == 'pending'),
  );

  #allAccessRequestsFilter = signal<AccessRequestFilter | undefined>(undefined);

  // signal to load all users' access requests
  #loadAllAccessRequests = signal<boolean>(false);

  /**
   * Load all users' access requests
   */
  loadAllAccessRequests(): void {
    this.#loadAllAccessRequests.set(true);
  }

  /**
   * Fetch all users' access requests again, bypassing the HTTP cache.
   * Requests are created and processed by others while the manager is open, so
   * entering it must not show what was fetched earlier in the session.
   */
  reloadAllAccessRequests(): void {
    this.#httpCache.delete(this.#allRequestsBucket);
    if (this.#loadAllAccessRequests()) {
      this.allAccessRequests.reload();
    } else {
      this.loadAllAccessRequests();
    }
  }

  /**
   * The current filter for the list of all access requests
   */
  allAccessRequestsFilter = computed(
    () =>
      this.#allAccessRequestsFilter() ?? {
        ticketId: '',
        dataset: '',
        requester: '',
        dac: '',
        fromDate: undefined,
        toDate: undefined,
        status: AccessRequestStatus.pending,
        requestText: '',
        noteToRequester: '',
        internalNote: '',
      },
  );

  /**
   * Set a filter for the list of all access requests
   * @param filter - the filter to apply
   */
  setAllAccessRequestsFilter(filter: AccessRequestFilter): void {
    this.#allAccessRequestsFilter.set(filter);
  }

  /**
   * Resource for loading all access requests.
   * Note: We do the filtering currently only on the client side,
   * but in principle we can also do some filtering on the sever.
   */
  allAccessRequests = httpResource<AccessRequest[]>(
    () =>
      this.#loadAllAccessRequests()
        ? { url: this.#arsRequestsUrl, context: this.#allRequestsContext }
        : undefined,
    {
      defaultValue: [],
    },
  );

  /**
   * Signal that gets all access requests filtered by the current filter
   */
  allAccessRequestsFiltered = computed(() => {
    let requests = this.allAccessRequests.value();
    const filter = this.#allAccessRequestsFilter();
    if (requests.length && filter) {
      const ticketId = filter.ticketId?.trim().toLowerCase();
      if (ticketId) {
        requests = requests.filter((ar) =>
          ar.ticket_id?.toLowerCase().includes(ticketId),
        );
      }
      const dataset = filter.dataset?.trim().toLowerCase();
      if (dataset) {
        requests = requests.filter(
          (ar) =>
            ar.dataset_id.toLowerCase().includes(dataset) ||
            ar.dataset_title.toLowerCase().includes(dataset),
        );
      }
      const name = filter.requester?.trim().toLowerCase();
      if (name) {
        requests = requests.filter(
          (ar) =>
            ar.full_user_name.toLowerCase().includes(name) ||
            ar.email.toLowerCase().includes(name),
        );
      }
      const dac = filter.dac?.trim().toLowerCase();
      if (dac) {
        requests = requests.filter(
          (ar) =>
            ar.dac_alias.toLowerCase().includes(dac) ||
            ar.dac_email.toLowerCase().includes(dac),
        );
      }
      if (filter.fromDate) {
        const fromDate = filter.fromDate.toISOString();
        requests = requests.filter((ar) => ar.request_created >= fromDate);
      }
      if (filter.toDate) {
        const toDate = filter.toDate.toISOString();
        requests = requests.filter((ar) => ar.request_created <= toDate);
      }
      if (filter.status) {
        requests = requests.filter((ar) => ar.status === filter.status);
      }
      const requestText = filter.requestText?.trim().toLowerCase();
      if (requestText) {
        requests = requests.filter((ar) =>
          ar.request_text.toLowerCase().includes(requestText),
        );
      }
      const noteToRequester = filter.noteToRequester?.trim().toLowerCase();
      if (noteToRequester) {
        requests = requests.filter((ar) =>
          ar.note_to_requester?.toLowerCase().includes(noteToRequester),
        );
      }
      const internalNote = filter.internalNote?.trim().toLowerCase();
      if (internalNote) {
        requests = requests.filter((ar) =>
          ar.internal_note?.toLowerCase().includes(internalNote),
        );
      }
    }
    return requests;
  });

  // signal to load an individual access request
  #loadSingle = signal<string>('');

  /**
   * Load an individual access request
   * @param id - the ID of the access request to load
   */
  loadAccessRequest(id: string): void {
    this.#loadSingle.set(id);
  }

  /**
   * Fetch an individual access request again, bypassing the HTTP cache.
   * Requesting the one that is already loaded would otherwise not issue any
   * request at all, since the resource request would remain unchanged.
   * @param id - the ID of the access request to load
   */
  reloadAccessRequest(id: string): void {
    this.#httpCache.delete(this.#requestBucket);
    if (this.#loadSingle() === id) {
      this.accessRequest.reload();
    } else {
      this.loadAccessRequest(id);
    }
  }

  /** Resource for loading an individual access request. */
  accessRequest = httpResource<AccessRequest>(
    () => {
      const id = this.#loadSingle();
      if (!id) return undefined;
      return {
        url: `${this.#arsRequestsUrl}/${id}`,
        context: this.#requestContext,
      };
    },
    {
      defaultValue: undefined,
    },
  );

  /**
   * Update the lists of access requests locally.
   * @param id - the ID of the updated access request
   * @param changes - the changes to the access request which may be partial
   */
  #updateAccessRequestLocally(id: string, changes: Partial<AccessRequest>): void {
    this.#invalidateRequestsAndGrants();
    const withStatusChange = (
      request: AccessRequest,
      changes: Partial<AccessRequest>,
    ) =>
      'status' in changes && request.status !== changes.status
        ? {
            ...changes,
            status_changed: new Date().toISOString(),
            changed_by: this.#auth.user()?.id || null,
          }
        : changes;
    if (!this.accessRequest.error()) {
      const oldRequest = this.accessRequest.value();
      if (oldRequest && oldRequest.id === id) {
        const newRequest = { ...oldRequest, ...withStatusChange(oldRequest, changes) };
        this.accessRequest.value.set(newRequest);
      }
    }
    if (!this.userAccessRequests.error()) {
      const oldRequest = this.userAccessRequests.value().find((ar) => ar.id === id);
      if (oldRequest) {
        const newRequest = { ...oldRequest, ...withStatusChange(oldRequest, changes) };
        const update = (accessRequests: AccessRequest[]) =>
          accessRequests.map((ar) => (ar.id === id ? newRequest : ar));
        this.userAccessRequests.value.set(update(this.userAccessRequests.value()));
      }
    }
    if (!this.allAccessRequests.error()) {
      const oldRequest = this.allAccessRequests.value().find((ar) => ar.id === id);
      if (oldRequest) {
        const newRequest = { ...oldRequest, ...withStatusChange(oldRequest, changes) };
        const update = (accessRequests: AccessRequest[]) =>
          accessRequests.map((ar) => (ar.id === id ? newRequest : ar));
        this.allAccessRequests.value.set(update(this.allAccessRequests.value()));
      }
    }
  }

  /**
   * Update one or more properties of an access request.
   * This can only be done by a data steward.
   * This method also updates the local state if the modification was successful.
   * @param id - the access request ID
   * @param changes - the changes to the access request which may be partial
   * @returns An observable that emits null when the request has been processed
   */
  updateRequest(id: string, changes: Partial<AccessRequest>): Observable<null> {
    return this.#http
      .patch<null>(`${this.#arsRequestsUrl}/${id}`, changes)
      .pipe(tap(() => this.#updateAccessRequestLocally(id, changes)));
  }

  // signal to load all users' access grants
  #loadAllAccessGrants = signal<boolean>(false);

  /**
   * Load all users' access grants
   * @param force - whether to force reload the grants
   */
  loadAllAccessGrants(force?: boolean): void {
    this.#loadAllAccessGrants.set(true);
    if (force) {
      this.#httpCache.delete(this.#allGrantsBucket);
      this.allAccessGrantsResource.reload();
    }
  }

  /**
   * Fetch all users' access grants again, bypassing the HTTP cache.
   */
  reloadAllAccessGrants(): void {
    this.loadAllAccessGrants(this.#loadAllAccessGrants());
  }

  // Similar structure to what we do for access requests but for access grants
  #allAccessGrantsFilter = signal<AccessGrantFilter | undefined>(undefined);
  allAccessGrantsFilter = computed(
    () =>
      this.#allAccessGrantsFilter() ?? {
        status: undefined,
        user: undefined,
        dataset_id: undefined,
      },
  );

  /**
   * Load all access grants
   * @param filter the filter to apply
   */
  setAllAccessGrantsFilter(filter: AccessGrantFilter): void {
    this.#allAccessGrantsFilter.set(filter);
  }

  allAccessGrantsResource = httpResource<AccessGrant[]>(
    () =>
      this.#loadAllAccessGrants()
        ? { url: this.#arsGrantUrl, context: this.#allGrantsContext }
        : undefined,
    {
      defaultValue: [],
    },
  );

  allAccessGrants = computed<AccessGrant[]>(() => {
    return this.allAccessGrantsResource.error()
      ? []
      : this.allAccessGrantsResource.value().map((grant) => {
          const updatedGrant = { ...grant };
          updatedGrant.status = this.computeStatusForAccessGrant(grant);
          return updatedGrant;
        });
  });

  computeStatusForAccessGrant = (grant: AccessGrant): AccessGrantStatus => {
    const now = new Date();
    const hasStarted = now >= new Date(grant.valid_from);
    const hasEnded = now >= new Date(grant.valid_until);
    if (hasStarted && !hasEnded) {
      return AccessGrantStatus.active;
    } else if (hasEnded) {
      return AccessGrantStatus.expired;
    } else {
      return AccessGrantStatus.waiting;
    }
  };

  /**
   * Build the composite key used to group access grants by user and dataset.
   * @param userId - the user ID
   * @param datasetId - the dataset ID
   * @returns the composite key
   */
  #grantKey = (userId: string, datasetId: string): string => `${userId} ${datasetId}`;

  /**
   * Aggregate the current access state across all grants of the same user and
   * dataset. Since a user can hold multiple grants for one dataset (e.g. after
   * a renewal), the most permissive current state wins: active if any grant is
   * currently active, otherwise waiting if any grant becomes valid in the
   * future, otherwise expired if grants exist but all have ended.
   * @param grants - the grants to aggregate (all for the same user and dataset)
   * @returns the aggregated grant status, or undefined if there are no grants
   */
  #aggregateGrantStatus(grants: AccessGrant[]): AccessGrantStatus | undefined {
    // Multiple passes are fine here: there is usually only one grant per
    // user and dataset (a handful at most after renewals).
    const statuses = grants.map(this.computeStatusForAccessGrant);
    if (statuses.includes(AccessGrantStatus.active)) return AccessGrantStatus.active;
    if (statuses.includes(AccessGrantStatus.waiting)) return AccessGrantStatus.waiting;
    return statuses.length ? AccessGrantStatus.expired : undefined;
  }

  /**
   * Map from the user/dataset key to all corresponding access grants (each with
   * its computed current status), derived from all loaded access grants. Grants
   * must have been loaded via loadAllAccessGrants() for this to be populated.
   */
  #grantsByUserAndDataset = computed<Map<string, AccessGrant[]>>(() => {
    const result = new Map<string, AccessGrant[]>();
    for (const grant of this.allAccessGrants()) {
      const key = this.#grantKey(grant.user_id, grant.dataset_id);
      const list = result.get(key);
      if (list) list.push(grant);
      else result.set(key, [grant]);
    }
    return result;
  });

  /**
   * Get all access grants for a given user and dataset, each with its computed
   * current status, ordered by creation date (oldest first).
   * Grants must have been loaded via loadAllAccessGrants().
   * @param userId - the user ID
   * @param datasetId - the dataset ID
   * @returns the matching access grants (empty if there are none)
   */
  grantsFor(userId: string, datasetId: string): AccessGrant[] {
    const grants = this.#grantsByUserAndDataset().get(
      this.#grantKey(userId, datasetId),
    );
    return grants ? [...grants].sort((a, b) => a.created.localeCompare(b.created)) : [];
  }

  /**
   * Map from the user/dataset key to the aggregated current grant state,
   * derived from all loaded access grants. Used to show the live access state
   * alongside the access requests in the manager list. Grants must have been
   * loaded via loadAllAccessGrants() for this to be populated.
   */
  #grantStateByUserAndDataset = computed<Map<string, AccessGrantStatus>>(() => {
    const result = new Map<string, AccessGrantStatus>();
    for (const [key, grants] of this.#grantsByUserAndDataset()) {
      const status = this.#aggregateGrantStatus(grants);
      if (status) result.set(key, status);
    }
    return result;
  });

  /**
   * Get the aggregated current grant state for a given user and dataset.
   * @param userId - the user ID
   * @param datasetId - the dataset ID
   * @returns the aggregated grant status, or undefined if there is no grant
   */
  grantStateFor(userId: string, datasetId: string): AccessGrantStatus | undefined {
    return this.#grantStateByUserAndDataset().get(this.#grantKey(userId, datasetId));
  }

  allAccessGrantsFiltered = computed(() => {
    let grants = this.allAccessGrants();
    const filter = this.#allAccessGrantsFilter();
    if (grants.length && filter) {
      if (filter.dataset_id) {
        grants = grants.filter((g) =>
          g.dataset_id.includes(filter.dataset_id as string),
        );
      }
      if (filter.user) {
        grants = grants.filter(
          (g) =>
            g.user_name.toLowerCase().includes((filter.user as string).toLowerCase()) ||
            g.user_email.toLowerCase().includes((filter.user as string).toLowerCase()),
        );
      }
      if (filter.status !== undefined) {
        const now = new Date();

        grants = grants.filter((g) => {
          const has_started = now >= new Date(g.valid_from);
          const has_ended = now >= new Date(g.valid_until);
          return (
            (filter.status === 'active' && has_started && !has_ended) ||
            (filter.status === 'expired' && has_ended) ||
            (filter.status === 'waiting' && !has_started)
          );
        });
      }
    }
    return grants;
  });

  /**
   * Resource for loading the currently logged-in user's access grants
   */
  userAccessGrants = httpResource<AccessGrant[]>(
    () => {
      const userId = this.#userId();
      if (!userId) return undefined;
      return {
        url: this.#userAccessGrantsUrl(userId),
        context: this.#userGrantsContext,
      };
    },
    {
      parse: (raw) =>
        (raw as AccessGrant[]).map((g) => {
          g.status = this.computeStatusForAccessGrant(g);
          return g;
        }),
      defaultValue: [],
    },
  );

  /**
   * The list of active access grants of the current user with days remaining
   */
  activeUserAccessGrants = computed(() =>
    this.userAccessGrants
      .value()
      .filter((x) => x.status === 'active')
      .map((grant: AccessGrant) => ({
        ...grant,
        daysRemaining: this.daysUntil(new Date(grant.valid_until)),
      })),
  );

  /**
   * Remove the grant locally.
   * @param id - the ID of the grant to remove
   */
  #removeGrantLocally(id: string): void {
    this.#invalidateRequestsAndGrants();
    if (this.allAccessGrantsResource.error()) return;
    const newGrants = this.allAccessGrantsResource
      .value()
      .filter((grant) => grant.id !== id);
    this.allAccessGrantsResource.value.set(newGrants);
  }

  /**
   * Revoke an access grant.
   * This can only be done by a data steward.
   * This method also updates the local state if the modification was successful.
   * @param id - the grant ID
   * @returns An observable that emits null when the request has been processed
   */
  revokeAccessGrant(id: string): Observable<null> {
    return this.#http
      .delete<null>(`${this.#arsGrantUrl}/${id}`)
      .pipe(tap(() => this.#removeGrantLocally(id)));
  }
}
