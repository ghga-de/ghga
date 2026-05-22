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
import { ConfigService } from '@app/shared/services/config';
import { localDateToContractIsoUtc } from '@app/shared/utils/date-formats';
import { AccessRequestDialogComponent } from './access-request-dialog';

const mockDialogRef = {
  close: vitest.fn(),
};

const mockDialogData = {
  datasetID: 'GHGAD12345678901234',
  email: 'user@example.test',
  description: '',
  fromDate: undefined,
  untilDate: undefined,
  userId: 'user-1',
};

const mockConfig = {
  base_url: 'https://portal.test',
  ars_url: 'test/ars',
  auth_url: '/test/auth',
  dins_url: '/test/dins',
  mass_url: '/test/mass',
  metldata_url: '/test/metldata',
  rs_url: '/test/rs',
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

describe('AccessRequestDialogComponent', () => {
  let component: AccessRequestDialogComponent;
  let fixture: ComponentFixture<AccessRequestDialogComponent>;

  beforeEach(async () => {
    mockDialogRef.close.mockReset();
    await TestBed.configureTestingModule({
      imports: [AccessRequestDialogComponent, MatDialogModule],
      providers: [
        provideNativeDateAdapter(),
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: mockDialogData },
        { provide: ConfigService, useValue: mockConfig },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AccessRequestDialogComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('datasetID', 'GHGAD12345678901234');
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should submit with ISO UTC dates based on service-contract day boundaries', () => {
    const fromDate = new Date(component.todayMidnight);
    const untilDate = new Date(component.todayMidnight);
    untilDate.setDate(untilDate.getDate() + mockConfig.access_grant_min_days);

    component.updateUntilRangeForFromValue(fromDate);
    component.updateFromRangeForUntilValue(untilDate);
    (component as any).model.set({
      description: 'Need access for analysis',
      fromDate,
      untilDate,
      email: 'user@example.test',
    });

    component.submit();

    expect(mockDialogRef.close).toHaveBeenCalledTimes(1);
    const payload = mockDialogRef.close.mock.calls[0][0];
    expect(payload.fromDate.toISOString()).toBe(localDateToContractIsoUtc(fromDate));
    expect(payload.untilDate.toISOString()).toBe(
      localDateToContractIsoUtc(untilDate, true),
    );
  });
});
