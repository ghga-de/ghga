/**
 * Tests for Upload Box Edit Details Dialog component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { NotificationService } from '@app/shared/services/notification';
import { ResearchDataUploadBox, UploadBoxState } from '@app/upload/models/box';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { of, throwError } from 'rxjs';
import { UploadBoxEditDetailsDialogComponent } from './upload-box-edit-details-dialog';

const mockDialogRef = { close: vitest.fn() };
const mockNotificationService = { showError: vitest.fn() };

const TIB = 1_099_511_627_776;

const mockBox: ResearchDataUploadBox = {
  id: 'box-1',
  version: 3,
  title: 'My Box',
  description: 'My description',
  storage_alias: 'TUE01',
  max_size: 4 * TIB,
  state: UploadBoxState.open,
  last_changed: '2026-01-01T00:00:00Z',
  changed_by: 'user-1',
  file_count: 2,
  size: 2 * TIB, // 2 TiB already used
};

/**
 * Minimal mock of UploadBoxService for edit dialog tests.
 */
class MockUploadBoxService {
  updateUploadBox = vitest.fn();
}

/**
 * Configure the testing module and create the component for a given box.
 * @param box - the box passed to the dialog via MAT_DIALOG_DATA
 * @returns the created component fixture and the mocked service
 */
async function createComponent(box: ResearchDataUploadBox = mockBox): Promise<{
  fixture: ComponentFixture<UploadBoxEditDetailsDialogComponent>;
  service: MockUploadBoxService;
}> {
  await TestBed.configureTestingModule({
    imports: [UploadBoxEditDetailsDialogComponent],
    providers: [
      { provide: MatDialogRef, useValue: mockDialogRef },
      { provide: MAT_DIALOG_DATA, useValue: { ...box } },
      { provide: UploadBoxService, useClass: MockUploadBoxService },
      { provide: NotificationService, useValue: mockNotificationService },
    ],
  }).compileComponents();

  const service = TestBed.inject(UploadBoxService) as unknown as MockUploadBoxService;
  const fixture = TestBed.createComponent(UploadBoxEditDetailsDialogComponent);
  fixture.detectChanges();
  return { fixture, service };
}

describe('UploadBoxEditDetailsDialogComponent', () => {
  beforeEach(() => {
    mockDialogRef.close.mockReset();
    mockNotificationService.showError.mockReset();
  });

  it('should create', async () => {
    const { fixture } = await createComponent();
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should show dialog title and action buttons', async () => {
    await createComponent();
    expect(screen.getByText(/edit upload box details/i)).toBeVisible();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeVisible();
    expect(screen.getByRole('button', { name: /^ok$/i })).toBeVisible();
  });

  it('should prefill the form with the current box details', async () => {
    await createComponent();
    expect(screen.getByRole('textbox', { name: 'Title' })).toHaveValue('My Box');
    expect(screen.getByRole('textbox', { name: 'Description' })).toHaveValue(
      'My description',
    );
    expect(screen.getByRole('spinbutton', { name: 'Size limit (in TiB)' })).toHaveValue(
      4,
    );
  });

  it('should not show the storage location field', async () => {
    await createComponent();
    expect(screen.queryByText(/storage location/i)).toBeNull();
  });

  it('should disable OK while nothing has changed', async () => {
    await createComponent();
    expect(screen.getByRole('button', { name: /^ok$/i })).toBeDisabled();
  });

  it('should keep OK disabled when the title is cleared', async () => {
    await createComponent();
    await userEvent.clear(screen.getByRole('textbox', { name: 'Title' }));
    expect(screen.getByRole('button', { name: /^ok$/i })).toBeDisabled();
  });

  it('should show an error and disable OK when size is below the used size', async () => {
    const { fixture } = await createComponent();
    const sizeInput = screen.getByRole('spinbutton', {
      name: 'Size limit (in TiB)',
    });
    await userEvent.clear(sizeInput);
    await userEvent.type(sizeInput, '1'); // below the 2 TiB already used
    fixture.detectChanges();

    expect(
      screen.getByText(/cannot be smaller than the currently used/i),
    ).toBeVisible();
    expect(screen.getByRole('button', { name: /^ok$/i })).toBeDisabled();
  });

  it('should close without result on cancel', async () => {
    const { fixture } = await createComponent();
    fixture.componentInstance.onCancel();
    expect(mockDialogRef.close).toHaveBeenCalledWith(undefined);
  });

  it('should send only the changed fields and close with box id on success', async () => {
    const { service } = await createComponent();
    service.updateUploadBox.mockReturnValue(of(undefined));

    const titleInput = screen.getByRole('textbox', { name: 'Title' });
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, '  Updated Box  ');
    // description and size stay unchanged and must be excluded from the patch
    await userEvent.click(screen.getByRole('button', { name: /^ok$/i }));

    expect(service.updateUploadBox).toHaveBeenCalledWith('box-1', {
      version: 3,
      title: 'Updated Box',
    });
    expect(mockDialogRef.close).toHaveBeenCalledWith('box-1');
    expect(mockNotificationService.showError).not.toHaveBeenCalled();
  });

  it('should include a changed size limit in the patch', async () => {
    const { service } = await createComponent();
    service.updateUploadBox.mockReturnValue(of(undefined));

    const sizeInput = screen.getByRole('spinbutton', {
      name: 'Size limit (in TiB)',
    });
    await userEvent.clear(sizeInput);
    await userEvent.type(sizeInput, '5');
    await userEvent.click(screen.getByRole('button', { name: /^ok$/i }));

    expect(service.updateUploadBox).toHaveBeenCalledWith('box-1', {
      version: 3,
      max_size: 5 * TIB,
    });
  });

  it('should hide the size limit and exclude it for archived boxes', async () => {
    const { service } = await createComponent({
      ...mockBox,
      state: UploadBoxState.archived,
    });
    service.updateUploadBox.mockReturnValue(of(undefined));

    expect(
      screen.queryByRole('spinbutton', { name: 'Size limit (in TiB)' }),
    ).toBeNull();

    const titleInput = screen.getByRole('textbox', { name: 'Title' });
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, 'Fixed Typo');
    await userEvent.click(screen.getByRole('button', { name: /^ok$/i }));

    expect(service.updateUploadBox).toHaveBeenCalledWith('box-1', {
      version: 3,
      title: 'Fixed Typo',
    });
  });

  it.each([
    [401, 'You are not authenticated. Please log in again.'],
    [403, 'You are not authorized to update this upload box.'],
    [404, 'The upload box could not be found. It may have been deleted.'],
    [
      409,
      'The upload box was changed in the meantime or a requirement was not met. Please reload the page and try again.',
    ],
    [422, 'The submitted values are invalid. Please check your input.'],
  ])('should show a specific message for a %i error', async (status, message) => {
    const { fixture, service } = await createComponent();
    service.updateUploadBox.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status, statusText: 'Error' })),
    );

    const titleInput = screen.getByRole('textbox', { name: 'Title' });
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, 'Changed');
    await userEvent.click(screen.getByRole('button', { name: /^ok$/i }));
    fixture.detectChanges();

    expect(mockDialogRef.close).not.toHaveBeenCalled();
    expect(mockNotificationService.showError).toHaveBeenCalledWith(message);
    expect(screen.getByText(message)).toBeVisible();
  });

  it.each(['An Upload Box with this title already exists.', 'duplicate title'])(
    'should show a duplicate-title message for a 409 with "%s"',
    async (detail) => {
      const { fixture, service } = await createComponent();
      service.updateUploadBox.mockReturnValue(
        throwError(() => new HttpErrorResponse({ status: 409, error: { detail } })),
      );

      const titleInput = screen.getByRole('textbox', { name: 'Title' });
      await userEvent.clear(titleInput);
      await userEvent.type(titleInput, 'Changed');
      await userEvent.click(screen.getByRole('button', { name: /^ok$/i }));
      fixture.detectChanges();

      expect(mockNotificationService.showError).toHaveBeenCalledWith(
        'An Upload Box with the same title already exists.',
      );
      expect(
        screen.getByText('An Upload Box with the same title already exists.'),
      ).toBeVisible();
    },
  );

  it('should show a generic message for an unexpected error', async () => {
    const { fixture, service } = await createComponent();
    service.updateUploadBox.mockReturnValue(throwError(() => new Error('boom')));

    const titleInput = screen.getByRole('textbox', { name: 'Title' });
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, 'Changed');
    await userEvent.click(screen.getByRole('button', { name: /^ok$/i }));
    fixture.detectChanges();

    expect(mockNotificationService.showError).toHaveBeenCalledWith(
      'Upload Box could not be updated. Please try again.',
    );
  });
});
