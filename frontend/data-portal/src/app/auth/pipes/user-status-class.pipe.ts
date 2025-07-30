/**
 * This pipe takes a user status and returns a specific class for styling
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';
import { UserStatus } from '../models/user';

/**
 * Mapping of user status to CSS classes
 */
export const UserStatusClass: {
  [K in UserStatus]: string;
} = {
  active: 'text-success',
  inactive: 'text-error',
};

/**
 * This pipe is used to provide status-specific classes for users.
 */
@Pipe({
  name: 'UserStatusClassPipe',
})
export class UserStatusClassPipe implements PipeTransform {
  /**
   * This method will return a class based on the user status provided
   * @param status The user status to process
   * @returns The CSS class based on the user status
   */
  transform(status: UserStatus): string {
    return UserStatusClass[status];
  }
}
