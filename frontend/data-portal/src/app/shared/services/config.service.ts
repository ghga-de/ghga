/**
 * The configuration service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Injectable } from '@angular/core';

interface Config {
  base_url: string;
  ars_url: string;
  auth_url: string;
  dins_url: string;
  mass_url: string;
  metldata_url: string;
  wps_url: string;
  wkvs_url: string | null;
  ribbon_text: string;
  max_facet_options: number;
  access_upfront_max_days: number;
  access_grant_min_days: number;
  access_grant_max_days: number;
  default_access_duration_days: number;
  oidc_client_id: string;
  oidc_redirect_url: string;
  oidc_scope: string;
  oidc_authority_url: string;
  oidc_authorization_url: string | null;
  oidc_token_url: string | null;
  oidc_userinfo_url: string | null;
  oidc_use_discovery: boolean;
  oidc_account_url: string;
  mock_api: boolean;
  mock_oidc: boolean;
  umami_url: string | null;
  umami_website_id: string | null;
  helpdesk_url: string;
  helpdesk_ticket_url: string;
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
@Injectable({ providedIn: 'root' })
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
   * Gets the access request service URL from the config object.
   * @returns the access request service URL sans end slash
   */
  get arsUrl(): string {
    return sansEndSlash(this.#config.ars_url);
  }

  /**
   * Gets the auth service URL from the config object.
   * @returns the auth service URL sans end slash
   */
  get authUrl(): string {
    return sansEndSlash(this.#config.auth_url);
  }

  /**
   * Gets the dataset information service URL from the config object.
   * @returns the dataset information service URL sans end slash
   */
  get dinsUrl(): string {
    return sansEndSlash(this.#config.dins_url);
  }

  /**
   * Gets the MASS URL from the config object.
   * @returns the MASS URL sans end slash
   */
  get massUrl(): string {
    return sansEndSlash(this.#config.mass_url);
  }

  /**
   * Gets the metldata service URL from the config object
   * @returns the metldata service URL sans slash
   */
  get metldataUrl(): string {
    return sansEndSlash(this.#config.metldata_url);
  }

  /**
   * Gets the WPS URL from the config object.
   * @returns the WPS URL sans end slash
   */
  get wpsUrl(): string {
    return sansEndSlash(this.#config.wps_url);
  }

  /**
   * Gets the URL of the well-known value service
   * @returns the URL of the well-known value service or the default '/.well-known if not configured
   */
  get wkvsUrl(): string {
    return this.#config.wkvs_url || '/.well-known';
  }

  /**
   * Gets the text to be shown in the corner ribbon
   * @returns the string with the version of the application
   */
  get ribbonText(): string {
    return this.#config.ribbon_text;
  }

  /**
   * Get the maximum number of facet options to be shown
   * @returns the maximum number of options
   */
  get maxFacetOptions(): number {
    return this.#config.max_facet_options;
  }

  /**
   * Gets the maximum number of days between now and the start of an access grant.
   * @returns the number of days
   */
  get accessUpfrontMaxDays(): number {
    return this.#config.access_upfront_max_days;
  }

  /**
   * Gets the minimum duration of an access grant
   * @returns the number of days
   */
  get accessGrantMinDays(): number {
    return this.#config.access_grant_min_days;
  }

  /**
   * Gets the maximum duration of an access grant
   * @returns the number of days
   */
  get accessGrantMaxDays(): number {
    return this.#config.access_grant_max_days;
  }

  /**
   * Gets the default number of days for an access grant
   * @returns the number of days
   */
  get defaultAccessDurationDays(): number {
    return this.#config.default_access_duration_days;
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
   * @returns the OIDC authorization URL or null (use oidcUseDiscovery)
   */
  get oidcAuthorizationUrl(): string | null {
    const url = this.#config.oidc_authorization_url;
    return url ? new URL(url, withEndSlash(this.oidcAuthorityUrl)).href : null;
  }

  /**
   * Gets the OIDC token URL from the config object
   * @returns the OIDC token URL or null (use oidcUseDiscovery)
   */
  get oidcTokenUrl(): string | null {
    const url = this.#config.oidc_token_url;
    return url ? new URL(url, withEndSlash(this.oidcAuthorityUrl)).href : null;
  }

  /**
   * Gets the OIDC userinfo URL from the config object
   * @returns the OIDC userinfo URL
   */
  get oidcUserInfoUrl(): string | null {
    const url = this.#config.oidc_userinfo_url;
    return url ? new URL(url, withEndSlash(this.oidcAuthorityUrl)).href : null;
  }

  /**
   * Checks whether OIDC discovery shall be used
   * @returns true if OIDC discovery shall be used
   */
  get oidcUseDiscovery(): boolean {
    return this.#config.oidc_use_discovery;
  }

  /**
   * Gets the URL for managing the OIDC provider account
   * @returns the external URL to manage the account
   */
  get oidcAccountUrl(): string {
    return this.#config.oidc_account_url;
  }

  /**
   * Gets the URL of the Umami backend that the analytics data will be reported to
   * @returns the URL of the Umami backend or null if not configured
   */
  get umami_url(): string | null {
    return this.#config.umami_url || null;
  }

  /**
   * Gets the key used to identify the website in the Umami backend
   * @returns the website ID or null if not configured
   */
  get umami_website_id(): string | null {
    return this.#config.umami_website_id || null;
  }

  /**
   * Gets the base URL of the Helpdesk portal for data stewards
   * @returns the base URL of the Helpdesk
   */
  get helpdeskUrl(): string {
    return this.#config.helpdesk_url;
  }

  /**
   * Gets the base URL for Helpdesk tickets
   * @returns the base URL for Helpdesk tickets
   */
  get helpdeskTicketUrl(): string {
    const url = this.#config.helpdesk_ticket_url;
    return new URL(url, withEndSlash(this.helpdeskUrl)).href;
  }
}
