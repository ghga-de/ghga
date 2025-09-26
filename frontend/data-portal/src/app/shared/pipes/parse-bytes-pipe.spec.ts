/**
 * These are the unit tests for the ParseBytes pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ParseBytes } from './parse-bytes-pipe';

describe('ParseBytesPipe', () => {
  it('can create an instance', () => {
    const pipe = new ParseBytes();
    expect(pipe).toBeTruthy();
  });

  it('should return an empty string for null or undefined input', () => {
    const pipe = new ParseBytes();
    expect(pipe.transform(null)).toBe('');
    expect(pipe.transform(undefined)).toBe('');
  });

  it('should return 750 B for 750 Bytes', () => {
    const pipe = new ParseBytes();
    const result = pipe.transform(750);
    expect(result).toBe('750\u00A0B');
  });

  it('should return 25 KB for 25 * 2^10 Bytes', () => {
    const pipe = new ParseBytes();
    const result = pipe.transform(25 * 2 ** 10);
    expect(result).toBe('25\u00A0kB');
  });

  it('should return 2.5 MB for 2.5 * 2^20 Bytes', () => {
    const pipe = new ParseBytes();
    const result = pipe.transform(2.5 * 2 ** 20);
    expect(result).toBe('2.5\u00A0MB');
  });
});
