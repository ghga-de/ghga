/**
 * Dialog allowing a data steward to manage an individual access request.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe } from '@angular/common';
import { Component, effect, inject, model, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatRadioModule } from '@angular/material/radio';
import {
  AccessRequest,
  AccessRequestStatus,
} from '@app/access-requests/models/access-requests';
import { AccessRequestStatusClassPipe } from '@app/access-requests/pipes/access-request-status-class.pipe';
import { ConfirmationService } from '@app/shared/services/confirmation.service';
import { NotificationService } from '@app/shared/services/notification.service';
import { FRIENDLY_DATE_FORMAT } from '@app/shared/utils/date-formats';
import { IvaState } from '@app/verification-addresses/models/iva';
import { IvaStatePipe } from '@app/verification-addresses/pipes/iva-state.pipe';
import { IvaTypePipe } from '@app/verification-addresses/pipes/iva-type.pipe';
import { IvaService } from '@app/verification-addresses/services/iva.service';

/**
 * The dialog component used for managing access requests in the access request manager.
 * Currently, the data steward can only allow or deny requests, and select and IVA.
 */
@Component({
  selector: 'app-access-request-manager-dialog',
  imports: [
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatRadioModule,
    DatePipe,
    AccessRequestStatusClassPipe,
    IvaTypePipe,
    IvaStatePipe,
  ],
  templateUrl: './access-request-manager-dialog.component.html',
})
export class AccessRequestManagerDialogComponent implements OnInit {
  readonly dialogRef = inject(MatDialogRef<AccessRequestManagerDialogComponent>);
  readonly data = inject<AccessRequest>(MAT_DIALOG_DATA);
  readonly friendlyDateFormat = FRIENDLY_DATE_FORMAT;
  #ivaService = inject(IvaService);
  #confirmationService = inject(ConfirmationService);
  #notificationService = inject(NotificationService);

  #ivas = this.#ivaService.userIvas;
  ivas = this.#ivas.value;
  ivasAreLoading = this.#ivas.isLoading;
  ivasError = this.#ivas.error;

  selectedIvaIdRadioButton = model<string | undefined>(undefined);
  allowedAccessRequestIvaId = signal<string | undefined>(undefined);

  #ivasErrorEffect = effect(() => {
    if (this.ivasError()) {
      this.#notificationService.showError('Error fetching verification addresses.');
    }
  });

  #ivasLoadedEffect = effect(() => {
    if (!this.ivasAreLoading() && !this.ivasError() && this.ivas().length) {
      this.#preSelectIvaRadioButton();
    }
  });

  /**
   * Load the IVAs of the user when the component is initialized
   */
  ngOnInit(): void {
    this.#ivaService.loadUserIvas(this.data.user_id);
  }

  cancel = () => {
    this.dialogRef.close(undefined);
  };

  /**
   * Allow the access request after confirmation.
   */
  safeAllow(): void {
    if (!this.selectedIvaIdRadioButton()) return;
    const iva = this.ivas().find((iva) => iva.id === this.selectedIvaIdRadioButton());
    if (!iva) return;
    const typeAndValue = new IvaTypePipe().transform(iva.type, iva.value).typeAndValue;
    this.#confirmationService.confirm({
      title: 'Confirm approval of the access request',
      message:
        'Please confirm that the access request shall be allowed' +
        ` and coupled to ${typeAndValue}.`,
      cancelText: 'Cancel',
      confirmText: 'Confirm approval',
      confirmClass: 'success',
      callback: (approvalConfirmed) => {
        if (approvalConfirmed) this.#allowRequestAndCloseDialog();
      },
    });
  }

  /**
   * Deny the access request after confirmation.
   */
  safeDeny(): void {
    this.#confirmationService.confirm({
      title: 'Confirm denial of the access request',
      message: 'Please confirm that the access request shall be denied.',
      cancelText: 'Cancel',
      confirmText: 'Confirm denial',
      confirmClass: 'error',
      callback: (denialConfirmed) => {
        if (denialConfirmed) this.#deny();
      },
    });
  }

  /**
   * Allow the access request and close the dialog.
   */
  #allowRequestAndCloseDialog = () => {
    if (!this.selectedIvaIdRadioButton()) return;
    const data = {
      ...this.data,
      iva_id: this.selectedIvaIdRadioButton,
      status: AccessRequestStatus.allowed,
    };
    this.dialogRef.close(data);
  };

  /**
   * Deny the access request and close the dialog.
   */
  #deny = () => {
    const data = {
      ...this.data,
      iva_id: this.selectedIvaIdRadioButton,
      status: AccessRequestStatus.denied,
    };
    this.dialogRef.close(data);
  };

  /**
   * Pre-select the radio button for the IVA that best matches
   * (the IVA used for an allowed access request or the best option for a pending or denied one)
   */
  #preSelectIvaRadioButton(): void {
    if (this.data.iva_id) {
      this.allowedAccessRequestIvaId.set(this.data.iva_id);
      this.selectedIvaIdRadioButton.set(this.data.iva_id);
    } else {
      this.#bestIvaForPendingOrDeniedAR();
    }
  }

  /**
   * Pre-select the "best" IVA for a pending or denied access request.
   * The best IVA is the one which is closest to being verified and latest.
   */
  #bestIvaForPendingOrDeniedAR(): void {
    let bestRank: number | undefined = undefined;
    let lastChanged: string | undefined = undefined;
    let ivaId: string | undefined = undefined;
    for (const iva of this.ivas()) {
      const rank = {
        [IvaState.Verified]: 1,
        [IvaState.CodeTransmitted]: 2,
        [IvaState.CodeCreated]: 3,
        [IvaState.CodeRequested]: 4,
        [IvaState.Unverified]: 5,
      }[iva.state];
      const changed = iva.changed;
      if (!bestRank || rank < bestRank) {
        bestRank = rank;
        lastChanged = changed;
        ivaId = iva.id;
      } else if (rank === bestRank && (!lastChanged || changed > lastChanged)) {
        lastChanged = changed;
        ivaId = iva.id;
      }
    }
    this.selectedIvaIdRadioButton.set(ivaId);
  }
}
