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
import { MetadataService } from '@app/metadata/services/metadata';
import { NotificationService } from '@app/shared/services/notification';
import { DatasetSummaryComponent } from '../dataset-summary/dataset-summary';
import { DatasetSummaryStencilComponent } from '../dataset-summary/dataset-summary.stencil';

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
  providers: [MetadataService],
  templateUrl: './search-result.html',
  styleUrl: './search-result.scss',
})
export class SearchResultComponent {
  #notify = inject(NotificationService);
  #metadata = inject(MetadataService);
  #summary = this.#metadata.datasetSummary;

  asStencil = input<boolean>(false);

  hit = input.required<Hit>();
  hitContent = computed(() => this.hit().content);

  summary = this.#summary.value;
  isLoading = this.#summary.isLoading;

  /**
   * On opening of the search result expansible panel,
   * load the query variables to the injectable service to trigger the backend query.
   */
  onOpen(): void {
    this.#metadata.loadDatasetSummary(this.hit().id_);
  }

  #errorEffect = effect(() => {
    if (this.#summary.error()) {
      this.#notify.showError('Error fetching dataset summary.');
    }
  });
}
