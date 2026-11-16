/**
 * Component that hosts the Upload Box Manager feature.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject, OnInit, signal, viewChild } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { HasPendingEdits } from '@app/shared/features/pending-edits';
import { Notifier } from '@app/shared/services/notification';
import { RefreshButton } from '@app/shared/ui/refresh-button/refresh-button';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { UploadBoxCreationDialog } from '../upload-box-creation-dialog/upload-box-creation-dialog';
import { UploadBoxManagerFilter } from '../upload-box-manager-filter/upload-box-manager-filter';
import { UploadBoxManagerList } from '../upload-box-manager-list/upload-box-manager-list';
import { UploadBoxPriorityEditor } from '../upload-box-priority-editor/upload-box-priority-editor';

/**
 * Upload Box Manager component.
 *
 * This component is the data steward entry point for upload box management.
 * It shows the list of upload boxes, or in reorder mode the priority order.
 */
@Component({
  selector: 'app-upload-box-manager',
  imports: [
    UploadBoxManagerFilter,
    UploadBoxManagerList,
    UploadBoxPriorityEditor,
    MatButtonModule,
    MatIconModule,
    RefreshButton,
  ],
  templateUrl: './upload-box-manager.html',
})
export class UploadBoxManager implements OnInit, HasPendingEdits {
  #uploadBoxService = inject(UploadBoxService);
  #dialog = inject(MatDialog);
  #notificationService = inject(Notifier);

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

  /** Whether the page is in reorder mode, where the steward changes the priority order */
  protected reordering = signal(false);

  private priorityEditor = viewChild(UploadBoxPriorityEditor);

  /** Whether the boxes and their priority order are loaded, so that the order can be changed */
  protected canChangePriority = computed(
    () =>
      !this.isLoading() &&
      !this.#uploadBoxService.boxRetrievalResults.error() &&
      this.#uploadBoxService.prioritizedUploadBoxes() !== undefined,
  );

  /**
   * Check if reorder mode has unsaved changes (implements the HasPendingEdits interface)
   * @returns true if there are pending edits, false otherwise
   */
  hasPendingEdits(): boolean {
    return this.priorityEditor()?.hasChanges() ?? false;
  }

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
    const ref = this.#dialog.open(UploadBoxCreationDialog, {
      width: 'clamp(40em, 85vw, 64em)',
      maxWidth: 'calc(100vw - 2rem)',
    });
    ref.afterClosed().subscribe((createdBoxId: string | undefined) => {
      if (!createdBoxId) return;
      this.#notificationService.showSuccess('Upload Box created successfully.');
    });
  }
}
