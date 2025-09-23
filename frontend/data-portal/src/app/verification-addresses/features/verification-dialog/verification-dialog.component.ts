/**
 * A dialog to input the IVA verification code
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject } from '@angular/core';
import {
  FormControl,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
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

/**
 * Dialog for entering the IVA verification code
 */
@Component({
  selector: 'app-verification-dialog',
  imports: [
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatDialogModule,
    MatDialogTitle,
    MatDialogContent,
    MatDialogActions,
  ],
  templateUrl: './verification-dialog.component.html',
})
export class VerificationDialogComponent {
  #dialogRef = inject(MatDialogRef<VerificationDialogComponent, string>);
  data = inject<{ address: string }>(MAT_DIALOG_DATA);
  address = computed(() => this.data.address);

  codeControl = new FormControl<string>('', [
    Validators.required,
    Validators.pattern(/^[A-Z0-9]{6}$/),
  ]);

  /**
   * On input, modify the code to uppercase
   */
  onInput(): void {
    const value = this.codeControl.value;
    if (value) {
      this.codeControl.setValue(value.toUpperCase());
    }
  }

  /**
   * Cancel the dialog
   */
  onCancel(): void {
    this.#dialogRef.close(undefined);
  }

  /**
   * Complete the verification and pass the code
   */
  onSubmit(): void {
    let code = this.codeControl.value;
    if (this.codeControl.valid) {
      this.#dialogRef.close(code);
    }
  }
}
