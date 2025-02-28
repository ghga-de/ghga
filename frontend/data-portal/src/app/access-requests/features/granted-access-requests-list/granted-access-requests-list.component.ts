/**
 * Show access requests that have been granted.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AccessRequestService } from '@app/access-requests/services/access-request.service';
import { isoDatePipe } from '@app/shared/utils/iso-date.pipe';
import { StencilComponent } from '../../../shared/ui/stencil/stencil/stencil.component';

/**
 * This component shows a list of access requests that have been granted.
 */
@Component({
  selector: 'app-granted-access-requests-list',
  imports: [RouterLink, StencilComponent, isoDatePipe],
  templateUrl: './granted-access-requests-list.component.html',
  styleUrl: './granted-access-requests-list.component.scss',
})
export class GrantedAccessRequestsListComponent {
  #ars = inject(AccessRequestService);

  grantedRequests = this.#ars.grantedUserAccessRequests;
  isLoading = this.#ars.userAccessRequestsAreLoading;
  hasError = this.#ars.userAccessRequestsError;
}
