/**
 * Show session information
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject } from '@angular/core';
import { AuthService } from '@app/auth/services/auth.service';

/**
 * Show user session information
 *
 * TODO: Only used for testing, remove this component later!
 */
@Component({
  selector: 'app-show-session',
  imports: [],
  templateUrl: './show-session.component.html',
})
export class ShowSessionComponent {
  #authService = inject(AuthService);

  fullName = this.#authService.fullName;
  sessionState = this.#authService.sessionState;
}
