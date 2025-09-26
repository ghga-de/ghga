/**
 * Account button with dropdown
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { NgOptimizedImage } from '@angular/common';
import { Component, computed, inject } from '@angular/core';

import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router } from '@angular/router';
import { AuthService } from '@app/auth/services/auth';
import { InitialsPipe } from '@app/shared/pipes/initials-pipe';
import { ConfigService } from '@app/shared/services/config';

/**
 * Account button component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */
@Component({
  selector: 'app-account-button',
  imports: [
    MatIconModule,
    MatButtonModule,
    MatMenuModule,
    MatTooltipModule,
    InitialsPipe,
    NgOptimizedImage,
  ],
  templateUrl: './account-button.html',
  styleUrl: './account-button.scss',
})
export class AccountButtonComponent {
  #router = inject(Router);
  #config = inject(ConfigService);
  #auth = inject(AuthService);
  #user = this.#auth.user;
  isLoggedIn = this.#auth.isLoggedIn;
  isAuthenticated = this.#auth.isAuthenticated;
  sessionState = this.#auth.sessionState;
  name = this.#auth.name;
  fullName = this.#auth.fullName;
  roleNames = this.#auth.roleNames;

  /**
   * User login
   */
  onLogin(): void {
    this.#auth.login();
  }

  /**
   * User logout
   */
  onLogout(): void {
    this.#auth.logout();
  }

  /**
   * Continue ongoing authentication process.
   * We don't actually need to do anything here.
   */
  continue(): void {}

  /**
   * Get ongoing process when user is logged in with 1st factor, but not with 2nd.
   * @returns the name of the ongoing process
   */
  ongoingProcess = computed(() => {
    switch (this.sessionState()) {
      case 'NeedsRegistration':
        return 'registration';
      case 'NeedsReRegistration':
        return 're-registration';
      default:
        return 'two-factor authentication setup';
    }
  });

  /**
   * Navigate to the account page
   */
  gotoAccount(): void {
    this.#router.navigate(['/account']);
  }

  /**
   * Open the (external) LS login page
   */
  manageLsLogin(): void {
    window.open(this.#config.oidcAccountUrl, '_blank', 'noreferrer,noopener');
  }
}
