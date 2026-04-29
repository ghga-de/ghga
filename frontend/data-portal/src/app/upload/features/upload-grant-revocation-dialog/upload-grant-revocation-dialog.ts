/**
 * Dialog component for confirming the revocation of an upload grant.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { MatButton } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { NotificationService } from '@app/shared/services/notification';
import { UploadGrant } from '@app/upload/models/grant';
import { UploadBoxService } from '@app/upload/services/upload-box';

/**
 * Dialog that asks the data steward to confirm an upload grant revocation.
 */
@Component({
  selector: 'app-upload-grant-revocation-dialog',
  imports: [MatButton, MatDialogActions, MatDialogModule, MatIconModule],
  templateUrl: './upload-grant-revocation-dialog.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadGrantRevocationDialogComponent {
  #dialogRef = inject(MatDialogRef<UploadGrantRevocationDialogComponent, boolean>);

  protected data = inject<{ grant: UploadGrant; boxTitle?: string; boxState?: string }>(
    MAT_DIALOG_DATA,
  );

  #uploadBoxService = inject(UploadBoxService);
  #notificationService = inject(NotificationService);

  #isProcessing = signal(false);

  protected revocationError = signal(false);

  /** Whether the confirm button should be disabled. */
  protected disabled = this.#isProcessing;

  /**
   * The upload grant to revoke.
   * @returns the grant passed via dialog data
   */
  get grant(): UploadGrant {
    return this.data.grant;
  }

  /**
   * Close the dialog without revoking.
   */
  onCancel(): void {
    this.#dialogRef.close(false);
  }

  /**
   * Revoke the grant and close the dialog on success.
   */
  onConfirm(): void {
    const id = this.data.grant.id;
    if (!id) return;
    this.#isProcessing.set(true);
    this.#uploadBoxService.revokeUploadGrant(id).subscribe({
      next: () => {
        this.#notificationService.showSuccess('Upload grant was successfully revoked.');
        this.revocationError.set(false);
        this.#dialogRef.close(true);
      },
      error: (err) => {
        console.debug(err);
        this.#notificationService.showError(
          'Upload grant could not be revoked. Please try again later.',
        );
        this.revocationError.set(true);
        setTimeout(() => this.#isProcessing.set(false), 2500);
      },
    });
  }
}
