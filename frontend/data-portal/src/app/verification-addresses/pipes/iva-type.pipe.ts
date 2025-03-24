/**
 * This pipe takes an IVA type and returns an object with the display name, type and value string, and icon for the specified type
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';
import { IvaType, IvaTypeIcon, IvaTypePrintable } from '../models/iva';

/**
 * This pipe is used to provide type-specific display names and classes for IVAs.
 */
@Pipe({
  name: 'IvaTypePipe',
})
export class IvaTypePipe implements PipeTransform {
  /**
   * This method will return an object containing a display name, type and value string, and icon for the IVA type provided
   * @param type The IVA type to process
   * @param value The value of the IVA to use
   * @returns The display name and class based on the type of the IVA type sent in an object of shape { display: string; class: string }
   */
  transform(
    type: IvaType,
    value?: string | undefined,
  ): { display: string; typeAndValue: string; icon: string } {
    if (!value) {
      value = '';
    }
    return {
      display: IvaTypePrintable[type],
      typeAndValue: `${IvaTypePrintable[type]}: ${value}`,
      icon: IvaTypeIcon[type],
    };
  }
}
