/**
 * Component that lists all upload boxes.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  viewChild,
} from '@angular/core';
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
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadBoxManagerListComponent {
  #uploadBoxService = inject(UploadBoxService);
  #notify = inject(NotificationService);
  #router = inject(Router);

  #uploadBoxResource = this.#uploadBoxService.boxRetrievalResults;
  uploadBoxes = this.#uploadBoxService.filteredUploadBoxes;
  uploadBoxesAreLoading = this.#uploadBoxResource.isLoading;
  uploadBoxesError = this.#uploadBoxResource.error;

  dataSource = new MatTableDataSource<ResearchDataUploadBox>([]);

  #updateDataSourceEffect = effect(() => (this.dataSource.data = this.uploadBoxes()));

  #uploadBoxErrorEffect = effect(() => {
    if (this.uploadBoxesError()) {
      this.#notify.showError('Error retrieving upload boxes.');
    }
  });

  #uploadBoxSortingAccessor = (
    uploadBox: ResearchDataUploadBox,
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
      case 'location':
        return this.getStorageLocationLabel(uploadBox.storage_alias);
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
   * Get the status class for an upload box state.
   * @param state - the upload box state
   * @returns a CSS class for the state
   */
  getUploadBoxStateClass(state: ResearchDataUploadBox['state']): string {
    return UploadBoxStateClass[state];
  }

  /**
   * Get the human-readable storage location for a storage alias.
   * @param storageAlias - storage alias from the upload box
   * @returns storage location label or alias fallback
   */
  getStorageLocationLabel(storageAlias: string): string {
    return this.#uploadBoxService.getStorageLocationLabel(storageAlias);
  }

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
