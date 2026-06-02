/**
 * Tests for the UserUploadBoxesListComponent.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { ConfirmationService } from '@app/shared/services/confirmation';
import { NotificationService } from '@app/shared/services/notification';
import { ResearchDataUploadBox, UploadBoxState } from '@app/upload/models/box';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { UploadWorkPackageDialogComponent } from '@app/work-packages/features/upload-work-package-dialog/upload-work-package-dialog';
import { screen } from '@testing-library/angular';
import { of, throwError } from 'rxjs';
import { UserUploadBoxesListComponent } from './user-upload-boxes-list';

// --- Test fixtures ---

const openBox: ResearchDataUploadBox = {
  id: 'box-001',
  title: 'Test Upload Box',
  description: 'A test upload box',
  state: UploadBoxState.open,
  version: 1,
  last_changed: '2026-06-02T13:41:13.302Z',
  changed_by: 'John Doe',
  file_count: 0,
  size: 0,
  max_size: 100,
  storage_alias: 'box-001',
};

// --- Mocks ---

/**
 * Mock of UploadBoxService for user upload boxes list tests.
 */
class MockUploadBoxService {
  #boxes = signal<ResearchDataUploadBox[]>([]);
  #error = signal<Error | undefined>(undefined);
  #loading = signal<boolean>(false);

  boxRetrievalResults = {
    value: this.#boxes,
    error: this.#error,
    isLoading: this.#loading,
    reload: vitest.fn(),
  };

  uploadBoxes = () => {
    if (this.boxRetrievalResults.error()) return [];
    return this.boxRetrievalResults.value();
  };

  updateUploadBox = vitest.fn();
  loadAllUploadBoxes = () => undefined;

  /**
   * Test helper: set the loaded boxes.
   * @param boxes - boxes to expose through the mocked boxRetrievalResults resource
   */
  setBoxes(boxes: ResearchDataUploadBox[]): void {
    this.#boxes.set(boxes);
  }

  /**
   * Test helper: set an error state.
   * @param error - error to expose through the mocked boxRetrievalResults resource
   */
  setError(error: Error): void {
    this.#error.set(error);
  }

  /**
   * Test helper: set the loading state.
   * @param loading - whether mocked boxRetrievalResults should appear loading
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

describe('UserUploadBoxesListComponent', () => {
  let component: UserUploadBoxesListComponent;
  let fixture: ComponentFixture<UserUploadBoxesListComponent>;
  let uploadBoxService: MockUploadBoxService;

  beforeEach(async () => {
    mockConfirmationService.confirm.mockReset();
    mockNotificationService.showInfo.mockReset();
    mockNotificationService.showSuccess.mockReset();
    mockNotificationService.showError.mockReset();
    mockDialog.open.mockReset();

    await TestBed.configureTestingModule({
      imports: [UserUploadBoxesListComponent],
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
    fixture = TestBed.createComponent(UserUploadBoxesListComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });
  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show a loading indicator while boxes are loading', async () => {
    uploadBoxService.setLoading(true);
    fixture.detectChanges();
    expect(document.querySelector('[role="loader"]')).toBeTruthy();
  });

  it('should show an error message when box loading fails', async () => {
    uploadBoxService.setError(new Error('backend error'));
    fixture.detectChanges();
    expect(screen.getByText(/error retrieving.*upload boxes/i)).toBeVisible();
  });

  it('should show an empty message when no open box exist', async () => {
    uploadBoxService.setBoxes([]);
    fixture.detectChanges();
    expect(screen.getByText(/no.*open Research Data Upload Boxes/i)).toBeVisible();
  });

  it('should render the box title for an open box', async () => {
    uploadBoxService.setBoxes([openBox]);
    fixture.detectChanges();
    expect(screen.getByText('Test Upload Box')).toBeVisible();
  });

  it('should not render boxes whose box state is not open', async () => {
    const lockedBox: ResearchDataUploadBox = {
      ...openBox,
      id: 'box-locked',
      state: UploadBoxState.locked,
      title: 'Locked Box',
    };
    uploadBoxService.setBoxes([openBox, lockedBox]);
    fixture.detectChanges();
    expect(screen.getByText('Test Upload Box')).toBeVisible();
    expect(screen.queryByText('Locked Box')).not.toBeInTheDocument();
  });

  it('should open upload token dialog when Create token is clicked', async () => {
    uploadBoxService.setBoxes([openBox]);
    fixture.detectChanges();
    const btn = screen.getByRole('button', { name: /create an upload token/i });
    btn.click();
    expect(mockDialog.open).toHaveBeenCalledWith(
      UploadWorkPackageDialogComponent,
      expect.objectContaining({
        data: openBox,
        width: '64rem',
        maxWidth: '96vw',
      }),
    );
  });

  it('should open a confirmation dialog when Submit is clicked', async () => {
    mockConfirmationService.confirm.mockImplementation(() => undefined);
    uploadBoxService.setBoxes([openBox]);
    fixture.detectChanges();
    screen.getByRole('button', { name: /submit this upload box/i }).click();
    expect(mockConfirmationService.confirm).toHaveBeenCalled();
  });

  describe('submitBox - confirmed, success', () => {
    beforeEach(async () => {
      mockConfirmationService.confirm.mockImplementation(({ callback }) =>
        callback(true),
      );
      uploadBoxService.updateUploadBox.mockReturnValue(of(undefined));
      uploadBoxService.setBoxes([openBox]);
      fixture.detectChanges();
      screen.getByRole('button', { name: /submit this upload box/i }).click();
      await fixture.whenStable();
    });

    it('should call updateUploadBox with box id, version, and locked state', () => {
      expect(uploadBoxService.updateUploadBox).toHaveBeenCalledWith('box-001', {
        version: 1,
        state: UploadBoxState.locked,
      });
    });

    it('should show a success notification', () => {
      expect(mockNotificationService.showSuccess).toHaveBeenCalledWith(
        'The upload box has been submitted successfully.',
      );
    });

    it('should not force reload user boxes after success', () => {
      expect(uploadBoxService.boxRetrievalResults.reload).not.toHaveBeenCalled();
    });
  });

  describe('submitBox - confirmed, error', () => {
    beforeEach(async () => {
      mockConfirmationService.confirm.mockImplementation(({ callback }) =>
        callback(true),
      );
      uploadBoxService.updateUploadBox.mockReturnValue(
        throwError(() => new Error('Server error')),
      );
      uploadBoxService.setBoxes([openBox]);
      fixture.detectChanges();
      screen.getByRole('button', { name: /submit this upload box/i }).click();
      await fixture.whenStable();
    });

    it('should show an error notification', () => {
      expect(mockNotificationService.showError).toHaveBeenCalledWith(
        'Failed to submit the upload box. Please try again.',
      );
    });

    it('should not reload user boxes on error', () => {
      expect(uploadBoxService.boxRetrievalResults.reload).not.toHaveBeenCalled();
    });
  });

  describe('submitBox - cancelled', () => {
    beforeEach(async () => {
      mockConfirmationService.confirm.mockImplementation(({ callback }) =>
        callback(false),
      );
      uploadBoxService.setBoxes([openBox]);
      fixture.detectChanges();
      screen.getByRole('button', { name: /submit this upload box/i }).click();
      await fixture.whenStable();
    });

    it('should not call updateUploadBox', () => {
      expect(uploadBoxService.updateUploadBox).not.toHaveBeenCalled();
    });

    it('should not show any notification', () => {
      expect(mockNotificationService.showSuccess).not.toHaveBeenCalled();
      expect(mockNotificationService.showError).not.toHaveBeenCalled();
    });
  });
});
