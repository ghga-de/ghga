/**
 * Component that lists all the access requests.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe } from '@angular/common';
import {
  AfterViewInit,
  Component,
  effect,
  inject,
  QueryList,
  ViewChild,
  ViewChildren,
} from '@angular/core';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { AccessRequest } from '@app/access-requests/models/access-requests';
import { AccessRequestService } from '@app/access-requests/services/access-request.service';

/**
 * Access Request Manager List component.
 *
 * This component lists all the access requests of all users
 * in the Access Request Manager. Filter conditions can be applied to the list.
 */
@Component({
  selector: 'app-access-request-manager-list',
  imports: [DatePipe, MatTableModule, MatSortModule, MatPaginatorModule],
  templateUrl: './access-request-manager-list.component.html',
  styleUrl: './access-request-manager-list.component.scss',
})
export class AccessRequestManagerListComponent implements AfterViewInit {
  #ars = inject(AccessRequestService);

  accessRequests = this.#ars.allAccessRequests;
  accessRequestsAreLoading = this.#ars.allAccessRequestsAreLoading;
  accessRequestsError = this.#ars.allAccessRequestsError;

  source = new MatTableDataSource<AccessRequest>([]);

  defaultTablePageSize = 10;
  tablePageSizeOptions = [10, 25, 50, 100, 250, 500];

  #updateSourceEffect = effect(() => (this.source.data = this.accessRequests()));

  #accessRequestSortingAccessor = (ar: AccessRequest, key: string) => {
    switch (key) {
      case 'dataset':
        return ar.dataset_id;
      case 'user':
        const parts = ar.full_user_name.split(' ');
        return parts.reverse().join(',');
      case 'starts':
        return ar.access_starts;
      case 'ends':
        return ar.access_ends;
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
}
