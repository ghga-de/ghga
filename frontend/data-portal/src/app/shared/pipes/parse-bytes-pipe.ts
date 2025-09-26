/**
 * This pipe takes a number of bytes and transforms it into a human-readable string.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';

/**
 * Note: Using 2^10 as multiplier we should strictly speaking also use
 * the new binary prefixes. But many uses are not familiar with these.
 */
const MULTIPLIER = 1024;
const PREFIXES = ['', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'];

/**
 * Pipe to convert number of bytes to a human-readable format
 */
@Pipe({
  name: 'parseBytes',
})
export class ParseBytes implements PipeTransform {
  /**
   * This function converts a number of bytes to a human-readable string
   * @param bytes Bytes as number
   * @returns Human readable size string, e.g. 5 kB
   */
  transform(bytes: number | null | undefined): string {
    if (bytes === null || bytes === undefined) return '';
    let parsedBytes = PREFIXES.flatMap((prefix, index) => {
      let calculatedVal = bytes / Math.pow(MULTIPLIER, index);
      if (calculatedVal < 1000 && calculatedVal >= 0.1) {
        return String(Math.round(calculatedVal * 100) / 100) + `\u00A0${prefix}B`;
      } else return null;
    });
    return parsedBytes.find((parsing) => parsing !== null) || String(bytes) + '\u00A0B';
  }
}
