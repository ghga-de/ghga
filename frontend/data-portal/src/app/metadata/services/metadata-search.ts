/**
 * Metadata search service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { httpResource } from '@angular/common/http';
import { Service, computed, inject, signal } from '@angular/core';
import { ConfigService } from '@app/shared/services/config';
import { FacetFilterSetting } from '../models/facet-filter';
import {
  DEFAULT_PAGE_SIZE,
  DEFAULT_SKIP_VALUE,
  SearchResults,
  emptySearchResults,
} from '../models/search-results';

/**
 * Metadata search service
 *
 * This service provides the functionality to fetch search results from the server via MASS.
 */
@Service()
export class MetadataSearchService {
  #config = inject(ConfigService);
  #massUrl = this.#config.massUrl;
  #searchUrl = `${this.#massUrl}/search`;
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
}
