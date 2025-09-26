/**
 * This pipe takes an IVA type and returns an object with the display name and icon for the specified type
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';
import { IvaType, IvaTypeIcon, IvaTypePrintable } from '../models/iva';

/**
 * This pipe is used to provide type-specific display names and icons for IVAs.
 */
@Pipe({ name: 'IvaTypePipe' })
export class IvaTypePipe implements PipeTransform {
  /**
   * This method will return an object containing a display name and icon for the IVA type provided
   * @param type The IVA type to process
   * @returns The display name and icon based on the given IVA type
   */
  transform(type: IvaType): { name: string; icon: string } {
    return {
      name: IvaTypePrintable[type] ?? (type || 'None'),
      icon: IvaTypeIcon[type] ?? 'warning',
    };
  }
}
