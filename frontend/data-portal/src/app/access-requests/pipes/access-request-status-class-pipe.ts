/**
 * This pipe takes an access request status and returns a specific class to use
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';
import {
  AccessRequestStatus,
  AccessRequestStatusClass,
} from '../models/access-requests';

/**
 * This pipe is used to provide status-specific classes for access request.
 */
@Pipe({
  name: 'AccessRequestStatusClassPipe',
})
export class AccessRequestStatusClassPipe implements PipeTransform {
  /**
   * This method will return a class based on the access request status provided
   * @param status The access request status to process
   * @returns The class based on the status of the access request
   */
  transform(status: AccessRequestStatus | undefined): string {
    return status ? AccessRequestStatusClass[status] : '';
  }
}
