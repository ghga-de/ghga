/**
 * Tests for Upload Box Creation Dialog component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef } from '@angular/material/dialog';
import { NotificationService } from '@app/shared/services/notification';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { screen } from '@testing-library/angular';
import { of, throwError } from 'rxjs';
import { UploadBoxCreationDialogComponent } from './upload-box-creation-dialog';

const mockDialogRef = { close: vitest.fn() };
const mockNotificationService = { showError: vitest.fn() };

/**
 * Minimal mock of UploadBoxService for creation dialog tests.
 */
class MockUploadBoxService {
  #locationOptions = signal([
    { value: 'TUE01', label: 'Tuebingen 1' },
    { value: 'HD02', label: 'Heidelberg 2' },
  ]);

  uploadBoxLocationOptions = this.#locationOptions.asReadonly();
  createUploadBox = vitest.fn();
}

describe('UploadBoxCreationDialogComponent', () => {
  let component: UploadBoxCreationDialogComponent;
  let fixture: ComponentFixture<UploadBoxCreationDialogComponent>;
  let uploadBoxService: MockUploadBoxService;

  beforeEach(async () => {
    mockDialogRef.close.mockReset();
    mockNotificationService.showError.mockReset();

    await TestBed.configureTestingModule({
      imports: [UploadBoxCreationDialogComponent],
      providers: [
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: UploadBoxService, useClass: MockUploadBoxService },
        { provide: NotificationService, useValue: mockNotificationService },
      ],
    }).compileComponents();

    uploadBoxService = TestBed.inject(
      UploadBoxService,
    ) as unknown as MockUploadBoxService;
    fixture = TestBed.createComponent(UploadBoxCreationDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show dialog title and action buttons', () => {
    expect(screen.getByText(/creeate a new upload box/i)).toBeVisible();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeVisible();
    expect(screen.getByRole('button', { name: /^ok$/i })).toBeVisible();
  });

  it('should disable OK while form is invalid', () => {
    expect(screen.getByRole('button', { name: /^ok$/i })).toBeDisabled();
  });

  it('should enable OK with multiline description when all fields are set', () => {
    component.form.setValue({
      title: 'New Box',
      description: 'First line\nSecond line',
      storage_alias: 'TUE01',
    });
    fixture.detectChanges();

    expect(component.form.valid).toBe(true);
    expect(screen.getByRole('button', { name: /^ok$/i })).toBeEnabled();
  });

  it('should close without result on cancel', () => {
    component.onCancel();
    expect(mockDialogRef.close).toHaveBeenCalledWith(undefined);
  });

  it('should call createUploadBox and close with created id on success', () => {
    uploadBoxService.createUploadBox.mockReturnValue(of('new-box-id'));

    component.form.setValue({
      title: '  New Box  ',
      description: '  Description  ',
      storage_alias: 'TUE01',
    });
    component.onSubmit();

    expect(uploadBoxService.createUploadBox).toHaveBeenCalledWith({
      title: 'New Box',
      description: 'Description',
      storage_alias: 'TUE01',
    });
    expect(mockDialogRef.close).toHaveBeenCalledWith('new-box-id');
    expect(mockNotificationService.showError).not.toHaveBeenCalled();
  });

  it('should show an error and keep dialog open when create fails', () => {
    uploadBoxService.createUploadBox.mockReturnValue(
      throwError(() => new Error('create failed')),
    );

    component.form.setValue({
      title: 'New Box',
      description: 'Description',
      storage_alias: 'HD02',
    });
    component.onSubmit();
    fixture.detectChanges();

    expect(mockDialogRef.close).not.toHaveBeenCalled();
    expect(mockNotificationService.showError).toHaveBeenCalledWith(
      'Upload Box could not be created. Please try again.',
    );
    expect(screen.getByText(/error creating the upload box/i)).toBeVisible();
  });
});
