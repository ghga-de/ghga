/**
 * Component for the individual expansion panels for the metadata browser
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
import { AddPluralS } from '@app/shared/utils/add-plural-s.pipe';
import { UnderscoreToSpace } from '@app/shared/utils/underscore-to-space.pipe';

/**
 * Component for the expansion panel for each dataset found in the search results
 */
@Component({
  selector: 'app-dataset-expansion-panel',
  imports: [
    MatExpansionModule,
    MatChipsModule,
    MatIconModule,
    MatButtonModule,
    UnderscoreToSpace,
    AddPluralS,
  ],
  templateUrl: './dataset-expansion-panel.component.html',
  styleUrl: './dataset-expansion-panel.component.scss',
})
export class DatasetExpansionPanelComponent {
  #notify = inject(NotificationService);
  #metadata = inject(MetadataService);

  hit = input.required<Hit>();
  hitContent = computed(() => this.hit().content);

  summary = this.#metadata.datasetSummary;
  studiesSummary = computed(() => this.summary().studies_summary);
  studiesSummaryStats = computed(() => this.studiesSummary().stats);
  samplesSummary = computed(() => this.summary().samples_summary);
  samplesSex = computed(() => this.samplesSummary().stats.sex);
  samplesTissues = computed(() => this.samplesSummary().stats.tissues);
  samplesPhenotypes = computed(() => this.samplesSummary().stats.phenotypic_features);
  filesSummary = computed(() => this.summary().files_summary);
  filesFormats = computed(() => this.filesSummary().stats.format);
  experimentsSummary = computed(() => this.summary().experiments_summary);
  experimentsPlatforms = computed(
    () => this.experimentsSummary().stats.experiment_methods,
  );

  /**
   * On opening of the expansible panel, load the query variables to the injectable service to prepare for the backend query
   */
  onOpen(): void {
    this.#metadata.loadDatasetID(this.hit().id_);
  }

  #errorEffect = effect(() => {
    if (this.#metadata.datasetSummaryError()) {
      this.#notify.showError('Error fetching dataset summary.');
    }
  });
}
