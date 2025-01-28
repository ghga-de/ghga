/**
 * Metadata search service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient } from '@angular/common/http';
import { Injectable, Signal, computed, inject, resource, signal } from '@angular/core';
import { ConfigService } from '@app/shared/services/config.service';
import { firstValueFrom } from 'rxjs';
import { FacetFilterSetting } from '../models/facet-filter';
import { SearchResults, emptySearchResults } from '../models/search-results';

/**
 * Metadata search service
 *
 * This service provides the functionality to fetch search results from the server via MASS.
 */
@Injectable({
  providedIn: 'root',
})
export class MetadataSearchService {
  #http = inject(HttpClient);

  #config = inject(ConfigService);
  #massUrl = this.#config.massUrl;
  #searchUrl = `${this.#massUrl}/search`;
  #className = signal<string | undefined>(undefined);
  #limit = signal<number | undefined>(undefined);
  #skip = signal<number | undefined>(undefined);
  #query = signal<string | undefined>(undefined);
  #facets = signal<FacetFilterSetting>({});

  facets = computed(() => this.#facets());
  query = computed(() => {
    if (!this.#query()) return '';
    return this.#query();
  });

  #searchResults = resource({
    request: computed(() => ({
      url: this.#massQueryUrl(),
    })),
    loader: ({ request }) => {
      if (request.url !== '') {
        return Promise.resolve(
          firstValueFrom(this.#http.get<SearchResults>(request.url)),
        );
      } else {
        return Promise.resolve(emptySearchResults);
      }
    },
  });

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
   * The search results (empty while loading) as a signal
   */
  searchResults: Signal<SearchResults> = computed(
    () => this.#searchResults.value() ?? emptySearchResults,
  );

  /**
   * The search results loading state as a signal
   */
  searchResultsAreLoading: Signal<boolean> = computed(
    () => this.#searchResults.isLoading() ?? false,
  );

  /**
   * The search results error as a signal
   */
  searchResultsError: Signal<unknown> = this.#searchResults.error;

  #massQueryUrl: Signal<string> = computed(() => {
    const baseUrl = this.#searchUrl;
    const query = this.#query();
    const className = this.#className();
    const limit = this.#limit();
    const skip = this.#skip();
    const facets = this.#facets();

    if (className) {
      return this.urlFromParameters(baseUrl, className, facets, query, skip, limit);
    } else {
      return '';
    }
  });

  /**
   * Computes an url from the provided parameters
   * @param baseUrl the server address to use for the api
   * @param className request parameter of the same name
   * @param facets The list of facets specified in the filter list
   * @param query content of the search field
   * @param skip how many items to skip
   * @param limit how many items to return
   * @returns a string containing the url
   */
  urlFromParameters(
    baseUrl: string,
    className: string,
    facets: FacetFilterSetting,
    query?: string,
    skip?: number,
    limit?: number,
  ): string {
    let massQueryUrl = baseUrl + '?';
    if (!className || className.length == 0) {
      return '';
    }
    massQueryUrl += `class_name=${className}`;
    for (let facetKey in facets) {
      for (let option in facets[facetKey]) {
        massQueryUrl += `&filter_by=${facetKey}&value=${facets[facetKey][option]}`;
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
