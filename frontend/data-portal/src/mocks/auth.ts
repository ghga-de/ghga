/**
 * Mock authentication flow
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { LoginState, User } from '@app/auth/models/user';
import { http, HttpResponse } from 'msw';

/**
 * The following session state will be set after the fake login.
 * Set this to 'NeedsRegistration' to test the full registration and 2FA flow.
 * Set this to 'Authenticated' to immediately have a fully authenticated user.
 */
const INITIAL_LOGIN_STATE = 'Authenticated' as LoginState;

/**
 * The TOTP code that should be considered valid when testing
 */
const VALID_TOTP_CODE = '123456';

const CONFIG = window.config;
const BASE_URL = new URL(CONFIG.base_url) + '/';
const AUTH_URL = new URL(CONFIG.auth_url, BASE_URL).href + '/';
const LOGIN_URL = new URL('rpc/login', AUTH_URL).href;
const LOGOUT_URL = new URL('rpc/logout', AUTH_URL).href;
const TOTP_TOKEN_URL = new URL('totp-token', AUTH_URL).href;
const TOTP_VALIDATION_URL = new URL('rpc/verify-totp', AUTH_URL).href;
const USERS_URL = new URL('users', AUTH_URL).href;
const OIDC_AUTHORITY_URL = CONFIG.oidc_authority_url;
const OIDC_CONFIG_PATH = '.well-known/openid-configuration';
const OIDC_CONFIG_URL = new URL(OIDC_CONFIG_PATH, OIDC_AUTHORITY_URL).href;
const OIDC_SCOPE = CONFIG.oidc_scope;
const OIDC_CLIENT_ID = CONFIG.oidc_client_id;
const OIDC_USER_KEY = `oidc.user:${OIDC_AUTHORITY_URL}:${OIDC_CLIENT_ID}`;

/**
 * The dummy user object for MSW
 */
export const user: User = {
  id: INITIAL_LOGIN_STATE === 'NeedsRegistration' ? undefined : 'j.doe@ghga.de',
  ext_id: 'aacaffeecaffeecaffeecaffeecaffeecaffeeaad@lifescience-ri.eu',
  name: 'John Doe',
  title: 'Dr.',
  full_name: 'Dr. John Doe',
  email: 'j.jdoe@home.org',
  role: 'data_steward',
  state: INITIAL_LOGIN_STATE, // the state after login
  csrf: 'mock-csrf-token',
  timeout: 3600,
  extends: 7200,
};

/**
 * Simulate login with dummy user via OIDC
 */
export function setOidcUser() {
  const iat = Math.round(new Date().getMilliseconds() / 1000);
  const exp = iat + 12 * 60 * 60;
  const userObj = {
    id_token: null,
    session_state: null,
    access_token: 'test123',
    token_type: 'Bearer',
    scope: OIDC_SCOPE,
    role: user.role,
    profile: {
      sub: user.ext_id,
      sid: null,
      scope: OIDC_SCOPE.split(' '),
      client_id: OIDC_CLIENT_ID,
      iss: OIDC_AUTHORITY_URL,
      iat,
      exp,
      aud: [OIDC_CLIENT_ID],
      name: user.name,
      given_name: user.name.split(' ')[0],
      family_name: user.name.split(' ')[1],
      email: user.email,
    },
    expires_at: exp,
  };
  sessionStorage.setItem(OIDC_USER_KEY, JSON.stringify(userObj));
}

/**
 * Remove the dummy user set for OIDC
 */
export function clearOidcUser() {
  sessionStorage.removeItem(OIDC_USER_KEY);
}

/**
 * Remove the session cookie (to mock logout properly)
 */
export function clearSessionCookie() {
  document.cookie = 'session=; SameSite=lax';
}

/**
 * Check if the user has a session cookie (to mock login properly)
 * @returns true if the user has a session cookie
 */
function hasSessionCookie(): boolean {
  const cookie = document.cookie;
  return !!cookie && cookie.includes('session=test-session');
}

/**
 * Get response headers for logged in user
 * @returns the headers for a logged in user or null if not logged in
 */
export function getLoginHeaders(): Record<string, string> | null {
  if (!hasSessionCookie() && !sessionStorage.getItem(OIDC_USER_KEY)) {
    return null;
  }
  return {
    'X-Session': JSON.stringify(user),
    // this should be actually HttpOnly, but this doesn't work with MSW
    'Set-Cookie': 'session=test-session; SameSite=lax',
  };
}

/**
 * MSW handlers for auth endpoints
 */

export const handlers = [
  /**
   * intercept OIDC configuration request and redirect authorization
   */
  http.get(OIDC_CONFIG_URL, () => {
    setOidcUser();
    return HttpResponse.json(
      {
        // let authorization endpoint redirect back to the current page
        authorization_endpoint: window.location.href,
      },
      { status: 200 },
    );
  }),
  /**
   * intercept login request and return session header
   */
  http.post(LOGIN_URL, () => {
    const headers = getLoginHeaders();
    return HttpResponse.json(
      undefined,
      headers ? { status: 204, headers } : { status: 401 },
    );
  }),
  /**
   * intercept logout request
   */
  http.post(LOGOUT_URL, () => {
    clearSessionCookie();
    clearOidcUser();
    return HttpResponse.json(undefined, { status: 204 });
  }),
  /**
   * intercept TOTP token creation request
   */
  http.post(TOTP_TOKEN_URL, () => {
    const userName = user.full_name.replace(' ', '%20');
    const issuer = 'GHGA';
    const secret = 'TEST-TOTP-TOKEN';
    return HttpResponse.json(
      { uri: `otpauth://totp/${issuer}:${userName}?secret=${secret}&issuer=${issuer}` },
      { status: 201 },
    );
  }),
  /**
   * intercept TOTP verification request
   */
  http.post(TOTP_VALIDATION_URL, ({ request }) => {
    // the code is passed in the X-Authorization header in this case
    let token = request.headers.get('X-Authorization') || '';
    if (token.startsWith('Bearer TOTP:')) token = token.substring(12);
    const status = token === VALID_TOTP_CODE ? 204 : 401;
    return HttpResponse.json(undefined, { status });
  }),
  // intercept user creation request
  http.post(USERS_URL, () => {
    user.id = user.id;
    user.state = 'Registered';
    return HttpResponse.json(undefined, { status: 201 });
  }),
];
