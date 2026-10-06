/**
 * This component is part of the flow to revoke an access grant.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject, signal } from '@angular/core';
import { form, FormField } from '@angular/forms/signals';
import { MatButton } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { RouterModule } from '@angular/router';
import { AccessGrant } from '@app/access-requests/models/access-requests';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { NotificationService } from '@app/shared/services/notification';

/**
 * This component contains the logic to re-check the id before revoking an access grant
 */
@Component({
  selector: 'app-access-grant-revocation-button',
  imports: [
    MatIconModule,
    RouterModule,
    FormField,
    MatButton,
    MatDialogActions,
    MatDialogModule,
    MatInputModule,
  ],
  providers: [AccessRequestService, NotificationService],
  templateUrl: './access-grant-revocation-dialog.html',
})
export class AccessGrantRevocationDialogComponent {
  #dialogRef = inject(MatDialogRef<AccessGrantRevocationDialogComponent, boolean>);
  protected data = inject<{
    grant: AccessGrant;
  }>(MAT_DIALOG_DATA);

  #ars = inject(AccessRequestService);
  #notificationService = inject(NotificationService);

  protected confirmForm = form(signal({ email: '', dataset: '' }));

  protected disabled = computed(
    () =>
      this.confirmForm.email().value().trim() !== this.grant.user_email ||
      this.confirmForm.dataset().value().trim() !== this.grant.dataset_id ||
      this.#isProcessing(),
  );
  #isProcessing = signal(false);

  protected revocationError = signal(false);

  /**
   * Grant to delete
   * @returns specified grant
   */
  get grant(): AccessGrant {
    return this.data.grant;
  }

  /**
   * Called when the cancel button is clicked. Closes the dialog.
   */
  onCancel() {
    this.#dialogRef.close(false);
  }

  /**
   * Called when the "confirm" button is clicked. Revokes the grant.
   */
  onConfirm(): void {
    const id = this.data.grant.id;
    if (!id) return;
    this.#isProcessing.set(true);
    this.#ars.revokeAccessGrant(id).subscribe({
      next: () => {
        this.#notificationService.showSuccess(`Access grant was successfully revoked.`);
        this.revocationError.set(false);
        this.#dialogRef.close(true);
      },
      error: (err) => {
        console.debug(err);
        this.#notificationService.showError(
          'Access grant could not be revoked. Please try again later',
        );
        this.revocationError.set(true);
        setTimeout(() => this.#isProcessing.set(false), 2500);
      },
    });
  }
}
