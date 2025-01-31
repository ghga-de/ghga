/**
 * These are the unit tests for the ParseBytes pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ParseBytes } from './parse-bytes.pipe';

describe('ParseBytesPipe', () => {
  it('can create an instance', () => {
    const pipe = new ParseBytes();
    expect(pipe).toBeTruthy();
  });

  it('should return 25 KB for 25000 Bytes', () => {
    const pipe = new ParseBytes();
    const result = pipe.transform(25000);
    expect(result).toBe('25\u00A0kB');
  });

  it('should return 2.5 MB for 25000000 Bytes', () => {
    const pipe = new ParseBytes();
    const result = pipe.transform(2500000);
    expect(result).toBe('2.5\u00A0MB');
  });
});
