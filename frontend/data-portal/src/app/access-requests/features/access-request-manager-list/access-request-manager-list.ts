/**
 * Component that lists all the access requests.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe as CommonDatePipe } from '@angular/common';
import {
  AfterViewInit,
  Component,
  QueryList,
  ViewChild,
  ViewChildren,
  computed,
  effect,
  inject,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatRippleModule } from '@angular/material/core';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { Router, RouterLink } from '@angular/router';
import {
  AccessGrantStateLabel,
  AccessGrantStatus,
  AccessRequest,
  AccessRequestStatus,
} from '@app/access-requests/models/access-requests';
import { AccessGrantStatusClassPipe } from '@app/access-requests/pipes/access-grant-status-class-pipe';
import { AccessRequestStatusClassPipe } from '@app/access-requests/pipes/access-request-status-class-pipe';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { DatePipe } from '@app/shared/pipes/date-pipe';
import { ConfigService } from '@app/shared/services/config';
import { providePaginatorIntl } from '@app/shared/services/paginator-intl';
import {
  DEFAULT_DATE_OUTPUT_FORMAT,
  DEFAULT_TIME_ZONE,
} from '@app/shared/utils/date-formats';

/**
 * Access Request Manager List component.
 *
 * This component lists all the access requests of all users
 * in the Access Request Manager. Filter conditions can be applied to the list.
 */
@Component({
  selector: 'app-access-request-manager-list',
  imports: [
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    MatButtonModule,
    MatRippleModule,
    DatePipe,
    AccessRequestStatusClassPipe,
    AccessGrantStatusClassPipe,
    MatIconModule,
    RouterLink,
  ],
  providers: [CommonDatePipe, providePaginatorIntl('Access requests per page')],
  templateUrl: './access-request-manager-list.html',
})
export class AccessRequestManagerListComponent implements AfterViewInit {
  #config = inject(ConfigService);
  #baseTicketUrl = this.#config.helpdeskTicketUrl;

  #router = inject(Router);
  #ars = inject(AccessRequestService);

  #accessRequests = this.#ars.allAccessRequests;
  accessRequests = this.#ars.allAccessRequestsFiltered;
  accessRequestsAreLoading = this.#accessRequests.isLoading;
  accessRequestsError = this.#accessRequests.error;

  #filter = this.#ars.allAccessRequestsFilter;

  /**
   * Whether the list is filtered to pending requests only. In that case the
   * grant state is irrelevant (a pending request has no grant yet), so the
   * grant-related columns are hidden and grants are not loaded.
   */
  pendingOnly = computed(() => this.#filter().status === AccessRequestStatus.pending);

  /**
   * The table columns to display, depending on the current filter.
   */
  columns = computed<string[]>(() =>
    this.pendingOnly()
      ? ['ticket', 'dataset', 'requester', 'requested', 'period', 'status', 'details']
      : [
          'ticket',
          'dataset',
          'requester',
          'requested',
          'period',
          'status',
          'grant',
          'details',
        ],
  );

  /**
   * Lazily load all access grants once the list shows more than pending
   * requests, so that the grant state can be derived for the grant column.
   */
  #loadGrantsEffect = effect(() => {
    if (!this.pendingOnly()) this.#ars.loadAllAccessGrants();
  });

  /**
   * Map from access request ID to the aggregated current grant state of the
   * corresponding user and dataset (undefined if there is no matching grant).
   */
  grantState = computed<Map<string, AccessGrantStatus | undefined>>(
    () =>
      new Map(
        this.accessRequests().map((ar) => [
          ar.id,
          this.#ars.grantStateFor(ar.user_id, ar.dataset_id),
        ]),
      ),
  );

  /**
   * User-facing labels for the aggregated grant state shown in the "Access"
   * column, shared with the access request details page.
   */
  accessLabels = AccessGrantStateLabel;

  source = new MatTableDataSource<AccessRequest>([]);

  periodFormat = DEFAULT_DATE_OUTPUT_FORMAT;
  periodTimeZone = DEFAULT_TIME_ZONE;

  ticketUrl = computed<Map<string, string | null>>(
    () =>
      new Map(
        this.accessRequests().map((ar) => [
          ar.id,
          ar.ticket_id ? this.#baseTicketUrl + ar.ticket_id : null,
        ]),
      ),
  );

  #updateSourceEffect = effect(() => (this.source.data = this.accessRequests()));

  #accessRequestSortingAccessor = (ar: AccessRequest, key: string) => {
    switch (key) {
      case 'ticket':
        return ar.ticket_id || '';
      case 'dataset':
        return ar.dataset_id;
      case 'requester':
        const parts = ar.full_user_name.split(' ');
        parts.push(ar.email);
        return parts.reverse().join(',');
      case 'status':
        const rank = { allowed: 0, pending: 1, denied: 2 }[ar.status as string] ?? 3;
        return `${rank}:${ar.access_starts}-${ar.access_ends})`;
      case 'grant':
        const grantRank =
          { active: 0, waiting: 1, expired: 2 }[
            this.#ars.grantStateFor(ar.user_id, ar.dataset_id) as string
          ] ?? 3;
        return `${grantRank}:${ar.access_ends})`;
      case 'period':
        return `${ar.access_starts}-${ar.access_ends})`;
      case 'requested':
        return ar.request_created;
      default:
        const value = ar[key as keyof AccessRequest];
        if (typeof value === 'string' || typeof value === 'number') {
          return value;
        }
        return '';
    }
  };

  @ViewChildren(MatSort) matSorts!: QueryList<MatSort>;
  @ViewChildren(MatPaginator) matPaginators!: QueryList<MatPaginator>;
  @ViewChild('paginator') paginator!: MatPaginator;
  @ViewChild('sort') sort!: MatSort;

  /**
   * Assign sorting
   */
  #addSorting() {
    if (this.sort) this.source.sort = this.sort;
  }

  /**
   * Assign pagination
   */
  #addPagination() {
    if (this.paginator) this.source.paginator = this.paginator;
  }

  /**
   * After the view has been initialised
   * assign the sorting of the table to the data source
   */
  ngAfterViewInit() {
    this.source.sortingDataAccessor = this.#accessRequestSortingAccessor;
    this.#addSorting();
    this.#addPagination();
    this.matSorts.changes.subscribe(() => this.#addSorting());
    this.matPaginators.changes.subscribe(() => this.#addPagination());
  }

  /**
   * Navigate to access request details page
   * @param event - the PointerEvent object to check if there is an anchor inside
   * @param ar - the selected access request
   */
  viewDetails(event: MouseEvent, ar: AccessRequest): void {
    if ((event.target as HTMLElement | null)?.closest('a')) return;
    this.#router.navigate(['/access-request-manager', ar.id]);
  }
}
