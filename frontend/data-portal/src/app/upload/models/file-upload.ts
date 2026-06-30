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
  /** ID of the box this file belongs to */
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
