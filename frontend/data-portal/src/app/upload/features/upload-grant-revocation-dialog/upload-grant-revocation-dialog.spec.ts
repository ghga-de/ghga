/**
 * Tests for the Upload Grant Revocation Dialog component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { uploadGrants } from '@app/../mocks/data';
import { NotificationService } from '@app/shared/services/notification';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { screen } from '@testing-library/angular';
import { of, throwError } from 'rxjs';
import { UploadGrantRevocationDialogComponent } from './upload-grant-revocation-dialog';

const testGrant = uploadGrants[0];

const mockDialogRef = { close: vitest.fn() };
const mockNotificationService = { showSuccess: vitest.fn(), showError: vitest.fn() };

/**
 * Minimal mock of UploadBoxService for revocation dialog tests.
 */
class MockUploadBoxService {
  revokeUploadGrant = vitest.fn();
}

describe('UploadGrantRevocationDialogComponent', () => {
  let component: UploadGrantRevocationDialogComponent;
  let fixture: ComponentFixture<UploadGrantRevocationDialogComponent>;
  let uploadBoxService: MockUploadBoxService;

  beforeEach(async () => {
    mockDialogRef.close.mockReset();
    mockNotificationService.showSuccess.mockReset();
    mockNotificationService.showError.mockReset();

    await TestBed.configureTestingModule({
      imports: [UploadGrantRevocationDialogComponent],
      providers: [
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: { grant: testGrant } },
        { provide: UploadBoxService, useClass: MockUploadBoxService },
        { provide: NotificationService, useValue: mockNotificationService },
      ],
    }).compileComponents();

    uploadBoxService = TestBed.inject(
      UploadBoxService,
    ) as unknown as MockUploadBoxService;
    fixture = TestBed.createComponent(UploadGrantRevocationDialogComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should expose the grant via the grant getter', () => {
    expect(component.grant).toBe(testGrant);
  });

  it('should display the grantee name with title', () => {
    expect(screen.getByText(/dr\. john doe/i)).toBeVisible();
  });

  it('should display the grantee email', () => {
    expect(screen.getByText(/doe@home\.org/i)).toBeVisible();
  });

  it('should not show a revocation error message initially', () => {
    expect(screen.queryByText(/grant revocation failed/i)).not.toBeInTheDocument();
  });

  it('should have the confirm button enabled initially', () => {
    const confirmButton = screen.getByRole('button', { name: /confirm revocation/i });
    expect(confirmButton).not.toBeDisabled();
  });

  describe('onCancel()', () => {
    it('should close the dialog with false', () => {
      component.onCancel();
      expect(mockDialogRef.close).toHaveBeenCalledWith(false);
    });
  });

  describe('onConfirm() - success', () => {
    beforeEach(() => {
      uploadBoxService.revokeUploadGrant.mockReturnValue(of(undefined));
      component.onConfirm();
    });

    it('should call revokeUploadGrant with the grant id', () => {
      expect(uploadBoxService.revokeUploadGrant).toHaveBeenCalledWith(testGrant.id);
    });

    it('should close the dialog with true', () => {
      expect(mockDialogRef.close).toHaveBeenCalledWith(true);
    });

    it('should show a success notification', () => {
      expect(mockNotificationService.showSuccess).toHaveBeenCalledWith(
        'Upload grant was successfully revoked.',
      );
    });

    it('should not show an error notification', () => {
      expect(mockNotificationService.showError).not.toHaveBeenCalled();
    });
  });

  describe('onConfirm() - error', () => {
    beforeEach(async () => {
      uploadBoxService.revokeUploadGrant.mockReturnValue(
        throwError(() => new Error('Network error')),
      );
      component.onConfirm();
      await fixture.whenStable();
    });

    it('should call revokeUploadGrant with the grant id', () => {
      expect(uploadBoxService.revokeUploadGrant).toHaveBeenCalledWith(testGrant.id);
    });

    it('should show an error notification', () => {
      expect(mockNotificationService.showError).toHaveBeenCalledWith(
        'Upload grant could not be revoked. Please try again later.',
      );
    });

    it('should not close the dialog', () => {
      expect(mockDialogRef.close).not.toHaveBeenCalled();
    });

    it('should display the revocation error message in the template', async () => {
      fixture.detectChanges();
      expect(screen.getByText(/grant revocation failed/i)).toBeVisible();
    });
  });
});
