/**
 * Tests for the UserUploadGrantsListComponent.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { ConfirmationService } from '@app/shared/services/confirmation';
import { NotificationService } from '@app/shared/services/notification';
import { UploadBoxState } from '@app/upload/models/box';
import { GrantWithBoxInfo } from '@app/upload/models/grant';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { UploadWorkPackageDialogComponent } from '@app/work-packages/features/upload-work-package-dialog/upload-work-package-dialog';
import { screen } from '@testing-library/angular';
import { of, throwError } from 'rxjs';
import { UserUploadGrantsListComponent } from './user-upload-grants-list';

// --- Test fixtures ---

const openGrant: GrantWithBoxInfo = {
  id: 'grant-1',
  user_id: 'doe@test.dev',
  iva_id: 'iva-verified-001',
  box_id: 'box-001',
  created: '2026-01-01T00:00:00Z',
  valid_from: '2026-01-01',
  valid_until: '2026-12-31',
  user_name: 'John Doe',
  user_email: 'doe@home.org',
  user_title: 'Dr.',
  box_title: 'Test Upload Box',
  box_description: 'A test upload box',
  box_state: UploadBoxState.open,
  box_version: 1,
};

// --- Mocks ---

/**
 * Mock of UploadBoxService for user upload grants list tests.
 */
class MockUploadBoxService {
  #grants = signal<GrantWithBoxInfo[]>([]);
  #error = signal<Error | undefined>(undefined);
  #loading = signal<boolean>(false);

  userGrants = {
    value: this.#grants,
    error: this.#error,
    isLoading: this.#loading,
    reload: vitest.fn(),
  };

  lockUploadBox = vitest.fn();

  /**
   * Test helper: set the loaded grants.
   * @param grants - grants to expose through the mocked userGrants resource
   */
  setGrants(grants: GrantWithBoxInfo[]): void {
    this.#grants.set(grants);
  }

  /**
   * Test helper: set an error state.
   * @param error - error to expose through the mocked userGrants resource
   */
  setError(error: Error): void {
    this.#error.set(error);
  }

  /**
   * Test helper: set the loading state.
   * @param loading - whether mocked userGrants should appear loading
   */
  setLoading(loading: boolean): void {
    this.#loading.set(loading);
  }
}

const mockConfirmationService = { confirm: vitest.fn() };
const mockNotificationService = {
  showInfo: vitest.fn(),
  showSuccess: vitest.fn(),
  showError: vitest.fn(),
};
const mockDialog = { open: vitest.fn() };

// --- Tests ---

describe('UserUploadGrantsListComponent', () => {
  let component: UserUploadGrantsListComponent;
  let fixture: ComponentFixture<UserUploadGrantsListComponent>;
  let uploadBoxService: MockUploadBoxService;

  beforeEach(async () => {
    mockConfirmationService.confirm.mockReset();
    mockNotificationService.showInfo.mockReset();
    mockNotificationService.showSuccess.mockReset();
    mockNotificationService.showError.mockReset();
    mockDialog.open.mockReset();

    await TestBed.configureTestingModule({
      imports: [UserUploadGrantsListComponent],
      providers: [
        { provide: UploadBoxService, useClass: MockUploadBoxService },
        { provide: ConfirmationService, useValue: mockConfirmationService },
        { provide: NotificationService, useValue: mockNotificationService },
        { provide: MatDialog, useValue: mockDialog },
      ],
    }).compileComponents();

    uploadBoxService = TestBed.inject(
      UploadBoxService,
    ) as unknown as MockUploadBoxService;
    fixture = TestBed.createComponent(UserUploadGrantsListComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });
  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show a loading indicator while grants are loading', async () => {
    uploadBoxService.setLoading(true);
    fixture.detectChanges();
    expect(document.querySelector('[role="loader"]')).toBeTruthy();
  });

  it('should show an error message when grant loading fails', async () => {
    uploadBoxService.setError(new Error('backend error'));
    fixture.detectChanges();
    expect(screen.getByText(/error retrieving.*upload boxes/i)).toBeVisible();
  });

  it('should show an empty message when no open grants exist', async () => {
    uploadBoxService.setGrants([]);
    fixture.detectChanges();
    expect(screen.getByText(/no.*open Research Data Upload Boxes/i)).toBeVisible();
  });

  it('should render the box title for an open grant', async () => {
    uploadBoxService.setGrants([openGrant]);
    fixture.detectChanges();
    expect(screen.getByText('Test Upload Box')).toBeVisible();
  });

  it('should not render grants whose box state is not open', async () => {
    const lockedGrant: GrantWithBoxInfo = {
      ...openGrant,
      id: 'grant-locked',
      box_state: UploadBoxState.locked,
      box_title: 'Locked Box',
    };
    uploadBoxService.setGrants([openGrant, lockedGrant]);
    fixture.detectChanges();
    expect(screen.getByText('Test Upload Box')).toBeVisible();
    expect(screen.queryByText('Locked Box')).not.toBeInTheDocument();
  });

  it('should render a box only once when multiple grants reference the same box', async () => {
    const duplicateGrantForSameBox: GrantWithBoxInfo = {
      ...openGrant,
      id: 'grant-duplicate',
      iva_id: null,
    };

    uploadBoxService.setGrants([openGrant, duplicateGrantForSameBox]);
    fixture.detectChanges();

    expect(screen.getAllByText('Test Upload Box')).toHaveLength(1);
  });

  it('should open upload token dialog when Create token is clicked', async () => {
    uploadBoxService.setGrants([openGrant]);
    fixture.detectChanges();
    const btn = screen.getByRole('button', { name: /create an upload token/i });
    btn.click();
    expect(mockDialog.open).toHaveBeenCalledWith(
      UploadWorkPackageDialogComponent,
      expect.objectContaining({
        data: openGrant,
        width: '64rem',
        maxWidth: '96vw',
      }),
    );
  });

  it('should open a confirmation dialog when Submit is clicked', async () => {
    mockConfirmationService.confirm.mockImplementation(() => undefined);
    uploadBoxService.setGrants([openGrant]);
    fixture.detectChanges();
    screen.getByRole('button', { name: /submit this upload box/i }).click();
    expect(mockConfirmationService.confirm).toHaveBeenCalled();
  });

  describe('submitBox - confirmed, success', () => {
    beforeEach(async () => {
      mockConfirmationService.confirm.mockImplementation(({ callback }) =>
        callback(true),
      );
      uploadBoxService.lockUploadBox.mockReturnValue(of(undefined));
      uploadBoxService.setGrants([openGrant]);
      fixture.detectChanges();
      screen.getByRole('button', { name: /submit this upload box/i }).click();
      await fixture.whenStable();
    });

    it('should call lockUploadBox with box id, version, and no force', () => {
      expect(uploadBoxService.lockUploadBox).toHaveBeenCalledWith('box-001', 1, false);
    });

    it('should show a success notification', () => {
      expect(mockNotificationService.showSuccess).toHaveBeenCalledWith(
        'The upload box has been submitted successfully.',
      );
    });

    it('should not force reload user grants after success', () => {
      expect(uploadBoxService.userGrants.reload).not.toHaveBeenCalled();
    });
  });

  describe('submitBox - confirmed, error', () => {
    beforeEach(async () => {
      mockConfirmationService.confirm.mockImplementation(({ callback }) =>
        callback(true),
      );
      uploadBoxService.lockUploadBox.mockReturnValue(
        throwError(() => new Error('Server error')),
      );
      uploadBoxService.setGrants([openGrant]);
      fixture.detectChanges();
      screen.getByRole('button', { name: /submit this upload box/i }).click();
      await fixture.whenStable();
    });

    it('should show an error notification', () => {
      expect(mockNotificationService.showError).toHaveBeenCalledWith(
        'Failed to submit the upload box. Please try again.',
      );
    });

    it('should not reload user grants on error', () => {
      expect(uploadBoxService.userGrants.reload).not.toHaveBeenCalled();
    });
  });

  describe('submitBox - incomplete uploads conflict', () => {
    /**
     * Build a 409 conflict reporting incomplete uploads, matching the backend
     * response that blocks locking a box with unfinished uploads.
     * @param incompleteUploads - the still-incomplete upload IDs
     * @returns an HttpErrorResponse with the conflict payload
     */
    const conflict = (incompleteUploads: string[]): HttpErrorResponse =>
      new HttpErrorResponse({
        status: 409,
        error: { data: { incomplete_uploads: incompleteUploads } },
      });

    beforeEach(() => {
      uploadBoxService.setGrants([openGrant]);
    });

    it('should force submission after confirmation when a 409 blocks the submission', async () => {
      uploadBoxService.lockUploadBox
        .mockReturnValueOnce(throwError(() => conflict(['file-2', 'file-3'])))
        .mockReturnValueOnce(of(undefined));
      // First confirm: the submit prompt. Second: the force-submit prompt.
      mockConfirmationService.confirm
        .mockImplementationOnce(({ callback }) => callback(true))
        .mockImplementationOnce(({ callback }) => callback(true));
      fixture.detectChanges();

      screen.getByRole('button', { name: /submit this upload box/i }).click();
      await fixture.whenStable();

      expect(mockConfirmationService.confirm).toHaveBeenNthCalledWith(
        2,
        expect.objectContaining({
          message:
            'Submission failed because there are still 2 incomplete file uploads. ' +
            'Do you want to submit anyway?',
          confirmText: 'Submit anyway',
        }),
      );
      expect(uploadBoxService.lockUploadBox).toHaveBeenNthCalledWith(
        1,
        'box-001',
        1,
        false,
      );
      expect(uploadBoxService.lockUploadBox).toHaveBeenNthCalledWith(
        2,
        'box-001',
        1,
        true,
      );
      expect(mockNotificationService.showSuccess).toHaveBeenCalledWith(
        'The upload box has been submitted successfully.',
      );
    });

    it('should leave the box open when force submission is declined', async () => {
      uploadBoxService.lockUploadBox.mockReturnValue(
        throwError(() => conflict(['file-2'])),
      );
      mockConfirmationService.confirm
        .mockImplementationOnce(({ callback }) => callback(true))
        .mockImplementationOnce(({ callback }) => callback(false));
      fixture.detectChanges();

      screen.getByRole('button', { name: /submit this upload box/i }).click();
      await fixture.whenStable();

      expect(mockConfirmationService.confirm).toHaveBeenNthCalledWith(
        2,
        expect.objectContaining({
          message:
            'Submission failed because there is still 1 incomplete file upload. ' +
            'Do you want to submit anyway?',
          confirmText: 'Submit anyway',
        }),
      );
      expect(uploadBoxService.lockUploadBox).toHaveBeenCalledTimes(1);
      expect(uploadBoxService.lockUploadBox).toHaveBeenCalledWith('box-001', 1, false);
      expect(mockNotificationService.showError).not.toHaveBeenCalled();
      expect(mockNotificationService.showSuccess).not.toHaveBeenCalled();
    });

    it('should show the generic error when a forced submission still fails', async () => {
      uploadBoxService.lockUploadBox
        .mockReturnValueOnce(throwError(() => conflict(['file-2'])))
        .mockReturnValueOnce(throwError(() => conflict(['file-2'])));
      mockConfirmationService.confirm
        .mockImplementationOnce(({ callback }) => callback(true))
        .mockImplementationOnce(({ callback }) => callback(true));
      fixture.detectChanges();

      screen.getByRole('button', { name: /submit this upload box/i }).click();
      await fixture.whenStable();

      // Two confirmations total: the submit prompt and a single force prompt.
      // The failed forced retry must not reopen the force prompt.
      expect(mockConfirmationService.confirm).toHaveBeenCalledTimes(2);
      expect(uploadBoxService.lockUploadBox).toHaveBeenCalledTimes(2);
      expect(uploadBoxService.lockUploadBox).toHaveBeenNthCalledWith(
        2,
        'box-001',
        1,
        true,
      );
      expect(mockNotificationService.showError).toHaveBeenCalledWith(
        'Failed to submit the upload box. Please try again.',
      );
    });

    it('should show the generic error for a non-conflict failure without prompting to force', async () => {
      uploadBoxService.lockUploadBox.mockReturnValue(
        throwError(() => new Error('Server error')),
      );
      mockConfirmationService.confirm.mockImplementationOnce(({ callback }) =>
        callback(true),
      );
      fixture.detectChanges();

      screen.getByRole('button', { name: /submit this upload box/i }).click();
      await fixture.whenStable();

      expect(mockConfirmationService.confirm).toHaveBeenCalledTimes(1);
      expect(uploadBoxService.lockUploadBox).toHaveBeenCalledTimes(1);
      expect(mockNotificationService.showError).toHaveBeenCalledWith(
        'Failed to submit the upload box. Please try again.',
      );
    });
  });

  describe('submitBox - cancelled', () => {
    beforeEach(async () => {
      mockConfirmationService.confirm.mockImplementation(({ callback }) =>
        callback(false),
      );
      uploadBoxService.setGrants([openGrant]);
      fixture.detectChanges();
      screen.getByRole('button', { name: /submit this upload box/i }).click();
      await fixture.whenStable();
    });

    it('should not call lockUploadBox', () => {
      expect(uploadBoxService.lockUploadBox).not.toHaveBeenCalled();
    });

    it('should not show any notification', () => {
      expect(mockNotificationService.showSuccess).not.toHaveBeenCalled();
      expect(mockNotificationService.showError).not.toHaveBeenCalled();
    });
  });
});
