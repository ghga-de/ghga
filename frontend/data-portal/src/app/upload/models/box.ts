/**
 * Upload box related models
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

/** All possible research upload box states */
export enum UploadBoxState {
  open = 'open',
  locked = 'locked',
  archived = 'archived',
}

/** State-specific classes for upload boxes */
export const UploadBoxStateClass: Record<UploadBoxState, string> = {
  open: 'text-success',
  locked: 'text-warning',
  archived: 'text-gray-600',
};

/** Base data required to create a Research Data Upload Box */
export interface ResearchDataUploadBoxBase {
  title: string;
  description: string;
  storage_alias: string;
}

/** All data describing a Research Data Upload Box */
export interface ResearchDataUploadBox extends ResearchDataUploadBoxBase {
  id: string;
  version: number;
  state: UploadBoxState;
  last_changed: string; // ISO date string
  changed_by: string;
  file_count: number;
  size: number; // in bytes
  // Note: the API also returns file_upload_box_id, file_upload_box_version, and
  // file_upload_box_state, but these are not used in the frontend.
}

/** Data to update a Research Data Upload Box */
export interface ResearchDataUploadBoxUpdate {
  version: number;
  state?: UploadBoxState;
  title?: string;
  description?: string;
}

/** Response when retrieving Research Data Upload Boxes */
export interface BoxRetrievalResults {
  count: number;
  boxes: ResearchDataUploadBox[];
}

/** A virtual filter value that excludes boxes in a specific state (e.g. 'not_archived') */
export type UploadBoxVirtualFilter = `not_${UploadBoxState}`;

/** All possible state filter values: real states and virtual negations */
export type UploadBoxStateFilter = UploadBoxState | UploadBoxVirtualFilter;

/** Filters for upload box management */
export interface UploadBoxFilter {
  title: string | undefined;
  state: UploadBoxStateFilter | undefined;
  location: string | undefined;
}
