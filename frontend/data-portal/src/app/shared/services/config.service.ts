import { Injectable } from '@angular/core';

interface Config {
  base_url: string;
  auth_url: string;
  mass_url: string;
  metldata_url: string;
  oidc_client_id: string;
  oidc_redirect_url: string;
  oidc_scope: string;
  oidc_authority_url: string;
  oidc_authorization_url: string;
  oidc_token_url: string;
  oidc_userinfo_url: string;
  oidc_use_discovery: boolean;
}

declare global {
  interface Window {
    config: Config;
  }
}

/**
 * Removes an end slash to a URL if needed
 * @param url - a URL that might not end with a slash
 * @returns the URL without an end slash
 */
function sansEndSlash(url: string): string {
  return url.endsWith('/') ? url.slice(0, -1) : url;
}

/**
 * Adds an end slash to a URL if needed
 * @param url - a URL that might not end with a slash
 * @returns the URL with an end slash
 */
function withEndSlash(url: string): string {
  return url.endsWith('/') ? url : url + '/';
}

/**
 * The config service provides access to the configuration of the application.
 */
@Injectable({
  providedIn: 'root',
})
export class ConfigService {
  #config: Config;

  /**
   * This constructor initializes the config via the window object
   */
  constructor() {
    this.#config = window.config;
  }
  /**
   * Gets the application base URL from the config object
   * @returns the application base URL sans end slash
   */
  get baseUrl(): string {
    return sansEndSlash(this.#config.base_url);
  }

  /**
   * Gets the auth service URL from the config object.
   * @returns the auth service URL sans end slash
   */
  get authUrl(): string {
    return new URL(this.#config.auth_url, withEndSlash(this.#config.base_url)).href;
  }

  /**
   * Gets the MASS URL from the config object.
   * @returns the MASS URL sans end slash
   */
  get massUrl(): string {
    return new URL(this.#config.mass_url, withEndSlash(this.#config.base_url)).href;
  }

  /**
   * Gets the metldata service URL from the config object
   * @returns the metldata service URL sans slash
   */
  get metldataUrl(): string {
    return new URL(this.#config.metldata_url, withEndSlash(this.#config.base_url)).href;
  }

  /**
   * Gets the OIDC client ID from the config object
   * @returns the OIDC client ID
   */
  get oidcClientId(): string {
    return this.#config.oidc_client_id;
  }

  /**
   * Gets the OIDC redirect URL from the config object
   * @returns the OIDC redirect URL
   */
  get oidcRedirectUrl(): string {
    return new URL(this.#config.oidc_redirect_url, withEndSlash(this.baseUrl)).href;
  }

  /**
   * Gets the OIDC scope from the config object
   * @returns the OIDC scope
   */
  get oidcScope(): string {
    return this.#config.oidc_scope;
  }

  /**
   * Gets the OIDC authority URL from the config object
   * @returns the OIDC authority URL
   */
  get oidcAuthorityUrl(): string {
    return this.#config.oidc_authority_url;
  }

  /**
   * Gets the OIDC authorization URL from the config object
   * @returns the OIDC authorization URL
   */
  get oidcAuthorizationUrl(): string {
    return new URL(
      this.#config.oidc_authorization_url,
      withEndSlash(this.oidcAuthorityUrl),
    ).href;
  }

  /**
   * Gets the OIDC token URL from the config object
   * @returns the OIDC token URL
   */
  get oidcTokenUrl(): string {
    return new URL(this.#config.oidc_token_url, withEndSlash(this.oidcAuthorityUrl))
      .href;
  }

  /**
   * Gets the OIDC userinfo URL from the config object
   * @returns the OIDC userinfo URL
   */
  get oidcUserInfoUrl(): string {
    return new URL(this.#config.oidc_userinfo_url, withEndSlash(this.oidcAuthorityUrl))
      .href;
  }

  /**
   * Checks whether OIDC discovery shall be used
   * @returns true if OIDC discovery shall be used
   */
  get oidcUseDiscovery(): boolean {
    return this.#config.oidc_use_discovery;
  }
}
