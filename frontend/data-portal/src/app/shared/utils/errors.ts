/**
 * Helper types and functions for error handling
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

/**
 * Type for backend service errors.
 * These are usually an HTTPErrorResponses that also contain backend error details.
 * We particularly handle the case of validation errors thrown by Pydantic.
 * But we also want to handle the case where other kinds of errors are thrown,
 * so we allow the case that the error object is not present.
 */
export type MaybeBackendError = {
  status?: number;
  statusText?: string;
  message?: string;
  error?: { detail?: string | Array<{ msg?: string }> };
};

/**
 * Get the error message from a backend error
 * @param error a backend error, but we accept any kind of error
 * @returns the most detailed and user friendly error message that can be derived
 * from the error or an empty string if no message can be extracted
 */
export function getBackendErrorMessage(
  error: MaybeBackendError | string | number | null | undefined,
): string {
  if (!error || typeof error == 'number') return '';
  if (typeof error === 'string') return error;
  const detail = error?.error?.detail;
  let detailText = Array.isArray(detail) ? detail[0].msg : detail;
  if (typeof detailText !== 'string') detailText = '';
  let msg = detailText || error?.statusText || error?.message;
  if (typeof msg !== 'string') msg = '';
  // remove superfluous quotes
  if (msg.startsWith("'") && msg.endsWith("'")) msg = msg.slice(1, -1);
  if (msg.startsWith('"') && msg.endsWith('"')) msg = msg.slice(1, -1);
  return msg;
}
