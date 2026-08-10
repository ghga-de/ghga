/**
 * Component that hosts the Access Request Manager feature.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject, OnInit } from '@angular/core';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { RefreshButtonComponent } from '@app/shared/ui/refresh-button/refresh-button';
import { AccessRequestManagerFilterComponent } from '../access-request-manager-filter/access-request-manager-filter';
import { AccessRequestManagerListComponent } from '../access-request-manager-list/access-request-manager-list';

/**
 * Access Request Manager component.
 *
 * The Access Request Manager allows data stewards to manage the access requests
 * of all users, particularly to deny or allow the requested access.
 */
@Component({
  selector: 'app-access-request-manager',
  imports: [
    AccessRequestManagerFilterComponent,
    AccessRequestManagerListComponent,
    RefreshButtonComponent,
  ],
  templateUrl: './access-request-manager.html',
})
export class AccessRequestManagerComponent implements OnInit {
  #ars = inject(AccessRequestService);

  /**
   * Load the access requests when the component is initialized
   */
  ngOnInit(): void {
    this.#ars.reloadAllAccessRequests();
  }

  /** Whether the access requests are currently being fetched. */
  protected isLoading = this.#ars.allAccessRequests.isLoading;

  /**
   * Fetch the access requests again on request, since users file new ones and
   * other data stewards process them while this view is open.
   */
  protected refresh(): void {
    this.#ars.reloadAllAccessRequests();
  }
}
