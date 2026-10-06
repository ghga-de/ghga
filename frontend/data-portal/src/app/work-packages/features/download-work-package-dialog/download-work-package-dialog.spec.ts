/**
 * Test the download work package dialog component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Clipboard } from '@angular/cdk/clipboard';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import {
  AccessGrantStatus,
  AccessGrantWithIva,
} from '@app/access-requests/models/access-requests';
import { Iva, IvaState, IvaType } from '@app/ivas/models/iva';
import { IvaService } from '@app/ivas/services/iva';
import { Notifier } from '@app/shared/services/notification';
import { DatasetWithExpiration } from '@app/work-packages/models/dataset';
import { WorkPackageService } from '@app/work-packages/services/work-package';
import { render, RenderResult, screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { of, Subject, throwError } from 'rxjs';
import { DownloadWorkPackageDialog } from './download-work-package-dialog';

const TEST_DATASET: DatasetWithExpiration = {
  id: 'GHGAD12345678901234',
  title: 'Test Dataset',
  description: 'A test dataset for unit testing',
  stage: 'download',
  files: [
    { id: 'file1', extension: 'txt' },
    { id: 'file2', extension: 'csv' },
    { id: 'file3', extension: 'json' },
  ],
  expires: '2026-12-31T23:59:59Z',
};

const TEST_GRANT: AccessGrantWithIva = {
  id: 'grant-123',
  user_id: 'user-123',
  created: '2026-01-01T00:00:00Z',
  dataset_id: 'GHGAD12345678901234',
  dataset_title: 'Test Dataset',
  valid_from: '2026-01-01T00:00:00Z',
  valid_until: '2026-12-31T23:59:59Z',
  user_email: 'test@example.com',
  user_name: 'Test User',
  user_title: 'Dr.',
  dac_alias: 'Test DAC',
  dac_email: 'dac@example.com',
  iva_id: 'iva-123',
  status: AccessGrantStatus.active,
  daysRemaining: 300,
  iva: {
    id: 'iva-123',
    type: IvaType.Phone,
    value: '+49123456789',
    state: IvaState.Verified,
    changed: '2026-01-01T00:00:00Z',
  },
};

/**
 * Minimal mock for the IVA service that exposes the current user's IVAs.
 */
class MockIvaService {
  userIvas = {
    value: signal<Iva[]>([TEST_GRANT.iva!]),
    error: signal<Error | undefined>(undefined),
    isLoading: signal(false),
  };
  loadUserIvas = vitest.fn();
}

const VALID_PUBKEY = 'MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=';

describe('DownloadWorkPackageDialog', () => {
  let result: RenderResult<DownloadWorkPackageDialog>;
  let component: DownloadWorkPackageDialog;
  let workPackageService: WorkPackageService;
  let notificationService: Notifier;
  let clipboard: Clipboard;

  const dialogRef = {
    close: vitest.fn(),
  };

  /**
   * Get the text area for the file IDs
   * @returns the file IDs text area
   */
  function filesInput(): HTMLElement {
    return screen.getByRole('textbox', { name: 'File IDs' });
  }

  /**
   * Get the input field for the public key
   * @returns the public key input field
   */
  function pubkeyInput(): HTMLElement {
    return screen.getByRole('textbox', { name: 'Your public Crypt4GH key' });
  }

  /**
   * Get the button that generates the download token
   * @returns the generate button
   */
  function generateButton(): HTMLElement {
    return screen.getByRole('button', { name: /generate download token/i });
  }

  beforeEach(async () => {
    const wpServiceMock = {
      datasets: {
        isLoading: vitest.fn(() => false),
        hasValue: vitest.fn(() => true),
        value: vitest.fn(() => [TEST_DATASET]),
      },
      createWorkPackage: vitest.fn(),
    };

    const notifyMock = {
      showSuccess: vitest.fn(),
      showError: vitest.fn(),
    };

    const clipboardMock = {
      copy: vitest.fn(() => true),
    };

    result = await render(DownloadWorkPackageDialog, {
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: TEST_GRANT },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: WorkPackageService, useValue: wpServiceMock },
        { provide: Notifier, useValue: notifyMock },
        { provide: Clipboard, useValue: clipboardMock },
        { provide: IvaService, useClass: MockIvaService },
      ],
    });
    component = result.fixture.componentInstance;
    workPackageService = TestBed.inject(WorkPackageService);
    notificationService = TestBed.inject(Notifier);
    clipboard = TestBed.inject(Clipboard);
    vitest.clearAllMocks();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
    expect(
      screen.getByRole('heading', { level: 1, name: 'Create a Download Token' }),
    ).toBeVisible();
  });

  describe('initialization', () => {
    it('should load grant data', () => {
      expect(component['grant']).toBe(TEST_GRANT);
      expect(component['iva']()).toBe(TEST_GRANT.iva);
      expect(screen.getByText(/300 days left/)).toBeVisible();
    });

    it('should show an error message when the IVA could not be loaded', async () => {
      expect(screen.queryByText('Could not load IVA')).toBeNull();

      const ivaService = TestBed.inject(IvaService) as unknown as MockIvaService;
      ivaService.userIvas.error.set(new Error('Internal server error'));
      await result.fixture.whenStable();

      expect(screen.getByText('Could not load IVA')).toBeVisible();
    });

    it('should load dataset from service', () => {
      const dataset = component['dataset']();
      expect(dataset).toBeDefined();
      expect(dataset?.id).toBe('GHGAD12345678901234');
      expect(screen.getByText(/GHGAD12345678901234/)).toBeVisible();
      expect(screen.getByText(/Test Dataset/)).toBeVisible();
    });

    it('should initialize form with empty values', () => {
      expect(component['model']().files).toBe('');
      expect(component['model']().pubkey).toBe('');
      expect(filesInput()).toHaveValue('');
      expect(pubkeyInput()).toHaveValue('');
    });

    it('should have form invalid initially', () => {
      expect(component['downloadForm']().valid()).toBe(false);
      expect(generateButton()).toBeDisabled();
    });
  });

  describe('onClose', () => {
    it('should close dialog', async () => {
      await userEvent.click(screen.getByRole('button', { name: 'Close' }));
      expect(dialogRef.close).toHaveBeenCalled();
    });
  });

  describe('onCreateToken', () => {
    beforeEach(async () => {
      // Set up valid form data
      await userEvent.type(filesInput(), 'file1, file2');
      await userEvent.type(pubkeyInput(), VALID_PUBKEY);
      await result.fixture.whenStable();
    });

    it('should not create token if form is invalid', async () => {
      await userEvent.clear(filesInput());
      await userEvent.clear(pubkeyInput());
      await result.fixture.whenStable();

      expect(generateButton()).toBeDisabled();
      component.onCreateToken();

      expect(workPackageService.createWorkPackage).not.toHaveBeenCalled();
    });

    it('should create work package with correct data', async () => {
      (
        workPackageService.createWorkPackage as ReturnType<typeof vitest.fn>
      ).mockReturnValue(
        of({
          id: 'wp-123',
          token: 'test-token-456',
          expires: '2026-02-01T00:00:00Z',
        }),
      );

      await userEvent.click(generateButton());

      expect(workPackageService.createWorkPackage).toHaveBeenCalledWith({
        dataset_id: 'GHGAD12345678901234',
        file_ids: ['file1', 'file2'],
        type: 'download',
        user_public_crypt4gh_key: expect.any(String),
      });
    });

    it('should create work package with null file_ids when files input is empty', async () => {
      await userEvent.clear(filesInput());
      await result.fixture.whenStable();

      (
        workPackageService.createWorkPackage as ReturnType<typeof vitest.fn>
      ).mockReturnValue(
        of({
          id: 'wp-123',
          token: 'test-token-456',
          expires: '2026-02-01T00:00:00Z',
        }),
      );

      await userEvent.click(generateButton());

      expect(workPackageService.createWorkPackage).toHaveBeenCalledWith(
        expect.objectContaining({
          file_ids: null,
        }),
      );
    });

    it('should display loading message during token creation', async () => {
      (
        workPackageService.createWorkPackage as ReturnType<typeof vitest.fn>
      ).mockReturnValue(new Subject());

      await userEvent.click(generateButton());
      await result.fixture.whenStable();

      // Verify the service was called (token creation initiated)
      expect(workPackageService.createWorkPackage).toHaveBeenCalled();
      expect(screen.getByText('Creating your download token...')).toBeVisible();
    });

    it('should display token on successful creation', async () => {
      (
        workPackageService.createWorkPackage as ReturnType<typeof vitest.fn>
      ).mockReturnValue(
        of({
          id: 'wp-123',
          token: 'test-token-456',
          expires: '2026-02-01T00:00:00Z',
        }),
      );

      await userEvent.click(generateButton());
      await result.fixture.whenStable();

      expect(screen.getByText('wp-123:test-token-456')).toBeVisible();
      expect(notificationService.showSuccess).not.toHaveBeenCalled();
    });

    it('should display error message on token creation failure', async () => {
      const error = new Error('Network error');
      (
        workPackageService.createWorkPackage as ReturnType<typeof vitest.fn>
      ).mockReturnValue(throwError(() => error));

      await userEvent.click(generateButton());
      await result.fixture.whenStable();

      expect(screen.getByText(/could not be created/)).toBeVisible();
      expect(notificationService.showError).toHaveBeenCalled();
    });
  });

  describe('resetToken', () => {
    it('should clear token and error state from view', async () => {
      component['token'].set('test-token');
      component['tokenError'].set('test-error');
      component['tokenIsLoading'].set(true);
      await result.fixture.whenStable();

      component.resetToken();
      await result.fixture.whenStable();

      // Verify token is no longer displayed
      expect(screen.queryByText('test-token')).not.toBeInTheDocument();

      // Verify error is no longer displayed
      expect(screen.queryByText('test-error')).not.toBeInTheDocument();

      // Verify the form is shown again
      expect(generateButton()).toBeVisible();
    });

    it('should clear the error from view when trying again', async () => {
      component['tokenError'].set('test-error');
      await result.fixture.whenStable();
      expect(screen.getByText('test-error')).toBeVisible();

      await userEvent.click(screen.getByRole('button', { name: 'try again' }));
      await result.fixture.whenStable();

      expect(screen.queryByText('test-error')).not.toBeInTheDocument();
    });
  });

  describe('copyToken', () => {
    it('should copy token to clipboard and show notification', async () => {
      component['token'].set('test-token-123');
      await result.fixture.whenStable();

      await userEvent.click(
        screen.getByRole('button', { name: 'Copy token to clipboard' }),
      );

      expect(clipboard.copy).toHaveBeenCalledWith('test-token-123');
      expect(notificationService.showSuccess).toHaveBeenCalledWith(
        'The token has been copied to the clipboard.',
      );
    });

    it('should not copy if token is empty', async () => {
      component['token'].set('');
      await result.fixture.whenStable();

      expect(
        screen.queryByRole('button', { name: 'Copy token to clipboard' }),
      ).not.toBeInTheDocument();
      component.copyToken();

      expect(clipboard.copy).not.toHaveBeenCalled();
      expect(notificationService.showSuccess).not.toHaveBeenCalled();
    });
  });

  describe('form validation', () => {
    it('should be invalid with empty pubkey', async () => {
      await userEvent.type(filesInput(), 'file1');
      await result.fixture.whenStable();

      expect(component['downloadForm']().valid()).toBe(false);
      expect(generateButton()).toBeDisabled();
    });

    it('should be valid with valid pubkey', async () => {
      await userEvent.type(filesInput(), 'file1');
      await userEvent.type(pubkeyInput(), VALID_PUBKEY);
      await result.fixture.whenStable();

      expect(component['downloadForm']().valid()).toBe(true);
      expect(generateButton()).toBeEnabled();
    });
  });
});
