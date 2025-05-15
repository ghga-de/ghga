/**
 * Type declarations for access requests
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

export enum AccessRequestStatus {
  allowed = 'allowed',
  denied = 'denied',
  pending = 'pending',
}

export const AccessRequestStatusClass: {
  [K in keyof typeof AccessRequestStatus]: string;
} = {
  denied: 'text-error',
  pending: 'text-info',
  allowed: 'text-success',
};

export interface AccessRequest {
  id: string;
  user_id: string;
  dataset_id: string;
  full_user_name: string;
  email: string;
  request_text: string;
  access_starts: string;
  access_ends: string;
  request_created: string;
  status: AccessRequestStatus;
  status_changed: null | string;
  changed_by: null | string;
  iva_id: null | string;
  ticket_id: null | string;
}

export interface GrantedAccessRequest {
  request: AccessRequest;
  isExpired: boolean;
  daysRemaining: number;
}

export interface AccessRequestDialogData {
  datasetID: string;
  email: string;
  description: string;
  fromDate: Date | undefined;
  untilDate: Date | undefined;
  userId: string;
}

export interface AccessRequestFilter {
  datasetId: string;
  name: string;
  fromDate: Date | undefined;
  toDate: Date | undefined;
  status: AccessRequestStatus | undefined;
}
