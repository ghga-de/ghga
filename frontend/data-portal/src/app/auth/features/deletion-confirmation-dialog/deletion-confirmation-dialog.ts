/**
 * Confirmation dialog for user deletion
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject, model } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogContent,
  MatDialogModule,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { DisplayUser } from '@app/auth/services/user';

/**
 * Component for the deletion confirmation dialog
 */
@Component({
  selector: 'app-deletion-confirmation-dialog',
  imports: [
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatDialogModule,
    MatDialogTitle,
    MatDialogContent,
    MatDialogActions,
  ],
  templateUrl: './deletion-confirmation-dialog.html',
})
export class DeletionConfirmationDialogComponent {
  #dialogRef = inject(MatDialogRef<DeletionConfirmationDialogComponent, boolean>);
  data = inject<{ user: DisplayUser }>(MAT_DIALOG_DATA);

  userInput = model<string | undefined>();

  /**
   * User to delete
   * @returns specified user
   */
  get user(): DisplayUser {
    return this.data.user;
  }

  /**
   * Cancel the dialog
   */
  onCancel(): void {
    this.#dialogRef.close(false);
  }

  /**
   * Confirm the dialog
   */
  onConfirm(): void {
    this.#dialogRef.close(true);
  }
}
