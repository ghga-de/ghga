/**
 * A custom snackbar
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MAT_SNACK_BAR_DATA, MatSnackBarRef } from '@angular/material/snack-bar';

/**
 * A custom snackbar component
 */
@Component({
  selector: 'app-custom-snack-bar',
  imports: [MatButtonModule, MatIconModule],
  templateUrl: './custom-snack-bar.component.html',
  styleUrl: './custom-snack-bar.component.scss',
})
export class CustomSnackBarComponent {
  data = inject(MAT_SNACK_BAR_DATA);
  snackBarRef = inject(MatSnackBarRef);

  /**
   * Close the snackbar
   */
  close(): void {
    this.snackBarRef.dismiss();
  }
}
