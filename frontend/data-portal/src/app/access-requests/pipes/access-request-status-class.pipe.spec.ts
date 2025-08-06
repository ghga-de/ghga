/**
 * These are the unit tests for the access request status class pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { AccessRequestStatus } from '../models/access-requests';
import { AccessRequestAndGrantStatusClassPipe } from './access-request-status-class.pipe';

describe('AccessRequestAndGrantStatusClassPipe', () => {
  it('can create an instance', () => {
    const pipe = new AccessRequestAndGrantStatusClassPipe();
    expect(pipe).toBeTruthy();
  });

  it('should return "text-error" for denied', () => {
    const pipe = new AccessRequestAndGrantStatusClassPipe();
    const result = pipe.transform(AccessRequestStatus['denied']);
    expect(result).toBe('text-error');
  });
});
