/**
 * User related models
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

/**
 * All possible states of the user session
 */
export type LoginState =
  | 'Undetermined' // the state is not yet determined
  | 'LoggedOut' // the user is logged out
  | 'LoggedIn' // the user is logged in with first factor
  | 'NeedsRegistration' // the user needs to register (backend state)
  | 'NeedsReRegistration' // the user needs to re-register (backend state)
  | 'Registered' // the user is registered (backend state)
  | 'NeedsTotpToken' // the user needs to set up TOTP (frontend state only)
  | 'LostTotpToken' // the user has lost the TOTP token (frontend state only)
  | 'NewTotpToken' // a new TOTP token has just been created (backend state)
  | 'HasTotpToken' // a TOTP token exists but not yet authenticated (backend state)
  | 'Authenticated'; // user is fully authenticated with second factor (backend state)

/**
 * All possible academic titles
 */
export type AcademicTitle = null | 'Dr.' | 'Prof.';

/**
 * Basic data of a user
 */
export interface UserBasicData {
  name: string;
  title?: AcademicTitle;
  email: string;
}

/**
 * Basic data of a registered user
 */
export interface UserRegisteredData extends UserBasicData {
  ext_id: string;
}

/**
 * Type alias for user roles (the enum keys which are strings)
 */
export type UserRole = keyof typeof RoleNames;

/**
 * All possible user states
 */
export enum UserStatus {
  active = 'active',
  inactive = 'inactive',
}

/**
 * Data of a fully registered user interface
 */
export interface RegisteredUser extends UserRegisteredData {
  id: string;
  roles: UserRole[];
  status: UserStatus;
  registration_date: string; // ISO date string
  status_change?: {
    previous: string;
    by: string;
    context: string;
    change_date: string;
  };
}

/**
 * User session interface
 *
 * Contains all data describing the user and the user session.
 *
 * Note that this is different from the low-level oidcUser object,
 * which does not contain the user data from the backend.
 */
export interface UserSession extends UserRegisteredData {
  id?: string;
  full_name: string;
  state: LoginState;
  roles: UserRole[];
  csrf: string;
  timeout?: number;
  extends?: number;
}

/**
 * Supported roles with readable names
 */
export enum RoleNames {
  data_steward = 'Data Steward',
}

/**
 * Interface for filter object for registered user
 */
export interface RegisteredUserFilter {
  idStrings: string;
  roles: (UserRole | null)[] | undefined;
  status: UserStatus | undefined;
}
