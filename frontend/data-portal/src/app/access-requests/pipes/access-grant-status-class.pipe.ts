/**
 * This pipe takes an access grant status and returns a specific class to use
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';
import { AccessGrantStatus, AccessGrantStatusClass } from '../models/access-requests';

/**
 * This pipe is used to provide status-specific classes for access grants.
 */
@Pipe({
  name: 'AccessGrantStatusClassPipe',
})
export class AccessGrantStatusClassPipe implements PipeTransform {
  /**
   * This method will return a class based on the access grant status provided
   * @param status The access grant status to process
   * @returns The class based on the status of the access grant
   */
  transform(status: AccessGrantStatus | undefined): string {
    return status ? AccessGrantStatusClass[status] : '';
  }
}
