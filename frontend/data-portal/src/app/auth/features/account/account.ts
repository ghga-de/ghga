/**
 * The Account module is the parent of all account-related components in the portal
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { ActiveAccessGrantsListComponent } from '@app/access-requests/features/active-access-grants-list/active-access-grants-list';
import { PendingAccessRequestsListComponent } from '@app/access-requests/features/pending-access-requests-list/pending-access-requests-list';
import { AuthService } from '@app/auth/services/auth';
import { ExternalLinkDirective } from '@app/shared/ui/external-link/external-link';
import { UserIvaListComponent } from '@app/verification-addresses/features/user-iva-list/user-iva-list';

/**
 * This Component shows data about the current user and allows managing their IVAs.
 */
@Component({
  selector: 'app-account',
  imports: [
    MatCardModule,
    MatIconModule,
    MatChipsModule,
    PendingAccessRequestsListComponent,
    ActiveAccessGrantsListComponent,
    UserIvaListComponent,
    ExternalLinkDirective,
  ],
  templateUrl: './account.html',
})
export class AccountComponent {
  #auth = inject(AuthService);
  fullName = this.#auth.fullName;
  roleNames = this.#auth.roleNames;
  email = this.#auth.email;
}
