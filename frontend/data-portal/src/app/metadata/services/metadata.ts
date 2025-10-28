/**
 * Global summary service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { httpResource } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { ConfigService } from '@app/shared/services/config';
import {
  DatasetDetails,
  DatasetDetailsRaw,
  emptyDatasetDetails,
  ExperimentMethod,
  Individual,
} from '../models/dataset-details';
import { DatasetSummary, emptyDatasetSummary } from '../models/dataset-summary';
import { emptyStudy, Study } from '../models/study';

/**
 * Metadata query service
 *
 * This service provides the functionality to fetch dataset summaries
 * and dataset details using the metldata API.
 *
 * Note that this service must be injected at the component level
 * since multiple different summaries can be visible at the same time.
 */
@Injectable()
export class MetadataService {
  #config = inject(ConfigService);
  #metldataUrl = this.#config.metldataUrl;

  #datasetSummaryUrl = `${this.#metldataUrl}/artifacts/stats_public/classes/DatasetStats/resources`;
  #datasetDetailsUrl = `${this.#metldataUrl}/artifacts/embedded_public/classes/EmbeddedDataset/resources`;
  #studyUrl = `${this.#metldataUrl}/artifacts/embedded_public/classes/Study/resources`;

  #summaryID = signal<string | undefined>(undefined);
  #detailsID = signal<string | undefined>(undefined);
  #studyID = signal<string | undefined>(undefined);

  /**
   * The study (empty while loading) as a resource
   */
  study = httpResource<Study>(
    () => {
      const id = this.#studyID();
      return id ? `${this.#studyUrl}/${id}` : undefined;
    },
    { defaultValue: emptyStudy },
  );

  /**
   * Load the study details for the given ID
   * @param id study ID
   */
  loadStudy(id: string): void {
    this.#studyID.set(id);
  }

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
   * The resolved dataset details (empty while loading) as a resource
   */
  datasetDetails = httpResource<DatasetDetails>(
    () => {
      const id = this.#detailsID();
      return id ? `${this.#datasetDetailsUrl}/${id}` : undefined;
    },
    {
      parse: (raw) => this.#resolveDatasetDetails(raw as DatasetDetailsRaw),
      defaultValue: emptyDatasetDetails,
    },
  ).asReadonly();

  /**
   * Load the dataset details for the given dataset ID
   * @param id Dataset ID
   */
  loadDatasetDetails(id: string): void {
    this.#detailsID.set(id);
  }
  /**
   * Resolve dataset details
   * @param raw The raw dataset details object
   * @returns The resolved DatasetDetails object
   *
   * This method resolves the references in the dataset details object
   * to the corresponding objects.
   * If a referenced object is not found (which should never happen),
   * it resolves to a default object with empty values.
   */
  #resolveDatasetDetails(raw: DatasetDetailsRaw): DatasetDetails {
    const experimentMethods = new Map<string, ExperimentMethod>(
      raw.experiment_methods.map((em) => [em.accession, em]),
    );
    const getExperimentMethod = (accession: string): ExperimentMethod =>
      experimentMethods.get(accession) || {
        accession,
        name: '',
        type: '',
        instrument_model: '',
      };
    const individuals = new Map<string, Individual>(
      raw.individuals.map((i) => [i.accession, i]),
    );
    const getIndividual = (accession: string): Individual =>
      individuals.get(accession) || {
        accession,
        sex: '',
      };
    return {
      ...raw,
      experiments: raw.experiments.map((e) => ({
        ...e,
        experiment_method: getExperimentMethod(e.experiment_method),
      })),
      samples: raw.samples.map((s) => ({
        ...s,
        individual: getIndividual(s.individual),
      })),
    };
  }
}
