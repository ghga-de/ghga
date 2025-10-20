/**
 * This component is part of the flow to revoke an access grant.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject, model } from '@angular/core';
import { FormsModule } from '@angular/forms';
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

/**
 * This component contains the logic to re-check the id before revoking an access grant
 */
@Component({
  selector: 'app-access-grant-revocation-button',
  imports: [
    MatIconModule,
    RouterModule,
    FormsModule,
    MatButton,
    MatDialogActions,
    MatDialogModule,
    MatInputModule,
  ],
  templateUrl: './access-grant-revocation-dialog.html',
  styleUrl: './access-grant-revocation-dialog.scss',
})
export class AccessGrantRevocationDialogComponent {
  #dialogRef = inject(MatDialogRef<AccessGrantRevocationDialogComponent, boolean>);
  data = inject<{
    grant: AccessGrant;
  }>(MAT_DIALOG_DATA);

  emailInput = model<string | undefined>();
  datasetInput = model<string | undefined>();

  disabled = computed(
    () =>
      !(
        this.emailInput()?.trim() === this.grant.user_email &&
        this.datasetInput()?.trim() === this.grant.dataset_id
      ),
  );

  /**
   * Grant to delete
   * @returns specified grant
   */
  get grant(): AccessGrant {
    return this.data.grant;
  }

  /**
   * Confirm the dialog
   */
  onConfirm(): void {
    this.#dialogRef.close(true);
  }

  /**
   * Called when the cancel button is clicked. Closes the dialog.
   */
  onCancel() {
    this.#dialogRef.close(false);
  }
}
