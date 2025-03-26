/**
 * Dataset Information Query Service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { httpResource } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { ConfigService } from '@app/shared/services/config.service';
import {
  DatasetInformation,
  emptyDatasetInformation,
} from '../models/dataset-information';

/**
 * Dataset Information query service
 *
 * This service provides the functionality to fetch aggregated information on datasets.
 */
@Injectable({ providedIn: 'root' })
export class DatasetInformationService {
  #config = inject(ConfigService);
  #dinsUrl = this.#config.dinsUrl;

  #datasetInformationUrl = `${this.#dinsUrl}/dataset_information`;

  #datasetID = signal<string | undefined>(undefined);

  /**
   * The dataset information (empty while loading) as a resource
   */
  datasetInformation = httpResource<DatasetInformation>(
    () => {
      const id = this.#datasetID();
      return id ? `${this.#datasetInformationUrl}/${id}` : undefined;
    },
    { defaultValue: emptyDatasetInformation },
  ).asReadonly();

  /**
   * Load the dataset information for the given dataset ID
   * @param id Dataset ID
   */
  loadDatasetInformation(id: string): void {
    this.#datasetID.set(id);
  }
}
