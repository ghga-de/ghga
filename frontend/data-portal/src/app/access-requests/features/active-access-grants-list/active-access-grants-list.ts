/**
 * Show access requests that have been granted.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink, RouterModule } from '@angular/router';
import { AccessGrant } from '@app/access-requests/models/access-requests';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { StencilComponent } from '../../../shared/ui/stencil/stencil/stencil';
// eslint-disable-next-line boundaries/dependencies
import { DownloadWorkPackageDialogComponent } from '@app/work-packages/features/download-work-package-dialog/download-work-package-dialog';

/**
 * This component shows a list of access grants that have been granted.
 */
@Component({
  selector: 'app-granted-access-grants-list',
  imports: [RouterLink, StencilComponent, MatIconModule, MatButtonModule, RouterModule],
  templateUrl: './active-access-grants-list.html',
})
export class ActiveAccessGrantsListComponent {
  #ars = inject(AccessRequestService);
  #dialog = inject(MatDialog);

  protected activeGrants = computed(() => this.#ars.activeUserAccessGrants());
  protected isLoading = this.#ars.userAccessGrants.isLoading;
  protected hasError = this.#ars.userAccessGrants.error;

  /**
   * Open the download work package dialog for a specific grant.
   * The dialog resolves and loads the associated IVA itself.
   * @param grant The access grant to download data for
   */
  openDownloadDialog(grant: AccessGrant): void {
    this.#dialog.open(DownloadWorkPackageDialogComponent, {
      data: grant,
      width: '64rem',
      maxWidth: '96vw',
    });
  }
}
