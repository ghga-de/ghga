/**
 * Component that lists all the access grants.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe as CommonDatePipe } from '@angular/common';
import {
  AfterViewInit,
  Component,
  effect,
  inject,
  QueryList,
  ViewChild,
  ViewChildren,
} from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { Router } from '@angular/router';
import { AccessGrant } from '@app/access-requests/models/access-requests';
import { AccessRequestStatusClassPipe } from '@app/access-requests/pipes/access-request-status-class.pipe';
import { AccessRequestService } from '@app/access-requests/services/access-request.service';
import { DatePipe } from '@app/shared/pipes/date.pipe';
import {
  DEFAULT_DATE_OUTPUT_FORMAT,
  DEFAULT_TIME_ZONE,
} from '@app/shared/utils/date-formats';

/**
 * Access Grant Manager List component.
 *
 * This component lists all the access grants of all users
 * in the Access Grant Manager. Filter conditions can be applied to the list and there is a details view.
 */
@Component({
  selector: 'app-access-grant-manager-list',
  imports: [
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    DatePipe,
    AccessRequestStatusClassPipe,
    MatIconModule,
  ],
  providers: [CommonDatePipe],
  templateUrl: './access-grant-manager-list.component.html',
  styleUrl: './access-grant-manager-list.component.scss',
})
export class AccessGrantManagerListComponent implements AfterViewInit {
  #ars = inject(AccessRequestService);
  #router = inject(Router);

  accessGrants = this.#ars.allAccessGrantsFiltered;
  source = new MatTableDataSource<AccessGrant>([]);

  defaultTablePageSize = 10;
  tablePageSizeOptions = [10, 25, 50, 100, 250, 500];

  periodFormat = DEFAULT_DATE_OUTPUT_FORMAT;
  periodTimeZone = DEFAULT_TIME_ZONE;

  #updateSourceEffect = effect(() => (this.source.data = this.accessGrants()));

  #accessGrantsSortingAccessor = (ag: AccessGrant, key: string) => {
    switch (key) {
      case 'dataset':
        return ag.dataset_id;
      case 'status':
        switch (ag.status) {
          case 'Active':
            return '0 ' + ag.valid_from;
          case 'Waiting':
            return '1 ' + ag.valid_from;
          case 'Expired':
            return '2 ' + ag.valid_from;
          default:
            return '3 ' + ag.valid_from;
        }
      case 'user':
        return ag.user_name + '(' + ag.user_email + ')';
      case 'period':
        return ag.valid_from;
      default:
        const value = ag[key as keyof AccessGrant];
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
    this.source.sortingDataAccessor = this.#accessGrantsSortingAccessor;
    this.#addSorting();
    this.#addPagination();
    this.matSorts.changes.subscribe(() => this.#addSorting());
    this.matPaginators.changes.subscribe(() => this.#addPagination());
  }

  /**
   * This function navigates to the details page for the selected access grant
   * @param grant - The access grant to view details for
   */
  openDetails(grant: AccessGrant) {
    if (grant && grant.id) {
      // Navigate to the access-grant-details/:id route
      this.#router.navigate(['access-grant-details', grant.id]);
    } else {
      console.error('Cannot navigate: Grant or grant ID is missing.');
    }
  }
}
