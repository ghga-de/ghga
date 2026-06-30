/**
 * Models for submitting a file accession mapping to the RS backend.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

/**
 * Request body for submitting a file accession mapping.
 * Maps metadata file accessions to upload box file IDs.
 */
export interface AccessionMapRequest {
  /** The current version of the upload box */
  box_version: number;
  /** The accession of the study this mapping belongs to */
  study_id: string;
  /** Mapping from metadata file accession to upload box file ID */
  mapping: Record<string, string>;
}
