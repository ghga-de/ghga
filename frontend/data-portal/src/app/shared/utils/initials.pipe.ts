/**
 * Get initial letters from a person's name
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';

/**
 * This pipe can be used to display the initials of a person's name.
 * @param name the name of a person
 * @returns the initials of the person
 */
@Pipe({
  name: 'initials',
})
export class InitialsPipe implements PipeTransform {
  /**
   * Transform the given name to its initials
   * Note: It is assumed that the name does not include a title or other prefixes
   * @param name The name of a person or null or undefined if it is not known
   * @returns the initials of the person or null if the name is not known
   */
  transform(name: string | null | undefined): string | null {
    if (!name) return null;
    const nameParts = name.split(/\s+/).filter((part) => part);
    let initials = '';
    if (nameParts.length) {
      initials += nameParts[0].charAt(0).toUpperCase();
      if (nameParts.length > 1) {
        initials += nameParts[nameParts.length - 1].charAt(0).toUpperCase();
      }
    }
    return initials || null;
  }
}
