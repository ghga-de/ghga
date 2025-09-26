/**
 * A smart button that either shows a button to create an access request or states that one already exists with it's state.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject, input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule } from '@angular/router';
import {
  AccessRequest,
  AccessRequestDetailData,
  AccessRequestStatus,
  GrantedAccessRequest,
} from '@app/access-requests/models/access-requests';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { AuthService } from '@app/auth/services/auth';
import { NotificationService } from '@app/shared/services/notification';
import { AccessRequestDialogComponent } from '../access-request-dialog/access-request-dialog';

/**
 * This component wraps some logic about access requests by only showing and controlling the dialog to create one if none exists so far.
 */
@Component({
  selector: 'app-dynamic-access-request-button',
  imports: [MatIconModule, MatButtonModule, RouterModule],
  templateUrl: './dynamic-access-request-button.html',
})
export class DynamicAccessRequestButtonComponent {
  datasetID = input.required<string>();
  #accessRequestService = inject(AccessRequestService);
  #auth = inject(AuthService);
  #notification = inject(NotificationService);
  #dialog = inject(MatDialog);
  #userId = computed<string | undefined>(() => this.#auth.user()?.id || undefined);
  #pendingAccessRequests = computed(() =>
    this.#accessRequestService
      .pendingUserAccessRequests()
      .some((ar: AccessRequest) => ar.dataset_id == this.datasetID()),
  );
  #activeGrantedAccessRequests = computed(() =>
    this.#accessRequestService
      .grantedUserAccessRequests()
      .some((grantedAccessRequest: GrantedAccessRequest) => {
        const hasSameId = grantedAccessRequest.request.dataset_id == this.datasetID();
        const isValid = grantedAccessRequest.daysRemaining > 0;
        return hasSameId && isValid;
      }),
  );
  status = computed<AccessRequestStatus>(() => {
    if (this.#activeGrantedAccessRequests()) return AccessRequestStatus.allowed;
    if (this.#pendingAccessRequests()) return AccessRequestStatus.pending;
    return AccessRequestStatus.denied;
  });

  showNewAccessRequestDialog = () => {
    if (!this.#auth.isAuthenticated()) {
      this.#notification.showError('You must be logged in to perform this action');
      return;
    }

    const data: AccessRequestDetailData = {
      datasetID: this.datasetID(),
      email: this.#auth.email() || '',
      description: '',
      fromDate: undefined,
      untilDate: undefined,
      userId: this.#userId() || '',
    };

    this.#dialog
      .open(AccessRequestDialogComponent, {
        data,
      })
      .afterClosed()
      .subscribe((componentData) => {
        if (componentData) {
          this.#processAccessRequest(componentData);
        }
      });
  };

  #processAccessRequest = (data: AccessRequestDetailData) => {
    const userid = this.#auth.user()?.id;
    if (!this.#auth.isAuthenticated() || !userid) {
      return;
    }
    this.#accessRequestService.performAccessRequest(data);
  };
}
