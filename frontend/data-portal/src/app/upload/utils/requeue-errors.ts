/**
 * Helpers for errors when requeueing file uploads that failed re-encryption
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { MaybeBackendError } from '@app/shared/utils/errors';

/** A notification describing why requeueing a file upload failed */
export interface RequeueErrorNotice {
  /** The severity of the notification */
  level: 'warning' | 'error';
  /** The message to show */
  message: string;
  /** Whether the shown box and files are outdated and should be fetched again */
  refresh: boolean;
}

/** Message for a requeue refused because the box has been archived meanwhile */
const ARCHIVED_BOX_MESSAGE = 'Files in archived upload boxes cannot be requeued.';

/**
 * Check whether the RS refused a requeue because the upload box is archived.
 * @param error - the error thrown by the requeue request
 * @returns true if the box state caused the conflict
 */
function isBoxStateConflict(error: MaybeBackendError | undefined): boolean {
  return error?.status === 409 && error.error?.exception_id === 'boxStateError';
}

/**
 * Describe why requeueing a single file upload failed, based on the RS response.
 * @param err - the error thrown by the requeue request
 * @param alias - the alias (file name) of the file upload
 * @returns the notification to show
 */
export function describeRequeueError(err: unknown, alias: string): RequeueErrorNotice {
  const response = err as MaybeBackendError | undefined;
  const status = response?.status;
  const exceptionId = response?.error?.exception_id;
  if (status === 409 && exceptionId === 'fileUploadStateError') {
    return {
      level: 'warning',
      message: `The file "${alias}" is no longer waiting for a retry.`,
      refresh: true,
    };
  }
  if (isBoxStateConflict(response)) {
    return {
      level: 'error',
      message: ARCHIVED_BOX_MESSAGE,
      refresh: true,
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

/**
 * Describe why requeueing all failed file uploads of a box failed.
 * @param err - the error thrown by the requeue request
 * @returns the notification to show
 */
export function describeRequeueAllError(err: unknown): RequeueErrorNotice {
  if (isBoxStateConflict(err as MaybeBackendError | undefined)) {
    return { level: 'error', message: ARCHIVED_BOX_MESSAGE, refresh: true };
  }
  return {
    level: 'error',
    message: 'The failed files could not be requeued. Please try again.',
    refresh: false,
  };
}
