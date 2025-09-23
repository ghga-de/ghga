/**
 * Show access requests that have been granted.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe } from '@angular/common';
import { Component, computed, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink, RouterModule } from '@angular/router';
import { AccessRequestService } from '@app/access-requests/services/access-request.service';
import { FRIENDLY_DATE_FORMAT } from '@app/shared/utils/date-formats';
import { StencilComponent } from '../../../shared/ui/stencil/stencil/stencil.component';

/**
 * This component shows a list of access requests that have been granted.
 */
@Component({
  selector: 'app-granted-access-requests-list',
  imports: [
    RouterLink,
    StencilComponent,
    DatePipe,
    MatIconModule,
    MatButtonModule,
    RouterModule,
  ],
  templateUrl: './granted-access-requests-list.component.html',
})
export class GrantedAccessRequestsListComponent {
  readonly friendlyDateFormat = FRIENDLY_DATE_FORMAT;
  #ars = inject(AccessRequestService);

  grantedRequests = computed(() =>
    this.#ars.grantedUserAccessRequests().filter((r) => !r.isExpired),
  );
  isLoading = this.#ars.userAccessRequests.isLoading;
  hasError = this.#ars.userAccessRequests.error;
}
