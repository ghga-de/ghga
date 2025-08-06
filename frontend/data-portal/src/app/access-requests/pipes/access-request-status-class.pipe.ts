/**
 * This pipe takes an access request status and returns a specific class or classes to use
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';
import {
  AccessGrantStatus,
  AccessRequestAndGrantStatusClass,
  AccessRequestStatus,
} from '../models/access-requests';

/**
 * This pipe is used to provide status-specific classes for access request.
 */
@Pipe({
  name: 'AccessRequestAndGrantStatusClassPipe',
})
export class AccessRequestAndGrantStatusClassPipe implements PipeTransform {
  /**
   * This method will return a class or set of classes based on the access request status provided
   * @param status The access request status to process
   * @returns The class based on the status of the access request status sent
   */
  transform(status: AccessRequestStatus | AccessGrantStatus): string {
    return AccessRequestAndGrantStatusClass[status];
  }
}
