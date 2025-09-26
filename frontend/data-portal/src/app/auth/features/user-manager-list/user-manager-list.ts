/**
 * Component that lists all the users.
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
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { Router } from '@angular/router';
import { UserExtIdPipe } from '@app/auth/pipes/user-ext-id-pipe';
import { UserStatusClassPipe } from '@app/auth/pipes/user-status-class-pipe';
import { DisplayUser, UserService } from '@app/auth/services/user';
import { DatePipe } from '@app/shared/pipes/date-pipe';

const DEFAULT_EXT_ID_SUFFIX = '@lifescience-ri.eu';

/**
 * User Manager List component.
 *
 * This component lists all the registered users
 * in the User Manager. Filter conditions can be applied to the list.
 */
@Component({
  selector: 'app-user-manager-list',
  imports: [
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    MatButtonModule,
    DatePipe,
    MatIconModule,
    MatChipsModule,
    UserStatusClassPipe,
    UserExtIdPipe,
  ],
  providers: [CommonDatePipe],
  templateUrl: './user-manager-list.html',
})
export class UserManagerListComponent implements AfterViewInit {
  #router = inject(Router);
  #userService = inject(UserService);

  #users = this.#userService.users;
  ambiguousUserIds = this.#userService.ambiguousUserIds;
  users = this.#userService.usersFiltered;
  usersAreLoading = this.#users.isLoading;
  usersError = this.#users.error;

  source = new MatTableDataSource<DisplayUser>([]);

  defaultTablePageSize = 10;
  tablePageSizeOptions = [10, 25, 50, 100, 250, 500];

  #updateSourceEffect = effect(() => (this.source.data = this.users()));

  #userSortingAccessor = (user: DisplayUser, key: string) => {
    switch (key) {
      case 'email':
        return user.email;
      case 'name':
        return user.sortName;
      case 'ext_id':
        return user.ext_id;
      case 'roles':
        return user.roleNames.join(', ');
      case 'status':
        return user.status;
      case 'registration_date':
        return user.registration_date;
      default:
        const value = user[key as keyof DisplayUser];
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
    this.source.sortingDataAccessor = this.#userSortingAccessor;
    this.#addSorting();
    this.#addPagination();
    this.matSorts.changes.subscribe(() => this.#addSorting());
    this.matPaginators.changes.subscribe(() => this.#addPagination());
  }

  /**
   * Navigate to user details page
   * @param user - the selected user
   */
  viewDetails(user: DisplayUser): void {
    this.#router.navigate(['/user-manager', user.id]);
  }
}
