/**
 * User status class pipe tests
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { UserStatus } from '../models/user';
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
    expect(pipe.transform('active' as UserStatus)).toBe('text-success');
  });

  it('should return text-error for inactive status', () => {
    expect(pipe.transform('inactive' as UserStatus)).toBe('text-error');
  });
});
