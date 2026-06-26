/**
 * A smart button that either shows a button to create an access request or states that one already exists with it's state.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject, input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import {
  AccessGrant,
  AccessRequest,
  AccessRequestDetailData,
  AccessRequestStatus,
} from '@app/access-requests/models/access-requests';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { AuthService } from '@app/auth/services/auth';
import { NotificationService } from '@app/shared/services/notification';
// eslint-disable-next-line boundaries/dependencies
import { DownloadWorkPackageDialogComponent } from '@app/work-packages/features/download-work-package-dialog/download-work-package-dialog';
import { AccessRequestDialogComponent } from '../access-request-dialog/access-request-dialog';

/**
 * This component wraps some logic about access requests by only showing and controlling the dialog to create one if none exists so far.
 */
@Component({
  selector: 'app-dynamic-access-request-button',
  imports: [MatIconModule, MatButtonModule],
  templateUrl: './dynamic-access-request-button.html',
})
export class DynamicAccessRequestButtonComponent {
  protected readonly AccessRequestStatus = AccessRequestStatus;
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
  #activeGrant = computed<AccessGrant | undefined>(
    () =>
      this.#accessRequestService
        .activeUserAccessGrants()
        .filter((grant: AccessGrant) => {
          const hasSameId = grant.dataset_id == this.datasetID();
          const isValid = (grant.daysRemaining ?? -1) > 0;
          return hasSameId && isValid;
        })
        .sort(
          (a, b) =>
            (b.daysRemaining ?? 0) - (a.daysRemaining ?? 0) || a.id.localeCompare(b.id),
        )[0],
  );
  status = computed<AccessRequestStatus>(() => {
    if (this.#activeGrant()) return AccessRequestStatus.allowed;
    if (this.#pendingAccessRequests()) return AccessRequestStatus.pending;
    return AccessRequestStatus.denied;
  });

  showDownloadTokenDialog = () => {
    const grant = this.#activeGrant();
    if (!grant) return;
    this.#dialog.open(DownloadWorkPackageDialogComponent, {
      data: grant,
      width: '64rem',
      maxWidth: '96vw',
    });
  };

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
