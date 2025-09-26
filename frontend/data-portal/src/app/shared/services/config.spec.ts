/**
 * Test the config service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { TestBed } from '@angular/core/testing';

import { ConfigService } from './config';

const mockConfig = {
  base_url: 'https://portal.test',
  ars_url: 'test/ars',
  auth_url: '/test/auth',
  dins_url: '/test/dins',
  mass_url: '/test/mass',
  metldata_url: '/test/metldata',
  rts_url: '/test/rts',
  wps_url: '/test/wps',
  wkvs_url: null,
  ribbon_text: 'Test ribbon text',
  max_facet_options: 12,
  access_upfront_max_days: 180,
  access_grant_min_days: 7,
  access_grant_max_days: 730,
  access_grant_max_extend: 5,
  default_access_duration_days: 365,
  oidc_client_id: 'test-oidc-client-id',
  oidc_redirect_url: 'test/redirect',
  oidc_scope: 'some scope',
  oidc_authority_url: 'https://login.test',
  oidc_authorization_url: 'test/authorize',
  oidc_token_url: 'test/token',
  oidc_userinfo_url: 'test/userinfo',
  oidc_use_discovery: true,
  oidc_account_url: 'https://account.test',
  umami_url: null,
  umami_website_id: null,
  mock_api: true,
  mock_oidc: true,
  helpdesk_url: 'https://helpdesk.test',
  helpdesk_ticket_url: '/#ticket/',
  version: '1.2.3',
};

describe('ConfigService', () => {
  let service: ConfigService;

  beforeEach(() => {
    window.config = mockConfig;

    TestBed.configureTestingModule({});
    service = TestBed.inject(ConfigService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should provide the base URL', () => {
    expect(service.baseUrl).toBe('https://portal.test');
  });

  it('should provide the auth service URL', () => {
    expect(service.authUrl).toBe('/test/auth');
  });

  it('should provide the MASS URL', () => {
    expect(service.massUrl).toBe('/test/mass');
  });

  it('should provide the metldata service URL', () => {
    expect(service.metldataUrl).toBe('/test/metldata');
  });

  it('should provide the default Well-Known Value Service URL', () => {
    expect(service.wkvsUrl).toBe('/.well-known');
  });

  it('should provide the OIDC client ID', () => {
    expect(service.oidcClientId).toBe('test-oidc-client-id');
  });

  it('should provide the OIDC redirect URL', () => {
    expect(service.oidcRedirectUrl).toBe('https://portal.test/test/redirect');
  });

  it('should provide the OIDC scope', () => {
    expect(service.oidcScope).toBe('some scope');
  });

  it('should provide the OIDC authority URL', () => {
    expect(service.oidcAuthorityUrl).toBe('https://login.test');
  });

  it('should provide the OIDC authorization URL', () => {
    expect(service.oidcAuthorizationUrl).toBe('https://login.test/test/authorize');
  });

  it('should provide the OIDC token URL', () => {
    expect(service.oidcTokenUrl).toBe('https://login.test/test/token');
  });

  it('should provide the OIDC userinfo URL', () => {
    expect(service.oidcUserInfoUrl).toBe('https://login.test/test/userinfo');
  });

  it('should provide the OIDC account URL', () => {
    expect(service.oidcAccountUrl).toBe('https://account.test');
  });

  it('should provide the helpdesk URL', () => {
    expect(service.helpdeskUrl).toBe('https://helpdesk.test');
  });

  it('should provide the helpdesk ticket URL', () => {
    expect(service.helpdeskTicketUrl).toBe('https://helpdesk.test/#ticket/');
  });

  it('should provide the application version', () => {
    expect(service.version).toBe('1.2.3');
  });
});
