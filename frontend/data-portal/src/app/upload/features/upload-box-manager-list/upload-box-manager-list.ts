/**
 * Component that lists all upload boxes.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe } from '@angular/common';
import { Component, computed, effect, inject, viewChild } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { Router } from '@angular/router';
import { Capitalise } from '@app/shared/pipes/capitalise-pipe';
import { ParseBytes } from '@app/shared/pipes/parse-bytes-pipe';
import { NotificationService } from '@app/shared/services/notification';
import { providePaginatorIntl } from '@app/shared/services/paginator-intl';
import {
  ResearchDataUploadBox,
  UploadBoxState,
  UploadBoxStateClass,
} from '@app/upload/models/box';
import { UploadBoxService } from '@app/upload/services/upload-box';

/** Sort order for upload box states: locked first, then open, then archived */
const STATE_SORT_ORDER: Record<UploadBoxState, number> = {
  [UploadBoxState.locked]: 0,
  [UploadBoxState.open]: 1,
  [UploadBoxState.archived]: 2,
};

/** An upload box row annotated with derived display values. */
interface UploadBoxRow extends ResearchDataUploadBox {
  stateClass: string;
  storageLabel: string;
}

/**
 * Upload Box Manager List component.
 *
 * This component lists upload boxes and applies active filter criteria.
 */
@Component({
  selector: 'app-upload-box-manager-list',
  imports: [
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    MatButtonModule,
    MatIcon,
    ParseBytes,
    Capitalise,
    DatePipe,
  ],
  providers: [providePaginatorIntl('Upload boxes per page')],
  templateUrl: './upload-box-manager-list.html',
})
export class UploadBoxManagerListComponent {
  #uploadBoxService = inject(UploadBoxService);
  #notify = inject(NotificationService);
  #router = inject(Router);

  #uploadBoxResource = this.#uploadBoxService.boxRetrievalResults;
  uploadBoxes = this.#uploadBoxService.filteredUploadBoxes;
  uploadBoxesAreLoading = this.#uploadBoxResource.isLoading;
  uploadBoxesError = this.#uploadBoxResource.error;

  /**
   * The upload boxes to display, each annotated with derived display values
   * (state CSS class and human-readable storage label). Deriving these in a
   * computed keeps the mappings out of the template and change detection, and
   * lets the labels react when the storage labels finish loading.
   */
  #rows = computed<UploadBoxRow[]>(() =>
    this.uploadBoxes().map((box) => ({
      ...box,
      stateClass: UploadBoxStateClass[box.state],
      storageLabel: this.#uploadBoxService.getStorageLocationLabel(box.storage_alias),
    })),
  );

  dataSource = new MatTableDataSource<UploadBoxRow>([]);

  #updateDataSourceEffect = effect(() => (this.dataSource.data = this.#rows()));

  #uploadBoxErrorEffect = effect(() => {
    if (this.uploadBoxesError()) {
      this.#notify.showError('Error retrieving upload boxes.');
    }
  });

  #uploadBoxSortingAccessor = (
    uploadBox: UploadBoxRow,
    key: string,
  ): string | number => {
    switch (key) {
      case 'title':
        return uploadBox.title;
      case 'state':
        return STATE_SORT_ORDER[uploadBox.state];
      case 'files':
        return uploadBox.file_count;
      case 'size':
        return uploadBox.size;
      case 'limit':
        return uploadBox.max_size;
      case 'location':
        return uploadBox.storageLabel;
      case 'last_change':
        return uploadBox.last_changed;
      default:
        const value = uploadBox[key as keyof ResearchDataUploadBox];
        if (typeof value === 'string' || typeof value === 'number') {
          return value;
        }
        return '';
    }
  };

  private readonly sort = viewChild(MatSort);
  private readonly paginator = viewChild(MatPaginator);

  /** Assign sort and configure sorting once available */
  #assignSortEffect = effect(() => {
    const sort = this.sort();
    if (!sort) return;
    this.dataSource.sortingDataAccessor = this.#uploadBoxSortingAccessor;
    this.dataSource.sortData = (data, s) => {
      const { active, direction } = s;
      return [...data].sort((a, b) => {
        if (!direction) {
          // Default / no-sort: state order (locked→open→archived), then last_changed descending
          const stateCompare = STATE_SORT_ORDER[a.state] - STATE_SORT_ORDER[b.state];
          if (stateCompare !== 0) return stateCompare;
          return b.last_changed.localeCompare(a.last_changed);
        }
        const valA = this.dataSource.sortingDataAccessor(a, active);
        const valB = this.dataSource.sortingDataAccessor(b, active);
        let compare = 0;
        if (valA > valB) compare = 1;
        else if (valA < valB) compare = -1;
        if (direction === 'desc') compare = -compare;
        // Secondary sort within same state: last_changed descending
        if (compare === 0 && active === 'state') {
          return b.last_changed.localeCompare(a.last_changed);
        }
        return compare;
      });
    };
    this.dataSource.sort = sort;
  });

  /** Assign paginator once available */
  #assignPaginatorEffect = effect(() => {
    const paginator = this.paginator();
    if (paginator) this.dataSource.paginator = paginator;
  });

  /**
   * Navigate to the detail view for a given upload box.
   * @param event - the originating mouse event
   * @param box - the upload box to view
   */
  viewDetails(event: MouseEvent, box: ResearchDataUploadBox): void {
    if ((event.target as HTMLElement | null)?.closest('a')) return;
    this.#router.navigate(['/upload-box-manager', box.id]);
  }
}
