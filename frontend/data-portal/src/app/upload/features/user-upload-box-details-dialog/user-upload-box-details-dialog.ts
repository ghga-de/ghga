/**
 * Read-only dialog showing an upload box owned by the current user.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, effect, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { PageEvent } from '@angular/material/paginator';
import { Sort } from '@angular/material/sort';
import { Capitalise } from '@app/shared/pipes/capitalise-pipe';
import { ParseBytes } from '@app/shared/pipes/parse-bytes-pipe';
import { RefreshButtonComponent } from '@app/shared/ui/refresh-button/refresh-button';
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
    RefreshButtonComponent,
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
   * The files on the currently shown page of the box. Filtered by the box's file
   * upload box ID so files left over from a previously opened box are never shown
   * while the fresh page is loading. Each file references the underlying file
   * upload box via its `box_id`, which is the `file_upload_box_id` of the research
   * box, not its `id`.
   */
  protected pageFiles = computed<FileUploadWithAccession[]>(() => {
    const fileUploadBoxId = this.box()?.file_upload_box_id;
    if (!fileUploadBoxId) return [];
    return this.#uploadBoxService
      .boxFiles()
      .filter((file) => file.box_id === fileUploadBoxId);
  });

  /** The total number of files in the box, across all pages. */
  protected filesTotalCount = this.#uploadBoxService.boxFilesTotalCount;

  /** The number of files shown per page. */
  protected filesPageSize = this.#uploadBoxService.boxFilesLimit;

  /** The zero-based index of the currently shown page of files. */
  protected filesPageIndex = computed<number>(() => {
    const pageSize = this.filesPageSize();
    if (!pageSize) return 0;
    return Math.floor(this.#uploadBoxService.boxFilesSkip() / pageSize);
  });

  /** The column and direction the files are currently sorted by. */
  protected filesSortState = this.#uploadBoxService.boxFilesSortState;

  /** Whether the box's file list is still being loaded. */
  protected filesLoading = computed<boolean>(() =>
    this.#uploadBoxService.boxFileUploads.isLoading(),
  );

  /**
   * Fetch the box and its files again on request. Uploads run through the GHGA
   * Connector, so file states advance while this dialog stays open.
   */
  protected refreshFiles(): void {
    this.#uploadBoxService.reloadUploadBox(this.boxId);
    this.#uploadBoxService.reloadFileUploadsForBox(this.boxId);
  }

  /**
   * Request a different page of files from the server.
   * @param event - the page event emitted by the paginator
   */
  protected onFilesPage(event: PageEvent): void {
    this.#uploadBoxService.paginateFileUploads(
      event.pageSize,
      event.pageIndex * event.pageSize,
    );
  }

  /**
   * Request the files in a different order from the server.
   * @param sort - the sort event emitted by the table headers
   */
  protected onFilesSort(sort: Sort): void {
    this.#uploadBoxService.sortFileUploadsByColumn(sort.active, sort.direction);
  }

  /** Whether the files of this box have already been requested for this dialog. */
  #filesRequested = false;

  /**
   * Load the box files once the box is available and known to be non-empty.
   * The dialog is created anew every time it is opened, so the flag limits this
   * to one fetch per opening: the box signal keeps changing afterwards (for
   * instance while paging through the files), and refetching on each of those
   * changes would be pointless.
   */
  #loadFilesEffect = effect(() => {
    const box = this.box();
    if (box && box.file_count > 0 && !this.#filesRequested) {
      this.#filesRequested = true;
      this.#uploadBoxService.reloadFileUploadsForBox(box.id);
    }
  });

  /**
   * Fetch the box again whenever the dialog is opened. Files are uploaded with
   * the GHGA Connector outside the portal, so the box contents and its file
   * list change without anything happening here. Merely loading the box would
   * not issue a request at all when the same box was inspected before, since
   * the request of the underlying resource would be unchanged.
   */
  constructor() {
    this.#uploadBoxService.reloadUploadBox(this.boxId);
  }
}
