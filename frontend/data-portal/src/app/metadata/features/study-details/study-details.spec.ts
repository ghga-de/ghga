/**
 * Test the study details component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { metadataGlobalSummary } from '@app/../mocks/data';
import { MetadataService } from '@app/metadata/services/metadata';
import { ConfigService } from '@app/shared/services/config';
import { StudyDetailsComponent } from './study-details';

/**
 * Mock the metadata service as needed for the study details
 */
class MockMetadataService {
  study = {
    value: () => metadataGlobalSummary.resource_stats,
    isLoading: () => false,
    error: () => undefined,
  };
}

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
  max_facet_options: 7,
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
};

describe('StudyDetailsComponent', () => {
  let component: StudyDetailsComponent;
  let fixture: ComponentFixture<StudyDetailsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StudyDetailsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MetadataService, useClass: MockMetadataService },
        { provide: ConfigService, useValue: mockConfig },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(StudyDetailsComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
