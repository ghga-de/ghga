/**
 * The Data Access service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient, httpResource } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { AuthService } from '@app/auth/services/auth.service';
import { ConfigService } from '@app/shared/services/config.service';
import { NotificationService } from '@app/shared/services/notification.service';
import { Observable, tap } from 'rxjs';
import {
  AccessGrant,
  AccessGrantFilter,
  AccessGrantStatus,
  AccessRequest,
  AccessRequestDetailData,
  AccessRequestFilter,
  AccessRequestStatus,
  GrantedAccessRequest,
} from '../models/access-requests';

/**
 *  This service handles state and management of access requests (to datasets)
 */
@Injectable({ providedIn: 'root' })
export class AccessRequestService {
  #http = inject(HttpClient);
  #auth = inject(AuthService);
  #notification = inject(NotificationService);
  #userId = computed<string | undefined>(() => this.#auth.user()?.id || undefined);
  #config = inject(ConfigService);

  #arsBaseUrl = this.#config.arsUrl;
  #arsEndpointUrl = `${this.#arsBaseUrl}/access-requests`;
  #arsManagementUrl = `${this.#arsBaseUrl}/access-grants`;

  #userAccessRequestsUrl = (userId: string) =>
    `${this.#arsEndpointUrl}?user_id=${userId}`;

  performAccessRequest = (data: AccessRequestDetailData) => {
    this.#http
      .post<void>(this.#arsEndpointUrl, {
        user_id: data.userId,
        dataset_id: data.datasetID,
        email: data.email,
        request_text: data.description,
        access_starts: data.fromDate?.toISOString(),
        access_ends: data.untilDate?.toISOString(),
      })
      .subscribe({
        next: () => {
          this.userAccessRequests.reload();
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
   * Resource for loading the current user's access requests
   */
  userAccessRequests = httpResource<AccessRequest[]>(
    () => {
      const userId = this.#userId();
      return userId ? this.#userAccessRequestsUrl(userId) : undefined;
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
   * The list of granted access requests of the current user
   */
  grantedUserAccessRequests = computed(() =>
    this.userAccessRequests
      .value()
      .filter((ar: AccessRequest) => ar.status == 'allowed')
      .map((request: AccessRequest) => {
        const expiryDate = new Date(request.access_ends);
        let grantedAccessRequest: GrantedAccessRequest = {
          request,
          isExpired: expiryDate < new Date(),
          daysRemaining: this.daysUntil(expiryDate),
        };
        return grantedAccessRequest;
      }),
  );

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
    () => (this.#loadAllAccessRequests() ? this.#arsEndpointUrl : undefined),
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

  /** Resource for loading an individual access request. */
  accessRequest = httpResource<AccessRequest>(
    () => {
      const id = this.#loadSingle();
      if (!id) return undefined;
      return `${this.#arsEndpointUrl}/${id}`;
    },
    {
      defaultValue: undefined,
      parse: (raw) => raw as AccessRequest,
    },
  );

  /**
   * Update the lists of access requests locally.
   * @param id - the ID of the updated access request
   * @param changes - the changes to the access request which may be partial
   */
  #updateAccessRequestLocally(id: string, changes: any): void {
    const oldRequest = this.allAccessRequests.value().find((ar) => ar.id === id);
    if (!oldRequest) return;

    if (changes.status != oldRequest.status) {
      changes.status_changed = new Date().toISOString();
      changes.changed_by = this.#auth.user()?.id || null;
    }

    const newRequest = { ...oldRequest, ...changes };

    const update = (accessRequests: AccessRequest[]) =>
      accessRequests.map((ar) => (ar.id === id ? newRequest : ar));

    this.userAccessRequests.value.set(update(this.userAccessRequests.value()));
    this.allAccessRequests.value.set(update(this.allAccessRequests.value()));
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
      .patch<null>(`${this.#arsEndpointUrl}/${id}`, changes)
      .pipe(tap(() => this.#updateAccessRequestLocally(id, changes)));
  }

  // signal to load all users' access grants
  #loadAllAccessGrants = signal<boolean>(false);

  /**
   * Load all users' access grants
   */
  loadAllAccessGrants(): void {
    this.#loadAllAccessGrants.set(true);
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
    () => (this.#loadAllAccessGrants() ? this.#arsManagementUrl : undefined),
    {
      defaultValue: [],
    },
  );

  allAccessGrants = computed<AccessGrant[]>(() => {
    const grants = this.allAccessGrantsResource.value();
    if (grants && Array.isArray(grants)) {
      return grants.map((grant) => {
        const updatedGrant = { ...grant };
        updatedGrant.status = this.computeStatusForAccessGrant(grant);
        return updatedGrant;
      });
    }
    return [];
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

  allAccessGrantsFiltered = computed(() => {
    let grants = this.allAccessGrants();
    const filter = this.#allAccessGrantsFilter();
    if (grants.length && filter) {
      if (filter.dataset_id !== undefined && filter.dataset_id !== '') {
        grants = grants.filter((g) =>
          g.dataset_id.includes(filter.dataset_id as string),
        );
      }
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
            (filter.status === 'Active' && has_started && !has_ended) ||
            (filter.status === 'Expired' && has_ended) ||
            (filter.status === 'Waiting' && !has_started)
          );
        });
      }
    }
    return grants;
  });
}
