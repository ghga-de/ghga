/**
 * This pipe takes an IVA state and returns an object with the display name and text class for the specified state
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';
import {
  IvaState,
  IvaStateClass,
  IvaStatePrintable,
} from '@app/verification-addresses/models/iva';

/**
 * This pipe is used to provide state-specific display names and classes for IVAs.
 */
@Pipe({
  name: 'IvaStatePipe',
})
export class IvaStatePipe implements PipeTransform {
  /**
   * This method will return an object containing a display name and classes based on the IVA state provided
   * @param state The IVA state to process
   * @returns The display name and class based on the state of the IVA state sent in an object of shape { display: string; class: string }
   */
  transform(state: IvaState): { display: string; class: string } {
    return { display: IvaStatePrintable[state], class: IvaStateClass[state] };
  }
}
