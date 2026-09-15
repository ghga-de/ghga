/**
 * Models and helpers for requeueing file uploads that failed re-encryption
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpErrorResponse } from '@angular/common/http';

/** Result of requeueing all failed file uploads of a box, as returned by the RS */
export interface BoxRequeueResult {
  /** IDs of the file uploads that were set back to the inbox state */
  requeued: string[];
  /** IDs of the file uploads that could not be requeued due to an error */
  skipped: string[];
}

/** A notification describing why requeueing a file upload failed */
export interface RequeueErrorNotice {
  /** The severity of the notification */
  level: 'warning' | 'error';
  /** The message to show */
  message: string;
  /** Whether the file list is outdated and should be fetched again */
  refresh: boolean;
}

/**
 * Describe why requeueing a single file upload failed, based on the RS response.
 * @param err - the error thrown by the requeue request
 * @param alias - the alias (file name) of the file upload
 * @returns the notification to show
 */
export function describeRequeueError(err: unknown, alias: string): RequeueErrorNotice {
  const response = err as HttpErrorResponse | undefined;
  const status = response?.status;
  const exceptionId: unknown = response?.error?.exception_id;
  if (status === 409 && exceptionId === 'fileUploadStateError') {
    return {
      level: 'warning',
      message: `The file "${alias}" is no longer waiting for a retry.`,
      refresh: true,
    };
  }
  if (status === 409 && exceptionId === 'boxStateError') {
    return {
      level: 'error',
      message: 'Files in archived upload boxes cannot be requeued.',
      refresh: false,
    };
  }
  if (status === 404) {
    return {
      level: 'error',
      message: `The file "${alias}" or its upload box was not found.`,
      refresh: true,
    };
  }
  if (status === 500 && exceptionId === 'requeueError') {
    return {
      level: 'error',
      message: `The uploaded data of "${alias}" is gone. Delete the file and upload it again.`,
      refresh: false,
    };
  }
  return {
    level: 'error',
    message: `The file "${alias}" could not be requeued.`,
    refresh: false,
  };
}
