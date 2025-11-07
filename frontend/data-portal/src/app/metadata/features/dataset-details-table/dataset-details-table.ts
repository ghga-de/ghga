/**
 * Component for showing the dataset details tables
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  AfterViewInit,
  Component,
  computed,
  effect,
  inject,
  input,
  QueryList,
  signal,
  ViewChild,
  ViewChildren,
} from '@angular/core';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatTooltip } from '@angular/material/tooltip';
import {
  datasetDetailsTableColumns,
  dataSortingDataAccessor,
} from '@app/metadata/models/dataset-details-table';
import { DetailsDataRendererPipe } from '@app/metadata/pipes/details-data-renderer-pipe';
import { WellKnownValueService } from '@app/metadata/services/well-known-value';
import { WithCopyButton } from '@app/shared/features/with-copy-button/with-copy-button';
import { ParseBytes } from '@app/shared/pipes/parse-bytes-pipe';

/**
 * Component for the dataset details table
 */
@Component({
  selector: 'app-dataset-details-table',
  imports: [
    DetailsDataRendererPipe,
    MatExpansionModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    WithCopyButton,
    MatTooltip,
  ],
  templateUrl: './dataset-details-table.html',
  styleUrl: './dataset-details-table.scss',
})
export class DatasetDetailsTableComponent implements AfterViewInit {
  tableName = input.required<'experiments' | 'samples' | 'files'>();
  data = input.required<any[]>();

  protected header = computed(() => {
    let header = `List of ${this.tableName()} (${this.numItems()} total`;
    if (this.tableName() === 'files') {
      const totalBytes = this.data().reduce(
        (acc, file) => acc + (file.file_information?.size ?? 0),
        0,
      );
      header = `${header}, ${ParseBytes.prototype.transform(totalBytes)}`;
    }
    return `${header})`;
  });

  protected tooltipDisabled = signal(false);

  #hoverHeaderTime: number = 0;

  /**
   * When entering the tooltip, memorize start time
   */
  startHoverHeader(): void {
    this.#hoverHeaderTime = Date.now();
  }

  /**
   * After leaving the tooltip, disable if it was shown long enough
   */
  endHoverHeader(): void {
    if (Date.now() - this.#hoverHeaderTime < 1000) return;
    const key = `hint.${this.tableName()}.details.shown`;
    if (!sessionStorage.getItem(key)) {
      sessionStorage.setItem(key, 'true');
      this.tooltipDisabled.set(true);
    }
    this.#hoverHeaderTime = 0;
  }

  protected numItems = computed(() => this.data().length);

  protected columns = computed(() =>
    this.tableName ? (datasetDetailsTableColumns[this.tableName()] ?? []) : [],
  );
  protected sortingDataAccessor = computed(() =>
    this.tableName ? dataSortingDataAccessor[this.tableName()] : undefined,
  );

  protected caption = computed(() => `Dataset ${this.header().split(' ')[0]}`);
  protected dataSource = new MatTableDataSource<any>([]);

  protected displayCols = computed(() =>
    this.columns()
      .filter((x) => !x.hidden)
      .flatMap((x) => x.columnDef),
  );

  #wkvs = inject(WellKnownValueService);
  #storageLabels = this.#wkvs.storageLabels;
  protected storageLabels = this.#storageLabels.value;

  protected defaultTablePageSize = 10;
  protected tablePageSizeOptions = [10, 25, 50, 100];

  @ViewChild(MatSort) sort!: MatSort;
  @ViewChildren(MatSort) matSorts!: QueryList<MatSort>;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChildren(MatPaginator) matPaginators!: QueryList<MatPaginator>;

  #updateDataSourceEffect = effect(() => (this.dataSource.data = this.data()));

  /**
   * After the view has been initialised
   * assign the sorting of the tables to the data sources
   */
  ngAfterViewInit() {
    if (this.sortingDataAccessor()) {
      this.dataSource.sortingDataAccessor = this.sortingDataAccessor()!;
    }

    this.matSorts.changes.subscribe(() => {
      if (this.data()) this.dataSource.sort = this.sort;
    });
    this.matPaginators.changes.subscribe(() => {
      if (this.paginator) this.dataSource.paginator = this.paginator;
    });

    const key = `hint.${this.tableName()}.details.shown`;
    if (sessionStorage.getItem(key)) this.tooltipDisabled.set(true);
  }
}
