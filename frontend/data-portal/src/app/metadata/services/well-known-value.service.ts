/**
 * Well-Known Value Service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { httpResource } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { ConfigService } from '@app/shared/services/config.service';
import {
  BaseStorageLabels,
  emptyStorageLabels,
  wellKnownValues,
} from '../models/well-known-values';

/**
 * Well-Known Value query service
 *
 * This service provides the functionality to fetch well-known values.
 */
@Injectable({ providedIn: 'root' })
export class WellKnownValueService {
  #config = inject(ConfigService);
  #wkvsUrl = this.#config.wkvsUrl;

  #valuesUrl = `${this.#wkvsUrl}/values`;

  #storageLabelsUrl = `${this.#valuesUrl}/storage_labels`;

  /**
   * The human-readable storage aliases (empty while loading) as a resource
   */
  storageLabels = httpResource<wellKnownValues>(this.#storageLabelsUrl, {
    parse: (raw) => (raw as BaseStorageLabels).storage_labels,
    defaultValue: emptyStorageLabels,
  }).asReadonly();
}
