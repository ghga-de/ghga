/**
 * This pipe takes a js Date object or a string and transforms it to an ISO-formatted date.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';

/**
 * This pipe can be used to display a year as a string from a Date object.
 */
@Pipe({
  name: 'isoDate',
})
export class isoDatePipe implements PipeTransform {
  /**
   * The transform method executes the business logic of the Pipe
   * @param date The js Date object or string of the date to convert to an ISO-formatted date
   * @returns the ISO-formatted date as a string
   */
  transform(date: Date | string): string {
    if (typeof date === 'string') date = new Date(date);
    if (date instanceof Date && !isNaN(date.getTime())) {
      return date.toISOString().substring(0, 10);
    }
    return '';
  }
}
