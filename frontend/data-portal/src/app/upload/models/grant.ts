/**
 * Upload grant related models
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { UploadBoxState } from './box';

/** Default number of days a new upload grant is valid */
export const VALID_GRANT_DAYS = 180;

/** Base data to create an upload grant */
export interface UploadGrantBase {
  /** Internal user ID */
  user_id: string;
  /** ID of an IVA associated with this grant */
  iva_id: string | null;
  /** ID of the upload box this grant is for */
  box_id: string;
  /** Start date of validity */
  valid_from: string;
  /** End date of validity */
  valid_until: string;
}

/** Response body returned by the backend when creating an upload grant */
export interface GrantId {
  /** Server-assigned grant ID */
  id: string;
}

/** An upload access grant */
export interface UploadGrant extends UploadGrantBase {
  /** Internal grant ID (same as claim ID) */
  id: string;
  /** Date of creation of this grant */
  created: string;
  /** Full name of the user */
  user_name: string;
  /** The email address of the user */
  user_email: string;
  /** Academic title of the user */
  user_title: string | null;
}

/** An UploadGrant with the ResearchDataUploadBox title, description, state, and version */
export interface GrantWithBoxInfo extends UploadGrant {
  /** Short meaningful name for the box */
  box_title: string;
  /** Describes the upload box in more detail */
  box_description: string;
  /** Current state of the upload box */
  box_state: UploadBoxState;
  /** Current version of the upload box */
  box_version: number;
}
