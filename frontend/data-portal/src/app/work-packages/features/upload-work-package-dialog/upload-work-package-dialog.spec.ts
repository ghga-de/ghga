/**
 * Test the upload work package dialog component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Clipboard } from '@angular/cdk/clipboard';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { NotificationService } from '@app/shared/services/notification';
import { ResearchDataUploadBox, UploadBoxState } from '@app/upload/models/box';
import { WorkPackageService } from '@app/work-packages/services/work-package';
import { of, throwError } from 'rxjs';
import { UploadWorkPackageDialogComponent } from './upload-work-package-dialog';

const TEST_BOX: ResearchDataUploadBox = {
  id: 'box-123',
  last_changed: '2026-01-01T00:00:00Z',
  title: 'Test Upload Box',
  description: 'A test upload box for unit testing',
  state: UploadBoxState.open,
  version: 1,
  changed_by: 'John Doe',
  file_count: 0,
  size: 0,
  max_size: 100,
  storage_alias: 'box-001',
};

describe('UploadWorkPackageDialogComponent', () => {
  let component: UploadWorkPackageDialogComponent;
  let fixture: ComponentFixture<UploadWorkPackageDialogComponent>;
  let workPackageService: WorkPackageService;
  let notificationService: NotificationService;
  let clipboard: Clipboard;

  const dialogRef = {
    close: vitest.fn(),
  };

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

    await TestBed.configureTestingModule({
      imports: [UploadWorkPackageDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: TEST_BOX },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: WorkPackageService, useValue: wpServiceMock },
        { provide: NotificationService, useValue: notifyMock },
        { provide: Clipboard, useValue: clipboardMock },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UploadWorkPackageDialogComponent);
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

  it('should initialize with the selected box', () => {
    expect(component['box']).toBe(TEST_BOX);
  });

  it('should close dialog', () => {
    component.onClose();
    expect(dialogRef.close).toHaveBeenCalled();
  });

  it('should not create token if form is invalid', () => {
    component['model'].set({ pubkey: '' });
    fixture.detectChanges();

    component.onCreateToken();

    expect(workPackageService.createWorkPackage).not.toHaveBeenCalled();
  });

  it('should create upload work package with correct request data', () => {
    component['model'].set({
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

    expect(workPackageService.createWorkPackage).toHaveBeenCalledWith({
      type: 'upload',
      research_data_upload_box_id: 'box-123',
      user_public_crypt4gh_key: expect.any(String),
    });
  });

  it('should display upload token on successful creation', () => {
    component['model'].set({
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
    fixture.detectChanges();

    // Verify token is displayed
    const tokenElement = fixture.debugElement.query(By.css('span.text-green-900'));
    expect(tokenElement?.nativeElement.textContent).toContain('wp-123:test-token-456');
  });

  it('should display error message on token creation failure', () => {
    component['model'].set({
      pubkey: 'MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=',
    });
    fixture.detectChanges();

    const error = new Error('Network error');
    (
      workPackageService.createWorkPackage as ReturnType<typeof vitest.fn>
    ).mockReturnValue(throwError(() => error));

    component.onCreateToken();
    fixture.detectChanges();

    const errorElement = fixture.debugElement.query(By.css('.text-red-600'));
    expect(errorElement?.nativeElement.textContent).toContain('could not be created');
    expect(notificationService.showError).toHaveBeenCalled();
  });

  it('should clear token state from view on reset', () => {
    (component as any)['token'].set('test-token');
    (component as any)['tokenError'].set('test-error');
    (component as any)['tokenIsLoading'].set(true);
    fixture.detectChanges();

    component.resetToken();
    fixture.detectChanges();

    // Verify token is no longer displayed
    let tokenElement = fixture.debugElement.query(By.css('span.text-green-900'));
    expect(tokenElement).toBeFalsy();

    // Verify error is no longer displayed
    let errorElement = fixture.debugElement.query(By.css('div.text-red-600'));
    expect(errorElement).toBeFalsy();
  });

  it('should not copy if token is empty', () => {
    (component as any)['token'].set('');
    fixture.detectChanges();

    component.copyToken();

    expect(clipboard.copy).not.toHaveBeenCalled();
    expect(notificationService.showSuccess).not.toHaveBeenCalled();
  });
  it('should copy token to clipboard and show notification', () => {
    (component as any)['token'].set('test-token-123');

    component.copyToken();

    expect(clipboard.copy).toHaveBeenCalledWith('test-token-123');
    expect(notificationService.showSuccess).toHaveBeenCalledWith(
      'The token has been copied to the clipboard.',
    );
  });
});
