/**
 * Test the config service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { TestBed } from '@angular/core/testing';

import { ConfigService } from './config.service';

const mockConfig = {
  base_url: 'https://portal.test',
  auth_url: '/test/auth',
  dins_url: '/test/dins',
  mass_url: '/test/mass',
  metldata_url: '/test/metldata',
  wps_url: '/test/wps',
  oidc_client_id: 'test-oidc-client-id',
  oidc_redirect_url: 'test/redirect',
  oidc_scope: 'some scope',
  oidc_authority_url: 'https://login.test',
  oidc_authorization_url: 'test/authorize',
  oidc_token_url: 'test/token',
  oidc_userinfo_url: 'test/userinfo',
  oidc_use_discovery: true,
  oidc_account_url: 'https://account.test',
  mock_api: true,
  mock_oidc: true,
  ribbon_text: 'Test ribbon text',
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

  it('should provide the OID client ID', () => {
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
});
