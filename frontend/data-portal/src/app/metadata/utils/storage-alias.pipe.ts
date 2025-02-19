/**
 * This pipe takes the storage alias
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';

const STORAGE_LOCATIONS: { [key: string]: string } = {
  B: 'Berlin',
  DD: 'Dresden',
  HD: 'Heidelberg',
  K: 'Cologne',
  KI: 'Kiel',
  M: 'Munich',
  TUE: 'Tübingen',
};

/**
 * Pipe to convert the storage locations aliases to a human-readable alias
 */
@Pipe({
  name: 'storageAlias',
})
export class StorageAlias implements PipeTransform {
  /**
   * The transform method executes the business logic of the Pipe
   * @param storageAlias Storage alias
   * @returns Human readable storage location, returns the original string if not known, with the first group of letters separated by a space
   */
  transform(storageAlias: string | null | undefined): string {
    return storageAlias
      ? storageAlias.replace(
          /^[A-Z]+/,
          (m: string) => (STORAGE_LOCATIONS[m] ?? m) + ' ',
        )
      : '';
  }
}
