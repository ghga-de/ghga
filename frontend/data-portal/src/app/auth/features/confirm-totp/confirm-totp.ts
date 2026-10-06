/**
 * Component to confirm TOTP codes
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  Component,
  computed,
  effect,
  inject,
  linkedSignal,
  signal,
} from '@angular/core';
import { form, FormField, maxLength, pattern, required } from '@angular/forms/signals';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { AuthService } from '@app/auth/services/auth';
import { Notifier } from '@app/shared/services/notification';
import { NormalizeInput } from '@app/shared/ui/normalize-input/normalize-input';

/**
 * Keep only the first 6 digits of an entered TOTP code
 * @param value - the raw text
 * @returns the code as the form keeps it
 */
export function toTotpCode(value: string): string {
  return value.replace(/\D/g, '').slice(0, 6);
}

/**
 * TOTP confirmation page
 */
@Component({
  selector: 'app-confirm-totp',
  imports: [
    FormField,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    NormalizeInput,
  ],
  templateUrl: './confirm-totp.html',
  styleUrl: './confirm-totp.scss',
})
export class ConfirmTotp {
  #notify = inject(Notifier);
  #authService = inject(AuthService);

  protected toTotpCode = toTotpCode;

  /**
   * The form model, which keeps only the first 6 digits of an entered code.
   */
  protected totpModel = linkedSignal<{ code: string }>(() => ({ code: '' }), {
    set: (model, rawSet) => rawSet({ ...model, code: toTotpCode(model.code) }),
  });

  protected totpForm = form(this.totpModel, (schemaPath) => {
    required(schemaPath.code);
    maxLength(schemaPath.code, 6);
    pattern(schemaPath.code, /^\d{6}$/);
  });

  #previousSubmission = signal('');

  #isProcessing = signal(false);

  /**
   * Whether the last submitted code was rejected. Resets itself as soon as the
   * user changes the code again.
   */
  protected verificationError = linkedSignal<string, boolean>({
    source: () => this.totpForm.code().value(),
    computation: () => false,
  });

  allowNavigation = false; // used by canDeactivate guard

  protected disabled = computed<boolean>(
    () =>
      !this.totpForm.code().value() ||
      this.totpForm.code().invalid() ||
      this.#isProcessing() ||
      this.totpForm.code().value() === this.#previousSubmission(),
  );

  /**
   * Submit automatically, but only once, as soon as a complete code was entered.
   */
  #autoSubmitEffect = effect(() => {
    if (!this.#previousSubmission() && !this.disabled()) void this.onSubmit();
  });

  /**
   * Submit authentication code
   * @param event the form submit event object
   */
  async onSubmit(event?: Event): Promise<void> {
    event?.preventDefault();
    if (this.disabled()) return;
    this.#isProcessing.set(true);
    const code = this.totpForm.code().value();
    this.#previousSubmission.set(code);
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
