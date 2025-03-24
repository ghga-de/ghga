/**
 * These are the unit tests for the Capitalise pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Capitalise } from './capitalise.pipe';

describe('CapitalisePipe', () => {
  it('can create an instance', () => {
    const pipe = new Capitalise();
    expect(pipe).toBeTruthy();
  });

  it('should return Hello world for hello world', () => {
    const pipe = new Capitalise();
    const result = pipe.transform('hello world');
    expect(result).toBe('Hello world');
  });

  it('should return 24 for 24', () => {
    const pipe = new Capitalise();
    const result = pipe.transform('24');
    expect(result).toBe('24');
  });

  it('should return "" for ""', () => {
    const pipe = new Capitalise();
    const result = pipe.transform('');
    expect(result).toBe('');
  });
});
