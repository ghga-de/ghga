/**
 * Notification Service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { inject, Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
// eslint-disable-next-line boundaries/element-types
import { CustomSnackBarComponent } from '../ui/custom-snack-bar/custom-snack-bar.component';

/**
 * A service that can show various kinds of notifications to the user
 */
@Injectable({
  providedIn: 'root',
})
export class NotificationService {
  #snackBar = inject(MatSnackBar);

  /**
   * Show a success message
   * @param message - the text to show to the user
   * @param duration - the duration in milliseconds to show the message
   */
  showSuccess(message: string, duration: number = 3000): void {
    console.debug(message);
    this.#show(message, 'ok', duration);
  }

  /**
   * Show an info message
   * @param message - the text to show to the user
   * @param duration - the duration in milliseconds to show the message
   */
  showInfo(message: string, duration: number = 3000): void {
    console.info(message);
    this.#show(message, 'info', duration);
  }

  /**
   * Show a warning message
   * @param message - the text to show to the user
   * @param duration - the duration in milliseconds to show the message
   */
  showWarning(message: string, duration: number = 4000): void {
    console.warn(message);
    this.#show(message, 'warn', duration);
  }

  /**
   * Show an error message
   * @param message - the text to show to the user
   * @param duration - the duration in milliseconds to show the message
   */
  showError(message: string, duration: number = 5000): void {
    console.error(message);
    this.#show(message, 'error', duration);
  }

  /**
   * Show an error message
   * @param message - the text to show to the user
   * @param type - the type of message to show
   * @param duration - the duration in milliseconds to show the message
   */
  #show(
    message: string,
    type: 'ok' | 'info' | 'warn' | 'error',
    duration: number | undefined,
  ): void {
    this.#snackBar.openFromComponent(CustomSnackBarComponent, {
      duration,
      horizontalPosition: 'end',
      verticalPosition: 'bottom',
      panelClass: `snackbar-${type}`,
      data: {
        message,
        type,
      },
    });
  }
}
