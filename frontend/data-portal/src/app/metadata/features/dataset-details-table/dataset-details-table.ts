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
  ViewChild,
  ViewChildren,
} from '@angular/core';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import {
  datasetDetailsTableColumns,
  dataSortingDataAccessor,
} from '@app/metadata/models/dataset-details-table';
import { DetailsDataRendererPipe } from '@app/metadata/pipes/details-data-renderer-pipe';
import { WellKnownValueService } from '@app/metadata/services/well-known-value';
import { WithCopyButton } from '@app/shared/features/with-copy-button/with-copy-button';

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
  ],
  templateUrl: './dataset-details-table.html',
  styleUrl: './dataset-details-table.scss',
})
export class DatasetDetailsTableComponent implements AfterViewInit {
  tableName = input.required<string>();
  data = input.required<any[]>();
  header = input.required<string>();

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
  }
}
