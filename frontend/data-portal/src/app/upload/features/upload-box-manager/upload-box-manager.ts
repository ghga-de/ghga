/**
 * Component that hosts the Upload Box Manager feature.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject, OnInit } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { NotificationService } from '@app/shared/services/notification';
import { RefreshButtonComponent } from '@app/shared/ui/refresh-button/refresh-button';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { UploadBoxCreationDialogComponent } from '../upload-box-creation-dialog/upload-box-creation-dialog';
import { UploadBoxManagerFilterComponent } from '../upload-box-manager-filter/upload-box-manager-filter';
import { UploadBoxManagerListComponent } from '../upload-box-manager-list/upload-box-manager-list';

/**
 * Upload Box Manager component.
 *
 * This component is the data steward entry point for upload box management.
 */
@Component({
  selector: 'app-upload-box-manager',
  imports: [
    UploadBoxManagerFilterComponent,
    UploadBoxManagerListComponent,
    MatButtonModule,
    MatIconModule,
    RefreshButtonComponent,
  ],
  templateUrl: './upload-box-manager.html',
})
export class UploadBoxManagerComponent implements OnInit {
  #uploadBoxService = inject(UploadBoxService);
  #dialog = inject(MatDialog);
  #notificationService = inject(NotificationService);

  /**
   * Fetch all upload boxes when the component is initialized. File counts and
   * sizes change outside the portal (files are uploaded with the GHGA
   * Connector), so the list is fetched again on every visit rather than reusing
   * what was loaded earlier in the session.
   */
  ngOnInit(): void {
    this.#uploadBoxService.reloadAllUploadBoxes();
  }

  /** Whether the upload boxes are currently being fetched. */
  protected isLoading = this.#uploadBoxService.boxRetrievalResults.isLoading;

  /**
   * Fetch the upload boxes again on request. File counts and sizes advance as
   * users upload with the GHGA Connector, without the portal being involved.
   */
  protected refresh(): void {
    this.#uploadBoxService.reloadAllUploadBoxes();
  }

  /**
   * Open the create upload box dialog and handle a successful creation.
   */
  openCreateUploadBoxDialog(): void {
    const ref = this.#dialog.open(UploadBoxCreationDialogComponent, {
      width: 'clamp(40em, 85vw, 64em)',
      maxWidth: 'calc(100vw - 2rem)',
    });
    ref.afterClosed().subscribe((createdBoxId: string | undefined) => {
      if (!createdBoxId) return;
      this.#notificationService.showSuccess('Upload Box created successfully.');
    });
  }
}
