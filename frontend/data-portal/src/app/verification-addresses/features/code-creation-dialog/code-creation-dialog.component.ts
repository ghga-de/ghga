/**
 * A dialog that shows created IVA verification codes
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Clipboard } from '@angular/cdk/clipboard';
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
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatTooltipModule } from '@angular/material/tooltip';
import { NotificationService } from '@app/shared/services/notification.service';
import { UserWithIva } from '@app/verification-addresses/models/iva';
import { IvaTypePipe } from '@app/verification-addresses/pipes/iva-type.pipe';

type IvaWithCode = UserWithIva & { code: string };

/**
 * Dialog for showing the IVA verification code
 * This dialog shows the IVA verification code that was created to the data steward,
 * offers an option to copy the code to the clipboard for easy sharing,
 * and an option to immediately confirm the transmission of the code to the user.
 */
@Component({
  selector: 'app-code-creation-dialog',
  imports: [
    MatDialogModule,
    MatDialogTitle,
    MatDialogContent,
    MatDialogActions,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatTooltipModule,
    IvaTypePipe,
  ],
  templateUrl: './code-creation-dialog.component.html',
  styleUrl: './code-creation-dialog.component.scss',
})
export class CodeCreationDialogComponent {
  #clipboard = inject(Clipboard);
  #dialogRef = inject(MatDialogRef<CodeCreationDialogComponent, boolean>);
  #notify = inject(NotificationService);

  iva = inject<IvaWithCode>(MAT_DIALOG_DATA);

  /**
   * Close the dialog without confirming transmission
   */
  onClose(): void {
    this.#dialogRef.close(false);
  }

  /**
   * Close the dialog and confirm transmission
   */
  onConfirmTransmission(): void {
    this.#dialogRef.close(true);
  }

  /**
   * Copy the verification code to the clipboard
   */
  copyCode(): void {
    const code = this.iva.code;
    if (code) {
      this.#clipboard.copy(code);
      this.#notify.showSuccess(
        'The verification code has been copied to the clipboard.',
      );
    }
  }
}
