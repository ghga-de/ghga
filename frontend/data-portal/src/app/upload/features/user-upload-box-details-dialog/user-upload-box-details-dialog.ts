/**
 * Read-only dialog showing an upload box owned by the current user.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, effect, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { Capitalise } from '@app/shared/pipes/capitalise-pipe';
import { ParseBytes } from '@app/shared/pipes/parse-bytes-pipe';
import { StencilComponent } from '@app/shared/ui/stencil/stencil/stencil';
import { ResearchDataUploadBox, UploadBoxStateClass } from '@app/upload/models/box';
import { FileUploadWithAccession } from '@app/upload/models/file-upload';
import { GrantWithBoxInfo } from '@app/upload/models/grant';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { UploadBoxFilesTableComponent } from '../upload-box-files-table/upload-box-files-table';

/**
 * Read-only details view of one of the current user's upload boxes, shown in a
 * dialog from the account page. Users can inspect the box metadata and the files
 * it contains, but cannot modify the box or its files.
 */
@Component({
  selector: 'app-user-upload-box-details-dialog',
  imports: [
    MatButtonModule,
    MatDialogModule,
    Capitalise,
    ParseBytes,
    StencilComponent,
    UploadBoxFilesTableComponent,
  ],
  templateUrl: './user-upload-box-details-dialog.html',
})
export class UserUploadBoxDetailsDialogComponent {
  #uploadBoxService = inject(UploadBoxService);

  /** The grant identifying the box to display, injected as dialog data. */
  #grant = inject<GrantWithBoxInfo>(MAT_DIALOG_DATA);

  /** The ID of the box to display. */
  protected readonly boxId = this.#grant.box_id;

  #box = this.#uploadBoxService.uploadBox;

  /** Map from box state to CSS class. */
  protected readonly stateClass = UploadBoxStateClass;

  /**
   * The box to display, or undefined while it is still being loaded. Guards on
   * the ID so a stale value from a previously opened box is not shown.
   */
  protected box = computed<ResearchDataUploadBox | undefined>(() => {
    const box = this.#box.error() ? undefined : this.#box.value();
    return box && box.id === this.boxId ? box : undefined;
  });

  /** Whether the box is currently being loaded. */
  protected isLoading = computed<boolean>(() => !this.box() && this.#box.isLoading());

  /** Whether loading the box failed. */
  protected hasError = computed<boolean>(() => !this.box() && !!this.#box.error());

  /**
   * The files contained in the box. Filtered by the box's file upload box ID so
   * files left over from a previously opened box are never shown while the fresh
   * list is loading. Each file references the underlying file upload box via its
   * `box_id`, which is the `file_upload_box_id` of the research box, not its `id`.
   */
  protected files = computed<FileUploadWithAccession[]>(() => {
    const fileUploadBoxId = this.box()?.file_upload_box_id;
    if (!fileUploadBoxId) return [];
    return this.#uploadBoxService.boxFileUploads
      .value()
      .filter((file) => file.box_id === fileUploadBoxId);
  });

  /** Whether the box's file list is still being loaded. */
  protected filesLoading = computed<boolean>(() =>
    this.#uploadBoxService.boxFileUploads.isLoading(),
  );

  /** Load the box files once the box is available and known to be non-empty. */
  #loadFilesEffect = effect(() => {
    const box = this.box();
    if (box && box.file_count > 0) {
      this.#uploadBoxService.loadFileUploadsForBox(box.id);
    }
  });

  /**
   * Trigger loading of the single box when the dialog is opened.
   */
  constructor() {
    this.#uploadBoxService.loadUploadBox(this.boxId);
  }
}
