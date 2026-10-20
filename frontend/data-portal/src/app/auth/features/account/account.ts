/**
 * The Account module is the parent of all account-related components in the portal
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { ActiveAccessGrantsList } from '@app/access-requests/features/active-access-grants-list/active-access-grants-list';
import { PendingAccessRequestsList } from '@app/access-requests/features/pending-access-requests-list/pending-access-requests-list';
import { AuthService } from '@app/auth/services/auth';
import { UserIvaList } from '@app/ivas/features/user-iva-list/user-iva-list';
import { ExternalLink } from '@app/shared/ui/external-link/external-link';
import { RefreshButton } from '@app/shared/ui/refresh-button/refresh-button';
// eslint-disable-next-line boundaries/dependencies
import { UserUploadGrantsList } from '@app/upload/features/user-upload-grants-list/user-upload-grants-list';

/**
 * This Component shows data about the current user and allows managing their IVAs.
 */
@Component({
  selector: 'app-account',
  imports: [
    MatCardModule,
    MatIconModule,
    MatChipsModule,
    PendingAccessRequestsList,
    ActiveAccessGrantsList,
    UserIvaList,
    ExternalLink,
    UserUploadGrantsList,
    RefreshButton,
  ],
  templateUrl: './account.html',
})
export class Account {
  #auth = inject(AuthService);
  fullName = this.#auth.fullName;
  roleNames = this.#auth.roleNames;
  email = this.#auth.email;
}
