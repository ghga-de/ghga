/**
 * Work package model
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

export interface WorkPackage {
  dataset_id: string;
  file_ids: string[] | null;
  type: 'download' | 'upload';
  user_public_crypt4gh_key: string;
}

export interface WorkPackageResponse {
  id: string;
  token: string;
}
