/**
 * Component that hosts the User Manager feature.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, OnInit, inject } from '@angular/core';
import { UserService } from '@app/auth/services/user';
import { RefreshButtonComponent } from '@app/shared/ui/refresh-button/refresh-button';
import { UserManagerFilterComponent } from '../user-manager-filter/user-manager-filter';
import { UserManagerListComponent } from '../user-manager-list/user-manager-list';

/**
 * User Manager component.
 *
 * The User Manager allows data stewards to manage users,
 * view user details, and perform administrative actions.
 */
@Component({
  selector: 'app-user-manager',
  imports: [
    UserManagerListComponent,
    UserManagerFilterComponent,
    RefreshButtonComponent,
  ],
  templateUrl: './user-manager.html',
})
export class UserManagerComponent implements OnInit {
  userService = inject(UserService);

  /**
   * Load the users when the component is initialized
   */
  ngOnInit(): void {
    this.userService.reloadUsers();
  }

  /** Whether the users are currently being fetched. */
  protected isLoading = this.userService.users.isLoading;

  /**
   * Fetch the users again on request, since users register and are changed by
   * other data stewards while this view is open.
   */
  protected refresh(): void {
    this.userService.reloadUsers();
  }
}
