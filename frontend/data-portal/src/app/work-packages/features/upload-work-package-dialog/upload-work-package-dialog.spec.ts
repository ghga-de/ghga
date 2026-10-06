/**
 * Test the upload work package dialog component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Clipboard } from '@angular/cdk/clipboard';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { IvaState, IvaType } from '@app/ivas/models/iva';
import { IvaService } from '@app/ivas/services/iva';
import { NotificationService } from '@app/shared/services/notification';
import { UploadBoxState } from '@app/upload/models/box';
import { GrantWithBoxInfo } from '@app/upload/models/grant';
import { WorkPackageService } from '@app/work-packages/services/work-package';
import { render, RenderResult, screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { of, throwError } from 'rxjs';
import { UploadWorkPackageDialogComponent } from './upload-work-package-dialog';

const TEST_GRANT: GrantWithBoxInfo = {
  id: 'grant-123',
  user_id: 'user-123',
  iva_id: 'iva-123',
  box_id: 'box-123',
  created: '2026-01-01T00:00:00Z',
  valid_from: '2026-01-01T00:00:00Z',
  valid_until: '2026-12-31T23:59:59Z',
  user_name: 'Test User',
  user_email: 'test@example.com',
  user_title: 'Dr.',
  box_title: 'Test Upload Box',
  box_description: 'A test upload box for unit testing',
  box_state: UploadBoxState.open,
  box_version: 1,
};

/**
 * Mock IVA service with mutable state for testing.
 */
class MockIvaService {
  ivasSignal = signal([
    {
      id: 'iva-123',
      type: IvaType.Phone,
      value: '+49123456789',
      changed: '2026-01-01T00:00:00Z',
      state: IvaState.Verified,
    },
  ]);
  errorSignal = signal<Error | undefined>(undefined);

  loadingSignal = signal(false);

  userIvas = {
    value: this.ivasSignal,
    error: this.errorSignal,
    isLoading: this.loadingSignal,
  };

  loadUserIvas = vitest.fn();
}

const VALID_PUBKEY = 'MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=';

describe('UploadWorkPackageDialogComponent', () => {
  let result: RenderResult<UploadWorkPackageDialogComponent>;
  let component: UploadWorkPackageDialogComponent;
  let workPackageService: WorkPackageService;
  let notificationService: NotificationService;
  let clipboard: Clipboard;
  let ivaService: MockIvaService;

  const dialogRef = {
    close: vitest.fn(),
  };

  /**
   * Get the input field for the public key
   * @returns the public key input field
   */
  function pubkeyInput(): HTMLElement {
    return screen.getByRole('textbox', { name: 'Your public Crypt4GH key' });
  }

  /**
   * Get the button that generates the upload token
   * @returns the generate button
   */
  function generateButton(): HTMLElement {
    return screen.getByRole('button', { name: /generate upload token/i });
  }

  /**
   * Enter a valid public key into the form
   */
  async function enterValidPubkey(): Promise<void> {
    await userEvent.type(pubkeyInput(), VALID_PUBKEY);
    await result.fixture.whenStable();
  }

  beforeEach(async () => {
    const wpServiceMock = {
      createWorkPackage: vitest.fn(),
    };

    const notifyMock = {
      showSuccess: vitest.fn(),
      showError: vitest.fn(),
    };

    const clipboardMock = {
      copy: vitest.fn(() => true),
    };

    result = await render(UploadWorkPackageDialogComponent, {
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: TEST_GRANT },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: WorkPackageService, useValue: wpServiceMock },
        { provide: NotificationService, useValue: notifyMock },
        { provide: Clipboard, useValue: clipboardMock },
        { provide: IvaService, useClass: MockIvaService },
      ],
    });
    component = result.fixture.componentInstance;
    workPackageService = TestBed.inject(WorkPackageService);
    notificationService = TestBed.inject(NotificationService);
    clipboard = TestBed.inject(Clipboard);
    ivaService = TestBed.inject(IvaService) as unknown as MockIvaService;
    vitest.clearAllMocks();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
    expect(
      screen.getByRole('heading', { level: 1, name: 'Create an Upload Token' }),
    ).toBeVisible();
  });

  it('should initialize with the selected grant', () => {
    expect(component['grant']).toBe(TEST_GRANT);
    expect(screen.getByText(/Test Upload Box/)).toBeVisible();
  });

  it('should show an error message when the IVA could not be loaded', async () => {
    expect(screen.queryByText('Could not load IVA')).toBeNull();

    ivaService.errorSignal.set(new Error('Internal server error'));
    await result.fixture.whenStable();

    expect(screen.getByText('Could not load IVA')).toBeVisible();
  });

  it('should close dialog', async () => {
    await userEvent.click(screen.getByRole('button', { name: 'Close' }));
    expect(dialogRef.close).toHaveBeenCalled();
  });

  it('should not create token if form is invalid', () => {
    expect(pubkeyInput()).toHaveValue('');
    expect(generateButton()).toBeDisabled();

    component.onCreateToken();

    expect(workPackageService.createWorkPackage).not.toHaveBeenCalled();
  });

  it('should not create token if IVA is missing', async () => {
    await enterValidPubkey();
    ivaService.ivasSignal.set([]);
    await result.fixture.whenStable();

    expect(screen.getByText('Missing IVA')).toBeVisible();
    expect(
      screen.queryByRole('button', { name: /generate upload token/i }),
    ).not.toBeInTheDocument();
    component.onCreateToken();

    expect(workPackageService.createWorkPackage).not.toHaveBeenCalled();
  });

  it('should not create token if IVA is unverified', async () => {
    await enterValidPubkey();
    ivaService.ivasSignal.set([
      {
        id: 'iva-123',
        type: IvaType.Phone,
        value: '+49123456789',
        changed: '2026-01-01T00:00:00Z',
        state: IvaState.Unverified,
      },
    ]);
    await result.fixture.whenStable();

    expect(screen.getByText('Unverified IVA:')).toBeVisible();
    expect(
      screen.queryByRole('button', { name: /generate upload token/i }),
    ).not.toBeInTheDocument();
    component.onCreateToken();

    expect(workPackageService.createWorkPackage).not.toHaveBeenCalled();
  });

  it('should create upload work package with correct request data', async () => {
    await enterValidPubkey();

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
      type: 'upload',
      research_data_upload_box_id: 'box-123',
      user_public_crypt4gh_key: expect.any(String),
    });
  });

  it('should display upload token on successful creation', async () => {
    await enterValidPubkey();

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

    // Verify token is displayed
    expect(screen.getByText('wp-123:test-token-456')).toBeVisible();
  });

  it('should display error message on token creation failure', async () => {
    await enterValidPubkey();

    const error = new Error('Network error');
    (
      workPackageService.createWorkPackage as ReturnType<typeof vitest.fn>
    ).mockReturnValue(throwError(() => error));

    await userEvent.click(generateButton());
    await result.fixture.whenStable();

    expect(screen.getByText(/could not be created/)).toBeVisible();
    expect(notificationService.showError).toHaveBeenCalled();
  });

  it('should clear token state from view on reset', async () => {
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
});
