/**
 * Interface for the study datatype as served by the research service (rs).
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

/** Lifecycle status of an rs study */
export type StudyStatus = 'draft' | 'archived';

/**
 * Map from a file accession to its internal file ID, or `null` when the file
 * is still unmapped (no internal file ID assigned yet).
 *
 * A non-null value means the file is already mapped. Such mappings are final:
 * the backend only ever adds new file mappings for a study, it never changes an
 * existing one, so the mapping tool lists only the files whose value is `null`
 * and hides the already-mapped ones.
 */
export type FileIdMap = Record<string, string | null>;

/**
 * A study as served by the research service (rs).
 *
 * Note that `id` equals the GHGA study accession (rs sets it during ingestion),
 * so it can be used directly to fetch the corresponding metldata Study resource.
 */
export interface Study {
  /** The study ID, equal to the GHGA study accession */
  id: string;
  /** The study title */
  title: string;
  /** The study description */
  description: string;
  /** The study types */
  types: string[];
  /** The affiliations associated with the study */
  affiliations: string[];
  /** The lifecycle status of the study */
  status: StudyStatus;
  /** The number of datasets belonging to the study */
  num_datasets: number;
  /** The number of publications associated with the study */
  num_publications: number;
  /** Whether the study has experimental metadata */
  has_em: boolean;
  /** The creation timestamp as an ISO datetime string */
  created: string;
  /** The ID of the user who created the study */
  created_by: string;
  /** The approval timestamp as an ISO datetime string, if approved */
  approved?: string | null;
  /** The ID of the user who approved the study, if approved */
  approved_by?: string | null;
  /** The ID of the study superseding this one, if any */
  superseded_by_id?: string | null;
}

/** An empty study used as a default value while loading */
export const emptyStudy: Study = {
  id: '',
  title: '',
  description: '',
  types: [],
  affiliations: [],
  status: 'draft',
  num_datasets: 0,
  num_publications: 0,
  has_em: false,
  created: '',
  created_by: '',
  approved: null,
  approved_by: null,
  superseded_by_id: null,
};
