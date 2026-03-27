/**
 * Component that hosts the Upload Box Manager feature.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ChangeDetectionStrategy, Component, inject, OnInit } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { NotificationService } from '@app/shared/services/notification';
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
  ],
  templateUrl: './upload-box-manager.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadBoxManagerComponent implements OnInit {
  #uploadBoxService = inject(UploadBoxService);
  #dialog = inject(MatDialog);
  #notificationService = inject(NotificationService);

  /**
   * Load all upload boxes when the component is initialized.
   */
  ngOnInit(): void {
    this.#uploadBoxService.loadAllUploadBoxes();
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
