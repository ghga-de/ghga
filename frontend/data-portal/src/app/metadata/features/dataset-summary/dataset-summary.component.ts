/**
 * Component for the individual expansion panels' content for the metadata browser
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject, input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';
// eslint-disable-next-line boundaries/element-types
import { DynamicAccessRequestButtonComponent } from '@app/access-requests/features/dynamic-access-request-button/dynamic-access-request-button.component';
import { Hit } from '@app/metadata/models/search-results';
import { MetadataService } from '@app/metadata/services/metadata.service';
import { AddPluralS } from '@app/shared/pipes/add-plural-s.pipe';
import { SummaryBadgesComponent } from '../../../shared/ui/summary-badges/summary-badges.component';

/**
 * Component for the content of the expansion panel for each dataset found in the search results
 */
@Component({
  selector: 'app-dataset-summary',
  imports: [
    MatExpansionModule,
    MatChipsModule,
    MatIconModule,
    MatButtonModule,
    AddPluralS,
    RouterLink,
    DynamicAccessRequestButtonComponent,
    SummaryBadgesComponent,
  ],
  templateUrl: './dataset-summary.component.html',
  styleUrl: './dataset-summary.component.scss',
})
export class DatasetSummaryComponent {
  #metadata = inject(MetadataService);

  hit = input.required<Hit>();
  hitContent = computed(() => this.hit().content);
  summary = this.#metadata.datasetSummary.value;
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
}
