/**
 * Unit tests for the dynamic access request button
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { signal } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { ActivatedRoute } from '@angular/router';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { AccessRequestDialogComponent } from '@app/access-requests/features/access-request-dialog/access-request-dialog';
import { AccessGrant } from '@app/access-requests/models/access-requests';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { AuthService } from '@app/auth/services/auth';
import { IvaService } from '@app/ivas/services/iva';
import { DownloadWorkPackageDialogComponent } from '@app/work-packages/features/download-work-package-dialog/download-work-package-dialog';
import { screen } from '@testing-library/angular';
import { of } from 'rxjs';
import { DynamicAccessRequestButtonComponent } from './dynamic-access-request-button';

const DATASET_ID = 'GHGAD12345678901234';

const TEST_GRANT: AccessGrant = {
  id: 'grant-test-001',
  user_id: 'doe@test.dev',
  dataset_id: DATASET_ID,
  created: '2025-07-20T10:00:00Z',
  valid_from: '2025-08-01T00:00:00Z',
  valid_until: '2026-08-01T00:00:00Z',
  user_name: 'John Doe',
  user_title: 'Dr.',
  user_email: 'doe@home.org',
  dataset_title: 'Test dataset',
  dac_alias: 'TEST-DAC',
  dac_email: 'dac@test.org',
  iva_id: 'iva-test-001',
  daysRemaining: 300,
};

/**
 * Minimal mock for the auth service
 */
export class MockAuthService {
  user = () => ({ id: 'doe@test.dev' });
  fullName = () => 'Dr. John Doe';
  email = () => 'doe@home.org';
  roles = () => ['data_steward'];
  roleNames = () => ['Data Steward'];
  isAuthenticated = () => true;
}

/**
 * Minimal mock for the IVA service
 */
class MockIvaService {
  userIvas = { error: signal(undefined), value: signal([]) };
  loadUserIvas = () => undefined;
}

describe('DynamicAccessRequestButtonComponent', () => {
  let component: DynamicAccessRequestButtonComponent;
  let fixture: ComponentFixture<DynamicAccessRequestButtonComponent>;
  let dialog: MatDialog;
  let accessRequestService: MockAccessRequestService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DynamicAccessRequestButtonComponent],
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
        { provide: AuthService, useClass: MockAuthService },
        { provide: IvaService, useClass: MockIvaService },
      ],
    }).compileComponents();

    accessRequestService = TestBed.inject(
      AccessRequestService,
    ) as unknown as MockAccessRequestService;
    dialog = TestBed.inject(MatDialog);

    fixture = TestBed.createComponent(DynamicAccessRequestButtonComponent);
    fixture.componentRef.setInput('datasetID', DATASET_ID);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('denied requests', () => {
    beforeEach(() => {
      accessRequestService.activeUserAccessGrants.set([]);
      accessRequestService.pendingUserAccessRequests.set([]);
      fixture.detectChanges();
    });

    it('should show the "Request Access" button', () => {
      expect(screen.getByRole('button', { name: /request access/i })).toBeVisible();
    });

    it('should open the access request dialog when clicked', () => {
      const openSpy = vitest.spyOn(dialog, 'open').mockReturnValue({
        afterClosed: () => of(null),
        close: vitest.fn(),
      } as never);

      screen.getByRole('button', { name: /request access/i }).click();

      expect(openSpy).toHaveBeenCalledWith(
        AccessRequestDialogComponent,
        expect.any(Object),
      );
    });
  });

  describe('pending requests', () => {
    beforeEach(() => {
      accessRequestService.activeUserAccessGrants.set([]);
      accessRequestService.pendingUserAccessRequests.set([
        { dataset_id: DATASET_ID } as never,
      ]);
      fixture.detectChanges();
    });

    it('should show the disabled "Pending Request" button', () => {
      const button = screen.getByRole('button', { name: /pending request/i });
      expect(button).toBeVisible();
      expect(button).toBeDisabled();
    });
  });

  describe('allowed requests', () => {
    beforeEach(() => {
      accessRequestService.activeUserAccessGrants.set([TEST_GRANT]);
      fixture.detectChanges();
    });

    it('should show the "Download the Data" button', () => {
      expect(screen.getByRole('button', { name: /download the data/i })).toBeVisible();
    });

    it('should open the download token dialog when clicked', () => {
      const openSpy = vitest.spyOn(dialog, 'open').mockReturnValue({} as never);

      screen.getByRole('button', { name: /download the data/i }).click();

      expect(openSpy).toHaveBeenCalledWith(
        DownloadWorkPackageDialogComponent,
        expect.objectContaining({
          data: expect.objectContaining({ dataset_id: DATASET_ID }),
        }),
      );
    });
  });
});
