/**
 * Confirmation dialog for user deletion
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject, model, signal } from '@angular/core';
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
import { DisplayUser, UserService } from '@app/auth/services/user';
import { NotificationService } from '@app/shared/services/notification';

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
  providers: [UserService],
  templateUrl: './deletion-confirmation-dialog.html',
})
export class DeletionConfirmationDialogComponent {
  #dialogRef = inject(MatDialogRef<DeletionConfirmationDialogComponent, boolean>);
  protected data = inject<{ user: DisplayUser }>(MAT_DIALOG_DATA);

  #userService = inject(UserService);
  #notificationService = inject(NotificationService);

  protected userInput = model<string | undefined>();

  protected disabled = computed(
    () => this.userInput()?.trim() !== this.user.email || this.#isProcessing(),
  );
  #isProcessing = signal(false);

  protected deletionError = signal(false);

  /**
   * User to delete
   * @returns specified user
   */
  get user(): DisplayUser {
    return this.data.user;
  }

  /**
   * Handle input change event
   * @param event The event object
   */
  onInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.userInput.set(input.value.trim());
  }

  /**
   * Called when the cancel button is clicked. Closes the dialog.
   */
  onCancel(): void {
    this.#dialogRef.close(false);
  }

  /**
   * Called when the "confirm" button is clicked. Deletes the user.
   */
  onConfirm(): void {
    this.#isProcessing.set(true);
    const id = this.data.user.id;
    if (!id) return;
    this.#userService.deleteUser(id).subscribe({
      next: () => {
        this.#notificationService.showSuccess(`User account was successfully deleted.`);
        this.deletionError.set(false);
        this.#dialogRef.close(true);
      },
      error: (err) => {
        console.debug(err);
        this.#notificationService.showError(
          'User account could not be deleted. Please try again later',
        );
        this.deletionError.set(true);
        setTimeout(() => this.#isProcessing.set(false), 2500);
      },
    });
  }
}
