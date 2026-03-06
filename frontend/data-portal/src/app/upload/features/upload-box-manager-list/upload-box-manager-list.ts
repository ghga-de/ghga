/**
 * Component that lists all upload boxes.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  AfterViewInit,
  Component,
  effect,
  inject,
  QueryList,
  ViewChild,
  ViewChildren,
} from '@angular/core';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { Capitalise } from '@app/shared/pipes/capitalise-pipe';
import { ParseBytes } from '@app/shared/pipes/parse-bytes-pipe';
import { NotificationService } from '@app/shared/services/notification';
import { providePaginatorIntl } from '@app/shared/services/paginator-intl';
import { ResearchDataUploadBox, UploadBoxStateClass } from '@app/upload/models/box';
import { UploadBoxService } from '@app/upload/services/upload-box';

/**
 * Upload Box Manager List component.
 *
 * This component lists upload boxes and applies active filter criteria.
 */
@Component({
  selector: 'app-upload-box-manager-list',
  imports: [MatTableModule, MatSortModule, MatPaginatorModule, ParseBytes, Capitalise],
  providers: [providePaginatorIntl('Upload boxes per page')],
  templateUrl: './upload-box-manager-list.html',
})
export class UploadBoxManagerListComponent implements AfterViewInit {
  #uploadBoxService = inject(UploadBoxService);
  #notify = inject(NotificationService);

  #uploadBoxResource = this.#uploadBoxService.boxRetrievalResults;
  uploadBoxes = this.#uploadBoxService.filteredUploadBoxes;
  uploadBoxesAreLoading = this.#uploadBoxResource.isLoading;
  uploadBoxesError = this.#uploadBoxResource.error;

  dataSource = new MatTableDataSource<ResearchDataUploadBox>([]);

  defaultTablePageSize = 10;
  tablePageSizeOptions = [10, 25, 50, 100, 250, 500];

  #updateDataSourceEffect = effect(() => (this.dataSource.data = this.uploadBoxes()));

  #uploadBoxErrorEffect = effect(() => {
    if (this.uploadBoxesError()) {
      this.#notify.showError('Error retrieving upload boxes.');
    }
  });

  #uploadBoxSortingAccessor = (uploadBox: ResearchDataUploadBox, key: string) => {
    switch (key) {
      case 'title':
        return uploadBox.title;
      case 'state':
        return uploadBox.state;
      case 'files':
        return uploadBox.file_count;
      case 'size':
        return uploadBox.size;
      case 'location':
        return this.getStorageLocationLabel(uploadBox.storage_alias);
      default:
        const value = uploadBox[key as keyof ResearchDataUploadBox];
        if (typeof value === 'string' || typeof value === 'number') {
          return value;
        }
        return '';
    }
  };

  @ViewChildren(MatSort) matSorts!: QueryList<MatSort>;
  @ViewChildren(MatPaginator) matPaginators!: QueryList<MatPaginator>;
  @ViewChild('paginator') paginator!: MatPaginator;
  @ViewChild('sort') sort!: MatSort;

  /**
   * Assign sorting.
   */
  #addSorting() {
    if (this.sort) this.dataSource.sort = this.sort;
  }

  /**
   * Assign pagination.
   */
  #addPagination() {
    if (this.paginator) this.dataSource.paginator = this.paginator;
  }

  /**
   * Assign sorting and pagination once the view has initialized.
   */
  ngAfterViewInit() {
    this.dataSource.sortingDataAccessor = this.#uploadBoxSortingAccessor;
    this.#addSorting();
    this.#addPagination();
    this.matSorts.changes.subscribe(() => this.#addSorting());
    this.matPaginators.changes.subscribe(() => this.#addPagination());
  }

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
}
