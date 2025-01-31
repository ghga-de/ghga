/**
 * Dataset Information Query Service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, Signal, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { ConfigService } from '@app/shared/services/config.service';
import { of } from 'rxjs';
import {
  DatasetInformation,
  emptyDatasetInformation,
} from '../models/dataset-information';

/**
 * Dataset Information query service
 *
 * This service provides the functionality to fetch aggregated information on datasets.
 */
@Injectable({
  providedIn: 'root',
})
export class DatasetInformationService {
  #http = inject(HttpClient);

  #config = inject(ConfigService);
  #dinsUrl = this.#config.dinsUrl;

  #datasetInformationUrl = `${this.#dinsUrl}/dataset_information`;

  #datasetID = signal<string | undefined>(undefined);

  #datasetInformation = rxResource({
    request: this.#datasetID,
    loader: ({ request: id }) => {
      if (!id) return of(undefined);
      return this.#http.get<DatasetInformation>(`${this.#datasetInformationUrl}/${id}`);
    },
  }).asReadonly();

  /**
   * The dataset information (empty while loading) as a signal
   */
  datasetInformation: Signal<DatasetInformation> = computed(
    () => this.#datasetInformation.value() ?? emptyDatasetInformation,
  );

  /**
   * Whether the dataset information is loading as a signal
   */
  datasetInformationIsLoading: Signal<boolean> = this.#datasetInformation.isLoading;

  /**
   * The dataset information error as a signal
   */
  datasetInformationError: Signal<unknown> = this.#datasetInformation.error;

  /**
   * Load the dataset information for the given dataset ID
   * @param id Dataset ID
   */
  loadDatasetID(id: string): void {
    this.#datasetID.set(id);
  }
}
