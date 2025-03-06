/**
 * Component for the individual search results in the metadata browser
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, effect, inject, input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { Hit } from '@app/metadata/models/search-results';
import { MetadataService } from '@app/metadata/services/metadata.service';
import { NotificationService } from '@app/shared/services/notification.service';
import { DatasetSummaryComponent } from '../dataset-summary/dataset-summary.component';
import { DatasetSummaryStencilComponent } from '../dataset-summary/dataset-summary.stencil.component';

/**
 * Component for the expansion panel for each dataset found in the search results
 */
@Component({
  selector: 'app-search-result',
  imports: [
    MatExpansionModule,
    MatChipsModule,
    MatIconModule,
    MatButtonModule,
    DatasetSummaryComponent,
    DatasetSummaryStencilComponent,
  ],
  templateUrl: './search-result.component.html',
  styleUrl: './search-result.component.scss',
})
export class SearchResultComponent {
  #notify = inject(NotificationService);
  #metadata = inject(MetadataService);

  asStencil = input<boolean>(false);

  hit = input.required<Hit>();
  hitContent = computed(() => this.hit().content);

  summary = this.#metadata.datasetSummary;
  studiesSummary = computed(() => this.summary.value().studies_summary);
  studiesSummaryStats = computed(() => this.studiesSummary().stats);
  samplesSummary = computed(() => this.summary.value().samples_summary);
  samplesSex = computed(() => this.samplesSummary().stats.sex);
  samplesTissues = computed(() => this.samplesSummary().stats.tissues);
  samplesPhenotypes = computed(() => this.samplesSummary().stats.phenotypic_features);
  filesSummary = computed(() => this.summary.value().files_summary);
  filesFormats = computed(() => this.filesSummary().stats.format);
  experimentsSummary = computed(() => this.summary.value().experiments_summary);
  experimentsPlatforms = computed(
    () => this.experimentsSummary().stats.experiment_methods,
  );

  /**
   * On opening of the search result expansible panel,
   * load the query variables to the injectable service to trigger the backend query.
   */
  onOpen(): void {
    this.#metadata.loadDatasetSummary(this.hit().id_);
  }

  #errorEffect = effect(() => {
    if (this.summary.error()) {
      this.#notify.showError('Error fetching dataset summary.');
    }
  });
}
