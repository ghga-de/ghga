/**
 * Component that hosts the Access Request Manager feature.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject, OnInit } from '@angular/core';
import { AccessRequestService } from '@app/access-requests/services/access-request.service';
import { AccessRequestManagerFilterComponent } from '../access-request-manager-filter/access-request-manager-filter.component';
import { AccessRequestManagerListComponent } from '../access-request-manager-list/access-request-manager-list.component';

/**
 * Access Request Manager component.
 *
 * The Access Request Manager allows data stewards to manage the access requests
 * of all users, particularly to deny or allow the requested access.
 */
@Component({
  selector: 'app-access-request-manager',
  imports: [AccessRequestManagerFilterComponent, AccessRequestManagerListComponent],
  templateUrl: './access-request-manager.component.html',
  styleUrl: './access-request-manager.component.scss',
})
export class AccessRequestManagerComponent implements OnInit {
  #ars = inject(AccessRequestService);

  /**
   * Load the access requests when the component is initialized
   */
  ngOnInit(): void {
    this.#ars.loadAllAccessRequests();
  }
}
