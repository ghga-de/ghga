/**
 * Improved DatePipe that supports IANA time zone names.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe as CommonDatePipe } from '@angular/common';
import { inject, Pipe, PipeTransform } from '@angular/core';

/**
 * This is an improved DatePipe that also supports IANA time zone names.
 *
 * The existing Angular DatePipe currently only supports time zone offsets
 * such as '+0100', but not abbreviations or IANA time zone names.
 *
 * This custom DatePipe extends the functionality by allowing
 * the use of IANA time zone names like 'Europe/Berlin'.
 *
 * Please use either time zone offsets or IANA time zone names, but do not
 * use time zone abbreviations such as 'CET', as they can be ambiguous and
 * lead to incorrect results depending on the runtime environment.
 *
 * We assume the Intl API is supported since all modern browsers have it.
 * If it is not supported, it behaves like the original DatePipe.
 */
@Pipe({ name: 'date' })
export class DatePipe implements PipeTransform {
  #datePipe = inject(CommonDatePipe);

  /**
   * Transforms a date value according to the specified parameters.
   * @param value - the date value to transform
   * @param format - the date format to use (optional)
   * @param timezone - the timezone to use (optional)
   * @param locale - the locale to use (optional)
   * @returns the formatted date
   */
  transform(
    value: Date | string | number | null | undefined,
    format?: string,
    timezone?: string,
    locale?: string,
  ): string | null {
    // If the timezone is specified as an IANA time zone name,
    // convert the time zone to an offset using the Intl API.
    if (timezone && timezone.includes('/')) {
      timezone = this.#convertTimezoneToOffset(value, timezone);
    }
    return this.#datePipe.transform(value, format, timezone, locale);
  }

  /**
   * Converts a timezone name to an offset using the Intl API
   * @param value The date value to use for timezone calculation
   * @param timezone The IANA timezone name to convert
   * @returns The timezone offset in +HHMM or -HHMM format
   */
  #convertTimezoneToOffset(
    value: Date | string | number | null | undefined,
    timezone: string,
  ): string {
    if (!value) {
      return timezone;
    }
    try {
      const date = new Date(value);
      if (isNaN(date.getTime())) {
        return timezone;
      }
      // Use Intl API to get offset in +01:00 format
      const formatter = new Intl.DateTimeFormat('en', {
        timeZone: timezone,
        timeZoneName: 'shortOffset',
      });
      const parts = formatter.formatToParts(date);
      const offsetPart = parts.find((part) => part.type === 'timeZoneName');
      if (offsetPart?.value) {
        // Convert "+01:00" to "+0100" format
        return offsetPart.value.replace(':', '');
      }
      return timezone;
    } catch {
      return timezone;
    }
  }
}
