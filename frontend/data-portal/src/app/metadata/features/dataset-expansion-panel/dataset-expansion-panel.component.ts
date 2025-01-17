/**
 * Component for the individual expansion panels for the metadata browser
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, effect, inject, input } from '@angular/core';
import { MatExpansionModule } from '@angular/material/expansion';
import { Hit } from '@app/metadata/models/search-results';
import { MetadataService } from '@app/metadata/services/metadata.service';

/**
 * Component for the expansion panel for each dataset found in the search results
 */
@Component({
  selector: 'app-dataset-expansion-panel',
  imports: [MatExpansionModule],
  templateUrl: './dataset-expansion-panel.component.html',
  styleUrl: './dataset-expansion-panel.component.scss',
})
export class DatasetExpansionPanelComponent {
  hit = input.required<Hit>();
  #metadata = inject(MetadataService);

  summary = this.#metadata.datasetSummary;

  /**
   * On opening of the expansible panel, load the query variables to the injectable service to prepare for the backend query
   */
  onOpen(): void {
    this.#metadata.loadDatasetID(this.hit().id_);
  }

  #errorEffect = effect(() => {
    if (this.#metadata.datasetSummaryError()) {
      console.log('Error fetching dataset summary'); // TODO: show a toast message
    }
  });
}
