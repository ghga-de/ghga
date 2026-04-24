/**
 * Metadata search service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient, httpResource } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { ConfigService } from '@app/shared/services/config';
import {
  Observable,
  concatMap,
  from,
  last,
  map,
  mergeMap,
  mergeScan,
  of,
  reduce,
} from 'rxjs';
import { DatasetSummary } from '../models/dataset-summary';
import { FacetFilterSetting } from '../models/facet-filter';
import {
  DEFAULT_PAGE_SIZE,
  DEFAULT_SKIP_VALUE,
  SearchResults,
  emptySearchResults,
} from '../models/search-results';
import { Study } from '../models/study';

interface StudyMapAccumulator {
  studyMap: Map<string, Study>;
  skippedDatasetIds: Set<string>;
  fetchedStudyAccessions: Set<string>;
}

/**
 * Metadata search service
 *
 * This service provides the functionality to fetch search results from the server via MASS.
 */
@Injectable({ providedIn: 'root' })
export class MetadataSearchService {
  #config = inject(ConfigService);
  #massUrl = this.#config.massUrl;
  #searchUrl = `${this.#massUrl}/search`;
  #metldataUrl = this.#config.metldataUrl;
  #datasetSummaryUrl = `${this.#metldataUrl}/artifacts/stats_public/classes/DatasetStats/resources`;
  #studyUrl = `${this.#metldataUrl}/artifacts/embedded_public/classes/Study/resources`;
  #http = inject(HttpClient);
  #className = signal<string | undefined>(undefined);
  #limit = signal<number>(DEFAULT_PAGE_SIZE);
  #skip = signal<number>(DEFAULT_SKIP_VALUE);
  #query = signal<string | undefined>(undefined);
  #facets = signal<FacetFilterSetting>({});

  query = computed(() => this.#query() ?? '');

  #massQueryUrl = computed(() => {
    const className = this.#className();
    if (!className) return undefined;
    return this.#urlFromParameters(
      this.#searchUrl,
      className,
      this.#facets(),
      this.#query(),
      this.#skip(),
      this.#limit(),
    );
  });

  /**
   * The search results (empty while loading) as a resource
   */
  #searchResultsResource = httpResource<SearchResults>(this.#massQueryUrl, {
    defaultValue: emptySearchResults,
  }).asReadonly();

  isLoading = this.#searchResultsResource.isLoading;

  error = this.#searchResultsResource.error;

  searchResults = computed(() =>
    this.error() ? undefined : this.#searchResultsResource.value(),
  );

  paginated = signal(false);

  /**
   * Change the local private variables when paginating
   * @param limit Number of results to fetch
   * @param skip Number of results to skip to enable pagination
   */
  paginate(limit: number, skip: number): void {
    this.#limit.set(limit);
    this.#skip.set(skip);
    this.paginated.set(true);
  }

  /**
   * Reset the skip variable to defaults (e.g. when changing the search query)
   */
  resetSkip() {
    this.paginated.set(false);
    this.#skip.set(DEFAULT_SKIP_VALUE);
  }

  /**
   * Function to set some data into the local private variables
   * @param className Name of the metldata class object we want to obtain
   * @param limit Number of results to fetch
   * @param skip Number of results to skip to enable pagination
   * @param query The Search term set in the input field
   * @param facets The list of facets specified in the filter list
   */
  loadQueryParameters(
    className: string,
    limit: number,
    skip: number,
    query?: string,
    facets?: FacetFilterSetting,
  ): void {
    this.#className.set(className);
    this.#limit.set(limit);
    this.#skip.set(skip);
    this.#query.set(query);
    this.#facets.set({ ...facets });
  }

  /**
   * The current search results skip value
   * to be used by the paginator
   */
  searchResultsSkip = computed(() => this.#skip());

  /**
   * The current search results limit value
   * to be used by the paginator
   */
  searchResultsLimit = computed(() => this.#limit());

  /**
   * Computes a url from the provided parameters
   * @param baseUrl the server address to use for the api
   * @param className request parameter of the same name
   * @param facets The list of facets specified in the filter list
   * @param query content of the search field
   * @param skip how many items to skip
   * @param limit how many items to return
   * @returns a string containing the url
   */
  #urlFromParameters(
    baseUrl: string,
    className: string,
    facets: FacetFilterSetting,
    query?: string,
    skip?: number,
    limit?: number,
  ): string {
    let massQueryUrl = `${baseUrl}?class_name=${className}`;
    for (const [facetKey, values] of Object.entries(facets)) {
      for (const value of values) {
        massQueryUrl += `&filter_by=${facetKey}&value=${value}`;
      }
    }
    if (query) {
      massQueryUrl += `&query=${encodeURIComponent(query)}`;
    }
    if (limit) {
      massQueryUrl += `&limit=${limit}`;
    }
    if (skip) {
      massQueryUrl += `&skip=${skip}`;
    }
    return massQueryUrl;
  }

  /**
   * Load a map of all studies keyed by study accession.
   *
   * Because there is no dedicated backend endpoint for listing studies, this
   * method first fetches all dataset IDs via a MASS search, then walks each
   * dataset summary to discover study accessions and fetches each study
   * individually. Dataset IDs that are already accounted for by a fetched
   * study's datasets list are skipped so each study is fetched at most once.
   *
   * Unfortunately, this method is not efficient, but it is only used temporarily
   * until we switch to a study-based backend.
   * @returns An observable that emits a Map from study accession to Study
   */
  loadStudiesMap(): Observable<Map<string, Study>> {
    return this.#http
      .get<SearchResults>(`${this.#searchUrl}?class_name=EmbeddedDataset`)
      .pipe(
        map((searchResults) => searchResults.hits.map((hit) => hit.id_)),
        mergeMap((datasetIds) => from(datasetIds)),
        mergeScan(
          (acc: StudyMapAccumulator, datasetId: string) => {
            if (acc.skippedDatasetIds.has(datasetId)) {
              return of(acc);
            }

            return this.#http
              .get<DatasetSummary>(`${this.#datasetSummaryUrl}/${datasetId}`)
              .pipe(
                mergeMap((summary) => from(summary.studies_summary.stats.accession)),
                concatMap((studyAccession) => {
                  if (acc.fetchedStudyAccessions.has(studyAccession)) {
                    return of(undefined);
                  }

                  return this.#http.get<Study>(`${this.#studyUrl}/${studyAccession}`);
                }),
                reduce((datasetAcc: StudyMapAccumulator, study: Study | undefined) => {
                  if (!study) {
                    return datasetAcc;
                  }

                  const studyMap = new Map(datasetAcc.studyMap);
                  studyMap.set(study.accession, study);

                  const skippedDatasetIds = new Set(datasetAcc.skippedDatasetIds);
                  for (const linkedDatasetId of study.datasets) {
                    skippedDatasetIds.add(linkedDatasetId);
                  }

                  const fetchedStudyAccessions = new Set(
                    datasetAcc.fetchedStudyAccessions,
                  );
                  fetchedStudyAccessions.add(study.accession);

                  return { studyMap, skippedDatasetIds, fetchedStudyAccessions };
                }, acc),
              );
          },
          {
            studyMap: new Map<string, Study>(),
            skippedDatasetIds: new Set<string>(),
            fetchedStudyAccessions: new Set<string>(),
          },
          1,
        ),
        last(),
        map((acc) => acc.studyMap),
      );
  }
}
