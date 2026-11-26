/**
 * This pipe cleans up the publication DOI
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';

/**
 * Pipe to validate and clean the publication DOI
 */
@Pipe({
  name: 'validateDOI',
})
export class ValidateDOI implements PipeTransform {
  /**
   * The transform method executes the business logic of the Pipe
   * @param doi DOI string, absent when the publication has none
   * @returns A clean DOI string (e.g. 10.1000/123), or an empty string.
   */
  transform(doi: string | null | undefined): string {
    if (!doi) {
      return '';
    }
    let cleanDOI = doi.trim();
    cleanDOI = cleanDOI.replace(/https?:\/\/.*?doi\.org\//i, '');
    cleanDOI = cleanDOI.replace(/doi:\s*/i, '');
    if (!cleanDOI.startsWith('10.')) {
      return '';
    }
    return cleanDOI;
  }
}
