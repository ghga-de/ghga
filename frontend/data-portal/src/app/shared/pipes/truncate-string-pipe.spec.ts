/**
 * These are the unit tests for the TruncateString pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { TruncateString } from './truncate-string-pipe';

describe('TruncateString', () => {
  it('can create an instance', () => {
    const pipe = new TruncateString();
    expect(pipe).toBeTruthy();
  });

  it('should return a 7 character long string from a longer one with an ellipsis at the end', () => {
    const pipe = new TruncateString();
    const result = pipe.transform('0a4d55a8d778e5022fab701977c5d840bbc486d0');
    expect(result).toHaveLength(7 + 1);
  });

  it('should return the same string for a string with less than 8 characters', () => {
    const pipe = new TruncateString();
    const result = pipe.transform('0a4d55');
    expect(result).toBe('0a4d55');
  });

  it('should return a 5 character long string from a longer one with an ellipsis at the end when the size param is set', () => {
    const pipe = new TruncateString();
    const result = pipe.transform('0a4d55a8d778e5022fab701977c5d840bbc486d0', 5);
    expect(result).toHaveLength(5 + 1);
  });
});
