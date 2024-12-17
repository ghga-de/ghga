/**
 * TOTP setup component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatTooltipModule } from '@angular/material/tooltip';
import { AuthService } from '@app/auth/services/auth.service';
import { QRCodeComponent } from 'angularx-qrcode';

// TODO: Polish this component
// TODO: Maybe show another warning or different text when state is "LostTotpToken"

/**
 * TOTP setup page
 */
@Component({
  selector: 'app-setup-totp',
  imports: [
    CommonModule,
    QRCodeComponent,
    MatButtonModule,
    MatInputModule,
    MatIcon,
    MatTooltipModule,
  ],
  templateUrl: './setup-totp.component.html',
})
export class SetupTotpComponent {
  #authService = inject(AuthService);
  #sessionState = this.#authService.sessionState;

  isLoading = this.#authService.isUndetermined;

  isNewlyRegistered = computed(() => this.#sessionState() === 'Registered');

  hasLostToken = computed(() => this.#sessionState() === 'LostTotpToken');

  lostTokenConfirmed = signal(false);

  /**
   * Get the provisioning URI as a signal
   */
  setupUri = computed(async () => {
    const state = this.#sessionState();
    if (!['NeedsTotpToken', 'LostTotpToken'].includes(state)) return null;
    const uri = await this.#authService.createTotpToken();
    return uri;
  });

  showManualSetup = false;

  /**
   * Confirm the registration status and proceed with the TOTP setup
   */
  confirmRegistration(): void {
    this.#authService.needsTotpSetup();
  }

  /**
   * Cancel the recreation of a lost TOTP token
   */
  cancelLostToken(): void {
    this.#authService.completeTotpSetup();
  }

  /**
   * Get the actual secret from the query parameter in the URI
   * @param uri The provisioning URI containing the secret
   * @returns just the secret from the URI
   */
  getSecret(uri: string): string {
    return new URLSearchParams(uri.substring(uri.indexOf('?'))).get('secret')!;
  }

  /**
   * Copy the secret to the clipboard
   * @param uri The provisioning URI containing the secret
   */
  copySecret(uri: string): void {
    navigator.clipboard.writeText(this.getSecret(uri));
  }

  /**
   * Complete the TOTP setup
   *
   * Assume that the user has added the TOTP token to the authenticator
   * and continue with the TOTP confirmation step.
   */
  completeSetup(): void {
    this.#authService.completeTotpSetup();
  }
}
