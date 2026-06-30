/**
 * This pipe takes a number of items and returns an empty string if it is exactly one, or an 's' if it is not.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';

/**
 * This pipe is used to add a final 's' to a word describing a set of items depending on the number of existing items.
 */
@Pipe({
  name: 'addPluralS',
})
export class AddPluralS implements PipeTransform {
  /**
   * This method will get the number of items and returns an s if it is different than 1 (e.g. 1 method vs. 0 methods)
   * @param count The number of elements in the object
   * @returns An s or an empty string, depending on the number of items
   */
  transform(count: number): string {
    if (count === 1) return '';
    return 's';
  }
}
