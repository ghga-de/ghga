/**
 * Global metadata summary stats service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { httpResource } from '@angular/common/http';
import { inject } from '@angular/core';
import { ConfigService } from '@app/shared/services/config.service';
import { emptyGlobalSummary, GlobalSummary } from '../models/global-summary';

/**
 * Metadata Stats service
 *
 * This service provides the functionality to fetch the global metadata summary stats from the server.
 */
export class MetadataStatsService {
  #config = inject(ConfigService);
  #metldataUrl = this.#config.metldataUrl;

  #globalSummaryUrl = `${this.#metldataUrl}/stats`;

  /**
   * The global summary (empty while loading)
   */
  globalSummary = httpResource<GlobalSummary>(() => this.#globalSummaryUrl, {
    parse: (raw) => (raw as { resource_stats: GlobalSummary }).resource_stats,
    defaultValue: emptyGlobalSummary,
  }).asReadonly();
}
