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
import { catchError, firstValueFrom, Observable, tap } from 'rxjs';
import {
  AccessRequest,
  AccessRequestDialogData,
  AccessRequestFilter,
  GrantedAccessRequest,
} from '../models/access-requests';

/**
 *  This service handles state and management of access requests (to datasets)
 */
@Injectable({
  providedIn: 'root',
})
export class AccessRequestService {
  #http = inject(HttpClient);
  #auth = inject(AuthService);
  #notification = inject(NotificationService);
  #userId = computed<string | undefined>(() => this.#auth.user()?.id || undefined);
  #config = inject(ConfigService);

  #arsBaseUrl = this.#config.arsUrl;
  #arsEndpointUrl = `${this.#arsBaseUrl}/access-requests`;
  #userAccessRequestsUrl = (userId: string) =>
    `${this.#arsEndpointUrl}?user_id=${userId}`;

  performAccessRequest = (data: AccessRequestDialogData) => {
    try {
      firstValueFrom(
        this.#http
          .post<void>(this.#arsEndpointUrl, {
            user_id: data.userId,
            dataset_id: data.datasetID,
            email: data.email,
            request_text: data.description,
            access_starts: data.fromDate?.toDateString(),
            access_ends: data.untilDate?.toDateString(),
          })
          .pipe(
            catchError(async () =>
              this.#notification.showError(
                'There was an error submitting your access request.',
              ),
            ),
          ),
      ).then(async () => {
        this.userAccessRequests.reload();
        this.#notification.showSuccess('Your request has been submitted successfully.');
      });
    } catch (error) {
      this.#notification.showError(
        'There was an error submitting your access request: ' + error,
      );
    }
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
  #loadAll = signal<boolean>(false);

  /**
   * Load all users' access requests
   */
  loadAllAccessRequests(): void {
    this.#loadAll.set(true);
  }

  /**
   * The current filter for the list of all access requests
   */
  allAccessRequestsFilter = computed(
    () =>
      this.#allAccessRequestsFilter() ?? {
        datasetId: '',
        name: '',
        fromDate: undefined,
        toDate: undefined,
        status: undefined,
      },
  );

  /**
   * Set a filter for the list of all access requests
   * @param filter - the filter to apply
   */
  setAllAccessRequestsFilter(filter: AccessRequestFilter): void {
    this.#allAccessRequestsFilter.set(
      filter.datasetId ||
        filter.name ||
        filter.fromDate ||
        filter.toDate ||
        filter.status
        ? filter
        : undefined,
    );
  }

  /**
   * Resource for loading all access requests.
   * Note: We do the filtering currently only on the client side,
   * but in principle we can also do some filtering on the sever.
   */
  allAccessRequests = httpResource<AccessRequest[]>(
    () => (this.#loadAll() ? this.#arsEndpointUrl : undefined),
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
      const datasetId = filter.datasetId.trim().toLowerCase();
      if (datasetId) {
        requests = requests.filter((ar) =>
          ar.dataset_id.toLowerCase().includes(datasetId),
        );
      }
      const name = filter.name.trim().toLowerCase();
      if (name) {
        requests = requests.filter((ar) =>
          ar.full_user_name.toLowerCase().includes(name),
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
    }
    return requests;
  });

  /**
   * Update the lists of access requests locally
   * @param accessRequest - the access request that has been modified
   */
  #updateAccessRequestLocally(accessRequest: AccessRequest): void {
    const update = (accessRequests: AccessRequest[]) =>
      accessRequests.map((ar) => (ar.id === accessRequest.id ? accessRequest : ar));

    accessRequest.status_changed = new Date().toISOString();
    accessRequest.changed_by = this.#auth.user()?.id || null;

    this.userAccessRequests.value.set(update(this.userAccessRequests.value()));
    this.allAccessRequests.value.set(update(this.allAccessRequests.value()));
  }

  /**
   * Process an access request, i.e. approve or disapprove it.
   * This can only be done by a data steward.
   * Currently, we can only set the status, and the selected IVA,
   * other fields like the access dates cannot be modified here.
   * This method also updates the local state if the modification was successful.
   * @param accessRequest - the access request with the new status
   * @returns An observable that emits null when the request has been processed
   */
  processRequest(accessRequest: AccessRequest): Observable<null> {
    const { id, iva_id, status } = accessRequest;
    return this.#http
      .patch<null>(`${this.#arsEndpointUrl}/${id}`, { iva_id, status })
      .pipe(tap(() => this.#updateAccessRequestLocally(accessRequest)));
  }
}

let dateInOneYear = new Date();
dateInOneYear.setDate(dateInOneYear.getDate() + 365);
dateInOneYear.setTime(dateInOneYear.getTime() + 60 * 60 * 1000);

let dateYesterday = new Date();
dateYesterday.setDate(dateYesterday.getDate() - 1);

let dateOneYearAgo = new Date();
dateOneYearAgo.setDate(dateOneYearAgo.getDate() - 365);

/**
 * Mock for the Access Request Service
 */
export class MockAccessRequestService {
  userAccessRequests = {
    isLoading: signal(false),
    error: signal(undefined),
  };
  grantedUserAccessRequests = signal([
    {
      request: {
        id: 'GHGAD15111403130971',
        user_id: '',
        dataset_id: 'GHGAD588887987',
        full_user_name: 'aacaffeecaffeecaffeecaffeecaffeecaffeeaad@lifescience-ri.eu',
        email: 'aacaffeecaffeecaffeecaffeecaffeecaffeeaad@lifescience-ri.eu',
        request_text: 'unit test request',
        access_starts: Date.now().toString(),
        access_ends: dateInOneYear.toString(),
        request_created: Date.now().toString(),
        status: 'approved',
        status_changed: '',
        changed_by: '',
        iva_id: '',
      },
      isExpired: false,
      daysRemaining: 365,
    },
    {
      request: {
        id: 'GHGAD15111403130451',
        user_id: '',
        dataset_id: 'GHGAD588887987',
        full_user_name: 'aacaffeecaffeecaffeecaffeecaffeecaffeeaad@lifescience-ri.eu',
        email: 'aacaffeecaffeecaffeecaffeecaffeecaffeeaad@lifescience-ri.eu',
        request_text: 'unit test request 2',
        access_starts: dateOneYearAgo.toString(),
        access_ends: dateYesterday.toString(),
        request_created: dateOneYearAgo.toString(),
        status: 'approved',
        status_changed: '',
        changed_by: '',
        iva_id: '',
      },
      isExpired: false,
      daysRemaining: -1,
    },
  ]);
  pendingUserAccessRequests = signal([
    {
      id: 'GHGAD15111403130971',
      user_id: '',
      dataset_id: 'GHGAD588887987',
      full_user_name: 'aacaffeecaffeecaffeecaffeecaffeecaffeeaad@lifescience-ri.eu',
      email: 'aacaffeecaffeecaffeecaffeecaffeecaffeeaad@lifescience-ri.eu',
      request_text: 'unit test request',
      access_starts: Date.now().toString(),
      access_ends: Date.now().toString(),
      request_created: Date.now().toString(),
      status: 'pending',
      status_changed: '',
      changed_by: '',
      iva_id: '',
    },
  ]);
}
