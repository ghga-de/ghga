/**
 * This pipe takes a string and splits it into an array of strings based on newlines.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';

/**
 * This pipe splits a string by newline characters or escaped sequences.
 */
@Pipe({
  name: 'splitLines',
})
export class SplitLinesPipe implements PipeTransform {
  /**
   * The transform method executes the business logic of the Pipe
   * @param string The string to split
   * @returns the array of strings separated by newlines
   */
  transform(string: string): string[] {
    return string
      .split(/\r?\n\r?|(?:\\r)?\\n(?:\\r)?/)
      .map((x) => x.trim())
      .filter((x) => x);
  }
}
