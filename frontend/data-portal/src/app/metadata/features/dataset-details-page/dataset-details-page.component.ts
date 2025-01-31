/**
 * Short module description
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Location } from '@angular/common';
import {
  Component,
  computed,
  effect,
  inject,
  input,
  OnInit,
  Signal,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { MatSortModule } from '@angular/material/sort';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { File } from '@app/metadata/models/dataset-details';
import { DatasetInformationService } from '@app/metadata/services/dataset-information.service';
import { MetadataService } from '@app/metadata/services/metadata.service';
import { StorageAlias } from '@app/metadata/utils/storage-alias.pipe';
import { NotificationService } from '@app/shared/services/notification.service';
import { AddPluralS } from '@app/shared/utils/add-plural-s.pipe';
import { ParseBytes } from '@app/shared/utils/parse-bytes.pipe';
import { UnderscoreToSpace } from '@app/shared/utils/underscore-to-space.pipe';

/**
 * Component for the dataset details page
 */
@Component({
  selector: 'app-dataset-details-page',
  imports: [
    MatIconModule,
    MatButtonModule,
    MatChipsModule,
    UnderscoreToSpace,
    MatTabsModule,
    MatTableModule,
    MatExpansionModule,
    AddPluralS,
    MatSortModule,
    ParseBytes,
    StorageAlias,
  ],
  templateUrl: './dataset-details-page.component.html',
  styleUrl: './dataset-details-page.component.scss',
})
export class DatasetDetailsPageComponent implements OnInit {
  id = input.required<string>();
  #notify = inject(NotificationService);
  #metadata = inject(MetadataService);
  #dins = inject(DatasetInformationService);

  datasetDetails = this.#metadata.datasetDetails;
  dap = computed(() => this.datasetDetails().data_access_policy);
  dac = computed(() => this.dap().data_access_committee);
  study = computed(() => this.datasetDetails().study);
  publications = computed(() => this.study().publications);
  experiments = computed(() => this.datasetDetails().experiments);
  samples = computed(() => this.datasetDetails().samples);

  datasetInformation = this.#dins.datasetInformation;
  allFiles: Signal<File[]> = computed(() =>
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

  /**
   * On component initialisation, load the dataset ID to the injectable services to prepare for the backend queries
   */
  ngOnInit(): void {
    this.#metadata.loadDatasetDetailsID(this.id());
    this.#dins.loadDatasetID(this.id());
  }

  location = inject(Location);

  /**
   * Function to go back to previous page
   */
  goBack() {
    this.location.back();
  }

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

  // TODO: implement sorting and pagination via MatDataSource using signals
  experimentsColumns: string[] = [
    'accession',
    'ega_accession',
    'title',
    'description',
    'method',
    'platform',
  ];
  samplesColumns: string[] = [
    'accession',
    'ega_accession',
    'description',
    'status',
    'sex',
    'phenotype',
    'biospecimen_type',
    'tissue',
  ];
  filesColumns: string[] = [
    'accession',
    'ega_accession',
    'name',
    'type',
    'origin',
    'size',
    'location',
    'hash',
  ];
}
