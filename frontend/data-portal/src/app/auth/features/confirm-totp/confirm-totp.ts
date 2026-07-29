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
import { NotificationService } from '@app/shared/services/notification';

/**
 * TOTP confirmation page
 */
@Component({
  selector: 'app-confirm-totp',
  imports: [FormField, MatButtonModule, MatFormFieldModule, MatInputModule],
  templateUrl: './confirm-totp.html',
  styleUrl: './confirm-totp.scss',
})
export class ConfirmTotpComponent {
  #notify = inject(NotificationService);
  #authService = inject(AuthService);

  protected totpModel = signal<{ code: string }>({
    code: '',
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
   * Keep only the first 6 digits of the entered code.
   */
  #sanitizeCodeEffect = effect(() => {
    const code = this.totpForm.code().value();
    const sanitized = code.replace(/\D/g, '').slice(0, 6);
    if (sanitized !== code) this.totpForm.code().value.set(sanitized);
  });

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
