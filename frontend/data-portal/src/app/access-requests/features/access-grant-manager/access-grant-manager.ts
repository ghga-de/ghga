/**
 * Component that hosts the Access Grant Manager feature.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject, OnInit } from '@angular/core';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { AccessGrantManagerFilterComponent } from '../access-grant-manager-filter/access-grant-manager-filter';
import { AccessGrantManagerListComponent } from '../access-grant-manager-list/access-grant-manager-list';

/**
 * Access Grant Manager component.
 *
 * The Access Grant Manager allows data stewards to view and manage access grants.
 */
@Component({
  selector: 'app-access-request-manager',
  imports: [AccessGrantManagerFilterComponent, AccessGrantManagerListComponent],
  templateUrl: './access-grant-manager.html',
})
export class AccessGrantManagerComponent implements OnInit {
  #ars = inject(AccessRequestService);
  /**
   * Load the access grants when the component is initialized
   */
  ngOnInit(): void {
    this.#ars.loadAllAccessGrants();
  }
}
