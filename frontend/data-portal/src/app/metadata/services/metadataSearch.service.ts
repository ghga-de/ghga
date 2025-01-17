/**
 * Metadata search service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient } from '@angular/common/http';
import { Injectable, Signal, computed, inject, resource, signal } from '@angular/core';
import { ConfigService } from '@app/shared/services/config.service';
import { firstValueFrom } from 'rxjs';
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

  #searchResults = resource({
    request: computed(() => ({
      className: this.#className(),
      limit: this.#limit(),
      skip: this.#skip(),
    })),
    loader: (param) => {
      const className = param.request.className;
      const limit = param.request.limit;
      const skip = param.request.skip;
      const massQueryUrl = `${this.#searchUrl}?class_name=${className}&limit=${limit}&skip=${skip}`;
      if (className && limit !== undefined && skip !== undefined) {
        return Promise.resolve(
          firstValueFrom(this.#http.get<SearchResults>(massQueryUrl)),
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
   */
  loadQueryParameters(className: string, limit: number, skip: number): void {
    this.#className.set(className);
    this.#limit.set(limit);
    this.#skip.set(skip);
  }

  /**
   * The search results (empty while loading) as a signal
   */
  searchResults: Signal<SearchResults> = computed(
    () => this.#searchResults.value() ?? emptySearchResults,
  );

  /**
   * The search results error as a signal
   */
  searchResultsError: Signal<unknown> = this.#searchResults.error;
}
