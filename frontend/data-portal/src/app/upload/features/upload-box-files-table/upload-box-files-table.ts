/**
 * Reusable table showing the file uploads contained in an upload box.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe as CommonDatePipe } from '@angular/common';
import { Component, computed, input, output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatSortModule, Sort, SortDirection } from '@angular/material/sort';
import { MatTableModule } from '@angular/material/table';
import { DatePipe } from '@app/shared/pipes/date-pipe';
import { ParseBytes } from '@app/shared/pipes/parse-bytes-pipe';
import {
  DEFAULT_TIME_ZONE,
  FRIENDLY_DATE_FORMAT,
} from '@app/shared/utils/date-formats';
import { UploadBoxState } from '@app/upload/models/box';
import {
  DEFAULT_UPLOADS_PAGE_SIZE,
  FileUploadWithAccession,
} from '@app/upload/models/file-upload';
import { FileUploadStatePipe } from '@app/upload/pipes/file-upload-state-pipe';

/**
 * Presentational, paginated table of the file uploads in an upload box.
 *
 * Pagination and sorting are driven by the server: `pageFiles` holds a single
 * page as delivered by the RS, and the paginator and sort headers only report
 * the requested page and order via the `page` and `sortChange` outputs. The
 * parent is responsible for fetching the matching page.
 *
 * The visible columns depend on the box state: archived boxes show the assigned
 * accession, other boxes show the upload status. When `showDelete` is set, an
 * extra column offers a delete button for each file for which `deletable`
 * returns true, emitting `deleteFile` on click.
 */
@Component({
  selector: 'app-upload-box-files-table',
  imports: [
    MatButtonModule,
    MatIcon,
    MatPaginatorModule,
    MatSortModule,
    MatTableModule,
    DatePipe,
    ParseBytes,
    FileUploadStatePipe,
  ],
  providers: [CommonDatePipe],
  templateUrl: './upload-box-files-table.html',
})
export class UploadBoxFilesTableComponent {
  /** The file uploads of the currently shown page, not the whole collection. */
  pageFiles = input.required<FileUploadWithAccession[]>();

  /** The state of the box the files belong to (controls the visible columns). */
  boxState = input.required<UploadBoxState>();

  /** The total number of file uploads in the box, across all pages. */
  totalCount = input<number>(0);

  /** The zero-based index of the currently shown page. */
  pageIndex = input<number>(0);

  /** The number of file uploads requested per page. */
  pageSize = input<number>(DEFAULT_UPLOADS_PAGE_SIZE);

  /** The column the files are currently sorted by. */
  sortActive = input<string>('alias');

  /** The direction the files are currently sorted in. */
  sortDirection = input<SortDirection>('asc');

  /**
   * Whether the file list is still being loaded. Controls the empty-table
   * placeholder: while loading it reads as "loading", once loaded it reads as
   * "empty" instead of showing a permanent loading message.
   */
  loading = input<boolean>(false);

  /** Whether to show a column with per-file delete buttons. */
  showDelete = input<boolean>(false);

  /** Predicate deciding whether an individual file may be deleted. */
  deletable = input<(file: FileUploadWithAccession) => boolean>(() => false);

  /** Umami analytics event label for the delete button, if any. */
  deleteEventLabel = input<string>('');

  /** Emitted when the delete button of a file is clicked. */
  deleteFile = output<FileUploadWithAccession>();

  /** Emitted when a different page or page size is requested. */
  page = output<PageEvent>();

  /** Emitted when a different sort order is requested. */
  sortChange = output<Sort>();

  /** Human-readable date format for the upload timestamp. */
  readonly friendlyDateFormat = FRIENDLY_DATE_FORMAT;

  /** Timezone for date display. */
  readonly timeZone = DEFAULT_TIME_ZONE;

  /** The columns to display, depending on box state and delete availability. */
  columns = computed<string[]>(() => {
    if (this.boxState() === UploadBoxState.archived) {
      return ['alias', 'accession', 'size', 'uploaded'];
    }
    const columns = ['alias', 'status', 'size', 'uploaded'];
    // Files can only be deleted while the box is still open for uploads.
    if (this.showDelete()) columns.push('delete');
    return columns;
  });

  /**
   * Whether to show the paginator (only useful for larger file lists). The
   * threshold is the total number of files rather than the page size, so that
   * choosing a larger page size can never hide the paginator.
   */
  showPaginator = computed<boolean>(
    () => this.totalCount() > DEFAULT_UPLOADS_PAGE_SIZE,
  );
}
