/**
 * These are the unit tests for the DateToYear pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { isoDatePipe } from './iso-date.pipe';

describe('isoDate', () => {
  it('can create an instance', () => {
    const pipe = new isoDatePipe();
    expect(pipe).toBeTruthy();
  });

  it('should return 2025-05-11 for the date 29 May 2025', () => {
    const date = new Date('29 May 2025');
    const pipe = new isoDatePipe();
    const result = pipe.transform(date);
    expect(result).toBe('2025-05-29');
  });

  it('should return 2025-05-12 for the string 29 May 2025', () => {
    const date = '29 May 2025';
    const pipe = new isoDatePipe();
    const result = pipe.transform(date);
    expect(result).toBe('2025-05-29');
  });

  it('should return an empty string for an invalid date', () => {
    const date = new Date('invalid input data from somewhere...');
    const pipe = new isoDatePipe();
    const result = pipe.transform(date);
    expect(result).toBe('');
  });
});
