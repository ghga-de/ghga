/**
 * Global summary service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { httpResource } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { ConfigService } from '@app/shared/services/config.service';
import { DatasetDetails, emptyDatasetDetails } from '../models/dataset-details';
import { DatasetSummary, emptyDatasetSummary } from '../models/dataset-summary';

/**
 * Metadata query service
 *
 * This service provides the functionality to fetch dataset summaries and details from the server.
 */
@Injectable({
  providedIn: 'root',
})
export class MetadataService {
  #config = inject(ConfigService);
  #metldataUrl = this.#config.metldataUrl;

  #datasetSummaryUrl = `${this.#metldataUrl}/artifacts/stats_public/classes/DatasetStats/resources`;
  #datasetDetailsUrl = `${this.#metldataUrl}/artifacts/embedded_public/classes/EmbeddedDataset/resources`;

  #summaryID = signal<string | undefined>(undefined);
  #detailsID = signal<string | undefined>(undefined);

  /**
   * The dataset summary (empty while loading) as a resource
   */
  datasetSummary = httpResource<DatasetSummary>(
    () => {
      const id = this.#summaryID();
      return id ? `${this.#datasetSummaryUrl}/${id}` : undefined;
    },
    { defaultValue: emptyDatasetSummary },
  ).asReadonly();

  /**
   * Load the dataset summary for the given dataset ID
   * @param id Dataset ID
   */
  loadDatasetSummary(id: string): void {
    this.#summaryID.set(id);
  }

  /**
   * The dataset details (empty while loading) as a resource
   */
  datasetDetails = httpResource<DatasetDetails>(
    () => {
      const id = this.#detailsID();
      return id ? `${this.#datasetDetailsUrl}/${id}` : undefined;
    },
    { defaultValue: emptyDatasetDetails },
  ).asReadonly();

  /**
   * Load the dataset details for the given dataset ID
   * @param id Dataset ID
   */
  loadDatasetDetails(id: string): void {
    this.#detailsID.set(id);
  }
}
