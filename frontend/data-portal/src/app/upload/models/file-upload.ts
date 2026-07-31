/**
 * File upload related models
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

/** All possible file upload states */
export type FileUploadState =
  | 'init'
  | 'inbox'
  | 'failed'
  | 'cancelled'
  | 'interrogated'
  | 'awaiting_archival'
  | 'archived';

/** User-friendly display names for file upload states */
export const FileUploadStatePrintable: Record<FileUploadState, string> = {
  init: 'uploading…',
  inbox: 're-encrypting…',
  interrogated: 're-encrypted',
  awaiting_archival: 'awaiting archival…',
  archived: 'archived',
  failed: 'failed',
  cancelled: 'deleted',
};

/** State-specific text classes for file upload states */
export const FileUploadStateClass: Record<FileUploadState, string> = {
  init: 'text-warning',
  inbox: 'text-warning',
  interrogated: 'text-success',
  awaiting_archival: 'text-warning',
  archived: 'text-gray-600',
  failed: 'text-error',
  cancelled: 'text-error',
};

/** A file upload with its accession number */
export interface FileUploadWithAccession {
  /** Unique identifier for the file upload */
  id: string;
  /** ID of the underlying file upload box this file belongs to */
  box_id: string;
  /** The alias (filename) of the uploaded file */
  alias: string;
  /** The state of the file upload */
  state: FileUploadState;
  /** Timestamp of when state was updated */
  state_updated: string;
  /** The storage alias of the Data Hub housing the file */
  storage_alias: string;
  /** The name of the bucket where the file is currently stored */
  bucket_id: string;
  /** SHA-256 checksum of the entire unencrypted file content */
  decrypted_sha256: string | null;
  /** The size of the unencrypted file in bytes */
  decrypted_size: number;
  /** The encrypted size of the file before re-encryption */
  encrypted_size: number;
  /** The number of bytes in each file part (last part is likely smaller) */
  part_size: number;
  /** The accession number assigned to this file */
  accession: string | null;
}

/**
 * A page of file uploads for an upload box, plus the total unpaginated count,
 * as returned by the paginated `/upload-boxes/{id}/uploads` endpoint of the RS.
 */
export interface BoxUploadsPage {
  /** The file uploads on this page, in the requested sort order */
  items: FileUploadWithAccession[];
  /** The total number of file uploads in the box (unpaginated) */
  total_count: number;
}

/** An empty page of file uploads, used as default value for the resources */
export const emptyBoxUploadsPage: BoxUploadsPage = { items: [], total_count: 0 };

/** Default number of file uploads requested per page (the backend default) */
export const DEFAULT_UPLOADS_PAGE_SIZE = 10;

/**
 * The largest page size the RS accepts for the file uploads endpoint. Also used
 * as the page size when the complete file list of a box is requested at once.
 */
export const MAX_UPLOADS_PAGE_SIZE = 1000;

/**
 * Mapping from the columns of the file uploads table to the field names the RS
 * accepts in the `sort` query parameter. Columns absent here are not sortable on
 * the server and must not offer a sort header, since sorting a single page in the
 * browser would order only the visible rows while looking authoritative.
 */
export const FileUploadSortFields: Record<string, string> = {
  alias: 'alias',
  status: 'state',
  size: 'decrypted_size',
  uploaded: 'state_updated',
  accession: 'accession',
};

/** Sort direction of the file uploads table (matches Material's SortDirection) */
export type FileUploadSortDirection = 'asc' | 'desc' | '';

/** The order the RS falls back to when no sort parameter is given */
const DEFAULT_UPLOADS_SORT_COLUMN = 'alias';

/**
 * Translate a sorted table column into the `sort` query parameter of the RS.
 * @param column - the sorted column of the file uploads table
 * @param direction - the direction the column is sorted in
 * @returns the sort specification, or undefined for the default server order
 */
export function fileUploadSortSpec(
  column: string,
  direction: FileUploadSortDirection,
): string | undefined {
  const field = FileUploadSortFields[column];
  if (!field || !direction) return undefined;
  return direction === 'desc' ? `-${field}` : field;
}

/**
 * Translate a `sort` query parameter back into the table column and direction,
 * so the sort headers reflect the order the server actually applied.
 * @param spec - the sort specification, or undefined for the default server order
 * @returns the sorted column and its direction
 */
export function fileUploadSortState(spec: string | undefined): {
  column: string;
  direction: FileUploadSortDirection;
} {
  const direction: FileUploadSortDirection = spec?.startsWith('-') ? 'desc' : 'asc';
  const field = spec?.replace(/^-/, '');
  const column = field
    ? Object.keys(FileUploadSortFields).find(
        (key) => FileUploadSortFields[key] === field,
      )
    : undefined;
  return column
    ? { column, direction }
    : { column: DEFAULT_UPLOADS_SORT_COLUMN, direction: 'asc' };
}
