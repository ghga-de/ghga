/**
 * These are the unit tests for the AddPluralS pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { AddPluralS } from './add-plural-s-pipe';

describe('AddPluralSPipe', () => {
  it('can create an instance', () => {
    const pipe = new AddPluralS();
    expect(pipe).toBeTruthy();
  });

  it('should return an empty string if count is 1', () => {
    const pipe = new AddPluralS();
    const result = pipe.transform(1);
    expect(result).toBe('');
  });

  it('should return s for anything besides 1', () => {
    const pipe = new AddPluralS();
    const result = pipe.transform(24);
    expect(result).toBe('s');
  });
});
