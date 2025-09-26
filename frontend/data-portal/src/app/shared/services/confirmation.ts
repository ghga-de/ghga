/**
 * A service for displaying confirmation dialogs
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { inject, Injectable } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
// eslint-disable-next-line boundaries/element-types
import { ConfirmDialogComponent } from '../ui/confirm-dialog/confirm-dialog';

/**
 * Service providing confirmation dialogs
 */
@Injectable({ providedIn: 'root' })
export class ConfirmationService {
  #dialog = inject(MatDialog);

  /**
   * Show confirmation dialog and call a function when confirmed
   * @param opts - dialog options
   * @param opts.title - optional title of the dialog
   * @param opts.message - message to display in the dialog
   * @param opts.cancelText - optional text for the cancel button
   * @param opts.confirmText - optional text for the confirm button
   * @param opts.confirmClass - optional class for the confirm button
   * @param opts.callback - function to call when the dialog is closed
   * @param opts.panelClass - optional class for the dialog panel
   * The callback receives a boolean indicating whether the dialog was confirmed
   */
  confirm({
    title,
    message,
    cancelText,
    confirmText,
    confirmClass,
    panelClass,
    callback,
  }: {
    title?: string;
    message: string;
    cancelText?: string;
    confirmText?: string;
    confirmClass?: string;
    panelClass?: string | string[];
    callback?: (confirmed: boolean | undefined) => void;
  }): void {
    const dialogRef = this.#dialog.open(ConfirmDialogComponent, {
      data: {
        title,
        message,
        cancelText,
        confirmText,
        confirmClass,
      },
      panelClass: panelClass,
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (callback) {
        callback(result);
      }
    });
  }
}
