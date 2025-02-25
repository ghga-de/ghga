/**
 * Tests for the Content of the data access request dialog.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { provideNativeDateAdapter } from '@angular/material/core';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { ConfigService } from '@app/shared/services/config.service';
import { DataAccessRequestDialogComponent } from './data-access-request-dialog.component';

const mockConfig = {
  base_url: 'https://portal.test',
  ars_url: 'test/ars',
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
  access_upfront_max_days: 180,
  access_grant_min_days: 7,
  access_grant_max_days: 730,
  default_access_duration_days: 365,
};

describe('DataAccessRequestDialogComponent', () => {
  let component: DataAccessRequestDialogComponent;
  let fixture: ComponentFixture<DataAccessRequestDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DataAccessRequestDialogComponent, MatDialogModule],
      providers: [
        provideNativeDateAdapter(),
        {
          provide: MatDialogRef,
          useValue: {},
        },
        { provide: MAT_DIALOG_DATA, useValue: {} },
        provideAnimationsAsync(),
        { provide: ConfigService, useValue: mockConfig },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DataAccessRequestDialogComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('datasetID', 'GHGAD588887987');
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
