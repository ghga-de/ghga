/**
 * The Data Access service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal, Signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { AuthService } from '@app/auth/services/auth.service';
import { ConfigService } from '@app/shared/services/config.service';
import { NotificationService } from '@app/shared/services/notification.service';
import { catchError, firstValueFrom, map } from 'rxjs';
// eslint-disable-next-line boundaries/element-types
import { AccessRequestDialogComponent } from '../features/access-request-dialog/access-request-dialog.component';
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
  #dialogRef: MatDialogRef<AccessRequestDialogComponent> | undefined;
  #http = inject(HttpClient);
  #auth = inject(AuthService);
  #notification = inject(NotificationService);
  #dialog = inject(MatDialog);
  #userId = computed<string | null>(() => this.#auth.user()?.id || null);
  #config = inject(ConfigService);

  #arsBaseUrl = this.#config.arsUrl;
  #arsEndpointUrl = `${this.#arsBaseUrl}/access-requests`;
  #userAccessRequestsUrl = (userId: string) =>
    `${this.#arsEndpointUrl}?user_id=${userId}`;

  showNewAccessRequestDialog = (datasetID: string) => {
    if (!this.#auth.isAuthenticated()) {
      this.#notification.showError('You must be logged in to perform this action');
      return;
    }

    const data: AccessRequestDialogData = {
      datasetID,
      email: this.#auth.email() || '',
      description: '',
      fromDate: undefined,
      untilDate: undefined,
      userId: '',
    };

    this.#dialogRef = this.#dialog.open(AccessRequestDialogComponent, {
      data,
    });

    this.#dialogRef
      .afterClosed()
      .subscribe((componentData) => this.#processAccessRequest(componentData));
  };

  #processAccessRequest = (data: AccessRequestDialogData) => {
    const userid = this.#auth.user()?.id;
    if (!data || !this.#auth.isAuthenticated() || !userid) {
      return;
    }
    data.userId = userid;
    this.#performAccessRequest(data);
  };

  #performAccessRequest = (data: AccessRequestDialogData) => {
    data.fromDate?.setUTCHours(0);
    data.fromDate?.setUTCMinutes(0);
    data.fromDate?.setUTCSeconds(0);
    data.fromDate?.setUTCMilliseconds(0);
    data.untilDate?.setHours(23);
    data.untilDate?.setMinutes(59);
    data.untilDate?.setSeconds(59);
    data.untilDate?.setMilliseconds(999);
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
        this.#userAccessRequests.reload();
        this.#notification.showSuccess('Your request has been submitted successfully.');
      });
    } catch (error) {
      this.#notification.showError(
        'There was an error submitting your access request: ' + error,
      );
    }
  };

  /**
   * Internal resource for loading the current user's access requests
   */
  #userAccessRequests = rxResource<AccessRequest[], string | null>({
    request: this.#userId,
    loader: ({ request: userId }) => {
      if (!userId) {
        throw new Error('User not authenticated');
      }
      return this.#http
        .get<AccessRequest[]>(this.#userAccessRequestsUrl(userId))
        .pipe(
          map((ar) =>
            ar.filter(({ status }) => status === 'pending' || status === 'allowed'),
          ),
        );
    },
  }).asReadonly();

  /**
   * The list of access requests of the current user
   */
  userAccessRequests: Signal<AccessRequest[]> = computed(
    () => this.#userAccessRequests.value() ?? [],
  );

  /**
   * The list of granted access requests of the current user
   */
  grantedUserAccessRequests = computed(() =>
    this.userAccessRequests()
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
    this.userAccessRequests().filter((ar: AccessRequest) => ar.status == 'pending'),
  );

  userAccessRequestsAreLoading = this.#userAccessRequests.isLoading;

  userAccessRequestsError = this.#userAccessRequests.error;

  #allAccessRequestsFilter = signal<AccessRequestFilter | undefined>(undefined);

  // signal to load all users' access requests
  #loadAll = signal<null | undefined>(undefined);

  /**
   * Load all users' access requests
   */
  loadAllAccessRequests(): void {
    this.#loadAll.set(null);
  }

  /**
   * The current filter for the list of all access requests
   */
  allAccessRequestsFilter = computed(
    () =>
      this.#allAccessRequestsFilter() ?? {
        name: '',
        fromDate: undefined,
        toDate: undefined,
        state: undefined,
      },
  );

  /**
   * Set a filter for the list of all access requests
   * @param filter - the filter to apply
   */
  setAllAccessRequestsFilter(filter: AccessRequestFilter): void {
    this.#allAccessRequestsFilter.set(
      filter.name || filter.fromDate || filter.toDate || filter.state
        ? filter
        : undefined,
    );
  }

  /**
   * Internal resource for loading all access requests.
   * Note: We do the filtering currently only on the client side,
   * but in principle we can also do some filtering on the sever.
   */
  #allAccessRequests = rxResource<AccessRequest[], null | undefined>({
    request: this.#loadAll,
    loader: () => this.#http.get<AccessRequest[]>(this.#arsEndpointUrl),
  });

  /**
   * The list of access requests
   */
  allAccessRequests: Signal<AccessRequest[]> = computed(() => {
    let requests = this.#allAccessRequests.value() ?? [];
    const filter = this.#allAccessRequestsFilter();
    if (requests.length && filter) {
      const datasetId = filter.datasetId.trim().toLowerCase();
      if (datasetId) {
        requests = requests.filter(
          (ar) => ar.dataset_id.toLowerCase() === filter.datasetId,
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
      if (filter.state) {
        requests = requests.filter((ar) => ar.status === filter.state);
      }
    }
    return requests;
  });

  /**
   * Whether the list of all access requests is loading as a signal
   */
  allAccessRequestsAreLoading: Signal<boolean> = this.#allAccessRequests.isLoading;

  /**
   * The list of all access requests error as a signal
   */
  allAccessRequestsError: Signal<unknown> = this.#allAccessRequests.error;
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
  userAccessRequestsAreLoading = signal(false);
  userAccessRequestsError = signal(false);
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
