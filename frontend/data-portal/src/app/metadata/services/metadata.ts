/**
 * Global summary service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient, httpResource } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { ConfigService } from '@app/shared/services/config';
import { concatMap, from, map, Observable, reduce } from 'rxjs';
import {
  DatasetDetails,
  DatasetDetailsRaw,
  File as DatasetFile,
  emptyDatasetDetails,
  ExperimentMethod,
  Individual,
} from '../models/dataset-details';
import { EmFile } from '../models/dataset-information';
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
  #http = inject(HttpClient);
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
   * Load the study details for the given study ID
   * @param id Study ID
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
   * Fetch the unique files for a study.
   *
   * Unfortunately, this method is not efficient, but it is only used temporarily
   * until we switch to a study-based backend.
   * @param study Study containing the list of dataset accessions to inspect
   * @returns An observable emitting a list of unique EM files
   */
  filesOfStudy(study: Study): Observable<EmFile[]> {
    return from(study.datasets).pipe(
      concatMap((datasetAccession) =>
        this.#http.get<DatasetDetails>(
          `${this.#datasetDetailsUrl}/${datasetAccession}`,
        ),
      ),
      concatMap((details) => from(Object.entries(details))),
      concatMap(([propertyName, propertyValue]) => {
        if (!propertyName.endsWith('_files') || !Array.isArray(propertyValue)) {
          return from([] as unknown[]);
        }

        return from(propertyValue);
      }),
      reduce((filesByAccession, file) => {
        if (!this.#isDatasetFile(file) || filesByAccession.has(file.accession)) {
          return filesByAccession;
        }

        filesByAccession.set(file.accession, {
          accession: file.accession,
          alias: file.alias,
          name: file.name,
          format: file.format,
        });
        return filesByAccession;
      }, new Map<string, EmFile>()),
      map((filesByAccession) => Array.from(filesByAccession.values())),
    );
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

  /**
   * Check if an unknown value looks like a dataset file object.
   * @param value Value from a dynamic dataset details property
   * @returns True when value is a dataset file with required fields
   */
  #isDatasetFile(value: unknown): value is DatasetFile & { alias: string } {
    if (!value || typeof value !== 'object') {
      return false;
    }

    const candidate = value as Partial<DatasetFile>;
    return (
      typeof candidate.accession === 'string' &&
      typeof candidate.alias === 'string' &&
      typeof candidate.name === 'string' &&
      typeof candidate.format === 'string'
    );
  }
}
