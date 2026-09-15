/**
 * Tests for the requeue error helpers.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpErrorResponse } from '@angular/common/http';
import { describeRequeueAllError, describeRequeueError } from './requeue-errors';

/**
 * Create an RS error response as thrown by the HttpClient.
 * @param status - the HTTP status code
 * @param exceptionId - the exception ID in the response body, if any
 * @returns the error response
 */
function rsError(status: number, exceptionId?: string): HttpErrorResponse {
  return new HttpErrorResponse({
    status,
    error: exceptionId ? { exception_id: exceptionId } : null,
  });
}

describe('describeRequeueError', () => {
  it('should warn and refresh when the file is no longer failed', () => {
    expect(describeRequeueError(rsError(409, 'fileUploadStateError'), 'a.bam')).toEqual(
      {
        level: 'warning',
        message: 'The file "a.bam" is no longer waiting for a retry.',
        refresh: true,
      },
    );
  });

  it('should report an archived box and refresh', () => {
    expect(describeRequeueError(rsError(409, 'boxStateError'), 'a.bam')).toEqual({
      level: 'error',
      message: 'Files in archived upload boxes cannot be requeued.',
      refresh: true,
    });
  });

  it('should report a missing file or box and refresh', () => {
    expect(describeRequeueError(rsError(404, 'fileUploadNotFound'), 'a.bam')).toEqual({
      level: 'error',
      message: 'The file "a.bam" or its upload box was not found.',
      refresh: true,
    });
  });

  it('should ask for a new upload when the uploaded data is gone', () => {
    expect(describeRequeueError(rsError(500, 'requeueError'), 'a.bam')).toEqual({
      level: 'error',
      message:
        'The uploaded data of "a.bam" is gone. Delete the file and upload it again.',
      refresh: false,
    });
  });

  it('should fall back to a generic error', () => {
    const generic = {
      level: 'error',
      message: 'The file "a.bam" could not be requeued.',
      refresh: false,
    };
    expect(describeRequeueError(rsError(500, 'internalError'), 'a.bam')).toEqual(
      generic,
    );
    expect(describeRequeueError(new Error('offline'), 'a.bam')).toEqual(generic);
  });
});

describe('describeRequeueAllError', () => {
  it('should report an archived box and refresh', () => {
    expect(describeRequeueAllError(rsError(409, 'boxStateError'))).toEqual({
      level: 'error',
      message: 'Files in archived upload boxes cannot be requeued.',
      refresh: true,
    });
  });

  it('should fall back to a generic error', () => {
    const generic = {
      level: 'error',
      message: 'The failed files could not be requeued. Please try again.',
      refresh: false,
    };
    expect(describeRequeueAllError(rsError(404, 'boxNotFoundError'))).toEqual(generic);
    expect(describeRequeueAllError(new Error('offline'))).toEqual(generic);
  });
});
