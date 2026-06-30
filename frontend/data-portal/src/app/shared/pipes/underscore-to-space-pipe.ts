/**
 * This pipe takes a string and replaces all underscores by spaces to make it look nicer in the ui.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';

/**
 * This pipe can be used to display a string that contains underscores looking a bit more readable.
 */
@Pipe({
  name: 'underscoreToSpace',
})
export class UnderscoreToSpace implements PipeTransform {
  /**
   * The transform method executes the business logic of the Pipe
   * @param input A string that possibly contains underscores
   * @returns The string with all underscores replaced by spaces
   */
  transform(input?: string): string {
    if (input) {
      return input.replaceAll('_', ' ');
    }
    return '';
  }
}
