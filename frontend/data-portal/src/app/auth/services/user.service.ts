/**
 * User management service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { httpResource } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { ConfigService } from '@app/shared/services/config.service';
import { RegisteredUser, RoleNames } from '../models/user';

/**
 * Display user interface with additional properties for template use
 */
export interface DisplayUser extends RegisteredUser {
  displayName: string;
  roleNames: string[];
  sortName: string;
}

/**
 * Service for managing users in the GHGA Data Portal.
 * This service handles fetching and managing user data for data stewards.
 */
@Injectable()
export class UserService {
  #config = inject(ConfigService);

  #authUrl = this.#config.authUrl;
  #usersUrl = `${this.#authUrl}/users`;

  /**
   * Creates a sortable name format by moving the last non-abbreviated word to front
   * and optionally adding title at the end
   * @param name - the user's full name
   * @param title - optional academic title
   * @returns formatted sort name (e.g., "Doe, John" or "Slate, Jeffrey Spencer Sr., Prof.")
   */
  #createSortName(name: string, title?: string): string {
    const words = name.trim().split(/\s+/);

    if (words.length === 1) {
      // Single name, just return as is with optional title
      return title ? `${name}, ${title}` : name;
    }

    // Find the last non-abbreviated word (not ending with a period and longer than 2 chars)
    let lastNameIndex = -1;
    for (let i = words.length - 1; i >= 0; i--) {
      const word = words[i];
      if (!word.endsWith('.') && word.length > 2) {
        lastNameIndex = i;
        break;
      }
    }

    // If no suitable last name found, use the last word
    if (lastNameIndex === -1) {
      lastNameIndex = words.length - 1;
    }

    const lastName = words[lastNameIndex];
    const beforeLastName = words.slice(0, lastNameIndex);
    const afterLastName = words.slice(lastNameIndex + 1);

    // Construct the sort name: "LastName, FirstName Middle Suffix"
    const restOfName = [...beforeLastName, ...afterLastName].join(' ');
    let sortName = restOfName ? `${lastName}, ${restOfName}` : lastName;

    // Add title at the end if present
    if (title) {
      sortName += `, ${title}`;
    }

    return sortName;
  }

  /**
   * Creates a display user with computed properties for UI consumption
   * @param user - raw user from backend
   * @returns display user with additional display properties
   */
  #createDisplayUser(user: RegisteredUser): DisplayUser {
    return {
      ...user,
      displayName: user.title ? `${user.title} ${user.name}` : user.name,
      roleNames: user.roles.map(
        (role) => RoleNames[role as keyof typeof RoleNames] || role,
      ),
      sortName: this.#createSortName(user.name, user.title || undefined),
    };
  }

  /**
   * Resource for loading all users with display properties.
   * Automatically loads when the service is instantiated and transforms
   * raw user data to include computed display properties.
   * Note: We do the filtering currently only on the client side,
   * but in principle we can also do some filtering on the server.
   */
  users = httpResource<DisplayUser[]>(() => ({ url: this.#usersUrl }), {
    parse: (rawUsers: unknown) =>
      (rawUsers as RegisteredUser[]).map((user) => this.#createDisplayUser(user)),
    defaultValue: [],
  });
}
