/**
 * Test the download work package dialog component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Clipboard } from '@angular/cdk/clipboard';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import {
  AccessGrantStatus,
  AccessGrantWithIva,
} from '@app/access-requests/models/access-requests';
import { IvaState, IvaType } from '@app/ivas/models/iva';
import { NotificationService } from '@app/shared/services/notification';
import { DatasetWithExpiration } from '@app/work-packages/models/dataset';
import { WorkPackageService } from '@app/work-packages/services/work-package';
import { of, throwError } from 'rxjs';
import { DownloadWorkPackageDialogComponent } from './download-work-package-dialog';

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

describe('DownloadWorkPackageDialogComponent', () => {
  let component: DownloadWorkPackageDialogComponent;
  let fixture: ComponentFixture<DownloadWorkPackageDialogComponent>;
  let workPackageService: WorkPackageService;
  let notificationService: NotificationService;
  let clipboard: Clipboard;

  const dialogRef = {
    close: vitest.fn(),
  };

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

    await TestBed.configureTestingModule({
      imports: [DownloadWorkPackageDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: TEST_GRANT },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: WorkPackageService, useValue: wpServiceMock },
        { provide: NotificationService, useValue: notifyMock },
        { provide: Clipboard, useValue: clipboardMock },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DownloadWorkPackageDialogComponent);
    component = fixture.componentInstance;
    workPackageService = TestBed.inject(WorkPackageService);
    notificationService = TestBed.inject(NotificationService);
    clipboard = TestBed.inject(Clipboard);
    vitest.clearAllMocks();
    fixture.detectChanges();
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('initialization', () => {
    it('should load grant data', () => {
      expect(component['grant']).toBe(TEST_GRANT);
      expect(component['iva']).toBe(TEST_GRANT.iva);
    });

    it('should load dataset from service', () => {
      const dataset = component['dataset']();
      expect(dataset).toBeDefined();
      expect(dataset?.id).toBe('GHGAD12345678901234');
    });

    it('should initialize form with empty values', () => {
      expect(component['model']().files).toBe('');
      expect(component['model']().pubkey).toBe('');
    });

    it('should have form invalid initially', () => {
      expect(component['downloadForm']().valid()).toBe(false);
    });
  });

  describe('onClose', () => {
    it('should close dialog', () => {
      component.onClose();
      expect(dialogRef.close).toHaveBeenCalled();
    });
  });

  describe('onCreateToken', () => {
    beforeEach(() => {
      // Set up valid form data
      component['model'].set({
        files: 'file1, file2',
        pubkey: 'MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=',
      });
      fixture.detectChanges();
    });

    it('should not create token if form is invalid', () => {
      component['model'].set({ files: '', pubkey: '' });
      fixture.detectChanges();

      component.onCreateToken();

      expect(workPackageService.createWorkPackage).not.toHaveBeenCalled();
    });

    it('should create work package with correct data', () => {
      (
        workPackageService.createWorkPackage as ReturnType<typeof vitest.fn>
      ).mockReturnValue(
        of({
          id: 'wp-123',
          token: 'test-token-456',
          expires: '2026-02-01T00:00:00Z',
        }),
      );

      component.onCreateToken();

      expect(workPackageService.createWorkPackage).toHaveBeenCalledWith({
        dataset_id: 'GHGAD12345678901234',
        file_ids: ['file1', 'file2'],
        type: 'download',
        user_public_crypt4gh_key: expect.any(String),
      });
    });

    it('should create work package with null file_ids when files input is empty', () => {
      component['model'].set({
        files: '',
        pubkey: 'MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=',
      });
      fixture.detectChanges();

      (
        workPackageService.createWorkPackage as ReturnType<typeof vitest.fn>
      ).mockReturnValue(
        of({
          id: 'wp-123',
          token: 'test-token-456',
          expires: '2026-02-01T00:00:00Z',
        }),
      );

      component.onCreateToken();

      expect(workPackageService.createWorkPackage).toHaveBeenCalledWith(
        expect.objectContaining({
          file_ids: null,
        }),
      );
    });

    it('should set loading state during token creation', () => {
      (
        workPackageService.createWorkPackage as ReturnType<typeof vitest.fn>
      ).mockReturnValue(
        of({
          id: 'wp-123',
          token: 'test-token-456',
          expires: '2026-02-01T00:00:00Z',
        }),
      );

      expect(component.tokenIsLoading()).toBe(false);
      component.onCreateToken();
      expect(component.tokenIsLoading()).toBe(false); // Already completed in sync test
    });

    it('should set token on successful creation', () => {
      (
        workPackageService.createWorkPackage as ReturnType<typeof vitest.fn>
      ).mockReturnValue(
        of({
          id: 'wp-123',
          token: 'test-token-456',
          expires: '2026-02-01T00:00:00Z',
        }),
      );

      component.onCreateToken();

      expect(component.token()).toBe('wp-123:test-token-456');
      expect(component.tokenExpiration()).toBe('2026-02-01T00:00:00Z');
      expect(component.tokenIsLoading()).toBe(false);
    });

    it('should handle error during token creation', () => {
      const error = new Error('Network error');
      (
        workPackageService.createWorkPackage as ReturnType<typeof vitest.fn>
      ).mockReturnValue(throwError(() => error));

      component.onCreateToken();

      expect(component.tokenError()).toContain('could not be created');
      expect(component.tokenIsLoading()).toBe(false);
      expect(notificationService.showError).toHaveBeenCalled();
    });

    it('should clear previous token state when creating new token', () => {
      component.token.set('old-token');
      component.tokenError.set('old-error');

      (
        workPackageService.createWorkPackage as ReturnType<typeof vitest.fn>
      ).mockReturnValue(
        of({
          id: 'wp-123',
          token: 'test-token-456',
          expires: '2026-02-01T00:00:00Z',
        }),
      );

      component.onCreateToken();

      expect(component.token()).toBe('wp-123:test-token-456');
      expect(component.tokenError()).toBe('');
    });
  });

  describe('resetToken', () => {
    it('should clear token and error state', () => {
      component.token.set('test-token');
      component.tokenError.set('test-error');
      component.tokenIsLoading.set(true);

      component.resetToken();

      expect(component.token()).toBe('');
      expect(component.tokenError()).toBe('');
      expect(component.tokenIsLoading()).toBe(false);
    });
  });

  describe('copyToken', () => {
    it('should copy token to clipboard and show notification', () => {
      component.token.set('test-token-123');

      component.copyToken();

      expect(clipboard.copy).toHaveBeenCalledWith('test-token-123');
      expect(notificationService.showSuccess).toHaveBeenCalledWith(
        'The token has been copied to the clipboard.',
      );
    });

    it('should not copy if token is empty', () => {
      component.token.set('');

      component.copyToken();

      expect(clipboard.copy).not.toHaveBeenCalled();
      expect(notificationService.showSuccess).not.toHaveBeenCalled();
    });
  });

  describe('form validation', () => {
    it('should be invalid with empty pubkey', () => {
      component['model'].set({ files: 'file1', pubkey: '' });
      fixture.detectChanges();

      expect(component['downloadForm']().valid()).toBe(false);
    });

    it('should be valid with valid pubkey', () => {
      component['model'].set({
        files: 'file1',
        pubkey: 'MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=',
      });
      fixture.detectChanges();

      expect(component['downloadForm']().valid()).toBe(true);
    });
  });
});
