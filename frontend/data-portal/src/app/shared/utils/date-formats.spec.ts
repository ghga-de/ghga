/**
 * Unit tests for date formats and utility functions.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { timeZoneToUTC } from './date-formats';

describe('Date Formats', () => {
  describe('timeZoneToUTC', () => {
    it('should create valid dates', () => {
      // Basic test to ensure no invalid date errors
      const result = timeZoneToUTC(2025, 5, 1);
      expect(result).toBeInstanceOf(Date);
      expect(isNaN(result.getTime())).toBe(false);
    });

    it('should convert Berlin summer time to UTC correctly', () => {
      // 2025-08-01 00:00 Berlin time should be 2025-07-31 22:00 UTC (CEST = UTC+2)
      const result = timeZoneToUTC(2025, 7, 1);
      expect(result.toISOString()).toBe('2025-07-31T22:00:00.000Z');
    });

    it('should convert Berlin winter time to UTC correctly', () => {
      // 2025-01-01 00:00 Berlin time should be 2024-12-31 23:00 UTC (CET = UTC+1)
      const result = timeZoneToUTC(2025, 0, 1);
      expect(result.toISOString()).toBe('2024-12-31T23:00:00.000Z');
    });

    it('should handle end of day correctly in summer time', () => {
      // 2025-08-01 23:59:59.999 Berlin time should be 2025-08-01 21:59:59.999 UTC (CEST = UTC+2)
      const result = timeZoneToUTC(2025, 7, 1, true);
      expect(result.toISOString()).toBe('2025-08-01T21:59:59.999Z');
    });

    it('should handle end of day correctly in winter time', () => {
      // 2025-01-01 23:59:59.999 Berlin time should be 2025-01-01 22:59:59.999 UTC (CET = UTC+1)
      const result = timeZoneToUTC(2025, 0, 1, true);
      expect(result.toISOString()).toBe('2025-01-01T22:59:59.999Z');
    });
  });
});
