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

export enum AccessGrantStatus {
  active = 'Active',
  expired = 'Expired',
  waiting = 'Waiting',
}

export type CombinedStatus = AccessRequestStatus | AccessGrantStatus;

export const AccessRequestStatusClass: Record<CombinedStatus, string> = {
  denied: 'text-error',
  pending: 'text-info',
  allowed: 'text-success',
  Waiting: 'text-warning',
  Expired: 'text-error',
  Active: 'text-success',
};

export interface AccessRequest {
  id: string;
  user_id: string;
  dataset_id: string;
  dataset_title: string;
  dac_alias: string;
  dac_email: string;
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
  internal_note: null | string;
  note_to_requester: null | string;
}

export interface GrantedAccessRequest {
  request: AccessRequest;
  isExpired: boolean;
  daysRemaining: number;
}

export interface AccessRequestDetailData {
  datasetID: string;
  email: string;
  description: string;
  fromDate: Date | undefined;
  untilDate: Date | undefined;
  userId: string;
}

export interface AccessRequestFilter {
  ticketId: string | undefined;
  datasetId: string | undefined;
  datasetTitle: string | undefined;
  name: string | undefined;
  dac: string | undefined;
  fromDate: Date | undefined;
  toDate: Date | undefined;
  status: AccessRequestStatus | undefined;
  requestText: string | undefined;
  noteToRequester: string | undefined;
  internalNote: string | undefined;
}

export interface AccessGrant {
  id: string;
  user_id: string;
  created: string;
  dataset_id: string;
  dataset_title: string;
  valid_from: string;
  valid_until: string;
  user_email: string;
  user_name: string;
  user_title: string | null;
  dac_alias: string;
  dac_email: string;
  iva_id: string | null;
  status?: AccessGrantStatus;
}

export interface AccessGrantFilter {
  status: AccessGrantStatus | undefined;
  user: string | undefined;
  dataset_id: string | undefined;
}
