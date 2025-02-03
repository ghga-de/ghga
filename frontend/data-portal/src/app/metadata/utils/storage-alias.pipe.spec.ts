/**
 * These are the unit tests for the FacetActivity pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { StorageAlias } from './storage-alias.pipe';

describe('StorageAlias', () => {
  it('can create an instance', () => {
    const pipe = new StorageAlias();
    expect(pipe).toBeTruthy();
  });

  it('returns empty string for null input', () => {
    const pipe = new StorageAlias();
    expect(pipe.transform(null)).toBe('');
  });

  it('returns Tübingen 01 for TUE01', () => {
    const pipe = new StorageAlias();
    expect(pipe.transform('TUE01')).toBe('Tübingen 01');
  });

  it('returns ESV 01 for ESV01', () => {
    const pipe = new StorageAlias();
    expect(pipe.transform('ESV01')).toBe('ESV 01');
  });

  it('returns ESV 01CHL01 for ESV01CHL01', () => {
    const pipe = new StorageAlias();
    expect(pipe.transform('ESV01CHL01')).toBe('ESV 01CHL01');
  });
});
