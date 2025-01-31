/**
 * Global metadata summary stats service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient } from '@angular/common/http';
import { computed, inject, Signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { ConfigService } from '@app/shared/services/config.service';
import { map } from 'rxjs';
import {
  BaseGlobalSummary,
  emptyGlobalSummary,
  GlobalSummary,
} from '../models/global-summary';

/**
 * Metadata Stats service
 *
 * This service provides the functionality to fetch the global metadata summary stats from the server.
 */
export class MetadataStatsService {
  #http = inject(HttpClient);

  #config = inject(ConfigService);
  #metldataUrl = this.#config.metldataUrl;

  #globalSummaryUrl = `${this.#metldataUrl}/stats`;

  #globalSummary = rxResource<GlobalSummary, void>({
    loader: () =>
      this.#http
        .get<BaseGlobalSummary>(this.#globalSummaryUrl)
        .pipe(map((value) => value.resource_stats)),
  }).asReadonly();

  /**
   * The global summary (empty while loading) as a signal
   */
  globalSummary: Signal<GlobalSummary> = computed(
    () => this.#globalSummary.value() ?? emptyGlobalSummary,
  );

  /**
   * Whether the global summary is loading as a signal
   */
  globalSummaryIsLoading: Signal<boolean> = this.#globalSummary.isLoading;

  /**
   * The global summary error as a signal
   */
  globalSummaryError: Signal<unknown> = this.#globalSummary.error;
}
