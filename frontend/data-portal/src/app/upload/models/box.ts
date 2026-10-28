/**
 * Upload box related models
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { countFileUploadStateGroup, FileUploadStateCounts } from './file-upload';

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

/** Minimum upload box limit in TiB (1 GiB in binary units). */
export const MIN_UPLOAD_BOX_SIZE_TIB = 1 / 1024;

/** Maximum upload box limit in TiB (1 million TiB in binary units). */
export const MAX_UPLOAD_BOX_SIZE_TIB = 1_000_000;

/** Number of bytes in one binary TiB (1024^4). */
export const BYTES_PER_TIB = 1_099_511_627_776;

/** Base data required to create a Research Data Upload Box */
export interface ResearchDataUploadBoxBase {
  title: string;
  description: string;
  storage_alias: string;
  max_size: number; // maximum size in bytes
}

/** All data describing a Research Data Upload Box */
export interface ResearchDataUploadBox extends ResearchDataUploadBoxBase {
  id: string;
  version: number;
  state: UploadBoxState;
  last_changed: string; // ISO date string
  changed_by: string;
  file_count: number;
  size: number; // current size in bytes
  // The ID of the underlying FileUploadBox. This differs from `id` (the research
  // data upload box ID) and is the value that each file upload references via its
  // own `box_id`, so it is needed to associate file uploads with this box.
  // Optional because locally created boxes (see UploadBoxService) do not have it
  // yet; the backend always returns it.
  file_upload_box_id?: string;
  // Note: the API also returns file_upload_box_version and file_upload_box_state,
  // but these are not used in the frontend.
}

/** Data to update a Research Data Upload Box */
export interface ResearchDataUploadBoxUpdate {
  version: number;
  state?: UploadBoxState;
  title?: string;
  description?: string;
  max_size?: number; // maximum size in bytes
}

/**
 * The number of file uploads per state for each upload box, keyed by the box ID.
 * The RS counts only the states that count toward the file count of a box, so a
 * box without such files is absent.
 */
export type FileStateCountsByBox = Record<string, FileUploadStateCounts>;

/** Response when retrieving Research Data Upload Boxes */
export interface BoxRetrievalResults {
  count: number;
  boxes: ResearchDataUploadBox[];
}

/** Result of requeueing all failed file uploads of a box, as returned by the RS */
export interface BoxRequeueResult {
  /** IDs of the file uploads that were set back to the inbox state */
  requeued: string[];
  /** IDs of the file uploads that could not be requeued due to an error */
  skipped: string[];
}

/** A virtual filter value that excludes boxes in a specific state (e.g. 'not_archived') */
export type UploadBoxVirtualFilter = `not_${UploadBoxState}`;

/** All possible state filter values: real states and virtual negations */
export type UploadBoxStateFilter = UploadBoxState | UploadBoxVirtualFilter;

/** Conditions on the file states of an upload box */
export type UploadBoxFileStatesFilter =
  'no_files' | 'some_in_progress' | 'some_failed' | 'some_not_ready' | 'all_ready';

/** Display labels of the conditions on the file states */
export const UploadBoxFileStatesFilterLabel: Record<UploadBoxFileStatesFilter, string> =
  {
    no_files: 'No files yet',
    some_in_progress: 'Some files in progress',
    some_failed: 'Some files failed',
    some_not_ready: 'Some files not ready',
    all_ready: 'All files ready',
  };

/**
 * Check whether the files of an upload box meet a condition. Only the check for
 * an empty box works without the state counts.
 * @param box - the upload box with its ID and file count
 * @param countsByBox - the state counts of all boxes, undefined if not loaded
 * @param filter - the condition to check
 * @returns whether the condition is met
 */
export function matchesFileStatesFilter(
  box: Pick<ResearchDataUploadBox, 'id' | 'file_count'>,
  countsByBox: FileStateCountsByBox | undefined,
  filter: UploadBoxFileStatesFilter,
): boolean {
  if (filter === 'no_files') return box.file_count === 0;
  if (!countsByBox) return false;
  const counts = countsByBox[box.id] ?? {};
  const ready = countFileUploadStateGroup(counts, 'ready');
  const archived = countFileUploadStateGroup(counts, 'archived');
  const inProgress = countFileUploadStateGroup(counts, 'in_progress');
  const failed = countFileUploadStateGroup(counts, 'failed');
  switch (filter) {
    case 'all_ready':
      return ready > 0 && archived + inProgress + failed === 0;
    case 'some_not_ready':
      return inProgress + failed > 0;
    case 'some_in_progress':
      return inProgress > 0;
    case 'some_failed':
      return failed > 0;
  }
}

/** Filters for upload box management */
export interface UploadBoxFilter {
  title: string | undefined;
  state: UploadBoxStateFilter | undefined;
  location: string | undefined;
  /** Keep only boxes whose file states meet this condition */
  fileStates?: UploadBoxFileStatesFilter;
}
