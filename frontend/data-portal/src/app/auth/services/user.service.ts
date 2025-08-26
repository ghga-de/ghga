/**
 * User management service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient, httpResource } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { ConfigService } from '@app/shared/services/config.service';
import { Observable, tap } from 'rxjs';
import {
  RegisteredUser,
  RegisteredUserFilter,
  RoleNames,
  UserStatus,
} from '../models/user';

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
  #http = inject(HttpClient);

  #authUrl = this.#config.authUrl;
  #usersUrl = `${this.#authUrl}/users`;

  #usersFilter = signal<RegisteredUserFilter | undefined>(undefined);

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

  // signal to load all users
  #loadAll = signal<boolean>(false);

  /**
   * Load all users
   */
  loadUsers(): void {
    console.log('Loading all users');
    this.#loadAll.set(true);
  }

  /**
   * Reload all users' IVAs
   */
  reloadUsers(): void {
    this.users.reload();
  }

  /**
   * The current filter for the list of all users
   */
  usersFilter = computed(() => {
    let filter = this.#usersFilter();
    if (!filter) {
      const filterStr = sessionStorage.getItem('usersFilter');
      if (filterStr) {
        try {
          filter = JSON.parse(filterStr) as RegisteredUserFilter;
        } catch {}
      }
    }
    return (
      filter || {
        idStrings: '',
        roles: undefined,
        status: UserStatus.active,
      }
    );
  });

  /**
   * Set a filter for the list of all Users
   * @param filter - the filter to apply
   */
  setUsersFilter(filter: RegisteredUserFilter): void {
    this.#usersFilter.set(filter);
  }

  /**
   * Resource for loading all users with display properties.
   * Automatically loads when the #loadAll signal is set to true
   * raw user data to include computed display properties.
   * Note: We do the filtering currently only on the client side,
   * but in principle we can also do some filtering on the server.
   */
  users = httpResource<DisplayUser[]>(
    () => (this.#loadAll() ? this.#usersUrl : undefined),
    {
      parse: (rawUsers: unknown) => {
        return (rawUsers as RegisteredUser[]).map((user) =>
          this.#createDisplayUser(user),
        );
      },
      defaultValue: [],
    },
  );

  /**
   * Signal that gets all users filtered by the current filter
   */
  usersFiltered = computed(() => {
    if (this.users.error()) return [];
    let users = this.users.value();
    const filter = this.#usersFilter();
    filter
      ? sessionStorage.setItem('usersFilter', JSON.stringify(filter))
      : sessionStorage.removeItem('usersFilter');
    if (users.length > 0 && filter !== undefined) {
      const idStrings = filter.idStrings.trim().toLowerCase();
      if (idStrings) {
        users = users.filter(
          (user) =>
            user.displayName.toLowerCase().includes(idStrings) ||
            user.email.toLowerCase().includes(idStrings) ||
            user.ext_id.toLowerCase().includes(idStrings),
        );
      }
      if (filter.roles && filter.roles.length) {
        const roles = filter.roles;
        users = users.filter((user) =>
          roles?.some((x) => {
            if (x !== null) {
              return user.roles.includes(x);
            } else {
              return user.roles.length === 0;
            }
          }),
        );
      }
      if (filter.status) {
        users = users.filter((user) => user.status === filter.status);
      }
    }
    return users;
  });

  #userId = signal<string | undefined>(undefined);

  /**
   * Load single user details
   * @param userId ID of the user to load
   */
  loadUser(userId: string) {
    this.#userId.set(userId);
  }

  user = httpResource<DisplayUser>(
    () => (this.#userId() ? `${this.#usersUrl}/${this.#userId()}` : undefined),
    {
      parse: (rawUser: unknown) => this.#createDisplayUser(rawUser as RegisteredUser),
      defaultValue: undefined,
    },
  );

  /**
   * Update the user locally.
   * @param id - the ID of the updated user
   * @param changes - the changes to the user which may be partial
   */
  #updateUserLocally(id: string, changes: any): void {
    if (!this.user.error()) {
      const oldUser = this.user.value();
      if (oldUser && oldUser.id === id) {
        const newUser = { ...oldUser, ...changes };
        this.user.value.set(this.#createDisplayUser(newUser));
      }
    }
    if (!this.users.error()) {
      const oldUser = this.users.value().find((user) => user.id === id);
      if (oldUser) {
        const newUser = { ...oldUser, ...changes };
        const update = (users: DisplayUser[]) =>
          users.map((user) => (user.id === id ? newUser : user));
        this.users.value.set(update(this.users.value()));
      }
    }
  }

  /**
   * Update one or more properties of a user.
   * This can only be done by a data steward.
   * This method also updates the local state if the modification was successful.
   * @param id - the user ID
   * @param changes - the changes to the user which may be partial
   * @returns An observable that emits null when the request has been processed
   */
  updateUser(id: string, changes: Partial<DisplayUser>): Observable<null> {
    return this.#http
      .patch<null>(`${this.#usersUrl}/${id}`, changes)
      .pipe(tap(() => this.#updateUserLocally(id, changes)));
  }

  /**
   * Remove the user locally.
   * @param id - the ID of the user to remove
   */
  #removeUserLocally(id: string): void {
    if (this.users.error()) return;
    const oldUser = this.users.value().find((user) => user.id === id);
    if (oldUser) {
      const newUser = { ...oldUser };
      const update = (users: DisplayUser[]) =>
        users.map((user) => (user.id === id ? newUser : user));
      this.users.value.set(update(this.users.value()));
    }
  }

  /**
   * Delete a user.
   * This can only be done by a data steward.
   * This method also updates the local state if the modification was successful.
   * @param id - the user ID
   * @returns An observable that emits null when the request has been processed
   */
  deleteUser(id: string): Observable<null> {
    return this.#http
      .delete<null>(`${this.#usersUrl}/${id}`)
      .pipe(tap(() => this.#removeUserLocally(id)));
  }
}
