/**
 * Dialog allowing a data steward to manage an individual access request.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe } from '@angular/common';
import {
  Component,
  computed,
  effect,
  inject,
  model,
  OnInit,
  signal,
  Signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatIcon } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatRadioModule } from '@angular/material/radio';
import {
  AccessRequest,
  AccessRequestStatus,
} from '@app/access-requests/models/access-requests';
import { AccessRequestStatusClassPipe } from '@app/access-requests/pipes/access-request-status-class.pipe';
import { AccessRequestService } from '@app/access-requests/services/access-request.service';
import { ConfirmationService } from '@app/shared/services/confirmation.service';
import { NotificationService } from '@app/shared/services/notification.service';
import { FRIENDLY_DATE_FORMAT } from '@app/shared/utils/date-formats';
import { Iva, IvaState } from '@app/verification-addresses/models/iva';
import { IvaStatePipe } from '@app/verification-addresses/pipes/iva-state.pipe';
import { IvaTypePipe } from '@app/verification-addresses/pipes/iva-type.pipe';
import { IvaService } from '@app/verification-addresses/services/iva.service';
import { AccessRequestFieldEditComponent } from '../access-request-field-edit/access-request-field-edit.component';

/**
 * The dialog component used for managing access requests in the access request manager.
 * Currently, the data steward can only allow or deny requests, and select and IVA.
 */
@Component({
  selector: 'app-access-request-manager-dialog',
  styleUrl: './access-request-manager-dialog.component.scss',
  imports: [
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatRadioModule,
    MatIcon,
    DatePipe,
    AccessRequestStatusClassPipe,
    IvaTypePipe,
    IvaStatePipe,
    AccessRequestFieldEditComponent,
    MatChipsModule,
    MatInputModule,
  ],
  providers: [IvaTypePipe],
  templateUrl: './access-request-manager-dialog.component.html',
})
export class AccessRequestManagerDialogComponent implements OnInit {
  readonly dialogRef = inject(MatDialogRef<AccessRequestManagerDialogComponent>);
  readonly data = inject<AccessRequest>(MAT_DIALOG_DATA);
  readonly friendlyDateFormat = FRIENDLY_DATE_FORMAT;
  #ivaService = inject(IvaService);
  #confirmationService = inject(ConfirmationService);
  #notificationService = inject(NotificationService);
  #accessRequestService = inject(AccessRequestService);

  #request = signal(this.data);

  #ivas = this.#ivaService.userIvas;
  ivas = this.#ivas.value;
  ivasAreLoading = this.#ivas.isLoading;
  ivasError = this.#ivas.error;

  #ivaTypePipe = inject(IvaTypePipe);

  selectedIvaIdRadioButton = model<string | undefined>(undefined);

  #pendingEdits = new Set<keyof AccessRequest>();

  /**
   * Get the IVA associated with the access request.
   */
  associatedIva: Signal<Iva | undefined> = computed(() => {
    const ivaId = this.#request().iva_id;
    return ivaId ? this.ivas().find((iva) => iva.id === ivaId) : undefined;
  });

  /**
   * Check whether the access request is changeable.
   * Currently the backend only allows to changed pending requests.
   */
  changeable: Signal<boolean> = computed(
    () => this.#request().status === AccessRequestStatus.pending,
  );

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
   * Get the display name for the IVA type
   * @param iva the IVA in question
   * @returns the display name for the type
   */
  #ivaTypeName(iva: Iva): string {
    return this.#ivaTypePipe.transform(iva.type).name;
  }

  /**
   * Load the IVAs of the user when the component is initialized
   */
  ngOnInit(): void {
    this.#ivaService.loadUserIvas(this.#request().user_id);
  }

  cancel = () => {
    this.dialogRef.close(undefined);
  };

  /**
   * Update the request.
   * @param changes - The changes to apply
   */
  #update(changes: Partial<AccessRequest>): void {
    const id = this.#request().id;
    this.#accessRequestService.updateRequest(id, changes).subscribe({
      next: () => {
        this.#notificationService.showSuccess(
          `Access request was successfully modified.`,
        );
        const request = this.#request();
        this.#request.update(() => ({ ...request, ...changes }));
      },
      error: (err) => {
        console.debug(err);
        this.#notificationService.showError(
          'Access request could not be modified. Please try again later',
        );
      },
    });
  }

  /**
   * Memorize which editors have changes.
   * @param event - The name of the field and whether it was edited
   */
  edited(event: [keyof AccessRequest, boolean]): void {
    const [name, edited] = event;
    if (edited) this.#pendingEdits.add(name);
    else this.#pendingEdits.delete(name);
  }

  /**
   * Save a field change.
   * @param event - The name of the field and the new value
   */
  saved(event: [keyof AccessRequest, string]): void {
    const [name, value] = event;
    this.#update({ [name]: value });
  }

  /**
   * Update the IVA selection.
   */
  saveIva() {
    this.#update({ iva_id: this.selectedIvaIdRadioButton() });
  }

  /**
   * Allow the access request after confirmation.
   */
  safeAllow(): void {
    if (!this.selectedIvaIdRadioButton()) return;
    const iva = this.ivas().find((iva) => iva.id === this.selectedIvaIdRadioButton());
    if (!iva) return;
    const ivaType = this.#ivaTypeName(iva);
    this.#confirmationService.confirm({
      title: 'Confirm approval of the access request',
      message:
        'Please confirm that the access request shall be allowed' +
        ` and coupled to ${ivaType}: ${iva.value}.`,
      cancelText: 'Cancel',
      confirmText: 'Confirm approval',
      confirmClass: 'success',
      callback: (approvalConfirmed) => {
        if (approvalConfirmed) this.#allowAndClose();
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
        if (denialConfirmed) this.#denyAndClose();
      },
    });
  }

  /**
   * Checks if the user has pending changes before proceeding with a status change.
   * If there are unsaved edits, prompts the user to confirm discarding them before proceeding.
   * @param action String literal specifying the desired status change.
   */
  saveBeforeStatusChange(action: 'deny' | 'allow'): void {
    if (this.#pendingEdits.size) {
      this.#confirmationService.confirm({
        title: 'Unsaved changes',
        message: 'Do you want to continue without saving your changes?',
        cancelText: 'Cancel',
        confirmText: 'Discard Changes',
        confirmClass: 'danger',
        callback: (wantsToDiscard) => {
          if (wantsToDiscard) {
            if (action === 'allow') this.safeAllow();
            else this.safeDeny();
          }
        },
      });
    } else {
      if (action === 'allow') this.safeAllow();
      else this.safeDeny();
    }
  }

  /**
   * Allow the access request and close the dialog.
   */
  #allowAndClose = () => {
    if (!this.selectedIvaIdRadioButton()) return;
    this.#update({
      status: AccessRequestStatus.allowed,
    });
    this.dialogRef.close();
  };

  /**
   * Deny the access request and close the dialog.
   */
  #denyAndClose = () => {
    this.#update({
      status: AccessRequestStatus.denied,
    });
    this.dialogRef.close();
  };

  /**
   * Pre-select the radio button for the IVA that best matches
   * (the IVA that is already selected or the best option otherwise)
   */
  #preSelectIvaRadioButton(): void {
    this.selectedIvaIdRadioButton.set(this.data.iva_id || this.#findBestIvaId());
  }

  /**
   * Get the "best" IVA for a changeable access request.
   * @returns The ID of the IVA closest to being verified and latest.
   */
  #findBestIvaId(): string | undefined {
    let bestRank: number | undefined = undefined;
    let lastChanged: string | undefined = undefined;
    let ivaId: string | undefined;
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
    return ivaId;
  }
}
