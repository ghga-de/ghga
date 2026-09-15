/**
 * Helpers for upload box conflicts caused by unsettled file uploads
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { MaybeBackendError } from '@app/shared/utils/errors';

/**
 * The file uploads that block locking, submitting or archiving an upload box, as
 * reported by a 409 `incompleteOrFailed` response of the RS.
 */
export interface IncompleteOrFailedConflict {
  /** IDs of file uploads that are still uploading (or not re-encrypted yet when archiving) */
  incompleteUploads: string[];
  /** IDs of file uploads whose re-encryption failed ('failed_interrogation') */
  needAttention: string[];
}

/** The upload box action that was prevented by a conflict */
export type BoxConflictAction = 'Locking' | 'Submission' | 'Archival';

/**
 * Read a list of file upload IDs from a conflict payload.
 * @param value - the value found in the payload
 * @returns the IDs, or an empty list if the value is not a list
 */
function idList(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String) : [];
}

/**
 * Extract the blocking file uploads from a 409 response of the RS.
 * @param err - the error thrown by the request
 * @returns the conflict, or null if the error is not a conflict caused by file uploads
 */
export function parseIncompleteOrFailedConflict(
  err: unknown,
): IncompleteOrFailedConflict | null {
  const response = err as MaybeBackendError | undefined;
  const data = response?.error?.data;
  if (response?.status !== 409 || !data || typeof data !== 'object') return null;
  const payload = data as { incomplete_uploads?: unknown; need_attention?: unknown };
  const conflict: IncompleteOrFailedConflict = {
    incompleteUploads: idList(payload.incomplete_uploads),
    needAttention: idList(payload.need_attention),
  };
  if (!conflict.incompleteUploads.length && !conflict.needAttention.length) return null;
  return conflict;
}

/**
 * Describe which file uploads keep an upload box from being locked or archived.
 * @param conflict - the file uploads that block the action
 * @returns a clause naming the number of incomplete and failed file uploads
 */
export function describeUnsettledFiles(conflict: IncompleteOrFailedConflict): string {
  const incomplete = conflict.incompleteUploads.length;
  const failed = conflict.needAttention.length;
  const [are, uploads] = incomplete === 1 ? ['is', 'upload'] : ['are', 'uploads'];
  const files = failed === 1 ? 'file' : 'files';
  const incompleteText = `there ${are} still ${incomplete} incomplete file ${uploads}`;
  if (!failed) return incompleteText;
  if (!incomplete) return `${failed} ${files} failed re-encryption`;
  return `${incompleteText} and ${failed} ${files} that failed re-encryption`;
}

/**
 * Describe in one sentence why an upload box action was prevented.
 * @param conflict - the file uploads that blocked the action
 * @param action - the action that was prevented
 * @returns a sentence naming the number of incomplete and failed file uploads
 */
export function describeIncompleteOrFailedConflict(
  conflict: IncompleteOrFailedConflict,
  action: BoxConflictAction,
): string {
  return `${action} failed because ${describeUnsettledFiles(conflict)}.`;
}

/**
 * Pick the dialog title for an upload box conflict.
 * @param conflict - the file uploads that blocked the action
 * @returns the title, depending on whether any file upload failed re-encryption
 */
export function incompleteOrFailedConflictTitle(
  conflict: IncompleteOrFailedConflict,
): string {
  return conflict.needAttention.length
    ? 'Unresolved files detected!'
    : 'Incomplete uploads detected!';
}
