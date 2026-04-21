/**
 * Work package model
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

interface BaseWorkPackageRequest {
  type: 'download' | 'upload';
  user_public_crypt4gh_key: string;
}

export interface DownloadWorkPackageRequest extends BaseWorkPackageRequest {
  type: 'download';
  dataset_id: string;
  file_ids: string[] | null;
}

export interface UploadWorkPackageRequest extends BaseWorkPackageRequest {
  type: 'upload';
  research_data_upload_box_id: string;
}

export type WorkPackageRequest = DownloadWorkPackageRequest | UploadWorkPackageRequest;

export interface WorkPackageResponse {
  id: string;
  token: string;
  expires: string;
}
