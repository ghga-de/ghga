/**
 * Component to confirm TOTP codes
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
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { AuthService } from '@app/auth/services/auth';
import { NotificationService } from '@app/shared/services/notification';

/**
 * TOTP confirmation page
 */
@Component({
  selector: 'app-confirm-totp',
  imports: [
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
  ],
  templateUrl: './confirm-totp.html',
  styleUrl: './confirm-totp.scss',
})
export class ConfirmTotpComponent {
  #notify = inject(NotificationService);
  #authService = inject(AuthService);

  protected disabled = computed(
    () => this.#validInput() !== 'VALID' || this.#isProcessing(),
  );

  #previousSubmission: string | undefined = undefined;

  #isProcessing = signal(false);

  protected codeControl = new FormControl<string>('', [
    Validators.required,
    Validators.pattern(/^\d{6}$/),
  ]);
  #validInput = toSignal(this.codeControl.statusChanges, {
    initialValue: this.codeControl.status,
  });

  protected verificationError = signal(false);

  allowNavigation = false; // used by canDeactivate guard

  /**
   * Input handler for the TOTP code
   * @param event The input event object
   */
  onInput(event: Event): void {
    event.preventDefault();
    const target = event.target as HTMLInputElement;
    target.value = target.value.replace(/\D/g, '').slice(0, 6);
    this.codeControl.setValue(target.value);
    if (!this.codeControl.valid) return;
    if (this.codeControl.value === this.#previousSubmission) return;
    this.onSubmit();
  }

  /**
   * Submit authentication code
   */
  async onSubmit(): Promise<void> {
    if (this.disabled()) return;
    const code = this.codeControl.value;
    if (!code || !this.codeControl.valid) return;
    this.#isProcessing.set(true);
    this.#previousSubmission = code;
    const verified = await this.#authService.verifyTotpCode(code);
    if (verified) {
      this.#notify.showSuccess('Successfully authenticated.');
      this.allowNavigation = true;
      this.#authService.redirectAfterLogin();
    } else {
      this.#notify.showError('Failed to authenticate.');
      this.verificationError.set(true);
      await new Promise((r) => setTimeout(r, 2500)).finally(() => {
        this.#isProcessing.set(false);
      });
    }
  }

  /**
   * Set status to "lost token" and redirect to token setup
   */
  onLostToken(): void {
    this.allowNavigation = true;
    this.#authService.lostTotpSetup();
  }
}
