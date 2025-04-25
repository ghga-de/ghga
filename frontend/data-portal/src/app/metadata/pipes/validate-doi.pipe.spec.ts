/**
 * These are the unit tests for the ValidateDOI pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ValidateDOI } from './validate-doi.pipe';

describe('validateDOI', () => {
  it('can create an instance', () => {
    const pipe = new ValidateDOI();
    expect(pipe).toBeTruthy();
  });

  it('returns an empty string for an empty string', () => {
    const pipe = new ValidateDOI();
    expect(pipe.transform('')).toBe('');
  });

  it('returns 10.1000/123 for "doi: 10.1000/123"', () => {
    const pipe = new ValidateDOI();
    expect(pipe.transform('doi: 10.1000/123')).toBe('10.1000/123');
  });

  it('returns 10.1000/123 for https://doi.org/10.1000/123', () => {
    const pipe = new ValidateDOI();
    expect(pipe.transform('https://doi.org/10.1000/123')).toBe('10.1000/123');
  });

  it('returns 10.1000/123 for https://dx.doi.org/10.1000/123', () => {
    const pipe = new ValidateDOI();
    expect(pipe.transform('https://dx.doi.org/10.1000/123')).toBe('10.1000/123');
  });

  it('returns an empty string for an invalid DOI', () => {
    const pipe = new ValidateDOI();
    expect(pipe.transform('https://www.doi.org/11.1000/123')).toBe('');
  });
});
