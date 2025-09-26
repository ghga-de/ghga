/**
 * User status class pipe tests
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { UserStatusClassPipe } from './user-status-class-pipe';

describe('UserStatusClassPipe', () => {
  let pipe: UserStatusClassPipe;

  beforeEach(() => {
    pipe = new UserStatusClassPipe();
  });

  it('should create an instance', () => {
    expect(pipe).toBeTruthy();
  });

  it('should return text-success for active status', () => {
    expect(pipe.transform('active')).toBe('text-success');
  });

  it('should return text-error for inactive status', () => {
    expect(pipe.transform('inactive')).toBe('text-error');
  });
});
