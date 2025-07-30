/**
 * Component that hosts the User Manager feature.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject, OnInit } from '@angular/core';
import { UserService } from '@app/auth/services/user.service';
import { UserManagerFilterComponent } from '../user-manager-filter/user-manager-filter.component';
import { UserManagerListComponent } from '../user-manager-list/user-manager-list.component';

/**
 * User Manager component.
 *
 * The User Manager allows data stewards to manage users,
 * view user details, and perform administrative actions.
 */
@Component({
  selector: 'app-user-manager',
  imports: [UserManagerListComponent, UserManagerFilterComponent],
  providers: [UserService],
  templateUrl: './user-manager.component.html',
})
export class UserManagerComponent implements OnInit {
  userService = inject(UserService);

  /**
   * Load the users when the component is initialized
   */
  ngOnInit(): void {
    this.userService.loadUsers();
  }
}
