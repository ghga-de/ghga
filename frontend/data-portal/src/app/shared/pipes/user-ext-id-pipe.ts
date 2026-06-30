/**
 * Pipe to format user external IDs by removing default suffix and optionally shortening
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';

const DEFAULT_EXT_ID_SUFFIX = '@lifescience-ri.eu';

/**
 * UserExtId Pipe
 *
 * Removes the default external ID suffix and optionally shortens the result
 */
@Pipe({ name: 'userExtId' })
export class UserExtIdPipe implements PipeTransform {
  /**
   * Transform the external ID by removing default suffix and optionally shortening
   * @param value - the external ID to transform
   * @param maxChars - optional maximum number of characters to display
   * @returns formatted external ID
   */
  transform(value: string | null | undefined, maxChars?: number): string {
    if (!value) {
      return '';
    }

    // Remove the default suffix if present
    value = value.endsWith(DEFAULT_EXT_ID_SUFFIX)
      ? value.slice(0, -DEFAULT_EXT_ID_SUFFIX.length)
      : value;

    // Optionally shorten the result
    if (maxChars && value.length > maxChars) {
      value = value.slice(0, maxChars) + '...';
    }

    return value;
  }
}
