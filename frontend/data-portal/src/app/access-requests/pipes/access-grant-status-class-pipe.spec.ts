/**
 * These are the unit tests for the access grant status class pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { AccessGrantStatus } from '../models/access-requests';
import { AccessGrantStatusClassPipe } from './access-grant-status-class-pipe';

describe('AccessGrantStatusClassPipe', () => {
  it('can create an instance', () => {
    const pipe = new AccessGrantStatusClassPipe();
    expect(pipe).toBeTruthy();
  });

  it('should return "" for undefined', () => {
    const pipe = new AccessGrantStatusClassPipe();
    const result = pipe.transform(undefined);
    expect(result).toBe('');
  });

  it('should return "text-error" for denied', () => {
    const pipe = new AccessGrantStatusClassPipe();
    const result = pipe.transform(AccessGrantStatus['expired']);
    expect(result).toBe('text-error');
  });
});
