/**
 * This pipe takes any string and shortens it to the first seven characters plus an ellipsis at the end.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';

/**
 * This pipe is used to shorten a string to its first seven characters plus an ellipsis at the end.
 */
@Pipe({
  name: 'truncateString',
})
export class TruncateString implements PipeTransform {
  /**
   * The transform method executes the business logic of the Pipe
   * @param str The string to shorten
   * @param size The number of characters from the original string to return (excluding ellipses)
   * @returns The shortened string
   */
  transform(str: string, size: number = 7): string {
    if (str.length > size) return str.substring(0, size) + '…';
    else return str;
  }
}
