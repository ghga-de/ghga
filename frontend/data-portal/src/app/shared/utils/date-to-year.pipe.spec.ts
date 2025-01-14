/**
 * These are the unit tests for the DateToYear (example) pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DateToYearPipe } from './date-to-year.pipe';

describe('DateToYearPipe', () => {
  it('can create an instance', () => {
    const pipe = new DateToYearPipe();
    expect(pipe).toBeTruthy();
  });

  it('should return 2025 for a date in 2025', () => {
    const date = new Date('2025-05-12');
    const pipe = new DateToYearPipe();
    const result = pipe.transform(date);
    expect(result).toBe('2025');
  });

  it('should return an empty string for an invalid date', () => {
    const date = new Date('invalid input data from somewhere...');
    const pipe = new DateToYearPipe();
    const result = pipe.transform(date);
    expect(result).toBe('');
  });
});
