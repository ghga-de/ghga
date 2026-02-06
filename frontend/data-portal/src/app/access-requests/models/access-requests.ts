/**
 * Type declarations for access requests
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Iva } from '@app/ivas/models/iva';

export enum AccessRequestStatus {
  allowed = 'allowed',
  denied = 'denied',
  pending = 'pending',
}

export enum AccessGrantStatus {
  active = 'active',
  expired = 'expired',
  waiting = 'waiting',
}

export const AccessRequestStatusClass: Record<AccessRequestStatus, string> = {
  allowed: 'text-success',
  denied: 'text-error',
  pending: 'text-info',
};

export const AccessGrantStatusClass: Record<AccessGrantStatus, string> = {
  active: 'text-success',
  waiting: 'text-warning',
  expired: 'text-error',
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
  dataset: string | undefined;
  requester: string | undefined;
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
  daysRemaining?: number;
}

export interface AccessGrantWithIva extends AccessGrant {
  iva?: Iva;
}

export interface AccessGrantFilter {
  status: AccessGrantStatus | undefined;
  user: string | undefined;
  dataset_id: string | undefined;
}
