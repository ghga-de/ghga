/**
 * Reusable table showing the file uploads contained in an upload box.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe as CommonDatePipe } from '@angular/common';
import { Component, computed, effect, input, output, viewChild } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { DatePipe } from '@app/shared/pipes/date-pipe';
import { ParseBytes } from '@app/shared/pipes/parse-bytes-pipe';
import {
  DEFAULT_TIME_ZONE,
  FRIENDLY_DATE_FORMAT,
} from '@app/shared/utils/date-formats';
import { UploadBoxState } from '@app/upload/models/box';
import { FileUploadWithAccession } from '@app/upload/models/file-upload';
import { FileUploadStatePipe } from '@app/upload/pipes/file-upload-state-pipe';

/**
 * Presentational, paginated table of the file uploads in an upload box.
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
  /** The file uploads to display. */
  files = input.required<FileUploadWithAccession[]>();

  /** The state of the box the files belong to (controls the visible columns). */
  boxState = input.required<UploadBoxState>();

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

  /** Whether to show the paginator (only useful for larger file lists). */
  showPaginator = computed<boolean>(() => this.files().length > 10);

  /** MatTableDataSource for paginated and sortable file uploads. */
  dataSource = new MatTableDataSource<FileUploadWithAccession>();

  private readonly paginator = viewChild(MatPaginator);
  private readonly sort = viewChild(MatSort);

  #syncFilesEffect = effect(() => {
    this.dataSource.data = this.files();
  });

  #assignPaginatorEffect = effect(() => {
    const paginator = this.paginator();
    if (paginator) {
      this.dataSource.paginator = paginator;
    }
  });

  #assignSortEffect = effect(() => {
    const sort = this.sort();
    if (sort) {
      this.dataSource.sort = sort;
    }
  });

  /**
   * Wire up sorting that reads the value backing each visible column, since the
   * column names do not match the file properties one-to-one.
   */
  constructor() {
    this.dataSource.sortingDataAccessor = (file, column) => {
      switch (column) {
        case 'size':
          return file.decrypted_size;
        case 'uploaded':
          return file.state_updated;
        case 'status':
          return file.state;
        case 'accession':
          return file.accession ?? '';
        default:
          return file.alias;
      }
    };
  }
}
