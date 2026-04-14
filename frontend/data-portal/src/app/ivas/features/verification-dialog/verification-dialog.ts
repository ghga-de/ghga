/**
 * A dialog to input the IVA verification code
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject, signal } from '@angular/core';
import { form, FormField, maxLength, pattern, required } from '@angular/forms/signals';
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
import { IvaService } from '@app/ivas/services/iva';
import { NotificationService } from '@app/shared/services/notification';

/**
 * Dialog for entering the IVA verification code
 */
@Component({
  selector: 'app-verification-dialog',
  imports: [
    FormField,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatDialogModule,
    MatDialogTitle,
    MatDialogContent,
    MatDialogActions,
  ],
  templateUrl: './verification-dialog.html',
})
export class VerificationDialogComponent {
  #dialogRef = inject(MatDialogRef<VerificationDialogComponent, string>);
  #notify = inject(NotificationService);
  #ivaService = inject(IvaService);
  protected data = inject<{ id: string; address: string }>(MAT_DIALOG_DATA);
  protected address = computed(() => this.data.address);

  protected codeModel = signal<{ code: string }>({ code: '' });

  protected codeForm = form(this.codeModel, (schemaPath) => {
    required(schemaPath.code);
    maxLength(schemaPath.code, 6);
    pattern(schemaPath.code, /^[A-Z0-9]{6}$/);
  });

  #previousSubmission = signal('');

  #isProcessing = signal(false);

  protected disabled = computed<boolean>(
    () =>
      !this.codeForm.code().value() ||
      this.codeForm.code().invalid() ||
      this.#isProcessing() ||
      this.codeForm.code().value() === this.#previousSubmission(),
  );

  protected verificationError = signal(false);

  /**
   * Input handler for the IVA verification code
   * @param event The input event object
   */
  onInput(event: Event): void {
    event.preventDefault();
    const target = event.target as HTMLInputElement;
    target.value = target.value
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, '')
      .slice(0, 6);
    this.codeForm.code().value.set(target.value);
    if (
      this.codeForm.code().invalid() ||
      this.codeForm.code().value() === this.#previousSubmission()
    )
      return;
    this.onSubmit();
  }

  /**
   * Cancel the dialog
   */
  onCancel(): void {
    this.#dialogRef.close(undefined);
  }

  /**
   * Submit the verification code for the given IVA
   * @param id - the IVA ID to verify
   * @param code - the verification code
   * @returns whether the verification was successful
   */
  async submitVerificationCode(id: string, code: string): Promise<boolean> {
    return new Promise((resolve) => {
      this.#ivaService.validateCodeForIva(id, code).subscribe({
        next: () => {
          this.#notify.showSuccess('Verification was successful');
          resolve(true);
        },
        error: (err) => {
          switch (err.status) {
            case 403:
              this.#notify.showError(
                'The entered verification code was invalid. Please enter the submitted code correctly.',
              );
              break;
            case 429:
              this.#notify.showError(
                'Too many attempts at entering a code. IVA has been reverted to unverified.',
              );
              break;
            default:
              console.debug(err);
              this.#notify.showError(
                'Code verification currently not possible. Please try again later.',
              );
          }
          resolve(false);
        },
      });
    });
  }

  /**
   * Complete the verification and pass the code
   */
  async onSubmit(): Promise<void> {
    if (this.#isProcessing()) return;
    const code = this.codeForm.code().value();
    if (!code || this.codeForm.code().invalid()) return;
    this.#isProcessing.set(true);
    this.#previousSubmission.set(code);
    const verified = await this.submitVerificationCode(this.data.id, code);
    if (verified) {
      this.#dialogRef.close(true);
    } else {
      this.verificationError.set(true);
      await new Promise((r) => setTimeout(r, 2500)).finally(() => {
        this.#isProcessing.set(false);
      });
    }
  }
}
