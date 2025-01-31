/**
 * Mock REST responses
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  datasetInformation,
  getDatasetDetails,
  getDatasetSummary,
  metadataGlobalSummary,
  searchResults,
} from './data';

export type ResponseValue = undefined | number | object;

/**
 * MSW responses to be returned for various endpoints of our API.
 *
 * The property names must contain a method and a URL separated by a space
 * and the values can be undefined (do not mock this endpoint)
 * a number (use it as response status), or an object (return it as JSON).
 */

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

  /**
   * Static assets
   */
  'GET /assets/*': undefined,
  'GET /*.css': undefined,
  'GET /*.js': undefined,
  'GET /*.woff2': undefined,

  // Get summary data from a single dataset
  'GET /api/metldata/artifacts/stats_public/classes/DatasetStats/resources/GHGAD588887987':
    getDatasetSummary('GHGAD588887987'),
  // Get summary data from a single dataset
  'GET /api/metldata/artifacts/stats_public/classes/DatasetStats/resources/GHGAD588887988':
    getDatasetSummary('GHGAD588887988'),
  // Get summary data from a single dataset
  'GET /api/metldata/artifacts/stats_public/classes/DatasetStats/resources/GHGAD588887989':
    getDatasetSummary('GHGAD588887989'),

  // Get dataset details (embedded)
  'GET /api/metldata/artifacts/embedded_public/classes/EmbeddedDataset/resources/GHGAD588887987':
    getDatasetDetails('GHGAD588887987'),
  'GET /api/metldata/artifacts/embedded_public/classes/EmbeddedDataset/resources/GHGAD588887988':
    getDatasetDetails('GHGAD588887988'),
  'GET /api/metldata/artifacts/embedded_public/classes/EmbeddedDataset/resources/GHGAD588887989':
    getDatasetDetails('GHGAD588887989'),

  // Get summary data from all files in a dataset
  'GET /api/dins/dataset_information/*': datasetInformation,
};
