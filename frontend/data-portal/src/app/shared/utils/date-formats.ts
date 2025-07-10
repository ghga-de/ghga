/**
 * Date formats used throughout the application.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { MatDateFormats } from '@angular/material/core';
import { enGB } from 'date-fns/locale';

export const DEFAULT_DATE_LOCALE = enGB;

export const DEFAULT_TIME_ZONE = 'Europe/Berlin';

export const DEFAULT_DATE_OUTPUT_FORMAT = 'yyyy-MM-dd';
export const DEFAULT_DATE_INPUT_FORMAT = 'yyyy-MM-dd';
export const FRIENDLY_DATE_FORMAT = 'd MMMM y';
export const DATE_INPUT_FORMAT_HINT = 'YYYY-MM-DD';

export const DEFAULT_DATE_FORMATS: MatDateFormats = {
  parse: {
    dateInput: [
      'yyyy-MM-dd',
      'dd.MM.yyyy',
      'dd/MM/yyyy',
      'd.M.yyyy',
      'd/M/yyyy',
      'dd.M.yyyy',
      'dd/M/yyyy',
      'd.MM.yyyy',
      'd/MM/yyyy',
    ],
  },
  display: {
    dateInput: DEFAULT_DATE_INPUT_FORMAT,
    monthYearLabel: 'MMM yyyy',
    dateA11yLabel: 'LL',
    monthYearA11yLabel: 'MMMM yyyy',
  },
};

/**
 * Create a UTC Date from a local time in the given IANA time zone
 * @param year - the year
 * @param month - the month (0-based, e.g. January = 0)
 * @param day - the day of the month
 * @param end - whether we want the time at the end of the day (default false)
 * @param timeZone - the IANA timezone name
 * @returns the Date in UTC
 */
export function timeZoneToUTC(
  year: number,
  month: number,
  day: number,
  end: boolean = false,
  timeZone: string = DEFAULT_TIME_ZONE,
): Date {
  const [hour, minute, second, ms] = end ? [23, 59, 59, 999] : [0, 0, 0, 0];
  const utcDate = new Date(Date.UTC(year, month, day, hour, minute, second, ms));
  const tzOptions: Intl.DateTimeFormatOptions = {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  };
  const tzFormatter = new Intl.DateTimeFormat('de-DE', tzOptions);
  const tzString = tzFormatter.format(utcDate); // e.g. "01.08.2025, 02:00:00"
  const [datePart, timePart] = tzString.split(', ');
  const [tzHour, tzMinute, tzSecond] = timePart.split(':').map(Number);
  const [tzDay, tzMonth, tzYear] = datePart.split('.').map(Number);
  const tzAsUtc = new Date(
    Date.UTC(tzYear, tzMonth - 1, tzDay, tzHour, tzMinute, tzSecond, ms),
  );
  const offset = utcDate.getTime() - tzAsUtc.getTime();
  return new Date(utcDate.getTime() + offset);
}
