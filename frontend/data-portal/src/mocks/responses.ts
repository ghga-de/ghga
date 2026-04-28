/**
 * Mock REST responses
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  accessGrants,
  accessRequests,
  allIvas,
  allIvasOfDoe,
  allIvasOfMar,
  allIvasOfRoe,
  datasetInformation,
  datasets,
  getAccessGrants,
  getAccessRequests,
  getDatasetDetails,
  getDatasetSummary,
  metadataGlobalSummary,
  searchResults,
  storageLabels,
  studyData,
  uploadBox1FileUploads,
  uploadBox2FileUploads,
  uploadBox3FileUploads,
  uploadBoxes,
  uploadBoxTestDatasetDetails,
  uploadBoxTestDatasetSummary,
  uploadBoxTestStudyData,
  uploadGrants,
  users,
  workPackageResponse,
} from './data';

export type ResponseValue = undefined | number | string | object;

/**
 * MSW responses to be returned for various endpoints of our API.
 *
 * The property names must contain a method and a URL separated by a space
 * and the values can be undefined (do not mock this endpoint)
 * a number (use it as response status), or an object (return it as JSON).
 */

export const responses: { [endpoint: string]: ResponseValue } = {
  /**
   * Auth API including 2FA and IVAs
   */

  // User Data
  'GET /api/auth/users/doe@test.dev': users[0],
  'GET /api/auth/users/roe@test.dev': users[1],
  'GET /api/auth/users/mar@test.dev': users[2],
  'GET /api/auth/users/jekyll@test.dev': users[3],
  'GET /api/auth/users/hyde@test.dev': users[4],
  'GET /api/auth/users/fred.flintstone@test.dev': users[5],
  'GET /api/auth/users/wilma.flintstone@test.dev': users[6],
  'GET /api/auth/users/barney.rubble@test.dev': users[7],
  'GET /api/auth/users/bamm-bamm.flintstone@test.dev': users[8],

  'GET /api/auth/users': users,

  // User IVAs
  'GET /api/auth/users/doe@test.dev/ivas': allIvasOfDoe,
  'GET /api/auth/users/roe@test.dev/ivas': allIvasOfRoe,
  'GET /api/auth/users/mar@test.dev/ivas': allIvasOfMar,
  'GET /api/auth/users/jekyll@test.dev/ivas': [],
  'GET /api/auth/users/hyde@test.dev/ivas': [],
  'GET /api/auth/users/fred.flintstone@test.dev/ivas': [],
  'GET /api/auth/users/wilma.flintstone@test.dev/ivas': [],
  'GET /api/auth/users/barney.rubble@test.dev/ivas': [],

  // Delete access grant
  'DELETE /api/auth/users/*': 204,

  // New IVA
  'POST /api/auth/users/*/ivas': { id: crypto.randomUUID() },

  // Delete IVA
  'DELETE /api/auth/users/*/ivas/*': 204,

  // Request IVA verification
  'POST /api/auth/rpc/ivas/*/request-code': 204,

  // Create IVA verification code
  'POST /api/auth/rpc/ivas/*/create-code': {
    verification_code: 'ABC123',
  },

  // Request IVA verification
  'POST /api/auth/rpc/ivas/*/code-transmitted': 204,

  // Request IVA verification with correct code
  'POST /api/auth/rpc/ivas/*/validate-code?verification_code=ABC123': 204,

  // Simulate a 2FA verification too many attempts error
  'POST /api/auth/rpc/ivas/*/validate-code?verification_code=ZZZ999': 429,

  // Request IVA verification with invalid codes
  'POST /api/auth/rpc/ivas/*/validate-code': 403,

  // Get all IVAs
  'GET /api/auth/ivas': allIvas,

  // Invalidate an access request
  'POST /api/auth/rpc/ivas/*/unverify': 204,

  /**
   * Metldata API
   */

  'GET /api/metldata/stats': metadataGlobalSummary,

  // Get summary data from a single dataset
  'GET /api/metldata/artifacts/stats_public/classes/DatasetStats/resources/GHGAD12345678901234':
    getDatasetSummary('GHGAD12345678901234'),
  // Get summary data from a single dataset
  'GET /api/metldata/artifacts/stats_public/classes/DatasetStats/resources/GHGAD12345678901235':
    getDatasetSummary('GHGAD12345678901235'),
  // Get summary data from a single dataset
  'GET /api/metldata/artifacts/stats_public/classes/DatasetStats/resources/GHGAD12345678901236':
    getDatasetSummary('GHGAD12345678901236'),
  // Get summary data from a single dataset
  'GET /api/metldata/artifacts/stats_public/classes/DatasetStats/resources/GHGAD12345678901237':
    getDatasetSummary('GHGAD12345678901237'),
  // Get summary data from a single dataset
  'GET /api/metldata/artifacts/stats_public/classes/DatasetStats/resources/GHGAD12345678901238':
    getDatasetSummary('GHGAD12345678901238'),
  // Upload box mapping test dataset summary (points to the new test study)
  'GET /api/metldata/artifacts/stats_public/classes/DatasetStats/resources/GHGAD99999999999001':
    uploadBoxTestDatasetSummary,

  // Get dataset details (embedded)
  'GET /api/metldata/artifacts/embedded_public/classes/EmbeddedDataset/resources/GHGAD12345678901234':
    getDatasetDetails('GHGAD12345678901234'),
  'GET /api/metldata/artifacts/embedded_public/classes/EmbeddedDataset/resources/GHGAD12345678901235':
    getDatasetDetails('GHGAD12345678901235'),
  'GET /api/metldata/artifacts/embedded_public/classes/EmbeddedDataset/resources/GHGAD12345678901236':
    getDatasetDetails('GHGAD12345678901236'),
  'GET /api/metldata/artifacts/embedded_public/classes/EmbeddedDataset/resources/GHGAD12345678901237':
    getDatasetDetails('GHGAD12345678901237'),
  'GET /api/metldata/artifacts/embedded_public/classes/EmbeddedDataset/resources/GHGAD12345678901238':
    getDatasetDetails('GHGAD12345678901238'),
  // Upload box mapping test dataset details (files match box 2 aliases for testing)
  'GET /api/metldata/artifacts/embedded_public/classes/EmbeddedDataset/resources/GHGAD99999999999001':
    uploadBoxTestDatasetDetails,

  // Get study details (embedded) — specific entries before the wildcard catch-all
  'GET /api/metldata/artifacts/embedded_public/classes/Study/resources/GHGAS99999999999001':
    uploadBoxTestStudyData,
  // Get study details (embedded)
  'GET /api/metldata/artifacts/embedded_public/classes/Study/resources/*': studyData,

  /**
   * MASS API
   */

  'GET /api/mass/search*': {
    facets: searchResults.facets,
    count: searchResults.count,
    hits: searchResults.hits,
  },

  /**
   * DINS API
   */

  // Get summary data from all files in a dataset
  'GET /api/dins/dataset_information/*': datasetInformation,

  /**
   * WPS API
   */

  // Datasets requested by doe@test.dev user
  'GET /api/wps/users/doe@test.dev/datasets': datasets,

  // Work package token returned after creating a work package
  'POST /api/wps/work-packages': workPackageResponse,

  // Simulate creating a work package with a bad file ID
  'POST /api/wps/work-packages?file_ids=["error"]': 403,

  /**
   * ARS API
   */

  // Specific access request
  'GET /api/ars/access-requests/*': accessRequests[4],

  // Specific dataset and user access requests
  'GET /api/ars/access-requests?dataset_id=GHGAD12345678901234&*': getAccessRequests(
    'doe@test.dev',
    'GHGAD12345678901234',
  ),

  // Specific dataset and user access requests
  'GET /api/ars/access-requests?*': getAccessRequests('doe@test.dev'),

  // All access requests
  'GET /api/ars/access-requests': getAccessRequests(),

  // All access grants
  'GET /api/ars/access-grants': accessGrants,

  // Specific dataset and user access requests
  'GET /api/ars/access-grants?*': getAccessGrants('doe@test.dev'),

  // User Grants
  'GET /api/ars/access-grants/doe@test.dev': accessGrants,

  // Delete access grant
  'DELETE /api/ars/access-grants/*': 204,

  // Create an access request
  'POST /api/ars/access-requests': 204,

  // Patch an access request
  'PATCH /api/ars/access-requests/*': 204,

  /**
   * RTS API
   */
  // Download metadata for a study
  'GET /api/rts/studies/GHGAS12345678901234': 404,

  /**
   * RS Upload Boxes API
   */

  // Create a new upload box
  'POST /api/rs/upload-boxes': crypto.randomUUID(),

  // Submit file mapping for box 2 (locked box used for mapping UI testing)
  'POST /api/rs/upload-boxes/0a36607a-b53f-49ed-bf3e-a5f2dbc68002/file-ids': 204,

  // Update (submit) an upload box
  'PATCH /api/rs/upload-boxes/*': 204,

  // Fetch all upload boxes
  'GET /api/rs/upload-boxes': uploadBoxes,

  // Fetch file uploads for a specific box
  'GET /api/rs/upload-boxes/0a36607a-b53f-49ed-bf3e-a5f2dbc68001/uploads':
    uploadBox1FileUploads,
  'GET /api/rs/upload-boxes/0a36607a-b53f-49ed-bf3e-a5f2dbc68002/uploads':
    uploadBox2FileUploads,
  'GET /api/rs/upload-boxes/0a36607a-b53f-49ed-bf3e-a5f2dbc68003/uploads':
    uploadBox3FileUploads,
  'GET /api/rs/upload-boxes/*/uploads': [],

  // Fetch a single upload box
  'GET /api/rs/upload-boxes/0a36607a-b53f-49ed-bf3e-a5f2dbc68001': uploadBoxes.boxes[0],
  'GET /api/rs/upload-boxes/0a36607a-b53f-49ed-bf3e-a5f2dbc68002': uploadBoxes.boxes[1],
  'GET /api/rs/upload-boxes/0a36607a-b53f-49ed-bf3e-a5f2dbc68003': uploadBoxes.boxes[2],

  // Unknown upload box (catch-all, must stay after nested routes above)
  'GET /api/rs/upload-boxes/*': 404,

  /**
   * RS Upload Grants API
   */

  // Create a new upload grant
  'POST /api/rs/upload-grants': {
    id: crypto.randomUUID(),
  },

  // Fetch upload grants for a specific box
  'GET /api/rs/upload-grants?*': uploadGrants,

  // Revoke an upload grant
  'DELETE /api/rs/upload-grants/*': 204,

  /**
   * WKVS API
   */
  // Get human-readable storage aliases
  'GET /.well-known/values/storage_labels': storageLabels,

  /**
   * Static assets
   */
  'GET /assets/*': undefined,
  'GET /*.css': undefined,
  'GET /*.js': undefined,
  'GET /*.woff2': undefined,
};
