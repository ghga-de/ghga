/**
 * This pipe takes a number of bytes and transforms it into a human-readable string.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';

/**
 * Binary prefixes for bytes (base 1024).
 * Using 2^10 as multiplier with official binary prefixes (KiB, MiB, GiB, etc.)
 */
const MULTIPLIER = 1024;
const PREFIXES = ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'];

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
   * @param fractionDigits Fixed number of decimals, so that values in a column
   *   line up at the decimal point; up to two decimals without trailing zeros
   *   if not given. Plain bytes never get decimals.
   * @returns Human readable size string, e.g. 5 KiB
   */
  transform(bytes: number | null | undefined, fractionDigits?: number): string {
    if (bytes === null || bytes === undefined) return '';
    const parsedBytes = PREFIXES.flatMap((prefix, index) => {
      const calculatedVal = bytes / Math.pow(MULTIPLIER, index);
      const value =
        fractionDigits === undefined || !prefix
          ? String(Math.round(calculatedVal * 100) / 100)
          : calculatedVal.toFixed(fractionDigits);
      // Check the rounded value, so that 999.95 KiB moves on to 1.0 MiB
      // instead of showing as 1000.0 KiB
      if (Number(value) < 1000 && calculatedVal >= 0.1) {
        return value + `\u00A0${prefix}${prefix ? 'i' : ''}B`;
      } else return null;
    });
    return parsedBytes.find((parsing) => parsing !== null) || String(bytes) + '\u00A0B';
  }
}
