/**
 * Tests for Upload Box Creation Dialog component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef } from '@angular/material/dialog';
import { NotificationService } from '@app/shared/services/notification';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
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
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show dialog title and action buttons', () => {
    expect(screen.getByText(/create a new upload box/i)).toBeVisible();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeVisible();
    expect(screen.getByRole('button', { name: /^ok$/i })).toBeVisible();
  });

  it('should disable OK while form is invalid', () => {
    expect(screen.getByRole('button', { name: /^ok$/i })).toBeDisabled();
  });

  it('should configure size limit step to 1 TiB', () => {
    const sizeInput = screen.getByRole('spinbutton', {
      name: 'Size limit (in TiB)',
    });

    expect(sizeInput).toHaveAttribute('step', '1');
  });

  it('should enable OK with multiline description when all fields are set', async () => {
    const titleInput = screen.getByRole('textbox', { name: 'Title' });
    const descriptionInput = screen.getByRole('textbox', {
      name: 'Description',
    });
    const locationSelect = screen.getByRole('combobox', {
      name: 'Storage location',
    });
    const sizeInput = screen.getByRole('spinbutton', {
      name: 'Size limit (in TiB)',
    });

    await userEvent.type(titleInput, 'New Box');
    await userEvent.type(descriptionInput, 'First line{enter}Second line');
    await userEvent.click(locationSelect);
    await userEvent.click(await screen.findByRole('option', { name: 'Tuebingen 1' }));
    await userEvent.type(sizeInput, '2.5');
    fixture.detectChanges();

    expect(screen.getByRole('button', { name: /^ok$/i })).toBeEnabled();
  });

  it('should keep OK disabled when size limit is missing', async () => {
    const titleInput = screen.getByRole('textbox', { name: 'Title' });
    const descriptionInput = screen.getByRole('textbox', {
      name: 'Description',
    });
    const locationSelect = screen.getByRole('combobox', {
      name: 'Storage location',
    });

    await userEvent.type(titleInput, 'New Box');
    await userEvent.type(descriptionInput, 'Description');
    await userEvent.click(locationSelect);
    await userEvent.click(await screen.findByRole('option', { name: 'Tuebingen 1' }));
    fixture.detectChanges();

    expect(screen.getByRole('button', { name: /^ok$/i })).toBeDisabled();
  });

  it('should keep OK disabled when size limit is below 1 GiB', async () => {
    const titleInput = screen.getByRole('textbox', { name: 'Title' });
    const descriptionInput = screen.getByRole('textbox', {
      name: 'Description',
    });
    const locationSelect = screen.getByRole('combobox', {
      name: 'Storage location',
    });
    const sizeInput = screen.getByRole('spinbutton', {
      name: 'Size limit (in TiB)',
    });

    await userEvent.type(titleInput, 'New Box');
    await userEvent.type(descriptionInput, 'Description');
    await userEvent.click(locationSelect);
    await userEvent.click(await screen.findByRole('option', { name: 'Tuebingen 1' }));
    await userEvent.type(sizeInput, '0.0009');
    fixture.detectChanges();

    expect(screen.getByRole('button', { name: /^ok$/i })).toBeDisabled();
  });

  it('should keep OK disabled when size limit exceeds 1,000,000 TiB', async () => {
    const titleInput = screen.getByRole('textbox', { name: 'Title' });
    const descriptionInput = screen.getByRole('textbox', {
      name: 'Description',
    });
    const locationSelect = screen.getByRole('combobox', {
      name: 'Storage location',
    });
    const sizeInput = screen.getByRole('spinbutton', {
      name: 'Size limit (in TiB)',
    });

    await userEvent.type(titleInput, 'New Box');
    await userEvent.type(descriptionInput, 'Description');
    await userEvent.click(locationSelect);
    await userEvent.click(await screen.findByRole('option', { name: 'Tuebingen 1' }));
    await userEvent.type(sizeInput, '1000000.0001');
    fixture.detectChanges();

    expect(screen.getByRole('button', { name: /^ok$/i })).toBeDisabled();
  });

  it('should close without result on cancel', () => {
    component.onCancel();
    expect(mockDialogRef.close).toHaveBeenCalledWith(undefined);
  });

  it('should call createUploadBox and close with created id on success', async () => {
    uploadBoxService.createUploadBox.mockReturnValue(of('new-box-id'));

    const titleInput = screen.getByRole('textbox', { name: 'Title' });
    const descriptionInput = screen.getByRole('textbox', {
      name: 'Description',
    });
    const locationSelect = screen.getByRole('combobox', {
      name: 'Storage location',
    });
    const sizeInput = screen.getByRole('spinbutton', {
      name: 'Size limit (in TiB)',
    });

    await userEvent.type(titleInput, '  New Box  ');
    await userEvent.type(descriptionInput, '  Description  ');
    await userEvent.click(locationSelect);
    await userEvent.click(await screen.findByRole('option', { name: 'Tuebingen 1' }));
    await userEvent.type(sizeInput, '1.25');
    await userEvent.click(screen.getByRole('button', { name: /^ok$/i }));

    expect(uploadBoxService.createUploadBox).toHaveBeenCalledWith({
      title: 'New Box',
      description: 'Description',
      storage_alias: 'TUE01',
      max_size: 1374389534720,
    });
    expect(mockDialogRef.close).toHaveBeenCalledWith('new-box-id');
    expect(mockNotificationService.showError).not.toHaveBeenCalled();
  });

  it('should show an error and keep dialog open when create fails', async () => {
    uploadBoxService.createUploadBox.mockReturnValue(
      throwError(() => new Error('create failed')),
    );

    const titleInput = screen.getByRole('textbox', { name: 'Title' });
    const descriptionInput = screen.getByRole('textbox', {
      name: 'Description',
    });
    const locationSelect = screen.getByRole('combobox', {
      name: 'Storage location',
    });
    const sizeInput = screen.getByRole('spinbutton', {
      name: 'Size limit (in TiB)',
    });

    await userEvent.type(titleInput, 'New Box');
    await userEvent.type(descriptionInput, 'Description');
    await userEvent.click(locationSelect);
    await userEvent.click(await screen.findByRole('option', { name: 'Heidelberg 2' }));
    await userEvent.type(sizeInput, '0.5');
    await userEvent.click(screen.getByRole('button', { name: /^ok$/i }));
    fixture.detectChanges();

    expect(mockDialogRef.close).not.toHaveBeenCalled();
    expect(mockNotificationService.showError).toHaveBeenCalledWith(
      'Upload Box could not be created. Please try again.',
    );
    expect(
      screen.getByText('Upload Box could not be created. Please try again.'),
    ).toBeVisible();
  });

  it('should show a title-conflict error when create fails with a 409', async () => {
    uploadBoxService.createUploadBox.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 409, statusText: 'Conflict' })),
    );

    const titleInput = screen.getByRole('textbox', { name: 'Title' });
    const descriptionInput = screen.getByRole('textbox', {
      name: 'Description',
    });
    const locationSelect = screen.getByRole('combobox', {
      name: 'Storage location',
    });
    const sizeInput = screen.getByRole('spinbutton', {
      name: 'Size limit (in TiB)',
    });

    await userEvent.type(titleInput, 'Existing Box');
    await userEvent.type(descriptionInput, 'Description');
    await userEvent.click(locationSelect);
    await userEvent.click(await screen.findByRole('option', { name: 'Heidelberg 2' }));
    await userEvent.type(sizeInput, '0.5');
    await userEvent.click(screen.getByRole('button', { name: /^ok$/i }));
    fixture.detectChanges();

    expect(mockDialogRef.close).not.toHaveBeenCalled();
    expect(mockNotificationService.showError).toHaveBeenCalledWith(
      'An Upload Box with the same title already exists.',
    );
    expect(
      screen.getByText('An Upload Box with the same title already exists.'),
    ).toBeVisible();
  });
});
