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
 * User session interface
 *
 * Contains all data describing the user and the user session.
 *
 * Note that this is different from the low-level oidcUser object,
 * which does not contain the user data from the backend.
 */
export interface User extends UserRegisteredData {
  id?: string;
  full_name: string;
  state: LoginState;
  role?: string;
  csrf: string;
  timeout?: number;
  extends?: number;
}
