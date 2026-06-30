/**
 * Reusable confirmation dialog component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogContent,
  MatDialogModule,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';

export interface ConfirmDialogData {
  title?: string;
  message: string;
  cancelText?: string;
  confirmText?: string;
  confirmClass?: string;
}

/**
 * A reusable confirmation dialog component
 */
@Component({
  selector: 'app-confirm-dialog',
  imports: [
    MatButtonModule,
    MatDialogModule,
    MatDialogTitle,
    MatDialogContent,
    MatDialogActions,
  ],
  templateUrl: './confirm-dialog.html',
})
export class ConfirmDialogComponent {
  #dialogRef = inject(MatDialogRef<ConfirmDialogComponent, boolean>);
  data = inject<ConfirmDialogData>(MAT_DIALOG_DATA);

  /**
   * Dialog heading
   * @returns specified or default title
   */
  get title(): string {
    return this.data.title || 'Confirmation';
  }

  /**
   * Dialog content
   * @returns specified or default message
   */
  get message(): string {
    return this.data.message || 'Do you really want to continue?';
  }

  /**
   * Cancel button text
   * @returns specified or default text
   */
  get cancelText(): string {
    return this.data.cancelText || 'Cancel';
  }

  /**
   * Confirm button text
   * @returns specified or default text
   */
  get confirmText(): string {
    return this.data.confirmText || 'Continue';
  }

  /**
   * Class of confirm button
   * @returns the class name of the confirm button
   */
  get confirmClass(): string {
    return this.data.confirmClass || '';
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
