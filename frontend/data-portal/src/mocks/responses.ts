/**
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { searchResults } from './data';

/**
 *  MSW responses to be returned for various endpoints.
 *
 * The property names must contain a method and a URL separated by a space
 * and the values can be undefined (do not mock this endpoint)
 * a number (use it as response status), or an object (return it as JSON).
 *
 * The responses are automatically converted into
 */

import { metadataGlobalSummary } from './data';

export type ResponseValue = undefined | number | object;

export const responses: { [endpoint: string]: ResponseValue } = {
  /**
   * Metldata API
   */

  'GET /api/metldata/stats': metadataGlobalSummary,

  /**
   * MASS API
   */

  'GET /api/mass/search*': {
    facets: searchResults.facets,
    count: searchResults.count,
    hits: searchResults.hits,
  },
};
