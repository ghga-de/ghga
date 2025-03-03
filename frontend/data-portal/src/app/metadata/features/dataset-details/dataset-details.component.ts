/**
 * Component for showing the dataset details page
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ClipboardModule } from '@angular/cdk/clipboard';
import { Location } from '@angular/common';
import {
  AfterViewInit,
  Component,
  computed,
  effect,
  inject,
  input,
  OnInit,
  QueryList,
  Signal,
  ViewChild,
  ViewChildren,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { Title } from '@angular/platform-browser';
// eslint-disable-next-line boundaries/element-types
import { DynamicAccessRequestButtonComponent } from '@app/access-requests/features/dynamic-access-request-button/dynamic-access-request-button.component';
import { Experiment, File, Sample } from '@app/metadata/models/dataset-details';
import { DatasetInformationService } from '@app/metadata/services/dataset-information.service';
import { MetadataService } from '@app/metadata/services/metadata.service';
import { StorageAlias } from '@app/metadata/utils/storage-alias.pipe';
import { NotificationService } from '@app/shared/services/notification.service';
import { AddPluralS } from '@app/shared/utils/add-plural-s.pipe';
import { ParseBytes } from '@app/shared/utils/parse-bytes.pipe';
import { UnderscoreToSpace } from '@app/shared/utils/underscore-to-space.pipe';

const COLUMNS = {
  experiments: 'accession ega_accession title description method platform',
  samples:
    'accession ega_accession description status sex phenotype biospecimen_type tissue',
  files: 'accession ega_accession name type origin size location hash',
};

/**
 * Component for the dataset details page
 */
@Component({
  selector: 'app-dataset-details',
  imports: [
    MatIconModule,
    MatButtonModule,
    MatChipsModule,
    MatTabsModule,
    MatExpansionModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    AddPluralS,
    StorageAlias,
    ParseBytes,
    UnderscoreToSpace,
    MatIconModule,
    ClipboardModule,
    DynamicAccessRequestButtonComponent,
  ],
  templateUrl: './dataset-details.component.html',
  styleUrl: './dataset-details.component.scss',
})
export class DatasetDetailsComponent implements OnInit, AfterViewInit {
  id = input.required<string>();
  #location = inject(Location);
  #title = inject(Title);
  #notify = inject(NotificationService);
  #metadata = inject(MetadataService);
  #dins = inject(DatasetInformationService);

  datasetDetails = this.#metadata.datasetDetails;
  datasetInformation = this.#dins.datasetInformation;

  dap = computed(() => this.datasetDetails().data_access_policy);
  dac = computed(() => this.dap().data_access_committee);
  study = computed(() => this.datasetDetails().study);
  publications = computed(() => this.study().publications);

  #experiments: Signal<Experiment[]> = computed(
    () => this.datasetDetails().experiments,
  );
  #samples: Signal<Sample[]> = computed(() => this.datasetDetails().samples);
  #files: Signal<File[]> = computed(() =>
    Object.entries(this.datasetDetails())
      .filter(([key]) => key.endsWith('_files'))
      .flatMap(([key, files]) => {
        const fileCategory = key.slice(0, -1).replace(' ', '_');
        const fileInfoMap = new Map();
        this.datasetInformation().file_information.forEach((fileInFo) =>
          fileInfoMap.set(fileInFo.accession, fileInFo),
        );
        return files.map((file: File) => {
          const fileInfo = fileInfoMap.get(file.accession);
          file.file_information = fileInfo;
          file.file_category = fileCategory;
          return { ...file };
        });
      }),
  );

  numExperiments = computed(() => this.#experiments().length);
  numSamples = computed(() => this.#samples().length);
  numFiles = computed(() => this.#files().length);
  numBytes = computed(() =>
    this.#files().reduce((acc, file) => acc + (file.file_information?.size ?? 0), 0),
  );

  experimentsDataSource = new MatTableDataSource<Experiment>([]);
  samplesDataSource = new MatTableDataSource<Sample>([]);
  filesDataSource = new MatTableDataSource<File>([]);

  defaultTablePageSize = 10;
  tablePageSizeOptions = [10, 25, 50, 100];

  @ViewChild('sortExperiments') sortExperiments!: MatSort;
  @ViewChild('sortSamples') sortSamples!: MatSort;
  @ViewChild('sortFiles') sortFiles!: MatSort;
  @ViewChildren(MatSort) matSorts!: QueryList<MatSort>;

  @ViewChild('experimentsPaginator') experimentsPaginator!: MatPaginator;
  @ViewChild('samplesPaginator') samplesPaginator!: MatPaginator;
  @ViewChild('filesPaginator') filesPaginator!: MatPaginator;
  @ViewChildren(MatPaginator) matPaginators!: QueryList<MatPaginator>;

  #updateExperimentsDataSourceEffect = effect(
    () => (this.experimentsDataSource.data = this.#experiments()),
  );
  #updateSamplesDataSourceEffect = effect(
    () => (this.samplesDataSource.data = this.#samples()),
  );
  #updateFilesDataSourceEffect = effect(
    () => (this.filesDataSource.data = this.#files()),
  );

  #datasetDetailsErrorEffect = effect(() => {
    if (this.#metadata.datasetDetailsError()) {
      this.#notify.showError('Error fetching dataset details.');
    }
  });

  #datasetInformationErrorEffect = effect(() => {
    if (this.#dins.datasetInformationError()) {
      this.#notify.showError('Error fetching dataset file information.');
    }
  });

  experimentsColumns: string[] = COLUMNS.experiments.split(' ');
  samplesColumns: string[] = COLUMNS.samples.split(' ');
  filesColumns: string[] = COLUMNS.files.split(' ');

  #experimentsSortingDataAccessor = (experiment: Experiment, key: string) => {
    switch (key) {
      case 'method':
        return experiment.experiment_method.name;
      case 'platform':
        return experiment.experiment_method.instrument_model;
      default:
        const value = experiment[key as keyof Experiment];
        if (typeof value === 'string' || typeof value === 'number') {
          return value;
        }
        return '';
    }
  };

  #samplesSortingDataAccessor = (sample: Sample, key: string) => {
    switch (key) {
      case 'status':
        return sample.case_control_status;
      case 'sex':
        return sample.individual.sex;
      case 'phenotype':
        return sample.individual.phenotypic_features_terms.join(', ');
      case 'tissue':
        return sample.biospecimen_tissue_term;
      default:
        const value = sample[key as keyof Sample];
        if (typeof value === 'string' || typeof value === 'number') {
          return value;
        }
        return '';
    }
  };

  #filesSortingDataAccessor = (file: File, key: string) => {
    switch (key) {
      case 'type':
        return file.format;
      case 'origin':
        return file.file_category ?? '';
      case 'size':
        return file.file_information?.size ?? '';
      case 'location':
        return file.file_information?.storage_alias ?? '';
      case 'hash':
        return file.file_information?.sha256_hash ?? '';
      default:
        const value = file[key as keyof File];
        if (typeof value === 'string' || typeof value === 'number') {
          return value;
        }
        return '';
    }
  };

  /**
   * On component initialisation
   * - update the title according to the ID
   * - request the detail information from the services
   */
  ngOnInit(): void {
    const id = this.id();
    if (id) {
      const title = this.#title.getTitle();
      if (title) {
        this.#title.setTitle(title.replace('Dataset Details', `Dataset ${id}`));
      }
      this.#metadata.loadDatasetDetails(id);
      this.#dins.loadDatasetInformation(id);
    }
  }

  /**
   * After the view has been initialised
   * assign the sorting of the tables to the data sources
   */
  ngAfterViewInit() {
    this.experimentsDataSource.sortingDataAccessor =
      this.#experimentsSortingDataAccessor;
    this.samplesDataSource.sortingDataAccessor = this.#samplesSortingDataAccessor;
    this.filesDataSource.sortingDataAccessor = this.#filesSortingDataAccessor;
    // Note: The following would be easier if the tables were their own components.
    // We need to wait for the tables to become visible before assigning the sorting.
    this.matSorts.changes.subscribe(() => {
      if (this.sortExperiments) this.experimentsDataSource.sort = this.sortExperiments;
      if (this.sortSamples) this.samplesDataSource.sort = this.sortSamples;
      if (this.sortFiles) this.filesDataSource.sort = this.sortFiles;
    });
    // Similarly for assigning the table paginators
    this.matPaginators.changes.subscribe(() => {
      if (this.experimentsPaginator)
        this.experimentsDataSource.paginator = this.experimentsPaginator;
      if (this.samplesPaginator)
        this.samplesDataSource.paginator = this.samplesPaginator;
      if (this.filesPaginator) this.filesDataSource.paginator = this.filesPaginator;
    });
  }

  /**
   * Function to go back to previous page
   */
  goBack() {
    this.#location.back();
  }

  /**
   * Function to notify user that full hash was copied to clipboard
   */
  notifyCopied() {
    this.#notify.showInfo('Complete file hash copied to clipboard', 1000);
  }
}
