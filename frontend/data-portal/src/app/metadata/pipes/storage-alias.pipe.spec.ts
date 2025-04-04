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

  it('returns empty string for null or undefined input', () => {
    const pipe = new StorageAlias();
    expect(pipe.transform(null)).toBe('');
    expect(pipe.transform(undefined)).toBe('');
  });

  it('returns Tübingen for TUE', () => {
    const pipe = new StorageAlias();
    expect(pipe.transform('TUE')).toBe('Tübingen');
  });

  it('returns Tübingen for TUE1', () => {
    const pipe = new StorageAlias();
    expect(pipe.transform('TUE1')).toBe('Tübingen');
  });

  it('returns Tübingen for TUE01', () => {
    const pipe = new StorageAlias();
    expect(pipe.transform('TUE01')).toBe('Tübingen');
  });

  it('returns Tübingen for TUE001', () => {
    const pipe = new StorageAlias();
    expect(pipe.transform('TUE001')).toBe('Tübingen');
  });

  it('returns Tübingen 2 for TUE2', () => {
    const pipe = new StorageAlias();
    expect(pipe.transform('TUE2')).toBe('Tübingen 2');
  });

  it('returns Tübingen 2 for TUE02', () => {
    const pipe = new StorageAlias();
    expect(pipe.transform('TUE02')).toBe('Tübingen 2');
  });

  it('returns Tübingen 2 for TUE002', () => {
    const pipe = new StorageAlias();
    expect(pipe.transform('TUE002')).toBe('Tübingen 2');
  });

  it('returns Heidelberg 7 for HD 007', () => {
    const pipe = new StorageAlias();
    expect(pipe.transform('HD 007')).toBe('Heidelberg 7');
  });

  it('returns ESV for ESV', () => {
    const pipe = new StorageAlias();
    expect(pipe.transform('ESV')).toBe('ESV');
  });

  it('returns ESV for ESV0001', () => {
    const pipe = new StorageAlias();
    expect(pipe.transform('ESV0001')).toBe('ESV');
  });

  it('returns ESV 123 for ESV0123', () => {
    const pipe = new StorageAlias();
    expect(pipe.transform('ESV0123')).toBe('ESV 123');
  });

  it('returns ESV 4CHL01 for ESV04CHL01', () => {
    const pipe = new StorageAlias();
    expect(pipe.transform('ESV04CHL01')).toBe('ESV 4CHL01');
  });
});
