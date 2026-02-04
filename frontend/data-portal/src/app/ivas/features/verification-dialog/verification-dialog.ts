/**
 * A dialog to input the IVA verification code
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
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
import { IvaService } from '@app/ivas/services/iva';
import { NotificationService } from '@app/shared/services/notification';

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
  templateUrl: './verification-dialog.html',
})
export class VerificationDialogComponent {
  #dialogRef = inject(MatDialogRef<VerificationDialogComponent, string>);
  #notify = inject(NotificationService);
  #ivaService = inject(IvaService);
  protected data = inject<{ id: string; address: string }>(MAT_DIALOG_DATA);
  protected address = computed(() => this.data.address);

  protected disabled = computed(
    () => this.#validInput() !== 'VALID' || this.#isProcessing(),
  );

  #previousSubmission: string | undefined = undefined;

  #isProcessing = signal(false);

  protected codeControl = new FormControl<string>('', [
    Validators.required,
    Validators.pattern(/^[A-Z0-9]{6}$/),
  ]);
  #validInput = toSignal(this.codeControl.statusChanges, {
    initialValue: this.codeControl.status,
  });

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
    this.codeControl.setValue(target.value);
    if (!this.codeControl.valid) return;
    if (this.codeControl.value === this.#previousSubmission) return;
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
                'Too many attempts at entering a code. Contact address has been reverted to unverified.',
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
    const code = this.codeControl.value;
    if (!code || !this.codeControl.valid) return;
    this.#isProcessing.set(true);
    this.#previousSubmission = code;
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
