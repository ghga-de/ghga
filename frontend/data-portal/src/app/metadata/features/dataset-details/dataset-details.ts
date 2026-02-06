/**
 * Component for showing the dataset details page
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ClipboardModule } from '@angular/cdk/clipboard';
import { HttpErrorResponse } from '@angular/common/http';
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
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Title } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';
// eslint-disable-next-line boundaries/element-types
import { DynamicAccessRequestButtonComponent } from '@app/access-requests/features/dynamic-access-request-button/dynamic-access-request-button';
import { Experiment, File, Sample } from '@app/metadata/models/dataset-details';
import { ValidateDOI } from '@app/metadata/pipes/validate-doi-pipe';
import { DatasetInformationService } from '@app/metadata/services/dataset-information';
import { MetadataService } from '@app/metadata/services/metadata';
import { WellKnownValueService } from '@app/metadata/services/well-known-value';
import { UnderscoreToSpace } from '@app/shared/pipes/underscore-to-space-pipe';
import { ConfigService } from '@app/shared/services/config';
import { NavigationTrackingService } from '@app/shared/services/navigation';
import { NotificationService } from '@app/shared/services/notification';
import { ExternalLinkDirective } from '@app/shared/ui/external-link/external-link';
import { ParagraphsComponent } from '../../../shared/ui/paragraphs/paragraphs';
import { DatasetDetailsTableComponent } from '../dataset-details-table/dataset-details-table';

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
    UnderscoreToSpace,
    MatIconModule,
    ClipboardModule,
    DynamicAccessRequestButtonComponent,
    MatTooltipModule,
    RouterLink,
    ValidateDOI,
    ParagraphsComponent,
    ExternalLinkDirective,
    DatasetDetailsTableComponent,
  ],
  providers: [MetadataService],
  templateUrl: './dataset-details.html',
})
export class DatasetDetailsComponent implements OnInit {
  id = input.required<string>();
  #config = inject(ConfigService);
  #location = inject(NavigationTrackingService);
  #title = inject(Title);
  #notify = inject(NotificationService);
  #metadata = inject(MetadataService);
  #dins = inject(DatasetInformationService);
  #wkvs = inject(WellKnownValueService);

  #rtsUrl = this.#config.rtsUrl;
  metadataDownloadUrl = computed(
    () => `${this.#rtsUrl}/studies/${this.study().accession}`,
  );

  #datasetDetails = this.#metadata.datasetDetails;
  #datasetDetailsError = this.#datasetDetails.error;
  datasetDetails = this.#datasetDetails.value;
  datasetInformation = this.#dins.datasetInformation.value;
  #storageLabels = this.#wkvs.storageLabels;
  storageLabels = this.#storageLabels.value;

  errorMessage = computed(() => {
    if (this.#datasetDetailsError()) {
      switch ((this.#datasetDetailsError() as HttpErrorResponse)?.status) {
        case 404:
          return 'The specified dataset could not be found.';
        case undefined:
          return undefined;
        default:
          return 'There was an error loading the dataset details. Please try again later.';
      }
    } else return undefined;
  });

  readonly baseDuoUrl = 'https://purl.obolibrary.org/obo/';

  dap = computed(() => {
    const dap = this.datasetDetails().data_access_policy;
    const data_use_permission_url = `${this.baseDuoUrl}${dap.data_use_permission_id.replace(':', '_')}`;
    const data_use_permission_term = dap.data_use_permission_term
      .toLowerCase()
      .replaceAll('_', ' ');
    const modifierIds = dap.data_use_modifier_ids || [];
    const modifierTerms = dap.data_use_modifier_terms || [];
    const numModifiers = Math.max(modifierIds.length, modifierTerms.length);
    const data_use_modifiers = numModifiers
      ? Array.from({ length: numModifiers }, (_, idx) => {
          return {
            id: modifierIds[idx],
            url: modifierIds[idx]
              ? `${this.baseDuoUrl}${modifierIds[idx].replace(':', '_')}`
              : undefined,
            term: modifierTerms[idx]
              ? modifierTerms[idx].toLowerCase().replaceAll('_', ' ')
              : undefined,
          };
        })
      : undefined;
    return {
      ...dap,
      data_use_permission_term,
      data_use_permission_url,
      data_use_modifiers,
    };
  });
  dac = computed(() => this.dap().data_access_committee);
  study = computed(() => this.datasetDetails().study);
  publications = computed(() => this.study().publications);

  experiments: Signal<Experiment[]> = computed(() => this.datasetDetails().experiments);
  samples: Signal<Sample[]> = computed(() => this.datasetDetails().samples);
  files: Signal<File[]> = computed(() =>
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

  numExperiments = computed(() => this.experiments().length);
  numSamples = computed(() => this.samples().length);
  numFiles = computed(() => this.files().length);
  numBytes = computed(() =>
    this.files().reduce((acc, file) => acc + (file.file_information?.size ?? 0), 0),
  );

  #datasetDetailsErrorEffect = effect(() => {
    if (this.#datasetDetails.error()) {
      this.#notify.showError('Error fetching dataset details.');
    }
  });

  #datasetInformationErrorEffect = effect(() => {
    if (this.#dins.datasetInformation.error()) {
      this.#notify.showError('Error fetching dataset file information.');
    }
  });

  #storageLabelsErrorEffect = effect(() => {
    if (this.#wkvs.storageLabels.error()) {
      this.#notify.showError('Error fetching storage aliases.');
    }
  });

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
   * Function to go back to previous page
   */
  goBack() {
    this.#location.back(['browse']);
  }
}
