/**
 * Global summary service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal, Signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { ConfigService } from '@app/shared/services/config.service';
import { of } from 'rxjs';
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
  #http = inject(HttpClient);

  #config = inject(ConfigService);
  #metldataUrl = this.#config.metldataUrl;

  #datasetSummaryUrl = `${this.#metldataUrl}/artifacts/stats_public/classes/DatasetStats/resources`;
  #datasetDetailsUrl = `${this.#metldataUrl}/artifacts/embedded_public/classes/EmbeddedDataset/resources`;

  #summaryID = signal<string | undefined>(undefined);
  #detailsID = signal<string | undefined>(undefined);

  #datasetSummary = rxResource({
    request: this.#summaryID,
    loader: ({ request: id }) => {
      if (!id) return of(undefined);
      return this.#http.get<DatasetSummary>(`${this.#datasetSummaryUrl}/${id}`);
    },
  });

  /**
   * The dataset summary (empty while loading) as a signal
   */
  datasetSummary: Signal<DatasetSummary> = computed(
    () => this.#datasetSummary.value() ?? emptyDatasetSummary,
  );

  /**
   * Whether the dataset summary is loading as a signal
   */
  datasetSummaryIsLoading: Signal<boolean> = this.#datasetSummary.isLoading;

  /**
   * The dataset summary error as a signal
   */
  datasetSummaryError: Signal<unknown> = this.#datasetSummary.error;

  /**
   * Load the dataset summary for the given dataset ID
   * @param id Dataset ID
   */
  loadDatasetSummaryID(id: string): void {
    this.#summaryID.set(id);
  }

  #datasetDetails = rxResource({
    request: this.#summaryID,
    loader: ({ request: id }) => {
      if (!id) return of(undefined);
      return this.#http.get<DatasetDetails>(`${this.#datasetDetailsUrl}/${id}`);
    },
  });

  /**
   * Load the dataset details for the given dataset ID
   * @param id Dataset ID
   */
  loadDatasetDetailsID(id: string): void {
    this.#detailsID.set(id);
  }

  /**
   * The dataset details (empty while loading) as a signal
   */
  datasetDetails: Signal<DatasetDetails> = computed(
    () => this.#datasetDetails.value() ?? emptyDatasetDetails,
  );

  /**
   * Whether the dataset details are loading as a signal
   */
  datasetDetailsIsLoading: Signal<boolean> = this.#datasetDetails.isLoading;

  /**
   * The dataset details error as a signal
   */
  datasetDetailsError: Signal<unknown> = this.#datasetDetails.error;
}
