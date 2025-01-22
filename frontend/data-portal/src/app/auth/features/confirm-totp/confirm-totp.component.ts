/**
 * Component to confirm TOTP codes
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject } from '@angular/core';
import {
  FormControl,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { AuthService } from '@app/auth/services/auth.service';
import { NotificationService } from '@app/shared/services/notification.service';

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
  templateUrl: './confirm-totp.component.html',
  styleUrl: './confirm-totp.component.scss',
})
export class ConfirmTotpComponent {
  #notify = inject(NotificationService);
  #authService = inject(AuthService);

  codeControl = new FormControl<string>('', [
    Validators.required,
    Validators.pattern(/^\d{6}$/),
  ]);

  verificationError = false;

  allowNavigation = false; // used by canDeactivate guard

  /**
   * Input handler for the TOTP code
   */
  onInput(): void {
    this.verificationError = false;
  }

  /**
   * Submit authentication code
   */
  async onSubmit(): Promise<void> {
    this.verificationError = false;
    const code = this.codeControl.value;
    if (!code) return;
    const verified = await this.#authService.verifyTotpCode(code);
    if (verified) {
      this.#notify.showSuccess('Successfully authenticated.');
      this.allowNavigation = true;
      this.#authService.redirectAfterLogin();
    } else {
      this.#notify.showError('Failed to authenticate.');
      this.codeControl.reset();
      this.verificationError = true;
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
