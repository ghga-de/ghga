/**
 * Tests for the upload box conflict helpers.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpErrorResponse } from '@angular/common/http';
import {
  describeIncompleteOrFailedConflict,
  incompleteOrFailedConflictTitle,
  parseIncompleteOrFailedConflict,
} from './box-conflict';

/**
 * Create an error response as thrown by the HttpClient.
 * @param status - the HTTP status code
 * @param error - the response body
 * @returns the error response
 */
function errorResponse(status: number, error: unknown): HttpErrorResponse {
  return new HttpErrorResponse({ status, error });
}

describe('parseIncompleteOrFailedConflict', () => {
  it('should return both lists of a conflict response', () => {
    const err = errorResponse(409, {
      exception_id: 'incompleteOrFailed',
      data: { incomplete_uploads: ['f1'], need_attention: ['f2', 'f3'] },
    });
    expect(parseIncompleteOrFailedConflict(err)).toEqual({
      incompleteUploads: ['f1'],
      needAttention: ['f2', 'f3'],
    });
  });

  it('should treat a missing list as empty', () => {
    const err = errorResponse(409, { data: { incomplete_uploads: ['f1'] } });
    expect(parseIncompleteOrFailedConflict(err)).toEqual({
      incompleteUploads: ['f1'],
      needAttention: [],
    });
  });

  it('should return null when both lists are empty', () => {
    const err = errorResponse(409, {
      data: { incomplete_uploads: [], need_attention: [] },
    });
    expect(parseIncompleteOrFailedConflict(err)).toBeNull();
  });

  it('should return null for other status codes', () => {
    const err = errorResponse(500, { data: { need_attention: ['f1'] } });
    expect(parseIncompleteOrFailedConflict(err)).toBeNull();
  });

  it('should return null for a conflict without data', () => {
    expect(parseIncompleteOrFailedConflict(errorResponse(409, null))).toBeNull();
    expect(parseIncompleteOrFailedConflict(new Error('failed'))).toBeNull();
    expect(parseIncompleteOrFailedConflict(undefined)).toBeNull();
  });
});

describe('describeIncompleteOrFailedConflict', () => {
  it('should describe incomplete uploads only', () => {
    expect(
      describeIncompleteOrFailedConflict(
        { incompleteUploads: ['f1', 'f2'], needAttention: [] },
        'Locking',
      ),
    ).toBe('Locking failed because there are still 2 incomplete file uploads.');
    expect(
      describeIncompleteOrFailedConflict(
        { incompleteUploads: ['f1'], needAttention: [] },
        'Submission',
      ),
    ).toBe('Submission failed because there is still 1 incomplete file upload.');
  });

  it('should describe failed re-encryptions only', () => {
    expect(
      describeIncompleteOrFailedConflict(
        { incompleteUploads: [], needAttention: ['f1'] },
        'Locking',
      ),
    ).toBe('Locking failed because 1 file failed re-encryption.');
    expect(
      describeIncompleteOrFailedConflict(
        { incompleteUploads: [], needAttention: ['f1', 'f2'] },
        'Archival',
      ),
    ).toBe('Archival failed because 2 files failed re-encryption.');
  });

  it('should describe incomplete uploads and failed re-encryptions together', () => {
    expect(
      describeIncompleteOrFailedConflict(
        { incompleteUploads: ['f1'], needAttention: ['f2', 'f3'] },
        'Locking',
      ),
    ).toBe(
      'Locking failed because there is still 1 incomplete file upload' +
        ' and 2 files that failed re-encryption.',
    );
  });
});

describe('incompleteOrFailedConflictTitle', () => {
  it('should mention incomplete uploads when no file failed re-encryption', () => {
    expect(
      incompleteOrFailedConflictTitle({ incompleteUploads: ['f1'], needAttention: [] }),
    ).toBe('Incomplete uploads detected!');
  });

  it('should mention unresolved files when a file failed re-encryption', () => {
    expect(
      incompleteOrFailedConflictTitle({
        incompleteUploads: ['f1'],
        needAttention: ['f2'],
      }),
    ).toBe('Unresolved files detected!');
  });
});
